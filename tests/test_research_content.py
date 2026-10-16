import unittest
from unittest.mock import patch

from backend.research_agent import extract_page, research_business, review_strategy


ARTICLE = ('Campaign planning requires clear business objectives and a useful landing page. '
           'Verify conversion tracking before optimizing for leads or purchases. '
           'Use genuine creative evidence and match the campaign to customer intent. ') * 3


class ResearchContentTests(unittest.TestCase):
    def test_extracts_main_text_without_navigation_footer_or_cookie_banner(self):
        raw = f'''<header>Brand mega menu</header><nav>Pricing Products Blog</nav>
            <main><article><h1>Campaign planning</h1><p>{ARTICLE}</p></article></main>
            <div class="cookie-consent">Accept all Cookie Preferences</div>
            <footer>Privacy Login</footer><script>secret script</script>'''
        result = extract_page(raw)
        self.assertEqual(result['retrieval_status'], 'retrieved')
        for unwanted in ['mega menu', 'Cookie Preferences', 'Privacy Login', 'secret script']:
            self.assertNotIn(unwanted, result['snippet'])
        self.assertIn('Verify conversion tracking', result['snippet'])

    def test_f6s_challenge_is_blocked_without_storing_request_details(self):
        result = extract_page('''<h1>Checking your browser</h1>
            <p>We think you might be a bot. Enable cookies and JavaScript.</p>
            <p>Request ID: private-request-id</p>''')
        self.assertEqual(result['retrieval_status'], 'blocked')
        self.assertEqual(result['snippet'], '')
        self.assertNotIn('private-request-id', str(result))

    def test_menu_only_and_title_only_pages_are_not_evidence(self):
        cases = ['<h1>Best CRM Software in Egypt</h1>',
                 '<nav>' + ARTICLE + '</nav>',
                 '<div>' + ''.join('<a href="/">' + ARTICLE + '</a>' for _ in range(4)) + '</div>']
        for raw in cases:
            with self.subTest(raw=raw[:30]):
                self.assertEqual(extract_page(raw)['retrieval_status'], 'insufficient_content')

    def test_article_without_semantic_main_tags_is_supported(self):
        result = extract_page(f'<div><h1>Planning</h1><p>{ARTICLE}</p></div>')
        self.assertEqual(result['retrieval_status'], 'retrieved')

    def test_legacy_challenge_labelled_retrieved_is_rejected_by_reviewer(self):
        strategy = {'recommended_platform': 'Meta', 'business_profile': {'vertical': 'SaaS'}}
        research = {'sources': [{'url': 'https://www.facebook.com/business/help',
                    'retrieval_status': 'retrieved', 'snippet': 'Checking your browser. We think you might be a bot.'}]}
        review = review_strategy(strategy, {}, research)
        self.assertEqual(review['source_count'], 0)
        self.assertFalse(review['checks'][1]['passed'])

    @patch('backend.research_agent.retrieve_source', return_value={
        'retrieval_status': 'retrieved', 'snippet': ARTICLE[:650]})
    @patch('backend.research_agent.ddg')
    def test_research_reaches_platform_query_when_business_results_are_full(self, search, retrieve):
        def results(query):
            if 'official ads guidance' in query:
                return [{'url': 'https://www.facebook.com/business/ads', 'title': 'Meta ads'}]
            slug = 'first' if 'competitors' in query else 'second'
            return [{'url': f'https://example.com/{slug}/{i}', 'title': str(i)} for i in range(6)]
        search.side_effect = results
        strategy = {'recommended_platform': 'Meta', 'recommended_campaign_type': 'Advantage+ Sales'}
        research = research_business({'product': 'AI support', 'country': 'Egypt'}, strategy)
        self.assertEqual(search.call_count, 3)
        self.assertTrue(any(source['url'].endswith('/business/ads') for source in research['sources']))
        self.assertLessEqual(len(research['sources']), 10)
        self.assertEqual(research['sources'][0]['official_provider'], 'meta')


if __name__ == '__main__':
    unittest.main()
