"""Browser regression against an API with disposable DB and mocked research.

Run with the same frontend/API setup as browser_agent_v21.py.
"""
import argparse
import json
import time
from pathlib import Path
from playwright.sync_api import expect, sync_playwright


def run(api, frontend, output):
    original = dict(business_name='FlowDesk AI', product='AI customer support SaaS software',
        offer='14-day paid trial', country='Egypt', audience='Small business owners',
        objective='sales', demand_type='discovery', sales_channel='website',
        currency='EGP', total_budget=3000, campaign_days=30, price=1000,
        gross_margin_percent=70, extra_variable_cost_per_order=50,
        has_website=True, has_tracking=True, has_previous_sales=True)
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(viewport={'width': 390, 'height': 844}, is_mobile=True)
        response = context.request.post(api + '/api/auth/signup', data=dict(
            name='Editor browser', email=f'editor-{time.time_ns()}@example.com', password='ExamplePassword123!'))
        assert response.ok, response.text()
        session = context.request.post(api + '/api/strategy-agent/start').json()['session_id']
        context.request.post(api + f'/api/strategy-agent/{session}/answer', data={'value': original['business_name']})
        page = context.new_page()
        errors = []
        page.on('pageerror', lambda error: errors.append(str(error)))
        page.route('http://localhost:3000/api/**', lambda route:
            route.continue_(url=route.request.url.replace('http://localhost:3000', api)))
        page.goto(frontend + '/app')
        page.locator('[data-page="ai"]').click()
        page.evaluate('sid => localStorage.setItem("marketflow_strategy_agent_session", sid)', str(session))
        page.reload()
        page.get_by_role('button', name='Review / edit answers').click()
        form = page.locator('#strategyForm')
        expect(form.locator('[name="business_name"]')).to_have_value(original['business_name'])
        for name, value in original.items():
            field = form.locator(f'[name="{name}"]')
            if isinstance(value, bool):
                field.set_checked(value)
            elif field.evaluate('element => element.tagName') == 'SELECT':
                field.select_option(str(value))
            else:
                field.fill(str(value))
        with page.expect_response('**/build') as built:
            page.get_by_role('button', name='Save answers & Build Strategy').click()
        assert built.value.ok, built.value.text()
        first = built.value.json()['strategy_id']
        expect(page.locator('#acceptStrategyBtn')).to_be_visible()
        page.get_by_role('button', name='Edit answers & rebuild').click()
        expect(form.locator('[name="total_budget"]')).to_have_value('3000')
        expect(form.locator('[name="objective"]')).to_have_value('sales')
        expect(form.locator('[name="has_tracking"]')).to_be_checked()
        # Editor refresh restores the saved brief, including false checkboxes.
        page.reload()
        expect(form.locator('[name="has_video_creatives"]')).not_to_be_checked()
        form.locator('[name="total_budget"]').fill('30000')
        form.locator('[name="objective"]').select_option('leads')
        form.locator('[name="demand_type"]').select_option('search')
        with page.expect_response('**/build') as built:
            page.get_by_role('button', name='Save answers & Build Strategy').click()
        assert built.value.ok, built.value.text()
        second = built.value.json()['strategy_id']
        assert second != first
        expect(page.locator('#acceptStrategyBtn')).to_have_attribute('data-strategy-id', str(second))
        expect(page.get_by_role('heading', name='Google Search', exact=True)).to_be_visible()
        saved = context.request.get(api + f'/api/strategy/{first}').json()['strategy']
        assert saved['input']['total_budget'] == 3000
        assert saved['input']['objective'] == 'sales'
        revised = context.request.get(api + f'/api/strategy/{second}').json()['strategy']
        assert revised['input']['total_budget'] == 30000
        assert revised['input']['objective'] == 'leads'
        assert revised['output']['research_evidence'] == {'sources': []}
        assert page.evaluate('document.documentElement.scrollWidth <= innerWidth')
        assert not errors, errors
        Path(output).mkdir(parents=True, exist_ok=True)
        page.get_by_role('button', name='Edit answers & rebuild').click()
        page.screenshot(path=str(Path(output) / 'strategy-editor-mobile.png'), full_page=True)
        print(json.dumps({'edit_before_build': 'passed', 'saved_values_prefilled': 'passed',
            'editor_reload': 'passed', 'new_version_with_research': 'passed',
            'original_preserved': 'passed', 'browser_errors': errors}))
        browser.close()


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--api', default='http://localhost:3000')
    parser.add_argument('--frontend', default='http://localhost:5173')
    parser.add_argument('--output', default='/tmp/marketflow-editor-report')
    args = parser.parse_args()
    run(args.api, args.frontend, args.output)
