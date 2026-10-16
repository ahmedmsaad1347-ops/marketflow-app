"""Real browser checks against a disposable file-mail API; never a production account store."""
import argparse
import json
import os
import time
from pathlib import Path
from urllib.parse import urlsplit

from playwright.sync_api import expect, sync_playwright
from browser_auth_helpers import latest_link


def run(api, frontend, outbox, output):
    Path(output).mkdir(parents=True, exist_ok=True)
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True, **({'executable_path': os.environ['MF_TEST_CHROMIUM']} if os.getenv('MF_TEST_CHROMIUM') else {}))
        context = browser.new_context(viewport={'width': 1440, 'height': 1000})
        page = context.new_page()
        errors = []
        page.on('pageerror', lambda err: errors.append(str(err)))
        page.route('http://localhost:3000/api/**', lambda route: route.continue_(url=route.request.url.replace('http://localhost:3000', api)))
        for width in (1440, 768, 390, 320):
            page.set_viewport_size({'width': width, 'height': 950 if width > 800 else 844})
            page.goto(frontend + '/login')
            expect(page.locator('#realLoginForm')).to_be_visible()
            expect(page.locator('#socialAvailability')).to_contain_text('continue with email')
            assert page.evaluate('document.documentElement.scrollWidth <= innerWidth'), width
            if width in (1440, 390):
                page.screenshot(path=str(Path(output) / f'signin-{width}.png'), full_page=True)
        page.goto(frontend + '/signup')
        email = f'browser-{time.time_ns()}@example.com'
        password = 'Bright river streets in Cairo!'
        new_password = 'A fresh map through the desert!'
        page.locator('[name="name"]').fill('Ahmed Browser')
        page.locator('[name="email"]').fill(email)
        page.get_by_role('button', name='Continue with email', exact=True).click()
        expect(page.locator('#signupPassword')).to_be_visible()
        expect(page.locator('#signupDetails')).not_to_be_visible()
        page.locator('#editSignupDetails').click()
        expect(page.locator('[name="email"]')).to_have_value(email)
        page.get_by_role('button', name='Continue with email', exact=True).click()
        page.locator('[name="password"]').fill(password)
        page.locator('[data-toggle-password="auth-password"]').click()
        expect(page.locator('[name="password"]')).to_have_attribute('type', 'text')
        page.get_by_role('button', name='Hide password', exact=True).click()
        page.locator('[name="confirm_password"]').fill('A different long password!')
        page.get_by_role('button', name='Create my account').click()
        expect(page.locator('#authError')).to_contain_text('do not match')
        page.locator('[name="confirm_password"]').fill(password)
        page.screenshot(path=str(Path(output) / 'signup-password-mobile.png'), full_page=True)
        page.get_by_role('button', name='Create my account').click()
        expect(page).to_have_url(frontend + '/verify-email')
        expect(page.locator('#localEmailNote')).to_be_visible()
        assert context.request.get(api + '/api/auth/me').status == 401
        link = latest_link(outbox, email, 'verify')
        page.goto(frontend + urlsplit(link).path + '#' + urlsplit(link).fragment)
        expect(page.locator('#verifyEmailForm')).to_be_visible()
        assert '#' not in page.url
        page.screenshot(path=str(Path(output) / 'verify-email-mobile.png'), full_page=True)
        page.get_by_role('button', name='Confirm email & continue').click()
        expect(page).to_have_url(frontend + '/app')
        expect(page.get_by_role('button', name='Guide Me', exact=True)).to_be_visible()
        page.route('**/api/auth/logout', lambda route: route.fulfill(status=503, content_type='application/json', body='{"detail":"Temporary outage"}'))
        page.get_by_role('button', name='Logout', exact=True).click()
        expect(page.locator('#logoutError')).to_contain_text('Sign-out could not be confirmed')
        expect(page).to_have_url(frontend + '/app')
        assert context.request.get(api + '/api/auth/me').status == 200
        page.unroute('**/api/auth/logout')
        page.get_by_role('button', name='Retry sign out', exact=True).click()
        expect(page).to_have_url(frontend + '/login')
        page.get_by_role('button', name='Forgot password?').click()
        page.locator('[name="email"]').fill(email)
        page.get_by_role('button', name='Send reset link').click()
        expect(page.locator('#authNotice')).to_contain_text('If this address is eligible')
        link = latest_link(outbox, email, 'reset')
        page.goto(frontend + urlsplit(link).path + '#' + urlsplit(link).fragment)
        assert '#' not in page.url
        page.locator('[name="password"]').fill(new_password)
        page.locator('[name="confirm_password"]').fill(new_password)
        page.get_by_role('button', name='Update password').click()
        expect(page).to_have_url(frontend + '/login')
        expect(page.locator('#authNotice')).to_contain_text('Password updated')
        page.locator('[name="email"]').fill(email)
        page.locator('[name="password"]').fill(new_password)
        page.get_by_role('button', name='Sign in to MarketFlow').click()
        expect(page).to_have_url(frontend + '/app')
        expect(page.get_by_role('button', name='Guide Me', exact=True)).to_be_visible()
        # The browser must never store authentication passwords or tokens in web storage.
        stored = page.evaluate('JSON.stringify({...localStorage,...sessionStorage})')
        assert password not in stored and new_password not in stored and 'marketflow_session' not in stored
        assert not errors, errors
        print(json.dumps({'responsive_widths': [1440, 768, 390, 320], 'signup_steps_and_edit': 'passed',
            'password_toggle_and_mismatch': 'passed', 'verification_and_workspace': 'passed',
            'logout_outage_retry_reset_and_new_login': 'passed', 'token_fragment_scrubbed': 'passed', 'browser_errors': errors}))
        browser.close()


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--api', default='http://localhost:3000')
    parser.add_argument('--frontend', default='http://localhost:5173')
    parser.add_argument('--outbox', required=True)
    parser.add_argument('--output', default='/tmp/marketflow-auth-report')
    args = parser.parse_args()
    run(args.api, args.frontend, args.outbox, args.output)
