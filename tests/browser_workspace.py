"""Workspace appearance/navigation checks. Use a disposable API and DB only."""
import argparse
from datetime import datetime, timedelta
import json
import os
from pathlib import Path
import sqlite3
import time

from playwright.sync_api import expect, sync_playwright
from browser_auth_helpers import signup_and_verify


def seed_data(context, api, database, uid):
    database = Path(database).resolve()
    if not database.parent.name.startswith('mf-workspace-browser-'):
        raise AssertionError('Refusing to seed a database outside the disposable browser test directory')
    campaigns = [('FlowDesk · Search demand', 'Google Search', 'Ready'),
                 ('Summer launch · Creative test', 'Meta', 'Draft'),
                 ('Product discovery · First test', 'TikTok', 'Draft'),
                 ('Spring campaign · Learning archive', 'Meta', 'Archived')]
    for name, platform, status in campaigns:
        result = context.request.post(api + '/api/campaigns', data=dict(name=name, platform=platform,
            audience='Small online business owners', country='Egypt', budget='3000 EGP',
            goal='Qualified leads', product='Customer support software'))
        assert result.ok, result.text()
        cid = result.json()['campaign']['id']
        if status != 'Draft':
            result = context.request.patch(api + f'/api/campaigns/{cid}/status', data={'status': status})
            assert result.ok, result.text()
    with sqlite3.connect(database) as db:
        for offset in range(7):
            date = (datetime.now() - timedelta(days=6-offset)).date().isoformat()
            for provider, scale in [('google', 1), ('meta', 2)]:
                db.execute('''INSERT INTO analytics_daily
                    (user_id,date,provider,campaign_id,campaign_name,impressions,clicks,leads,conversions,spend,revenue,currency,created_at,updated_at)
                    VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)''',
                    (uid,date,provider,provider+'-sample',provider.title()+' sample campaign',1200+offset*180,
                     70+offset*8,12+offset,3+offset,35+offset*scale,120+offset*30*scale,'USD',date,date))


def choose_page(page, target):
    nav = page.locator(f'.workspace-sidebar [data-page="{target}"]')
    if not nav.is_visible():
        page.locator('#workspaceMenuToggle').click()
        expect(page.locator('#workspaceMenuToggle')).to_have_attribute('aria-expanded', 'true')
    nav.click()
    expect(nav).to_have_attribute('aria-current', 'page')
    page.wait_for_function('document.querySelector("#pageContent").querySelector(".page") !== null')


def check_overflow(page, label):
    assert page.evaluate('document.documentElement.scrollWidth <= innerWidth'), label


def contrast_ratio(a, b):
    def luminance(color):
        channel = [int(color[i:i+2], 16) / 255 for i in (1, 3, 5)]
        channel = [v / 12.92 if v <= .04045 else ((v+.055)/1.055)**2.4 for v in channel]
        return sum(v * w for v, w in zip(channel, [.2126, .7152, .0722]))
    light, dark = sorted([luminance(a), luminance(b)], reverse=True)
    return (light+.05)/(dark+.05)


