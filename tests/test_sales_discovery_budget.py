import unittest

from backend.strategy_engine import StrategyRequest, build_strategy


class SalesDiscoveryBudgetTests(unittest.TestCase):
    def test_user_example_keeps_sales_discovery_and_warns_on_small_daily_budget(self):
        request = StrategyRequest(
            business_name='FlowDesk AI',
            product='AI customer support software for small online stores',
            offer='14-day paid trial', country='Egypt',
            audience='Small business owners and customer support managers at online stores',
            objective='sales', demand_type='discovery', currency='EGP',
            total_budget=3000, campaign_days=30, price=1000,
            gross_margin_percent=70, extra_variable_cost_per_order=50,
            has_website=True, has_tracking=True, has_previous_sales=True,
        )
        strategy = build_strategy(request)
        self.assertEqual(strategy['requested_objective'], 'Sales')
        self.assertEqual(strategy['recommended_campaign_type'], 'Advantage+ Sales')
        self.assertEqual(strategy['fit_score'], 95)
        self.assertEqual(strategy['budget_plan']['daily_budget'], 100)
        self.assertIn('455.0 EGP', strategy['budget_plan']['planning_warning'])
        self.assertIn('not a performance forecast', strategy['budget_plan']['planning_warning'])
        self.assertEqual(strategy['economics']['contribution_per_sale'], 650)


if __name__ == '__main__':
    unittest.main()
