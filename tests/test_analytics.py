"""Reporting correctness checks against an isolated database and real auth/API."""
import importlib
import tempfile
import unittest
from dataclasses import replace
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import patch

from fastapi.testclient import TestClient
from auth_helpers import prepare_client, signup_verified


class AnalyticsTests(unittest.TestCase):
    def setUp(self):
        self.main = importlib.import_module('backend.main')
        self.directory = tempfile.TemporaryDirectory(prefix='mf-analytics-test-')
        self.addCleanup(self.directory.cleanup)
        database = patch.object(self.main, 'DATABASE', str(Path(self.directory.name)/'test.db'))
        database.start()
        self.addCleanup(database.stop)
        config = patch.object(self.main.auth, 'config', replace(self.main.auth.config,
            outbox=str(Path(self.directory.name)/'mail'), mail_mode='file'))
        config.start()
        self.addCleanup(config.stop)
        self.main.init_db()
        self.main.auth.migrate()
        self.client = prepare_client(TestClient(self.main.app))
        self.addCleanup(self.client.close)
        self.uid = signup_verified(self.client, self.main, json={'name':'Report owner',
            'email':'reports@example.com','password':'A precise view of the numbers!'}).json()['user']['id']
        self.today = datetime.utcnow().date()

    def record(self, offset=0, **kwargs):
        db = self.main.get_db()
        try:
            uid = kwargs.pop('user_id', self.uid)
            self.main.upsert_analytics_record(db, uid, date=(self.today-timedelta(days=offset)).isoformat(),
                provider=kwargs.pop('provider','meta'), currency=kwargs.pop('currency','EGP'), **kwargs)
        finally:
            db.close()

    def report(self, query=''):
        result = self.client.get('/api/analytics/overview?days=7' + query)
        self.assertEqual(result.status_code, 200, result.text)
        return result.json()

    def test_weighted_ratios_fractional_events_and_timeline_reconcile(self):
        self.record(campaign_id='small', spend=10, revenue=50, impressions=100, clicks=10,
            leads=2.5, message_leads=1.5, messages=8, conversions=2)
        self.record(offset=1, campaign_id='large', spend=90, revenue=150, impressions=900, clicks=30,
            leads=7.5, message_leads=2, messages=20, conversions=3)
        report = self.report()
        expected = {'spend':100,'revenue':200,'ctr':4,'cpc':2.5,'cpl':10,'cpa':20,
            'roas':2,'conversion_rate':12.5,'message_leads':3.5,'messages':28,'leads':10,'conversions':5}
        for key,value in expected.items():
            self.assertEqual(report['summary'][key], value, key)
        for key in ('spend','revenue','clicks','leads','message_leads','messages','conversions'):
            self.assertAlmostEqual(sum(row[key] for row in report['timeline']), report['summary'][key])
        self.assertEqual(report['data_status']['days_with_data'],2)
        self.assertFalse(report['timeline'][0]['has_data'])
        self.assertTrue(report['timeline'][-1]['has_data'])

    def test_currencies_never_mix_and_filters_apply_to_every_section(self):
        self.record(spend=100, revenue=400, campaign_id='egp')
        self.record(spend=5, revenue=10, campaign_id='usd', currency='USD')
        self.record(spend=50, revenue=100, campaign_id='google-egp', provider='google')
        report = self.report()
        self.assertEqual(report['currency'],'EGP')
        self.assertEqual(report['summary']['spend'],150)
        report = self.report('&currency=USD&provider=meta')
        self.assertEqual(report['summary']['spend'],5)
        self.assertEqual(report['timeline'][-1]['spend'],5)
        self.assertEqual(report['platforms'][0]['spend'],5)
        self.assertEqual([row['campaign_id'] for row in report['top_campaigns']],['usd'])
        self.assertEqual(report['data_status']['records'],1)

    def test_zero_denominator_is_unavailable_and_recorded_zero_is_real(self):
        self.record(spend=100, clicks=0, conversions=0, leads=0)
        report = self.report()
        self.assertTrue(report['has_data'])
        self.assertEqual(report['summary']['roas'],0)
        for key in ('cpa','cpl','cpc','ctr','conversion_rate'):
            self.assertIsNone(report['summary'][key])
        self.assertIsNone(report['comparison']['spend'])
        self.assertEqual(report['data_status']['previous_records'],0)

    def test_previous_period_bounds_and_no_current_records(self):
        self.record(offset=7, spend=50, revenue=100)
        self.record(offset=13, spend=50, revenue=100)
        self.record(offset=14, spend=999)
        self.record(offset=-1, spend=999, campaign_id='future')
        report = self.report()
        self.assertFalse(report['has_data'])
        self.assertTrue(report['has_any_data'])
        self.assertEqual(report['previous']['spend'],100)
        self.assertEqual(report['summary']['spend'],0)
        self.record(spend=150, revenue=400)
        report = self.report()
        self.assertEqual(report['comparison']['spend'],50)
        self.assertEqual(report['comparison']['revenue'],100)
        self.assertEqual(report['data_status']['records'],1)

    def test_campaigns_keep_account_identity_and_user_data_is_private(self):
        self.record(campaign_id='same-id',account_id='account-a',spend=10,revenue=20)
        self.record(campaign_id='same-id',account_id='account-b',spend=90,revenue=180)
        self.record(user_id=self.uid+1000, spend=99999, campaign_id='private',currency='EUR',provider='private')
        report = self.report()
        self.assertEqual(len(report['top_campaigns']),2)
        self.assertEqual(report['summary']['spend'],100)
        self.assertNotIn('EUR',report['filters']['currencies'])
        self.assertNotIn('private',report['filters']['providers'])
        with TestClient(self.main.app) as stranger:
            self.assertEqual(stranger.get('/api/analytics/overview').status_code,401)

    def test_invalid_filters_and_empty_workspace(self):
        report = self.report()
        self.assertFalse(report['has_data'])
        self.assertFalse(report['has_any_data'])
        self.assertIsNone(report['currency'])
        for query in ('days=8','currency=EUR','provider=somebody-elses-source'):
            self.assertEqual(self.client.get('/api/analytics/overview?'+query).status_code,400)


if __name__ == '__main__':
    unittest.main()