def run(api, frontend, outbox, database, output):
    Path(output).mkdir(parents=True, exist_ok=True)
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True, **({'executable_path': os.environ['MF_TEST_CHROMIUM']} if os.getenv('MF_TEST_CHROMIUM') else {}))
        context = browser.new_context(viewport={'width':1440,'height':1050})
        email = f'workspace-{time.time_ns()}@example.com'
        password = 'A clear plan for the next move!'
        me = signup_and_verify(context, api, outbox, data={'name':'Ahmed', 'email':email, 'password':password})
        seed_data(context, api, database, me.json()['user']['id'])
        page = context.new_page()
        errors = []
        page.on('pageerror', lambda err: errors.append(str(err)))
        page.route('http://localhost:3000/api/**', lambda route: route.continue_(url=route.request.url.replace('http://localhost:3000', api)))
        page.goto(frontend + '/app')
        expect(page.locator('.workspace-page-heading h1')).to_contain_text('Ahmed')
        expect(page.locator('.workspace-stat-card > strong').first).to_have_text('4')
        expect(page.locator('.workspace-stat-card > strong').nth(1)).to_have_text('2')
        expect(page.locator('.workspace-sidebar .mf-brand-image')).to_be_visible()
        assert page.locator('.workspace-sidebar .mf-brand-image').evaluate('img => img.complete && img.naturalWidth > 0')
        expect(page.locator('html')).to_have_attribute('data-mf-theme', 'dark')
        for theme in ('dark','light'):
            page.locator(f'.workspace-sidebar-theme [data-theme-choice="{theme}"]').click()
            expect(page.locator('html')).to_have_attribute('data-mf-theme', theme)
            for width in (1440, 1024, 768, 390, 320):
                page.set_viewport_size({'width':width,'height':1050 if width > 800 else 844})
                check_overflow(page, f'dashboard {theme} {width}')
                if width in (1440,390):
                    page.screenshot(path=str(Path(output)/f'dashboard-{theme}-{width}.png'),full_page=True)
            page.set_viewport_size({'width':1440,'height':1050})
            palette = page.locator('.app-shell').evaluate("el => Object.fromEntries(['--mf-text','--mf-muted','--mf-faint','--mf-bg','--mf-surface'].map(k => [k,getComputedStyle(el).getPropertyValue(k).trim()]))")
            for text in ('--mf-text','--mf-muted','--mf-faint'):
                for background in ('--mf-bg','--mf-surface'):
                    assert contrast_ratio(palette[text],palette[background]) >= 4.5, (theme,text,background)
        # A theme change updates existing charts rather than rerendering the report or losing its range.
        choose_page(page, 'reports')
        expect(page.locator('#moneyChart')).to_be_visible()
        assert page.locator('#moneyChart').evaluate('el => el.width > 0')
        page.wait_for_timeout(300)
        light_canvas = page.locator('#moneyChart').evaluate('el => el.toDataURL()')
        page.locator('#workspaceThemeToggle').click()
        expect(page.locator('html')).to_have_attribute('data-mf-theme','dark')
        dark_canvas = page.locator('#moneyChart').evaluate('el => el.toDataURL()')
        assert light_canvas != dark_canvas
        page.screenshot(path=str(Path(output)/'reports-dark-desktop.png'),full_page=True)
        # Do not erase the user's unsaved brief when they change appearance.
        choose_page(page, 'dashboard')
        page.get_by_role('button', name='I Know What I Want', exact=True).click()
        expect(page.locator('#strategyForm')).to_be_visible()
        page.locator('[name="business_name"]').fill('Keep my business draft')
        page.locator('[name="product"]').fill('A product description that must survive theme switching')
        page.locator('#workspaceThemeToggle').click()
        expect(page.locator('[name="business_name"]')).to_have_value('Keep my business draft')
        expect(page.locator('[name="product"]')).to_have_value('A product description that must survive theme switching')
        page.screenshot(path=str(Path(output)/'strategy-light-desktop.png'),full_page=True)
        # Mobile menu, Escape, additional navigation and settings controls.
        page.set_viewport_size({'width':390,'height':844})
        page.locator('#workspaceMenuToggle').click()
        expect(page.locator('#workspaceSidebar')).to_have_attribute('aria-modal','true')
        page.keyboard.press('Escape')
        expect(page.locator('#workspaceMenuToggle')).to_be_focused()
        expect(page.locator('#workspaceMenuToggle')).to_have_attribute('aria-expanded','false')
        page.locator('#workspaceMenuToggle').click()
        page.set_viewport_size({'width':1440,'height':1050})
        expect(page.locator('#workspaceMenuToggle')).to_have_attribute('aria-expanded','false')
        assert page.evaluate('document.body.style.overflow') == ''
        page.set_viewport_size({'width':390,'height':844})
        choose_page(page,'settings')
        expect(page.locator('.workspace-appearance-card')).to_be_visible()
        page.locator('.workspace-theme-previews [data-theme-choice="dark"]').click()
        page.reload()
        expect(page.locator('.workspace-appearance-card')).to_be_visible()
        expect(page.locator('html')).to_have_attribute('data-mf-theme','dark')
        expect(page.locator('.workspace-theme-previews [data-theme-choice="dark"]')).to_have_attribute('aria-pressed','true')
        page.screenshot(path=str(Path(output)/'settings-dark-mobile.png'),full_page=True)
        for target in ('campaigns','reports','messages','ai','connections','strategy-history'):
            choose_page(page,target)
            for theme in ('light','dark'):
                if page.locator('html').get_attribute('data-mf-theme') != theme:
                    page.locator('#workspaceThemeToggle').click()
                for width in (390,320):
                    page.set_viewport_size({'width':width,'height':844})
                    check_overflow(page, f'{target} {theme} {width}')
        # A separate tab follows the saved device theme.
        other = context.new_page()
        other.route('http://localhost:3000/api/**', lambda route: route.continue_(url=route.request.url.replace('http://localhost:3000', api)))
        other.goto(frontend + '/app')
        page.locator('#workspaceThemeToggle').click()
        expect(other.locator('html')).to_have_attribute('data-mf-theme','light')
        other.close()
        # Leaving and re-entering the workspace does not apply the theme to marketing pages.
        page.goto(frontend + '/')
        expect(page.locator('.mf-landing')).to_be_visible()
        expect(page.locator('html')).to_have_attribute('data-workspace','false')
        assert page.locator('.mf-nav .mf-brand-image').evaluate('img => img.complete && img.naturalWidth > 0')
        page.goto(frontend + '/app')
        expect(page.locator('html')).to_have_attribute('data-mf-theme','light')
        page.get_by_role('button',name='Logout',exact=True).click()
        expect(page.locator('#realLoginForm')).to_be_visible()
        assert page.evaluate("localStorage.getItem('marketflow:theme')") == 'light'
        page.locator('[name="email"]').fill(email)
        page.locator('[name="password"]').fill(password)
        page.get_by_role('button',name='Sign in to MarketFlow').click()
        expect(page.locator('.workspace-dashboard')).to_be_visible()
        expect(page.locator('html')).to_have_attribute('data-mf-theme','light')
        assert not errors, errors
        print(json.dumps({'widths':[1440,1024,768,390,320],'themes':['dark','light'],
            'real_fixture_counts':'passed','charts_update':'passed','unsaved_brief_preserved':'passed',
            'mobile_menu_escape_and_tools':'passed','theme_reload_tabs_logout':'passed',
            'public_brand_and_theme_scope':'passed','text_token_contrast':'passed','browser_errors':errors}))
        browser.close()


if __name__ == '__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('--api',default='http://localhost:3008')
    parser.add_argument('--frontend',default='http://localhost:5173')
    parser.add_argument('--outbox',required=True)
    parser.add_argument('--database',required=True)
    parser.add_argument('--output',default='/tmp/marketflow-workspace-report')
    args=parser.parse_args()
    run(args.api,args.frontend,args.outbox,args.database,args.output)
