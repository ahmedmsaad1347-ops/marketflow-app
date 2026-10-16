import unittest

from backend.strategy_engine import StrategyRequest, build_strategy


class TrialOfferTests(unittest.TestCase):
    def strategy(self, offer):
        return build_strategy(StrategyRequest(
            business_name='FlowDesk', product='AI customer support SaaS software',
            offer=offer, country='Egypt', audience='Small business owners',
            objective='leads', demand_type='search', sales_channel='website',
            total_budget=30000, has_website=True, has_tracking=True,
        ))

    def test_paid_trial_never_becomes_free_in_generated_creative(self):
        strategy = self.strategy('14-day paid trial')
        self.assertEqual(strategy['cta'], strategy['creative_plan']['cta'])
        self.assertEqual(strategy['cta'], 'Start your trial')
        import json
        self.assertNotIn('free trial', json.dumps(strategy['creative_plan']).lower())

    def test_explicit_free_trial_keeps_the_free_cta(self):
        self.assertEqual(self.strategy('14-day free trial')['cta'], 'Start Free Trial')

    def test_no_trial_does_not_generate_trial_cta(self):
        self.assertNotIn('trial', self.strategy('No trial available; book a demo')['cta'].lower())


if __name__ == '__main__':
    unittest.main()
