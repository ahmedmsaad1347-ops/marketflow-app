"""Landing navigation, keyboard interaction, and responsive layout checks."""
import argparse
from pathlib import Path
from playwright.sync_api import expect, sync_playwright


def run(frontend, output):
    Path(output).mkdir(parents=True, exist_ok=True)
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        for width, height in [(1440, 1000), (768, 1024), (390, 844), (320, 740)]:
            page = browser.new_page(viewport={'width': width, 'height': height})
            errors = []
            page.on('pageerror', lambda error: errors.append(str(error)))
            page.goto(frontend + '/', wait_until='networkidle')
            expect(page.locator('h1')).to_contain_text('A clearer plan.')
            assert page.evaluate('document.documentElement.scrollWidth <= innerWidth')
            signup = page.locator('.mf-nav-actions [data-route="/signup"]')
            box = signup.bounding_box()
            assert box['x'] >= 0 and box['x'] + box['width'] <= width
            page.get_by_role('tab', name='01 Brief').click()
            expect(page.locator('#mf-panel-brief')).to_be_visible()
            page.get_by_role('tab', name='01 Brief').press('ArrowRight')
            expect(page.get_by_role('tab', name='02 Strategy')).to_be_focused()
            expect(page.locator('#mf-panel-strategy')).to_be_visible()
            page.get_by_role('tab', name='03 Creative').click()
            expect(page.locator('#mf-panel-creative')).to_be_visible()
            page.locator('.mf-faq-items summary').first.click()
            assert page.locator('.mf-faq-items details').first.get_attribute('open') is not None
            page.get_by_role('tab', name='02 Strategy').click()
            page.evaluate('window.scrollTo(0, 0)')
            page.screenshot(path=str(Path(output) / f'landing-{width}.png'), full_page=True)
            if width == 390:
                page.screenshot(path=str(Path(output) / 'landing-mobile-top.png'))
            page.get_by_role('button', name='Build my first strategy').click()
            expect(page.locator('#signupForm')).to_be_visible()
            page.goto(frontend + '/')
            page.locator('.mf-nav-actions').get_by_role('button', name='Sign in').click()
            expect(page.locator('#realLoginForm')).to_be_visible()
            assert not errors, errors
            print(f'Landing {width}px: layout, tabs, keyboard, FAQ, signup and login PASS')
            page.close()
        browser.close()


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--frontend', default='http://localhost:5173')
    parser.add_argument('--output', default='/tmp/marketflow-landing-report')
    args = parser.parse_args()
    run(args.frontend, args.output)
