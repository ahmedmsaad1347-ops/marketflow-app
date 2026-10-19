"""Campaign wizard, budget/idea persistence, editing, filters and strategy auto budgeting."""
import argparse
import json
import os
from pathlib import Path
import time
from playwright.sync_api import expect, sync_playwright
from browser_auth_helpers import signup_and_verify


def run(api,frontend,outbox,output):
    Path(output).mkdir(parents=True,exist_ok=True)
    with sync_playwright() as p:
        browser=p.chromium.launch(headless=True,executable_path=os.environ.get('MF_TEST_CHROMIUM','/usr/bin/chromium'))
        context=browser.new_context(viewport={'width':1440,'height':1000},reduced_motion='reduce')
        signup_and_verify(context,api,outbox,data={'name':'Campaign planner','email':f'budget-{time.time_ns()}@example.com','password':'A practical first campaign with clear goals!'})
        page=context.new_page();errors=[];page.on('pageerror',lambda error:errors.append(str(error)))
        page.route('http://localhost:3000/api/**',lambda route:route.continue_(url=route.request.url.replace('http://localhost:3000',api)))
        page.goto(frontend+'/app')
        page.locator('[data-page="campaign-create"]').first.click()
        form=page.locator('#campaignForm')
        expect(page.locator('[data-campaign-step="1"]')).to_be_visible()
        expect(page.locator('[data-campaign-step="2"]')).not_to_be_visible()
        # Step validation prevents an empty brief from advancing.
        page.locator('#campaignStepNext').click()
        expect(page.locator('[data-campaign-step="1"]')).to_be_visible()
        for key,value in dict(name='معاينات الشروق',product='شقة 140 مترًا في الشروق، 3 غرف و2 حمام',
            audience='الباحثون عن شقة للسكن في الشروق',country='Egypt').items():
            form.locator(f'[name="{key}"]').fill(value)
        form.locator('[name=goal]').select_option('Leads');form.locator('[name=platform]').select_option('Facebook')
        expect(page.locator('#campaignGoalHint')).to_contain_text('commission')
        page.locator('#campaignStepNext').click()
        expect(page.locator('[data-campaign-step="2"]')).to_be_visible()
        form.locator('[name=planner_business_name]').fill('سكنك للعقارات')
        form.locator('[name=planner_creative_language]').select_option('ar-EG')
        form.locator('[name=planner_target_results]').fill('20')
        form.locator('[name=planner_spend_ceiling]').fill('600')
        form.locator('[name=planner_sales_channel]').select_option('phone')
        form.locator('[name=planner_benefit]').fill('فصل الاستقبال عن غرف النوم')
        offer='السعر 2,400,000 جنيه. مقدم 600,000 جنيه والباقي على 5 سنوات.'
        form.locator('[name=planner_offer]').fill(offer)
        page.locator('#campaignPlanGenerate').click()
        expect(page.locator('#campaignPlanNotice')).to_contain_text('Add a cost assumption')
        expect(page.locator('#campaignPlanResult .budget-ad-concept')).to_contain_text(offer)
        expect(page.locator('#campaignPlanApply')).to_have_count(0)
        form.locator('[name=planner_cost_per_result]').fill('50')
        page.locator('#campaignPlanGenerate').click()
        expect(page.locator('#campaignPlanApply')).to_be_visible()
        expect(page.locator('#campaignPlanResult .budget-funding-gap')).to_contain_text('400')
        page.locator('#campaignPlanApply').click()
        expect(form.locator('[name=budget]')).to_have_value('600.00 EGP / 14 days')
        for theme in ('dark','light'):
            if page.locator('html').get_attribute('data-mf-theme')!=theme:page.locator('#workspaceThemeToggle').click()
            for width in (1440,768,390,320):
                page.set_viewport_size({'width':width,'height':1000 if width>800 else 844})
                assert page.evaluate('document.documentElement.scrollWidth <= innerWidth'),('wizard',theme,width)
                if width in (1440,390):
                    page.evaluate("document.activeElement?.blur();window.scrollTo({top:0,behavior:'instant'})")
                    page.screenshot(path=str(Path(output)/f'campaign-planner-{theme}-{width}.png'),full_page=True)
        page.locator('#campaignStepNext').click()
        expect(page.locator('[data-campaign-step="3"]')).to_be_visible()
        expect(page.locator('#campaignWizardReview')).to_contain_text('600.00 EGP / 14 days')
        with page.expect_response('**/api/campaigns') as created:page.locator('#campaignSave').click()
        assert created.value.ok,created.value.text()
        item=created.value.json()['campaign'];cid=item['id']
        expect(page.locator('.mf-campaign-review')).to_be_visible()
        expect(page.locator('.budget-ad-concept')).to_contain_text(offer)
        page.reload()
        expect(page.locator('.budget-ad-concept')).to_contain_text(offer)
        page.locator('[data-edit-campaign]').click()
        expect(form.locator('[name=product]')).to_have_value('شقة 140 مترًا في الشروق، 3 غرف و2 حمام')
        page.locator('#campaignStepNext').click()
        expect(form.locator('[name=planner_cost_per_result]')).to_have_value('50')
        expect(form.locator('[name=planner_creative_language]')).to_have_value('ar-EG')
        # A restored proposal can be applied again without generating different copy.
        page.locator('#campaignPlanApply').click()
        expect(form.locator('[name=budget]')).to_have_value('600.00 EGP / 14 days')
        form.locator('[name=budget]').fill('300 EGP for a smaller test')
        page.locator('#campaignStepNext').click()
        expect(page.locator('#campaignWizardReview')).to_contain_text('Reference scenario budget')
        with page.expect_response(lambda response:response.url.endswith(f'/api/campaigns/{cid}') and response.request.method=='PUT') as updated:
            page.locator('#campaignSave').click()
        assert updated.value.ok,updated.value.text()
        expect(page.locator('.mf-campaign-review')).to_be_visible()
        expect(page.locator('.mf-campaign-summary')).to_contain_text('300 EGP for a smaller test')
        saved=context.request.get(api+f'/api/campaigns/{cid}').json()['campaign']
        assert not json.loads(saved['planning_json'])['applied_budget']
        # Listing uses real saved records and keeps search/filter/edit/review actions.
        page.locator('.mf-campaign-review [data-page=campaigns]').click()
        expect(page.locator('.mf-campaign-card')).to_have_count(1)
        page.locator('#campaignSearch').fill('no matching project');page.locator('#campaignSearchForm button[type=submit]').click()
        expect(page.locator('.mf-campaign-empty')).to_be_visible()
        page.locator('[data-clear-campaign-search]').click()
        expect(page.locator('.mf-campaign-card')).to_have_count(1)
        page.locator('[data-duplicate-campaign]').click()
        expect(page.locator('.mf-campaign-card')).to_have_count(2)
        page.locator('[data-campaign-status][data-status=Archived]').first.click()
        page.locator('[data-campaign-filter=Archived]').click()
        expect(page.locator('.mf-campaign-card')).to_have_count(1)
        for theme in ('dark','light'):
            if page.locator('html').get_attribute('data-mf-theme')!=theme:page.locator('#workspaceThemeToggle').click()
            for width in (1440,390,320):
                page.set_viewport_size({'width':width,'height':1000 if width>800 else 844})
                assert page.evaluate('document.documentElement.scrollWidth <= innerWidth'),('list',theme,width)
                if width!=320:
                    page.evaluate("document.activeElement?.blur();window.scrollTo({top:0,behavior:'instant'})")
                    page.screenshot(path=str(Path(output)/f'campaigns-{theme}-{width}.png'),full_page=True)
        # Changing the outcome cannot silently reuse a cost with incompatible units.
        page.locator('[data-page="campaign-create"]').first.click()
        manual=page.locator('#campaignForm')
        for key,value in dict(name='Manual awareness test',product='Local property service',audience='Property buyers',country='Egypt').items():manual.locator(f'[name="{key}"]').fill(value)
        manual.locator('[name=goal]').select_option('Leads');manual.locator('[name=platform]').select_option('Meta')
        page.locator('#campaignStepNext').click()
        manual.locator('[name=planner_cost_per_result]').fill('50');manual.locator('[name=planner_target_results]').fill('20')
        page.locator('#campaignStepBack').click();manual.locator('[name=goal]').select_option('Brand awareness')
        page.locator('#campaignStepNext').click()
        expect(manual.locator('[name=planner_cost_per_result]')).to_have_value('')
        expect(manual.locator('[name=planner_target_results]')).to_have_value('')
        expect(manual.locator('[data-budget-cost-label]')).to_contain_text('CPM')
        manual.locator('[name=budget]').fill('900 EGP / 14 days')
        page.locator('#campaignStepNext').click()
        with page.expect_response('**/api/campaigns') as manual_created:page.locator('#campaignSave').click()
        assert manual_created.value.ok,manual_created.value.text()
        expect(page.locator('.mf-campaign-review')).to_be_visible()
        assert manual_created.value.json()['campaign']['planning_json'] is None
        # Existing strategy brief also supports no entered total budget.
        page.locator('.workspace-navigation [data-page=dashboard]').click()
        page.locator('[data-strategy-start=quick]').click()
        strategy=page.locator('#strategyForm')
        values=dict(business_name='FlowDesk',product='Customer support software',offer='14-day paid trial',
            country='Egypt',audience='Store owners',price='1000',gross_margin_percent='70',extra_variable_cost_per_order='50',lead_to_sale_rate_percent='10')
        for key,value in values.items():strategy.locator(f'[name="{key}"]').fill(value)
        for key,value in dict(budget_mode='recommend',objective='leads',creative_language='en',currency='EGP',campaign_days='14').items():strategy.locator(f'[name="{key}"]').select_option(value)
        strategy.locator('[name=has_website]').check();strategy.locator('[name=has_tracking]').check()
        expect(strategy.locator('[name=total_budget]')).to_be_disabled()
        with page.expect_response('**/api/strategy/generate') as generated:page.locator('#strategyGenerate').click()
        assert generated.value.ok,generated.value.text()
        result=generated.value.json()['strategy'];assert result['budget_plan']['total_budget']==455
        expect(page.locator('[data-budget-advice]')).to_contain_text('455')
        expect(page.locator('.budget-ad-concept')).to_contain_text('14-day paid trial')
        assert not errors,errors
        print(json.dumps({'wizard_validation':'passed','missing_basis_and_local_idea':'passed','budget_cap_and_apply':'passed',
            'saved_ad_and_budget_restore':'passed','edit_and_manual_override':'passed','list_search_duplicate_archive':'passed',
            'strategy_auto_budget':'passed','goal_unit_change_and_manual_draft':'passed','responsive_widths':[1440,768,390,320],'browser_errors':errors}))
        browser.close()


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--api',default='http://localhost:3008');parser.add_argument('--frontend',default='http://localhost:5173')
    parser.add_argument('--outbox',required=True);parser.add_argument('--output',default='/tmp/mf-budget-evidence')
    args=parser.parse_args();run(args.api,args.frontend,args.outbox,args.output)
