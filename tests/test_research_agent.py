import unittest
from unittest.mock import patch

from backend.research_agent import (
    apply_review, official_provider, research_business, review_strategy,
)


class ResearchReviewTests(unittest.TestCase):
    def setUp(self):
        self.strategy = {
            'recommended_platform': 'Google',
            'recommended_campaign_type': 'Google Search',
            'business_profile': {'vertical': 'Services'},
            'launch_readiness': 'Ready for review',
            'risks': [],
        }
        self.state = {'objective': 'leads', 'has_website': True,
                      'has_tracking': True}

    def review(self, sources):
        return review_strategy(self.strategy, self.state, {'sources': sources})

    def test_unreachable_official_seed_is_not_evidence(self):
        review = self.review([{
            'url': 'https://support.google.com/google-ads/',
            'official_provider': 'google', 'snippet': '',
        }])
        self.assertEqual(review['source_count'], 0)
        self.assertEqual(review['discovered_source_count'], 1)
        self.assertEqual(review['status'], 'needs_review')
        self.assertFalse(review['checks'][1]['passed'])
        result = apply_review(self.strategy, review)
        self.assertEqual(result['launch_readiness'], 'Review required before launch')
        self.assertTrue(result['risks'])
        self.assertEqual(self.strategy['risks'], [])

    def test_search_result_count_does_not_create_high_confidence(self):
        review = self.review([
            {'url': f'https://example.com/{i}', 'snippet': 'A search page'}
            for i in range(4)
        ])
        self.assertEqual(review['source_count'], 4)
        self.assertEqual(review['status'], 'needs_review')
        self.assertNotEqual(review['confidence'], 'High')

    def test_official_metadata_cannot_impersonate_official_domain(self):
        review = self.review([{
            'url': 'https://support.google.com.example.org/',
            'official_provider': 'google', 'snippet': 'Ads guidance',
        }])
        self.assertFalse(review['checks'][1]['passed'])
        self.assertIsNone(official_provider('https://google.com@evil.example/'))
        self.assertEqual(official_provider('https://SUPPORT.GOOGLE.COM:443/'), 'google')

    def test_retrieved_official_content_has_limited_confidence(self):
        review = self.review([{
            'url': 'https://support.google.com/google-ads/',
            'snippet': 'Google Ads documentation', 'retrieval_status': 'retrieved',
        }])
        self.assertTrue(review['checks'][1]['passed'])
        self.assertEqual(review['status'], 'reviewed')
        self.assertEqual(review['confidence'], 'Medium')

    def test_flags_are_not_reported_as_already_corrected(self):
        self.state.update(objective='Sales', has_tracking=False)
        review = self.review([])
        self.assertTrue(any('tracking' in x.lower() for x in review['corrections']))
        self.assertEqual(review['status'], 'needs_review')

    def test_trial_cta_is_corrected_without_inventing_a_free_offer(self):
        self.strategy.update(business_profile={'vertical': 'SaaS', 'vertical_key': 'saas'},
                             cta='Get a quote', creative_plan={'cta': 'Get a quote'})
        self.state['offer'] = '14-day paid trial'
        review = self.review([{'url': 'https://support.google.com/google-ads/',
                               'snippet': 'Official campaign guidance'}])
        result = apply_review(self.strategy, review)
        self.assertEqual(result['cta'], 'Start your trial')
        self.assertEqual(result['creative_plan']['cta'], result['cta'])
        self.assertEqual(result['agent_review']['status'], 'corrected')
        self.assertEqual(result['agent_review']['corrections'], [])
        self.assertEqual(len(result['agent_review']['applied_corrections']), 1)
        self.assertEqual(self.strategy['creative_plan']['cta'], 'Get a quote')

    def test_negative_trial_offer_does_not_create_a_trial_cta(self):
        self.strategy['business_profile'] = {'vertical': 'SaaS', 'vertical_key': 'saas'}
        self.strategy['cta'] = 'Book a demo'
        self.state['offer'] = 'No trial available'
        result = apply_review(self.strategy, self.review([]))
        self.assertEqual(result['cta'], 'Book a demo')
        self.assertEqual(result['agent_review']['applied_corrections'], [])

    @patch('backend.research_agent.retrieve_source', return_value={
        'snippet': '', 'retrieval_status': 'unavailable'})
    @patch('backend.research_agent.ddg', return_value=[])
    def test_failed_fetch_is_explicit(self, search, fetch_snippet):
        research = research_business(self.state, self.strategy)
        self.assertEqual(research['sources'][0]['retrieval_status'], 'unavailable')
        self.assertEqual(self.review(research['sources'])['source_count'], 0)

    @patch('backend.research_agent.retrieve_source')
    @patch('backend.research_agent.ddg')
    def test_official_seed_is_reserved_and_its_failure_is_not_hidden(self, search, fetch_snippet):
        search.return_value = [{'url': 'https://example.com/', 'title': 'Business'}]
        fetch_snippet.side_effect = lambda url: {
            'snippet': '' if 'google.com' in url else 'Readable content',
            'retrieval_status': 'unavailable' if 'google.com' in url else 'retrieved'}
        research = research_business(self.state, self.strategy, max_sources=2)
        self.assertEqual(research['sources'][0]['official_provider'], 'google')
        self.assertEqual(research['sources'][0]['retrieval_status'], 'unavailable')
        self.assertEqual(len(research['sources']), 2)

    @patch('backend.research_agent.ddg')
    def test_zero_source_limit_does_not_search(self, search):
        self.assertEqual(research_business({}, {}, 0)['sources'], [])
        search.assert_not_called()


if __name__ == '__main__':
    unittest.main()
