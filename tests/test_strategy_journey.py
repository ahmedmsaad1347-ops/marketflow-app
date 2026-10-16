"""Offline API checks using a fresh database and mocked external research."""
import importlib
import os
import tempfile
import unittest
from concurrent.futures import ThreadPoolExecutor
from threading import Event
from unittest.mock import patch

from fastapi.testclient import TestClient


class StrategyJourneyTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.directory = tempfile.TemporaryDirectory(prefix='marketflow-test-')
        previous = os.getcwd()
        try:
            os.chdir(cls.directory.name)
            cls.main = importlib.import_module('backend.main')
            cls.main.DATABASE = os.path.join(cls.directory.name, 'marketflow.db')
        finally:
            os.chdir(previous)

    @classmethod
    def tearDownClass(cls):
        cls.directory.cleanup()

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
                response = client.post('/api/auth/signup', json={
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
