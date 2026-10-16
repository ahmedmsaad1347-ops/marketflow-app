from datetime import datetime, timedelta, timezone
import unittest
from unittest.mock import patch

from backend.google_ads_capabilities import (
    DemandGenMinimum, daily_micros, demand_gen_budget_check,
    eu_declaration_required, validate_google_ads_capabilities,
)
from backend.google_ads_measurement import summarize_conversion_rows
from backend.strategy_engine import StrategyRequest, build_strategy, _candidate


class GoogleAdsCapabilityTests(unittest.TestCase):
    def setUp(self):
        self.now = datetime.now(timezone.utc)
        # Synthetic test data, not a real Google currency minimum.
        self.minimum = DemandGenMinimum('EGP', 10_000_000, self.now)
        self.campaign = dict(api_version='v26', campaign_type='Demand Gen', currency='EGP',
                             daily_budget_micros=10_000_000,
                             contains_eu_political_advertising='DOES_NOT_CONTAIN_EU_POLITICAL_ADVERTISING')

    def test_demand_gen_budget_at_and_below_exact_boundary(self):
        self.assertTrue(demand_gen_budget_check('EGP', 10_000_000, self.minimum)['passed'])
        self.assertFalse(demand_gen_budget_check('EGP', 9_999_999, self.minimum)['passed'])
        self.assertEqual(daily_micros(1, 3), 333333)

    def test_unavailable_stale_foreign_and_wrong_version_minimum_are_unverified(self):
        cases = [None, DemandGenMinimum('USD', 10, self.now),
                 DemandGenMinimum('EGP', 10, self.now - timedelta(hours=25)),
                 DemandGenMinimum('EGP', 10, self.now, 'v25'),
                 DemandGenMinimum('EGP', 10, self.now + timedelta(hours=1)),
                 DemandGenMinimum('EGP', 10, self.now.replace(tzinfo=None))]
        for minimum in cases:
            with self.subTest(minimum=minimum):
                result = demand_gen_budget_check('EGP', 100000000, minimum, self.now)
                self.assertEqual(result['code'], 'demand_gen_minimum_unverified')

    def test_supported_check_still_requires_google_validate_only(self):
        result = validate_google_ads_capabilities(self.campaign, minimum=self.minimum,
            tracking={'enablement_setting': 'UNSPECIFIED'})
        self.assertTrue(result['passed'])
        self.assertTrue(result['requires_provider_validate_only'])

    def test_local_services_pmax_requires_country_and_listing(self):
        campaign = {**self.campaign, 'campaign_type': 'Local Services Performance Max'}
        result = validate_google_ads_capabilities(campaign, tracking={})
        self.assertEqual({x['code'] for x in result['issues']}, {'country_code_required', 'listing_id_required'})
        campaign['local_services_settings'] = {'country_code': 'EG', 'listing_id': '123456789'}
        self.assertTrue(validate_google_ads_capabilities(campaign, tracking={})['passed'])
        campaign['local_services_settings']['listing_id'] = 'not-a-listing'
        self.assertFalse(validate_google_ads_capabilities(campaign, tracking={})['passed'])

    def test_missing_account_measurement_snapshot_requires_review(self):
        result = validate_google_ads_capabilities(self.campaign, minimum=self.minimum)
        self.assertIn('measurement_settings_unverified', {item['code'] for item in result['issues']})

    def test_unknown_version_and_removed_tracking_field_are_explicit(self):
        campaign = {**self.campaign, 'api_version': 'v25'}
        result = validate_google_ads_capabilities(campaign, minimum=self.minimum,
            tracking={'enhanced_conversions_for_leads_enabled': True, 'enablement_setting': 'UNSPECIFIED'})
        codes = {item['code'] for item in result['issues']}
        self.assertIn('unsupported_api_version', codes)
        self.assertIn('removed_conversion_field', codes)
        self.assertEqual(result['measurement']['enablement_setting'], 'UNSPECIFIED')

    def test_positive_outside_eu_location_exemption_and_negative_eu_location(self):
        criteria = [dict(type='location', require_eu_political_advertising_declaration=False),
                    dict(type='location', negative=True, require_eu_political_advertising_declaration=True)]
        self.assertFalse(eu_declaration_required(criteria))
        criteria.append(dict(type='proximity'))
        self.assertTrue(eu_declaration_required(criteria))

    def test_upgraded_demand_gen_uses_every_active_group(self):
        outside = [dict(type='location', require_eu_political_advertising_declaration=False)]
        inside = [dict(type='location', require_eu_political_advertising_declaration=True)]
        self.assertTrue(eu_declaration_required([], upgraded_demand_gen=True, active_ad_groups=[outside, inside]))
        self.assertFalse(eu_declaration_required([], upgraded_demand_gen=True, active_ad_groups=[]))
        self.assertIsNone(eu_declaration_required([], upgraded_demand_gen=True))

    def test_missing_declaration_and_unknown_geography_are_not_exempt(self):
        campaign = {**self.campaign, 'contains_eu_political_advertising': None}
        self.assertIn('eu_targeting_unverified', {
            item['code'] for item in validate_google_ads_capabilities(campaign, minimum=self.minimum)['issues']})
        campaign['criteria'] = [dict(type='location', require_eu_political_advertising_declaration=True)]
        self.assertIn('eu_declaration_required', {
            item['code'] for item in validate_google_ads_capabilities(campaign, minimum=self.minimum)['issues']})

    def test_strategy_excludes_unverified_or_underfunded_demand_gen(self):
        request = StrategyRequest(business_name='Test shop', product='Shoes', country='Egypt',
                                  audience='Shoppers', objective='traffic', total_budget=10,
                                  campaign_days=1, currency='EGP', has_website=True)
        def candidates(_):
            return [_candidate('google_demand_gen', 'Google', 'Demand Gen', 95, True, [], ''),
                    _candidate('google_search', 'Google', 'Google Search', 40, True, [], '')]
        with patch('backend.strategy_engine._score_candidates', side_effect=candidates):
            self.assertEqual(build_strategy(request)['recommended_campaign_type'], 'Google Search')
            expensive = DemandGenMinimum('EGP', 11_000_000, self.now)
            self.assertEqual(build_strategy(request, google_currency_minimum=expensive)['recommended_campaign_type'], 'Google Search')
            self.assertEqual(build_strategy(request, google_currency_minimum=self.minimum)['recommended_campaign_type'], 'Demand Gen')

    def test_message_interest_is_not_a_qualified_lead_or_sale(self):
        result = summarize_conversion_rows([
            dict(category='MESSAGE_LEAD', count=4, value=800, attribution_event_type='CLICK'),
            dict(category='QUALIFIED_LEAD', count=2, value=300, attribution_event_type='UNKNOWN'),
            dict(category='PURCHASE', count=1, value=500, attribution_event_type='CLICK'),
            dict(category='FUTURE_CATEGORY', count=3, value=400),
        ])
        self.assertEqual(result['message_leads'], 4)
        self.assertEqual(result['qualified_leads'], 2)
        self.assertEqual(result['leads'], 6)
        self.assertEqual(result['conversions'], 1)
        self.assertEqual(result['revenue'], 500)
        self.assertEqual(result['attribution_event_types']['CLICK'], 5)
        self.assertEqual(result['unclassified_conversions'], 3)

    def test_fractional_attribution_is_preserved(self):
        result = summarize_conversion_rows([dict(category='MESSAGE_LEAD', count=0.5)])
        self.assertEqual(result['message_leads'], 0.5)
        with self.assertRaises(ValueError):
            summarize_conversion_rows([dict(category='MESSAGE_LEAD', count=float('nan'))])


if __name__ == '__main__':
    unittest.main()
