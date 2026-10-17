"""Explicit live browser check. Start Vite and an API with a disposable DB first.

Run: python tests/browser_agent_v21.py --api http://localhost:3000
Requires Playwright and its Chromium browser. This performs real web research
and creates a test account/session/strategy in the selected API database.
"""
import argparse
import json
import os
import time
from pathlib import Path

from playwright.sync_api import expect, sync_playwright
from browser_auth_helpers import signup_and_verify


def run(api, frontend, output, outbox):
    answers = {
        'business_name': 'FlowDesk', 'product': 'AI customer support software for small businesses',
        'offer': '14-day paid trial', 'country': 'Egypt',
        'audience': 'Small business owners and customer support managers',
        'objective': 'leads', 'demand_type': 'search', 'sales_channel': 'website',
        'currency': 'EGP', 'total_budget': 30000, 'campaign_days': 30, 'price': 1000,
        'gross_margin_percent': 70, 'extra_variable_cost_per_order': 50,
        'lead_to_sale_rate_percent': 10, 'has_website': True, 'has_tracking': True,
        'has_previous_sales': True, 'has_video_creatives': False,
    }
    report = {}
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True, **({'executable_path': os.environ['MF_TEST_CHROMIUM']} if os.getenv('MF_TEST_CHROMIUM') else {}))
        context = browser.new_context()
        page = context.new_page()
        errors = []
        page.on('pageerror', lambda error: errors.append(str(error)))
        page.route('http://localhost:3000/api/**',
                   lambda route: route.continue_(url=route.request.url.replace('http://localhost:3000', api)))
        response = signup_and_verify(context, api, outbox, data={
            'name': 'V2.1 Browser Test', 'email': f'v21-{time.time_ns()}@example.com',
            'password': 'ExamplePassword123!',
        })
        assert response.ok, response.text()
        page.goto(frontend + '/app')
        page.locator('.workspace-navigation [data-page="ai"]').click()
        page.locator('#startStrategyAgentBtn').click()
        composer = page.locator('#strategyAgentComposer')
        composer.locator('textarea').fill(answers['business_name'])
        with page.expect_response('**/answer'):
            composer.get_by_role('button', name='Send', exact=True).click()
        composer.locator('textarea').fill(answers['product'])
        sid = page.evaluate('localStorage.getItem("marketflow_strategy_agent_session")')
        assert sid
        page.reload()
        expect(composer.locator('textarea')).to_have_value(answers['product'])
        report['session_and_draft_reload'] = 'passed'

        pattern = '**/api/strategy-agent/*/resume'
        page.route(pattern, lambda route: route.fulfill(
            status=503, content_type='application/json', body='{"detail":"Temporary outage"}'))
        page.reload()
        retry = page.get_by_role('button', name='Retry restoring session')
        expect(retry).to_be_visible()
        assert page.evaluate('localStorage.getItem("marketflow_strategy_agent_session")') == sid
        assert page.evaluate('localStorage.getItem("marketflow_strategy_agent_draft")') == answers['product']
        page.unroute(pattern)
        retry.click()
        expect(composer.locator('textarea')).to_have_value(answers['product'])
        report['temporary_outage_keeps_session'] = 'passed'

        endpoint = f'{api}/api/strategy-agent/{sid}'
        while True:
            response = context.request.get(endpoint + '/resume')
            assert response.ok, response.text()
            progress = response.json()
            if progress.get('ready_to_build'):
                break
            question = progress['question']
            value = answers[question['key']]
            with page.expect_response('**/answer') as pending:
                if question['type'] == 'choice':
                    label = next(option['label'] for option in question['options'] if option['value'] == value)
                    composer.get_by_role('button', name=label, exact=True).click()
                elif question['type'] == 'boolean':
                    composer.get_by_role('button', name='Yes' if value else 'No', exact=True).click()
                else:
                    composer.locator('textarea, input').fill(str(value))
                    composer.get_by_role('button', name='Continue' if question.get('optional') else 'Send', exact=True).click()
            assert pending.value.ok, pending.value.text()

        build = composer.get_by_role('button', name='Build Strategy', exact=True)
        expect(build).to_have_count(1)
        page.reload()
        expect(build).to_have_count(1)
        expect(build).to_be_enabled()
        report['single_build_button_after_reload'] = 'passed'
        with page.expect_response('**/build', timeout=180000) as pending:
            build.click()
            expect(composer.get_by_role('button')).to_be_disabled()
            concurrent = context.request.post(endpoint + '/build')
            assert concurrent.status == 409, concurrent.text()
        response = pending.value
        assert response.ok, response.text()
        result = response.json()
        strategy = result['strategy']
        assert 'research_evidence' in strategy and 'agent_review' in strategy
        assert strategy['cta'] == strategy['creative_plan']['cta'] == 'Start your trial'
        assert 'free trial' not in json.dumps(strategy['creative_plan']).lower()
        report['paid_trial_and_consistent_cta'] = 'passed'
        report['concurrent_build_prevented'] = 'passed'
        sources = strategy['research_evidence']['sources']
        report['live_research'] = {
            'discovered': len(sources),
            'retrieved': strategy['agent_review']['source_count'],
            'urls': [source['url'] for source in sources],
        }
        report['review'] = strategy['agent_review']
        expect(page.locator('#acceptStrategyBtn')).to_be_visible(timeout=10000)
        expect(page.locator('#acceptStrategyBtn')).to_have_attribute('data-strategy-id', str(result['strategy_id']))
        resumed = context.request.get(endpoint + '/resume').json()
        assert resumed['strategy'] == strategy and resumed['status'] == 'Complete'
        page.reload()
        expect(page.locator('#acceptStrategyBtn')).to_have_attribute('data-strategy-id', str(result['strategy_id']))
        assert context.request.post(endpoint + '/build').json()['strategy_id'] == result['strategy_id']
        report['final_result_saved_and_reloadable'] = 'passed'
        # Simulate a completed server build whose response was lost before the
        # client could switch to the result page and clear its saved session.
        page.evaluate('''sid => {
            localStorage.setItem('marketflow_strategy_agent_session', sid);
            history.replaceState({marketflowApp: true, page: 'ai'}, '', '/app');
        }''', sid)
        page.reload()
        expect(page.locator('#acceptStrategyBtn')).to_have_attribute('data-strategy-id', str(result['strategy_id']))
        page.reload()
        expect(page.locator('#acceptStrategyBtn')).to_have_attribute('data-strategy-id', str(result['strategy_id']))
        report['completed_session_recovery_and_history'] = 'passed'
        report['browser_errors'] = errors
        assert not errors, errors
        Path(output).mkdir(parents=True, exist_ok=True)
        page.screenshot(path=str(Path(output) / 'agent-v21-result.png'), full_page=True)
        (Path(output) / 'agent-v21-result.json').write_text(json.dumps(result, indent=2))
        (Path(output) / 'agent-v21-report.json').write_text(json.dumps(report, indent=2))
        browser.close()
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--api', default='http://localhost:3000')
    parser.add_argument('--frontend', default='http://localhost:5173')
    parser.add_argument('--output', default='/tmp/marketflow-v21-report')
    options = parser.parse_args()
    run(options.api, options.frontend, options.output)
