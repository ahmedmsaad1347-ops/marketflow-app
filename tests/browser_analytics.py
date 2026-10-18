"""Exercise reporting filters, real API totals, charts, exports and failure recovery."""
import argparse
import csv
from io import StringIO
import json
import os
from pathlib import Path
import sqlite3
import time
from datetime import datetime, timedelta
from playwright.sync_api import expect, sync_playwright
from browser_auth_helpers import signup_and_verify


def run(api, frontend, outbox, database, output):
    database=Path(database).resolve()
    assert database.parent.name.startswith('mf-workspace-browser-'), 'Disposable database required'
    Path(output).mkdir(parents=True,exist_ok=True)
    with sync_playwright() as p:
        browser=p.chromium.launch(headless=True, **({'executable_path':os.environ['MF_TEST_CHROMIUM']} if os.getenv('MF_TEST_CHROMIUM') else {}))
        context=browser.new_context(viewport={'width':1440,'height':1050},accept_downloads=True)
        me=signup_and_verify(context,api,outbox,data={'name':'Ahmed','email':f'analytics-{time.time_ns()}@example.com','password':'A clear view of every campaign!'})
        uid=me.json()['user']['id']
        today=datetime.utcnow().date()
        with sqlite3.connect(database) as db:
            for offset in range(14):
                date=(today-timedelta(days=offset)).isoformat()
                for provider,scale in [('google',1),('meta',2)]:
                    # Current period: EGP 630 spend / EGP 1,890 revenue. Previous: half.
                    factor=1 if offset<7 else .5
                    db.execute('''INSERT INTO analytics_daily
                        (user_id,date,provider,account_id,campaign_id,campaign_name,impressions,clicks,leads,message_leads,messages,conversions,spend,revenue,currency,created_at,updated_at)
                        VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)''',
                        (uid,date,provider,'account-'+provider,'campaign-'+provider,
                        'FlowDesk · '+('Search demand' if provider=='google' else 'Product discovery'),
                        1000*scale,50*scale,10*scale,2*scale,15*scale,3*scale,30*scale*factor,90*scale*factor,'EGP',date,date))
            db.execute('''INSERT INTO analytics_daily
                (user_id,date,provider,campaign_id,campaign_name,spend,revenue,currency,created_at,updated_at)
                VALUES (?,?,?,?,?,?,?,?,?,?)''',(uid,today.isoformat(),'google','usd','<img src=x onerror="window.injected=true">',2,4,'USD',today.isoformat(),today.isoformat()))
        page=context.new_page()
        errors=[]
        page.on('pageerror',lambda error:errors.append(str(error)))
        page.route('http://localhost:3000/api/**',lambda route:route.continue_(url=route.request.url.replace('http://localhost:3000',api)))
        page.goto(frontend+'/app')
        page.locator('.workspace-navigation [data-page="reports"]').click()
        expect(page.locator('.analytics-page')).to_be_visible()
        expect(page.locator('#analyticsCurrency')).to_have_value('EGP')
        page.locator('[data-analytics-days="7"]').click()
        expect(page.locator('[data-analytics-days="7"]')).to_have_attribute('aria-pressed','true')
        expect(page.locator('[data-metric="spend"] > strong')).to_have_text('630 EGP')
        expect(page.locator('[data-metric="revenue"] > strong')).to_have_text('1,890 EGP')
        expect(page.locator('[data-metric="roas"] > strong')).to_have_text('3×')
        expect(page.locator('[data-metric="spend"] .analytics-delta')).to_contain_text('100%')
        with page.expect_download() as download:
            page.locator('#analyticsExport').click()
        rows=list(csv.DictReader(StringIO(Path(download.value.path()).read_text(encoding='utf-8-sig'))))
        assert len(rows)==7
        assert {row['currency'] for row in rows}=={'EGP'}
        assert sum(float(row['spend']) for row in rows)==630
        for mode,title in [('traffic','Traffic over time'),('acquisition','Leads & conversions'),('money','Revenue & spend')]:
            page.locator(f'[data-analytics-chart="{mode}"]').click()
            expect(page.locator('#analyticsTrendTitle')).to_have_text(title)
        page.wait_for_timeout(450)
        page.screenshot(path=str(Path(output)/'analytics-dark-desktop.png'),full_page=True)
        page.locator('#workspaceThemeToggle').click()
        page.screenshot(path=str(Path(output)/'analytics-light-desktop.png'),full_page=True)
        page.locator('#analyticsProvider').select_option('google')
        expect(page.locator('[data-metric="spend"] > strong')).to_have_text('210 EGP')
        page.locator('#analyticsCurrency').select_option('USD')
        expect(page.locator('[data-metric="spend"] > strong')).to_have_text('2 USD')
        expect(page.locator('.analytics-campaign-name strong')).to_have_text('<img src=x onerror="window.injected=true">')
        assert not page.evaluate('Boolean(window.injected)')
        # A failed refresh retains and labels the previous successful selection.
        page.route('**/api/analytics/overview?**',lambda route:route.fulfill(status=503,content_type='application/json',body='{"detail":"Temporary outage"}'))
        page.locator('#analyticsCurrency').select_option('EGP')
        expect(page.locator('#analyticsFeedback')).to_contain_text('previous results are still shown')
        expect(page.locator('#analyticsCurrency')).to_have_value('USD')
        expect(page.locator('[data-metric="spend"] > strong')).to_have_text('2 USD')
        page.unroute('**/api/analytics/overview?**')
        page.locator('#analyticsCurrency').select_option('EGP')
        expect(page.locator('[data-metric="spend"] > strong')).to_have_text('210 EGP')
        page.locator('#analyticsProvider').select_option('all')
        expect(page.locator('[data-metric="spend"] > strong')).to_have_text('630 EGP')
        for theme in ('light','dark'):
            if page.locator('html').get_attribute('data-mf-theme')!=theme:
                page.locator('#workspaceThemeToggle').click()
            for width in (1024,768,390,320):
                page.set_viewport_size({'width':width,'height':844})
                assert page.evaluate('document.documentElement.scrollWidth <= innerWidth'),(theme,width)
                if width==390:
                    page.screenshot(path=str(Path(output)/f'analytics-{theme}-mobile.png'),full_page=True)
        # Empty current selection must not borrow results from a different currency/source.
        with sqlite3.connect(database) as db:
            db.execute('UPDATE analytics_daily SET date=? WHERE user_id=? AND currency=?',((today-timedelta(days=100)).isoformat(),uid,'USD'))
        page.locator('#analyticsCurrency').select_option('USD')
        expect(page.locator('.analytics-no-data h2')).to_have_text('No results for these filters.')
        expect(page.locator('[data-metric="spend"] > strong')).to_have_text('—')
        expect(page.locator('#analyticsExport')).to_be_disabled()
        expect(page.locator('#moneyChart')).to_have_count(0)
        assert not errors,errors
        print(json.dumps({'weighted_totals_and_currency':'passed','period_and_source_filters':'passed',
            'previous_period':'passed','chart_modes_and_themes':'passed','csv_matches_report':'passed',
            'failed_request_keeps_previous':'passed','campaign_names_escaped':'passed','empty_selection':'passed',
            'responsive_widths':[1440,1024,768,390,320],'browser_errors':errors}))
        browser.close()


if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('--api',default='http://localhost:3008')
    parser.add_argument('--frontend',default='http://localhost:5173')
    parser.add_argument('--outbox',required=True)
    parser.add_argument('--database',required=True)
    parser.add_argument('--output',default='/tmp/marketflow-analytics-report')
    args=parser.parse_args()
    run(args.api,args.frontend,args.outbox,args.database,args.output)
