"""Offline API checks using a fresh database and mocked external research."""
import importlib
import os
import tempfile
import unittest
from concurrent.futures import ThreadPoolExecutor
from threading import Event
from datetime import datetime, timezone
from backend.google_ads_capabilities import save_currency_constant, load_currency_minimum
from unittest.mock import patch

from fastapi.testclient import TestClient
from auth_helpers import signup_verified


class StrategyJourneyTests(unittest.TestCase):
    def revision_payload(self):
        return dict(business_name='FlowDesk AI', product='AI customer support SaaS software',
                    offer='14-day paid trial', country='Egypt', audience='Small business owners',
                    objective='sales', demand_type='discovery', sales_channel='website',
                    currency='EGP', total_budget=3000, campaign_days=30,
                    price=1000, gross_margin_percent=70, extra_variable_cost_per_order=50,
                    has_website=True, has_tracking=True, has_previous_sales=True)

    @classmethod
    def setUpClass(cls):
        cls.directory = tempfile.TemporaryDirectory(prefix='marketflow-test-')
        previous = os.getcwd()
        try:
            os.chdir(cls.directory.name)
            cls.main = importlib.reload(importlib.import_module('backend.main'))
            cls.main.DATABASE = os.path.join(cls.directory.name, 'marketflow.db')
            cls.main.init_db()
            cls.main.auth.migrate()
        finally:
            os.chdir(previous)

    @classmethod
    def tearDownClass(cls):
        cls.directory.cleanup()

    def test_google_message_analytics_and_currency_snapshot(self):
        with TestClient(self.main.app) as client:
            response = signup_verified(client, self.main, json={
                'name': 'Measurement test', 'email': 'measurement@example.com',
                'password': 'ExamplePassword123!',
            })
            self.assertEqual(response.status_code, 200, response.text)
            uid = response.json()['user']['id']
            db = self.main.get_db()
            # Exercise migration on the old schema, preserving existing data.
            db.execute('ALTER TABLE analytics_daily DROP COLUMN message_leads')
            db.execute('''INSERT INTO analytics_daily
                (user_id, date, provider, messages, created_at, updated_at)
                VALUES (?, ?, 'legacy', 7, ?, ?)''',
                (uid, datetime.now().date().isoformat(), 'test', 'test'))
            db.commit()
            self.main.init_db()
            self.assertEqual(db.execute('SELECT message_leads FROM analytics_daily').fetchone()[0], 0)
            self.main.upsert_analytics_record(db, uid, date=datetime.now().date().isoformat(),
                provider='google', campaign_id='test-campaign', messages=20,
                message_leads=2.5, leads=2.5, conversions=0, revenue=0)
            report = client.get('/api/analytics/overview').json()
            self.assertEqual(report['summary']['messages'], 27)
            self.assertEqual(report['summary']['message_leads'], 2.5)
            self.assertEqual(report['summary']['conversions'], 0)
            self.assertEqual(report['summary']['revenue'], 0)
            self.assertEqual(report['timeline'][-1]['message_leads'], 2.5)
            self.assertEqual(report['top_campaigns'][0]['message_leads'], 2.5)
            save_currency_constant(db, {'code': 'EGP', 'demand_gen_info': {
                'minimum_budget_per_day_micros': '10000000'}}, datetime.now(timezone.utc))
            db.close()
            minimum = load_currency_minimum(self.main.get_db, 'EGP')
            self.assertEqual(minimum.minimum_budget_per_day_micros, 10000000)

    def test_edit_answers_and_rebuild_preserves_original_strategy_and_campaign(self):
        payload = self.revision_payload()
        with TestClient(self.main.app) as owner, TestClient(self.main.app) as other:
            for client, name in [(owner, 'editor'), (other, 'editor-other')]:
                self.assertEqual(signup_verified(client, self.main, json={
                    'name': name, 'email': name + '@example.com', 'password': 'ExamplePassword123!',
                }).status_code, 200)
            sid = owner.post('/api/strategy-agent/start').json()['session_id']
            edit_url = f'/api/strategy-agent/{sid}/answers'
            self.assertEqual(other.put(edit_url, json=payload).status_code, 404)
            self.assertEqual(owner.put(edit_url, json=payload).status_code, 200)
            resumed = owner.get(f'/api/strategy-agent/{sid}/resume').json()
            self.assertEqual(resumed['answers']['total_budget'], 3000)
            with patch('backend.strategy_agent.research_business', return_value={'sources': []}):
                original = owner.post(f'/api/strategy-agent/{sid}/build').json()
            original_id = original['strategy_id']
            campaign = owner.post(f'/api/strategy/{original_id}/accept').json()['campaign']
            self.assertEqual(owner.put(edit_url, json=payload).status_code, 409)
            changed = {**payload, 'objective': 'leads', 'demand_type': 'search', 'total_budget': 30000}
            revised_session = owner.post('/api/strategy-agent/revise', json=changed)
            self.assertEqual(revised_session.status_code, 200, revised_session.text)
            revised_sid = revised_session.json()['session_id']
            with patch('backend.strategy_agent.research_business', return_value={'sources': []}):
                revised = owner.post(f'/api/strategy-agent/{revised_sid}/build').json()
            self.assertNotEqual(original_id, revised['strategy_id'])
            self.assertEqual(revised['strategy']['requested_objective'], 'Leads')
            self.assertEqual(revised['strategy']['budget_plan']['total_budget'], 30000)
            saved = owner.get(f'/api/strategy/{original_id}').json()['strategy']
            self.assertEqual(saved['input']['total_budget'], 3000)
            self.assertEqual(saved['output'], original['strategy'])
            self.assertEqual(saved['campaign_id'], campaign['id'])
            self.assertEqual(other.get(f'/api/strategy/{revised["strategy_id"]}').status_code, 404)

    def test_editor_rejects_invalid_brief_and_building_session(self):
        with TestClient(self.main.app) as client:
            signup_verified(client, self.main, json={'name': 'Invalid edit',
                'email': 'invalid-edit@example.com', 'password': 'ExamplePassword123!'})
            payload = self.revision_payload()
            self.assertEqual(client.post('/api/strategy-agent/revise', json={**payload, 'total_budget': -1}).status_code, 422)
            self.assertEqual(client.post('/api/strategy-agent/revise', json={**payload, 'objective': 'invalid'}).status_code, 400)
            sid = client.post('/api/strategy-agent/revise', json=payload).json()['session_id']
            db = self.main.get_db()
            db.execute("UPDATE strategy_agent_sessions SET status = 'Building' WHERE id = ?", (sid,))
            db.commit()
            db.close()
            self.assertEqual(client.put(f'/api/strategy-agent/{sid}/answers', json=payload).status_code, 409)

    def test_resume_build_review_accept_and_user_isolation(self):
        answers = {
            'business_name': 'FlowDesk',
            'product': 'Customer support software for small businesses',
            'offer': '14 day free trial', 'country': 'Egypt',
            'audience': 'Small business owners', 'objective': 'leads',
            'demand_type': 'search', 'sales_channel': 'website',
            'currency': 'EGP', 'total_budget': 30000, 'campaign_days': 30,
            'price': 1000, 'gross_margin_percent': 70,
            'extra_variable_cost_per_order': 50,
            'lead_to_sale_rate_percent': 10,
            'has_website': True, 'has_tracking': True,
            'has_previous_sales': True, 'has_video_creatives': False,
        }
        with TestClient(self.main.app) as owner, TestClient(self.main.app) as other:
            for client, name in [(owner, 'owner'), (other, 'other')]:
                response = signup_verified(client, self.main, json={
                    'name': name, 'email': name + '@example.com',
                    'password': 'ExamplePassword123!',
                })
                self.assertEqual(response.status_code, 200, response.text)
            response = owner.post('/api/strategy-agent/start')
            self.assertEqual(response.status_code, 200, response.text)
            progress = response.json()
            sid = progress['session_id']
            endpoint = f'/api/strategy-agent/{sid}'
            self.assertEqual(other.get(endpoint + '/resume').status_code, 404)
            self.assertEqual(owner.post(endpoint + '/build').status_code, 400)
            seen = set()
            while progress.get('question'):
                key = progress['question']['key']
                self.assertNotIn(key, seen)
                seen.add(key)
                response = owner.post(endpoint + '/answer', json={'value': answers[key]})
                self.assertEqual(response.status_code, 200, response.text)
                progress = response.json()
                resumed = owner.get(endpoint + '/resume').json()
                if progress.get('question'):
                    self.assertEqual(resumed['question']['key'], progress['question']['key'])
            self.assertTrue(owner.get(endpoint + '/resume').json()['ready_to_build'])
            with patch('backend.strategy_agent.research_business', side_effect=RuntimeError('Temporary research failure')):
                self.assertEqual(owner.post(endpoint + '/build').status_code, 400)
            self.assertTrue(owner.get(endpoint + '/resume').json()['ready_to_build'])
            entered, release = Event(), Event()
            def slow_research(*args):
                entered.set()
                if not release.wait(5):
                    raise RuntimeError('Test research timed out')
                return {'sources': []}
            with patch('backend.strategy_agent.research_business', side_effect=slow_research) as research:
                with ThreadPoolExecutor(max_workers=1) as pool:
                    pending = pool.submit(owner.post, endpoint + '/build')
                    try:
                        self.assertTrue(entered.wait(3))
                        duplicate = owner.post(endpoint + '/build')
                        self.assertEqual(duplicate.status_code, 409, duplicate.text)
                    finally:
                        release.set()
                    response = pending.result(timeout=5)
                self.assertEqual(research.call_count, 1)
            self.assertEqual(response.status_code, 200, response.text)
            built = response.json()
            strategy_id = built['strategy_id']
            self.assertEqual(built['strategy']['agent_review']['status'], 'needs_review')
            self.assertEqual(built['strategy']['agent_review']['source_count'], 0)
            with patch('backend.strategy_agent.research_business') as research:
                repeated = owner.post(endpoint + '/build').json()
                research.assert_not_called()
            self.assertEqual(repeated['strategy_id'], strategy_id)
            resumed = owner.get(endpoint + '/resume').json()
            self.assertEqual(resumed['status'], 'Complete')
            self.assertEqual(resumed['strategy'], built['strategy'])
            accept = f'/api/strategy/{strategy_id}/accept'
            self.assertEqual(other.post(accept).status_code, 404)
            response = owner.post(accept)
            self.assertEqual(response.status_code, 200, response.text)
            campaign = response.json()['campaign']
            self.assertEqual(campaign['status'], 'Draft')
            repeated = owner.post(accept).json()
            self.assertTrue(repeated['already_created'])
            self.assertEqual(repeated['campaign']['id'], campaign['id'])
            self.assertEqual(other.get(f"/api/campaigns/{campaign['id']}").status_code, 404)


if __name__ == '__main__':
    unittest.main()
