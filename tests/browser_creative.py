"""Creative Studio: choose language, compare/edit/save/revise, restore and theme."""
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
        browser=p.chromium.launch(headless=True, **({'executable_path':os.environ['MF_TEST_CHROMIUM']} if os.getenv('MF_TEST_CHROMIUM') else {}))
        context=browser.new_context(viewport={'width':1440,'height':1000},reduced_motion='reduce')
        signup_and_verify(context,api,outbox,data={'name':'Ahmed','email':f'creative-{time.time_ns()}@example.com','password':'Build content that fits your brand!'})
        page=context.new_page();errors=[]
        page.on('pageerror',lambda error:errors.append(str(error)))
        page.route('http://localhost:3000/api/**',lambda route:route.continue_(url=route.request.url.replace('http://localhost:3000',api)))
        page.goto(frontend+'/app')
        page.locator('[data-page="creative"]').click()
        expect(page.locator('#creativeEngineStatus')).to_contain_text('Local content engine')
        form=page.locator('#creativeBriefForm')
        values={'brand':'FlowDesk AI','product':'Customer support software for online stores',
            'audience':'Online store support managers','benefit':'Organise recurring customer questions',
            'offer':'14-day paid trial','cta':'Book a demo','constraints':'No invented numbers or free trials'}
        for key,value in values.items():form.locator(f'[name="{key}"]').fill(value)
        assert form.locator('[name="language"]').input_value()==''
        expect(form.locator('[name="funnel_stage"]')).to_have_value('full')
        expect(form.locator('[name="generation_mode"]')).to_have_value('local')
        expect(form.locator('[name="content_length"]')).to_have_value('standard')
        expect(form.locator('[name="generation_mode"] option[value=ai]')).to_have_attribute('disabled','')
        expect(form.locator('[name="domain"] option')).to_have_count(26)
        form.locator('[name="domain"]').select_option('software')
        form.locator('[name="language"]').select_option('en')
        page.locator('#workspaceThemeToggle').click()
        expect(form.locator('[name="product"]')).to_have_value(values['product'])
        page.locator('#creativeGenerate').click()
        expect(page.locator('[data-creative-variant]')).to_have_count(3)
        assert page.locator('.creative-stage-badge').evaluate_all('nodes => nodes.map(node => node.dataset.funnelStage)') == ['tofu','mofu','bofu']
        expect(page.locator('#creativeNotice')).to_contain_text('Three local content directions saved')
        page.locator('[data-creative-variant="1"]').click()
        editor=page.locator('#creativeSelectionForm')
        edited='A clear voice for your customer-support team. An extra explanatory sentence.\n\n14-day paid trial.'
        editor.locator('[name="body"]').fill(edited)
        editor.locator('[name="rating"]').select_option('5')
        editor.locator('[name="reviewed"]').check()
        editor.get_by_role('button',name='Save my choice',exact=True).click()
        expect(page.locator('#creativeSaveState')).to_contain_text('Saved with your review')
        page.reload()
        expect(page.locator('#creativeSelectionForm [name="body"]')).to_have_value(edited)
        expect(page.locator('#creativeSelectionForm [name="rating"]')).to_have_value('5')
        expect(page.locator('#creativeSelectionForm [name="reviewed"]')).to_be_checked()
        expect(page.locator('[data-creative-variant="1"]')).to_have_attribute('aria-pressed','true')
        expect(page.locator('#creativeSelectionForm [name="funnel_stage"]')).to_have_value('mofu')
        first=page.locator('#creativeVersions').input_value()
        expect(page.locator('#creativeFeedback')).to_have_count(1)
        expect(page.locator('#creativeRefine')).to_contain_text('Apply local edit')
        page.locator('[data-local-edit=shorter]').click()
        page.locator('#creativeRefine').click()
        expect(page.locator('#creativeVersions option')).to_have_count(2)
        expect(page.locator('#creativeNotice')).to_contain_text('1 changed local direction saved')
        expect(page.locator('[data-creative-variant]')).to_have_count(1)
        shortened=page.locator('#creativeSelectionForm [name="body"]').input_value()
        assert shortened != edited and len(shortened)<len(edited)
        assert 'A clear voice for your customer-support team.' in shortened
        assert '14-day paid trial.' in shortened
        expect(page.locator('#creativeSelectionForm [name="funnel_stage"]')).to_have_value('mofu')
        # Repeating an edit must not mint an unchanged saved version.
        shortened_id=page.locator('#creativeVersions').input_value()
        page.locator('[data-local-edit=shorter]').click()
        page.locator('#creativeRefine').click()
        expect(page.locator('#creativeNotice')).to_contain_text('No new version was saved')
        expect(page.locator('#creativeVersions option')).to_have_count(2)
        expect(page.locator('#creativeVersions')).to_have_value(shortened_id)
        expect(page.locator('#creativeSelectionForm [name="body"]')).to_have_value(shortened)
        # A different local hook changes the selected copy without touching its body.
        old_hook=page.locator('#creativeSelectionForm [name="hook"]').input_value()
        page.locator('[data-local-edit=new_hook]').click()
        page.locator('#creativeRefine').click()
        expect(page.locator('#creativeVersions option')).to_have_count(3)
        expect(page.locator('#creativeSelectionForm [name="hook"]')).not_to_have_value(old_hook)
        expect(page.locator('#creativeSelectionForm [name="body"]')).to_have_value(shortened)
        expect(page.locator('#creativeSelectionForm [name="funnel_stage"]')).to_have_value('mofu')
        page.locator('#creativeVersions').select_option(first)
        expect(page.locator('#creativeSelectionForm [name="body"]')).to_have_value(edited)
        # Language belongs to each brief, not a global fixed default.
        form.locator('[name="language"]').select_option('ar-EG')
        form.locator('[name="brand"]').fill('فلو ديسك')
        form.locator('[name="benefit"]').fill('تنظيم أسئلة العملاء المتكررة')
        form.locator('[name="product"]').fill('برنامج لتنظيم خدمة العملاء في المتاجر الإلكترونية')
        form.locator('[name="audience"]').fill('أصحاب المتاجر ومديري خدمة العملاء')
        form.locator('[name="cta"]').fill('احجز عرض توضيحي')
        page.locator('#creativeGenerate').click()
        expect(page.locator('.creative-copy-fields')).to_have_attribute('dir','rtl')
        expect(page.locator('#creativeSelectionForm [name="body"]')).to_contain_text('تنظيم أسئلة العملاء المتكررة')
        expect(page.locator('#creativeVersions option')).to_have_count(4)
        for theme in ('dark','light'):
            if page.locator('html').get_attribute('data-mf-theme')!=theme:page.locator('#workspaceThemeToggle').click()
            for width in (1440,768,390,320):
                page.set_viewport_size({'width':width,'height':1000 if width>800 else 844})
                assert page.evaluate('document.documentElement.scrollWidth <= innerWidth'),(theme,width)
                if width in (1440,390):
                    page.evaluate("window.scrollTo({top:0,behavior:'instant'})")
                    page.screenshot(path=str(Path(output)/f'creative-{theme}-{width}.png'),full_page=True)
        # A single-stage brief creates three angles for that stage, not a mixed funnel.
        form.locator('[name="funnel_stage"]').select_option('bofu')
        page.locator('#creativeGenerate').click()
        expect(page.locator('#creativeVersions option')).to_have_count(5)
        assert page.locator('.creative-stage-badge').evaluate_all('nodes => nodes.map(node => node.dataset.funnelStage)') == ['bofu']*3
        expect(page.locator('#creativeSelectionForm [name="body"]')).to_contain_text('14-day paid trial')
        # A failed generation leaves the last saved directions visible.
        page.route('**/api/creative/generate',lambda route:route.fulfill(status=502,content_type='application/json',body='{"detail":"The agent could not finish. Your saved drafts are unchanged."}'))
        page.locator('#creativeGenerate').click()
        expect(page.locator('#creativeNotice')).to_contain_text('saved drafts are unchanged')
        expect(page.locator('#creativeVersions option')).to_have_count(5)
        expect(page.locator('#creativeGenerate')).to_be_enabled()
        assert not errors,errors
        print(json.dumps({'language_choice_and_rtl':'passed','full_funnel_and_single_stage':'passed','three_directions':'passed','edit_rating_review_restore':'passed',
            'revision_changes_selected_copy_and_keeps_offer':'passed','unchanged_revision_not_saved':'passed',
            'local_hook_changes_without_api':'passed','domain_choices_and_local_default':'passed','revision_keeps_original':'passed','theme_preserves_brief':'passed','generation_failure_recovery':'passed',
            'responsive_widths':[1440,768,390,320],'browser_errors':errors}))
        browser.close()

if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('--api',default='http://localhost:3008')
    parser.add_argument('--frontend',default='http://localhost:5173')
    parser.add_argument('--outbox',required=True)
    parser.add_argument('--output',default='/tmp/marketflow-creative-report')
    args=parser.parse_args()
    run(args.api,args.frontend,args.outbox,args.output)
