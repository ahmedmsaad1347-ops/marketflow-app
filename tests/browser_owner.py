"""Owner console: real role/bootstrap, management, audited review and responsive UI.

Run only against a disposable API/database. The owner fixture is intentionally reusable.
"""
import argparse
from datetime import datetime, timedelta, timezone
import json
import os
from pathlib import Path
import subprocess
import time

from playwright.sync_api import expect, sync_playwright
from browser_auth_helpers import signup_and_verify

PASSWORD = 'Independent silver clouds over Cairo!'
OWNER_EMAIL = 'owner-browser@example.com'


def login(context, api, email):
    configuration = context.request.get(api + '/api/auth/config').json()
    context.set_extra_http_headers({'X-CSRF-Token': configuration['csrf_token']})
    response = context.request.post(api + '/api/auth/login', data={'email': email, 'password': PASSWORD})
    assert response.ok, response.text()


def run(api, frontend, outbox, database, python, output):
    output = Path(output)
    output.mkdir(parents=True, exist_ok=True)
    errors = []
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True, executable_path=os.environ.get('MF_TEST_CHROMIUM', '/usr/bin/chromium'))
        owner = browser.new_context(viewport={'width': 1440, 'height': 1000}, reduced_motion='reduce')
        configuration = owner.request.get(api + '/api/auth/config').json()
        owner.set_extra_http_headers({'X-CSRF-Token': configuration['csrf_token']})
        initial = owner.request.post(api + '/api/auth/login', data={'email': OWNER_EMAIL, 'password': PASSWORD})
        if initial.status == 401:
            signup_and_verify(owner, api, outbox, {'name':'Platform owner','email':OWNER_EMAIL,'password':PASSWORD})
        else:
            assert initial.ok, initial.text()
        me = owner.request.get(api + '/api/auth/me').json()['user']
        if me['platform_role'] != 'owner':
            source = "import json,sys;sys.path.insert(0,sys.argv[1]);from backend.owner import claim_owner;d=json.load(sys.stdin);claim_owner(d['database'],d['email'],d['password'])"
            bootstrap = subprocess.run([python, '-c', source, str(Path(__file__).resolve().parents[1])],
                input=json.dumps({'database':database,'email':OWNER_EMAIL,'password':PASSWORD}),
                capture_output=True, text=True)
            assert bootstrap.returncode == 0, bootstrap.stderr
            login(owner, api, OWNER_EMAIL)
        owner_id = owner.request.get(api + '/api/auth/me').json()['user']['id']
        member = browser.new_context(viewport={'width': 1440, 'height': 1000}, reduced_motion='reduce')
        member_email = f'member-browser-{time.time_ns()}@example.com'
        member_id = signup_and_verify(member, api, outbox,
            {'name':'Mazag Coffee','email':member_email,'password':PASSWORD}).json()['user']['id']
        campaign_data = {'name':'Mazag coffee enquiries','product':'Two packs of ground coffee, 250 grams each',
            'audience':'Home coffee makers in Cairo','country':'Egypt','platform':'Facebook',
            'budget':'2380 EGP / 14 days','goal':'Messages'}
        made = member.request.post(api + '/api/campaigns', data=campaign_data)
        assert made.ok, made.text()
        campaign_id = made.json()['campaign']['id']
        creative_data = {'brand':'Mazag Coffee','product':'Two coffee packs, 250 grams each',
            'audience':'Home coffee makers in Cairo','benefit':'Choose the grind for your brewing tool',
            'offer':'500 EGP for two packs. Shipping depends on the address.',
            'cta':'Ask for details','language':'en','tone':'friendly','channel':'meta','goal':'leads',
            'generation_mode':'local','funnel_stage':'full','domain':'auto','content_length':'standard'}
        generated = member.request.post(api + '/api/creative/generate', data={'brief':creative_data})
        assert generated.ok, generated.text()
        project_id = generated.json()['version']['project_id']
        first_version_id = generated.json()['version']['id']
        # Build real local history so administration must page through more than20 versions.
        for _ in range(20):
            additional = member.request.post(api + '/api/creative/generate', data={'brief':creative_data,'project_id':project_id})
            assert additional.ok, additional.text()

        def new_page(context):
            page = context.new_page()
            page.on('pageerror', lambda error: errors.append(str(error)))
            page.route('http://localhost:3000/api/**', lambda route: route.continue_(url=route.request.url.replace('http://localhost:3000', api)))
            return page

        member_page = new_page(member)
        member_page.goto(frontend + '/app')
        expect(member_page.locator('.workspace-account strong')).to_have_text('Mazag Coffee')
        expect(member_page.locator('[data-page=owner]')).to_have_count(0)
        assert member.request.get(api + '/api/owner/overview').status == 403

        page = new_page(owner)
        page.goto(frontend + '/app')
        page.locator('[data-page=owner]').click()
        expect(page.locator('.owner-metric')).to_have_count(4)
        totals = owner.request.get(api + '/api/owner/overview').json()['overview']
        expect(page.locator('.owner-metric').nth(0).locator('strong')).to_have_text(f"{totals['users']['total']:,}")
        expect(page.locator('.owner-metric').nth(1).locator('strong')).to_have_text(f"{totals['campaigns']['total']:,}")
        expect(page.locator('.owner-service-list')).to_contain_text('Local previews')
        expect(page.locator('.owner-scope-note')).to_contain_text('not measured')

        def tab(name):
            page.locator(f'[data-owner-tab={name}]').click()
            expect(page.locator('#ownerPanel')).not_to_have_attribute('aria-busy', 'true')

        def search(email):
            page.locator('#ownerUserSearch').fill(email)
            page.locator('#ownerSearchForm button[type=submit]').click()
            expect(page.locator('#ownerPanel tbody tr')).to_have_count(1)
            expect(page.locator('#ownerPanel tbody')).to_contain_text(email)

        def confirm(reason, password=PASSWORD):
            dialog = page.locator('.owner-dialog')
            expect(dialog).to_be_visible()
            dialog.locator('[name=reason]').fill(reason)
            dialog.locator('[name=current_password]').fill(password)
            dialog.locator('[type=submit]').click()
            return dialog

        def customer_profile():
            tab('users')
            search(member_email)
            page.locator(f'[data-owner-action=user][data-id="{member_id}"]').click()
            expect(page.locator('.owner-customer-card')).to_contain_text(member_email)
            expect(page.locator('#ownerCareNoteForm')).to_be_visible()

        def support_filter(status='open', priority='all'):
            form = page.locator('#ownerSupportFilters')
            form.locator('[name=status]').select_option(status)
            form.locator('[name=priority]').select_option(priority)
            with page.expect_response(lambda response:'/api/owner/support?' in response.url and response.request.method=='GET') as filtered:
                form.locator('[type=submit]').click()
            assert filtered.value.ok, filtered.value.text()
            expect(page.locator('#ownerPanel')).not_to_have_attribute('aria-busy', 'true')

        def update_ticket(ticket_id, status, priority='high', due_at=None):
            form = page.locator(f'#ownerSupportTicketForm{ticket_id}')
            form.locator('[name=status]').select_option(status)
            form.locator('[name=priority]').select_option(priority)
            if due_at is not None:
                form.locator('[name=due_at]').fill(due_at)
            with page.expect_response(lambda response:response.url.endswith(f'/api/owner/support/{ticket_id}') and response.request.method=='PATCH') as updated:
                form.locator('[type=submit]').click()
            assert updated.value.ok, updated.value.text()
            expect(page.locator('#ownerPanel')).not_to_have_attribute('aria-busy', 'true')
            return updated.value.json()['ticket']

        # Care data is grounded in actual signup/session creation and saved member work.
        customer_profile()
        care_response = owner.request.get(api + f'/api/owner/customers/{member_id}/care')
        assert care_response.ok, care_response.text()
        care = care_response.json()['care']
        assert care['last_sign_in'] and care['last_seen_at']
        assert care['last_sign_in_evidence_source'] == 'recorded_sign_in'
        assert any(item['kind']=='campaigns' and item['title']==campaign_data['name'] for item in care['activity'])
        assert any(item['kind']=='creative' and item['title']==creative_data['brand'] for item in care['activity'])
        expect(page.locator('.owner-care-presence')).to_contain_text('Last sign-in')
        expect(page.locator('.owner-care-presence')).to_contain_text('Last workspace activity')
        expect(page.locator('.owner-care-summary')).to_contain_text('every five minutes')
        expect(page.get_by_text('Online now', exact=True)).to_have_count(0)
        expect(page.locator('.owner-care-activity')).to_contain_text(campaign_data['name'])
        expect(page.locator('.owner-care-activity')).to_contain_text(creative_data['brand'])

        note_body = 'PRIVATE_CARE_NOTE: grind question <img src=x onerror="window.careXss=true">'
        ticket_subject = 'Review first coffee campaign <img src=x onerror="window.careXss=true">'
        ticket_description = 'PRIVATE_CARE_DESCRIPTION: discuss the actual offer and preferred grind.'
        today = datetime.now(timezone.utc).date()
        overdue_date = (today-timedelta(days=1)).isoformat()
        future_date = (today+timedelta(days=3)).isoformat()
        # Saving a private note must retain another in-progress customer form.
        page.locator('#ownerCareTicketForm [name=subject]').fill(ticket_subject)
        page.locator('#ownerCareTicketForm [name=description]').fill(ticket_description)
        page.locator('#ownerCareNoteForm [name=body]').fill(note_body)
        with page.expect_response(lambda response:response.url.endswith(f'/api/owner/customers/{member_id}/notes') and response.request.method=='POST') as noted:
            page.locator('#ownerCareNoteForm [type=submit]').click()
        assert noted.value.ok, noted.value.text()
        note_id = noted.value.json()['note']['id']
        expect(page.locator('.owner-care-notes')).to_contain_text(note_body)
        expect(page.locator('.owner-care-notes img')).to_have_count(0)
        expect(page.locator('#ownerCareNoteForm [name=body]')).to_have_value('')
        expect(page.locator('#ownerCareTicketForm [name=subject]')).to_have_value(ticket_subject)
        expect(page.locator('#ownerCareTicketForm [name=description]')).to_have_value(ticket_description)
        page.locator('#ownerCareTicketForm [name=priority]').select_option('high')
        page.locator('#ownerCareTicketForm [name=due_at]').fill(overdue_date)
        with page.expect_response(lambda response:response.url.endswith(f'/api/owner/customers/{member_id}/tickets') and response.request.method=='POST') as ticket_created:
            page.locator('#ownerCareTicketForm [type=submit]').click()
        assert ticket_created.value.ok, ticket_created.value.text()
        high_ticket = ticket_created.value.json()['ticket']
        high_id = high_ticket['id']
        expect(page.locator(f'#ownerSupportTicketForm{high_id}')).to_be_visible()
        expect(page.locator('.owner-support-ticket').filter(has=page.locator(f'#ownerSupportTicketForm{high_id}'))).to_contain_text('Overdue')
        expect(page.locator('.owner-support-ticket img')).to_have_count(0)
        expect(page.locator('.owner-care-summary')).to_contain_text('1 open follow-ups')
        expect(page.locator('.owner-care-summary')).to_contain_text('1 overdue')
        assert page.evaluate('window.careXss') is None
        expect(page.locator('.owner-dialog')).to_have_count(0)

        page.locator('#ownerCareTicketForm [name=subject]').fill('Check coffee product photos')
        page.locator('#ownerCareTicketForm [name=description]').fill('Confirm usable images before reviewing the ad.')
        page.locator('#ownerCareTicketForm [name=priority]').select_option('normal')
        page.locator('#ownerCareTicketForm [name=due_at]').fill(future_date)
        with page.expect_response(lambda response:response.url.endswith(f'/api/owner/customers/{member_id}/tickets') and response.request.method=='POST') as second_created:
            page.locator('#ownerCareTicketForm [type=submit]').click()
        assert second_created.value.ok, second_created.value.text()
        normal_id = second_created.value.json()['ticket']['id']
        expect(page.locator(f'#ownerSupportTicketForm{normal_id}')).to_be_visible()

        # Notes/tickets remain owner-only, including access by the related customer.
        for path in (f'/api/owner/customers/{member_id}/care','/api/owner/support'):
            denied = member.request.get(api + path)
            assert denied.status == 403 and 'PRIVATE_CARE_NOTE' not in denied.text()
        denied_note = member.request.post(api + f'/api/owner/customers/{member_id}/notes', data={'body':'Should not be saved'})
        assert denied_note.status == 403
        assert 'PRIVATE_CARE_NOTE' not in member.request.get(api + '/api/dashboard/overview').text()
        assert ticket_description not in member.request.get(api + '/api/auth/me').text()

        page.reload()
        expect(page.locator('.owner-metric')).to_have_count(4)
        customer_profile()
        expect(page.locator('.owner-care-notes')).to_contain_text(note_body)
        expect(page.locator(f'#ownerSupportTicketForm{high_id}')).to_be_visible()
        stored_care = owner.request.get(api + f'/api/owner/customers/{member_id}/care').json()['care']
        assert any(note['id']==note_id and note['body']==note_body for note in stored_care['notes'])
        assert stored_care['summary'] == {'open_tickets':2,'overdue_tickets':1}

        tab('support')
        expect(page.locator('.owner-support-summary .owner-metric').nth(0).locator('strong')).to_have_text('2')
        expect(page.locator('.owner-support-summary .owner-metric').nth(1).locator('strong')).to_have_text('1')
        support_filter('new','high')
        expect(page.locator('.owner-support-ticket')).to_have_count(1)
        expect(page.locator(f'#ownerSupportTicketForm{high_id}')).to_be_visible()
        support_filter('new','normal')
        expect(page.locator('.owner-support-ticket')).to_have_count(1)
        expect(page.locator(f'#ownerSupportTicketForm{normal_id}')).to_be_visible()
        support_filter('resolved','all')
        expect(page.locator('.owner-support-ticket')).to_have_count(0)
        support_filter('open','high')
        updated = update_ticket(high_id, 'in_progress')
        assert updated['status']=='in_progress' and updated['priority']=='high'
        expect(page.locator(f'#ownerSupportTicketForm{high_id} [name=status]')).to_have_value('in_progress')
        updated = update_ticket(high_id, 'waiting_customer')
        assert updated['status']=='waiting_customer'
        expect(page.locator(f'#ownerSupportTicketForm{high_id} [name=status]')).to_have_value('waiting_customer')
        updated = update_ticket(high_id, 'resolved')
        assert updated['status']=='resolved' and updated['resolved_at']
        expect(page.locator('.owner-support-ticket')).to_have_count(0)
        expect(page.locator('.owner-support-summary .owner-metric').nth(0).locator('strong')).to_have_text('1')
        expect(page.locator('.owner-support-summary .owner-metric').nth(1).locator('strong')).to_have_text('0')
        support_filter('resolved','high')
        expect(page.locator(f'#ownerSupportTicketForm{high_id}')).to_be_visible()
        expect(page.locator('.owner-support-ticket')).to_contain_text(ticket_subject)
        expect(page.locator('.owner-support-ticket')).to_contain_text(ticket_description)
        expect(page.locator('.owner-support-ticket img')).to_have_count(0)
        assert page.evaluate('window.careXss') is None
        customer_profile()
        expect(page.locator('.owner-care-summary')).to_contain_text('1 open follow-ups')
        expect(page.locator('.owner-care-summary')).not_to_contain_text('overdue')

        # Content is private even inside the audit trail; action metadata retains IDs.
        care_audit=[]
        audit_page=1
        while True:
            audit_response=owner.request.get(api + f'/api/owner/audit?page={audit_page}').json()
            care_audit.extend(audit_response['events'])
            if len(care_audit)>=audit_response['total']:break
            audit_page+=1
        audit_dump=json.dumps(care_audit)
        assert 'PRIVATE_CARE_NOTE' not in audit_dump and 'Review first coffee campaign' not in audit_dump and 'PRIVATE_CARE_DESCRIPTION' not in audit_dump
        assert any(event['action']=='owner.customer_note_added' and event['details'].get('note_id')==note_id for event in care_audit)
        assert any(event['action']=='owner.support_ticket_created' and event['target_id']==high_id for event in care_audit)
        assert any(event['action']=='owner.support_ticket_updated' and event['target_id']==high_id for event in care_audit)

        tab('users')
        search(member_email)
        page.locator(f'[data-owner-action=user][data-id="{member_id}"]').click()
        expect(page.locator('.owner-customer-card')).to_contain_text(member_email)
        page.locator('[data-owner-action=user-status]').click()
        dialog = confirm('Browser fixture: confirm password rejection', 'Incorrect fixture password!')
        expect(dialog.locator('[role=alert]')).to_be_visible()
        expect(dialog.locator('[name=current_password]')).to_have_value('')
        page.keyboard.press('Escape')
        expect(page.locator('.owner-dialog')).to_have_count(0)
        page.locator('[data-owner-action=user-status]').click()
        confirm('Browser fixture: suspend this customer')
        expect(page.locator('.owner-dialog')).to_have_count(0)
        expect(page.locator('.owner-customer-card')).to_contain_text('Suspended')
        assert member.request.get(api + '/api/auth/me').status == 401
        page.locator('[data-owner-action=user-status]').click()
        confirm('Browser fixture: restore customer access')
        expect(page.locator('.owner-customer-card [data-owner-action=user-status]')).to_have_text('Suspend access')
        login(member, api, member_email)
        page.locator('[data-owner-action=revoke]').click()
        confirm('Browser fixture: revoke customer sessions')
        expect(page.locator('.owner-dialog')).to_have_count(0)
        assert member.request.get(api + '/api/auth/me').status == 401
        login(member, api, member_email)

        tab('users')
        search(OWNER_EMAIL)
        page.locator(f'[data-owner-action=user][data-id="{owner_id}"]').click()
        expect(page.locator('[data-owner-action=user-status]')).to_be_disabled()
        expect(page.locator('[data-owner-action=revoke]')).to_be_disabled()
        tab('campaigns')
        page.locator(f'[data-owner-action=record][data-kind=campaigns][data-id="{campaign_id}"]').click()
        expect(page.locator('.owner-record-facts')).to_contain_text(campaign_data['product'])
        expect(page.locator('.owner-caption')).to_contain_text('does not publish')
        page.locator('[data-owner-action=campaign-status][data-status=Archived]').click()
        confirm('Browser fixture: archive the saved campaign')
        expect(page.locator('.owner-dialog')).to_have_count(0)
        expect(page.locator('[data-owner-action=campaign-status][data-status=Archived]')).to_be_disabled()
        saved = member.request.get(api + f'/api/campaigns/{campaign_id}').json()['campaign']
        assert saved['status'] == 'Archived' and saved['product'] == campaign_data['product']
        tab('content')
        page.locator(f'[data-owner-action=record][data-kind=creative][data-id="{project_id}"]').click()
        expect(page.locator('.owner-record-snapshot pre')).to_contain_text(creative_data['offer'])
        expect(page.locator('.owner-version-navigation')).to_contain_text('21 versions')
        first_history = json.loads(page.locator('.owner-record-snapshot pre').inner_text())
        assert len(first_history['versions']) == 20
        assert first_version_id not in {item['id'] for item in first_history['versions']}
        page.locator('[data-owner-action=version-page][data-page="2"]').click()
        expect(page.locator('.owner-version-navigation')).to_contain_text('Page 2 of 2')
        last_history = json.loads(page.locator('.owner-record-snapshot pre').inner_text())
        assert len(last_history['versions']) == 1 and last_history['versions'][0]['id'] == first_version_id

        tab('settings')
        announcement = 'Service note <img src=x onerror="window.ownerXss=true">'
        page.locator('#ownerSettingsForm [name=announcement]').fill(announcement)
        page.locator('#ownerSettingsForm [name=maintenance]').check()
        page.locator('#ownerSettingsForm [type=submit]').click()
        confirm('Browser fixture: pause member workspace changes')
        expect(page.locator('.owner-dialog')).to_have_count(0)
        expect(page.locator('#ownerSettingsForm [name=maintenance]')).to_be_checked()
        rejected = member.request.post(api + '/api/campaigns/preview', data=campaign_data)
        assert rejected.status == 503 and rejected.json()['code'] == 'maintenance'
        assert member.request.get(api + '/api/campaigns').ok
        assert member.request.get(api + '/api/auth/me').ok
        assert owner.request.post(api + '/api/campaigns/preview', data=campaign_data).ok
        member_page.goto(frontend + '/app')
        expect(member_page.locator('#platformNotice')).to_contain_text(announcement)
        expect(member_page.locator('#platformNotice img')).to_have_count(0)
        assert member_page.evaluate('window.ownerXss') is None
        page.locator('#ownerSettingsForm [name=maintenance]').uncheck()
        page.locator('#ownerSettingsForm [name=announcement]').fill('')
        page.locator('#ownerSettingsForm [type=submit]').click()
        confirm('Browser fixture: restore member workspace changes')
        expect(page.locator('.owner-dialog')).to_have_count(0)
        assert member.request.post(api + '/api/campaigns/preview', data=campaign_data).ok

        tab('activity')
        expect(page.locator('.owner-audit-list')).to_contain_text('owner.user_status')
        expect(page.locator('.owner-audit-list')).to_contain_text('owner.record_view')
        expect(page.locator('.owner-audit-list')).to_contain_text('owner.campaign_status')
        expect(page.locator('.owner-audit-list')).to_contain_text('owner.settings')
        audit_text = page.locator('.owner-audit-list').inner_text()
        assert PASSWORD not in audit_text and 'Incorrect fixture password!' not in audit_text
        tab('overview')
        page.locator('[data-owner-tab=overview]').focus()
        page.keyboard.press('End')
        expect(page.locator('[data-owner-tab=settings]')).to_have_attribute('aria-selected', 'true')
        page.keyboard.press('Home')
        expect(page.locator('[data-owner-tab=overview]')).to_have_attribute('aria-selected', 'true')
        expect(page.locator('.owner-metric')).to_have_count(4)
        page.locator('[data-owner-action=refresh]').click()
        expect(page.locator('.owner-metric')).to_have_count(4)

        for theme in ('dark', 'light'):
            if page.locator('html').get_attribute('data-mf-theme') != theme:
                page.locator('#workspaceThemeToggle').click()
            for section in ('overview', 'users', 'settings', 'support', 'customer-profile'):
                if section=='customer-profile':
                    customer_profile()
                else:
                    tab(section)
                    if section=='support':support_filter('all','all')
                for width in (1440, 768, 390, 320):
                    page.set_viewport_size({'width':width,'height':1000 if width>800 else 844})
                    assert page.evaluate('document.documentElement.scrollWidth <= innerWidth'), (theme, section, width)
                    if width in (1440, 390):
                        page.evaluate("document.activeElement?.blur();window.scrollTo({top:0,behavior:'instant'})")
                        page.screenshot(path=str(output / f'owner-{section}-{theme}-{width}.png'),full_page=True)
        page.reload()
        expect(page.locator('.owner-metric')).to_have_count(4)
        expect(page.locator('[data-page=owner]')).to_have_count(1)
        assert not errors, errors
        print(json.dumps({'owner_bootstrap_and_navigation':'passed','member_navigation_and_api_denial':'passed',
            'real_overview_and_search':'passed','reauth_password_clear_and_cancel':'passed',
            'suspend_restore_revoke_and_self_protection':'passed','audited_campaign_and_creative_review':'passed','creative_full_history_pagination':'passed',
            'settings_maintenance_and_escaped_announcement':'passed','audit_keyboard_refresh_reload':'passed',
            'customer_activity_evidence':'passed','private_note_escape_persistence_and_draft_retention':'passed',
            'support_priority_due_date_filters_and_resolution':'passed','customer_care_privacy_and_audit_metadata':'passed',
            'themes':['dark','light'],'responsive_widths':[1440,768,390,320],'browser_errors':errors}))
        browser.close()


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--api',default='http://localhost:3009')
    parser.add_argument('--frontend',default='http://localhost:5173')
    parser.add_argument('--outbox',required=True)
    parser.add_argument('--database',required=True)
    parser.add_argument('--python',default='/tmp/mf-owner-venv/bin/python')
    parser.add_argument('--output',default='/tmp/mf-owner-evidence')
    args = parser.parse_args()
    run(args.api,args.frontend,args.outbox,args.database,args.python,args.output)
