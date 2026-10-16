"""Documented v26 checks, not a substitute for Google's validate_only request.

Provider facts enter through internal functions, never through a public brief.
No OAuth, campaign mutation, or assumed currency minimum is implemented here.
"""
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from decimal import Decimal, ROUND_FLOOR
import re

API_VERSION = 'v26'
RELEASE_DATE = '2026-10-14'
RELEASE_NOTES = 'https://developers.google.com/google-ads/api/docs/release-notes'


@dataclass(frozen=True)
class DemandGenMinimum:
    currency: str
    minimum_budget_per_day_micros: int
    fetched_at: datetime
    api_version: str = API_VERSION


def demand_gen_budget_check(currency, daily_budget_micros, minimum=None, now=None):
    now = now or datetime.now(timezone.utc)
    if (minimum is None or minimum.api_version != API_VERSION
            or minimum.currency != currency.upper()
            or minimum.minimum_budget_per_day_micros <= 0
            or minimum.fetched_at.tzinfo is None
            or not timedelta(0) <= now - minimum.fetched_at <= timedelta(hours=24)):
        return {'passed': False, 'code': 'demand_gen_minimum_unverified',
                'detail': 'Demand Gen requires a current Google currency minimum before recommendation.'}
    passed = daily_budget_micros >= minimum.minimum_budget_per_day_micros
    return {'passed': passed,
            'code': 'demand_gen_budget_ok' if passed else 'demand_gen_budget_too_low',
            'minimum_budget_per_day_micros': minimum.minimum_budget_per_day_micros,
            'currency': minimum.currency,
            'detail': ('Daily budget meets the retrieved currency minimum.' if passed else
                       'Daily budget is below the retrieved Demand Gen currency minimum.')}


def daily_micros(total_budget, days):
    """Round down so a fractional micro never incorrectly passes a minimum."""
    value = Decimal(str(total_budget)) * 1_000_000 / Decimal(str(days))
    if not value.is_finite() or value <= 0:
        raise ValueError('Daily budget must be finite and positive.')
    return int(value.to_integral_value(rounding=ROUND_FLOOR))


def conversion_tracking_settings(settings):
    """Preserve the new enums without interpreting unknown values as enabled."""
    return {
        'conversion_tracking_status': settings.get('conversion_tracking_status'),
        'enablement_setting': settings.get('enablement_setting'),
        'effective_enablement_setting': settings.get('effective_enablement_setting'),
        'legacy_field_present': 'enhanced_conversions_for_leads_enabled' in settings,
    }


def eu_declaration_required(campaign_criteria, *, upgraded_demand_gen=False,
                            active_ad_groups=None):
    """Use Google's returned criterion flags; don't guess EU status from text.

    None means evidence is incomplete. Empty campaign targeting is not evidence
    of an exemption. Empty active-ad-group targeting for upgraded DG is likewise
    incomplete, while no active groups is an explicit documented exemption.
    """
    def group_required(criteria):
        positive = [item for item in criteria if not item.get('negative', False)]
        if not positive:
            return None
        required = False
        unknown = False
        for item in positive:
            if item.get('type') in {'proximity', 'location_group'}:
                required = True
            elif item.get('type') == 'location':
                flag = item.get('require_eu_political_advertising_declaration')
                required = required or flag is True
                unknown = unknown or flag not in (True, False)
        has_location = any(item.get('type') == 'location' for item in positive)
        return True if required else (None if unknown or not has_location else False)

    if upgraded_demand_gen:
        if active_ad_groups is None:
            return None
        requirements = [group_required(group) for group in active_ad_groups]
        if True in requirements:
            return True
        return None if None in requirements else False
    return group_required(campaign_criteria)


def validate_google_ads_capabilities(campaign, *, minimum=None, tracking=None, now=None):
    issues = []
    version = campaign.get('api_version')
    kind = campaign.get('campaign_type')
    if version != API_VERSION:
        issues.append({'code': 'unsupported_api_version', 'detail': 'This validator covers v26 only.'})
    if kind not in {'Google Search', 'Performance Max', 'Demand Gen', 'Local Services Performance Max'}:
        issues.append({'code': 'unsupported_campaign_type', 'detail': 'Campaign type is not covered by this validator.'})
    amount = campaign.get('daily_budget_micros')
    if type(amount) is not int or amount <= 0:
        issues.append({'code': 'invalid_daily_budget', 'detail': 'Daily budget must be a positive integer in micros.'})
    if not re.fullmatch(r'[A-Z]{3}', campaign.get('currency', '')):
        issues.append({'code': 'invalid_currency', 'detail': 'Use the account ISO currency code.'})
    if kind == 'Demand Gen' and type(amount) is int and amount > 0:
        check = demand_gen_budget_check(campaign.get('currency', ''), amount, minimum, now)
        if not check['passed']:
            issues.append(check)
    if kind == 'Local Services Performance Max':
        settings = campaign.get('local_services_settings') or {}
        if not re.fullmatch(r'[A-Z]{2}', settings.get('country_code', '')):
            issues.append({'code': 'country_code_required', 'detail': 'Local Services PMax requires country_code.'})
        listing_id = str(settings.get('listing_id') or '').strip()
        if not re.fullmatch(r'[1-9][0-9]{0,18}', listing_id) or int(listing_id) > 2**63 - 1:
            issues.append({'code': 'listing_id_required', 'detail': 'Local Services PMax requires a valid int64 Google Business Profile listing_id.'})
    declaration = campaign.get('contains_eu_political_advertising')
    required = eu_declaration_required(
        campaign.get('criteria') or [],
        upgraded_demand_gen=kind == 'Demand Gen' and campaign.get('upgraded_targeting', False),
        active_ad_groups=campaign.get('active_ad_groups'),
    )
    if declaration not in {'CONTAINS_EU_POLITICAL_ADVERTISING', 'DOES_NOT_CONTAIN_EU_POLITICAL_ADVERTISING'}:
        if required is not False:
            issues.append({'code': 'eu_declaration_required' if required else 'eu_targeting_unverified',
                           'detail': 'A valid EU political advertising declaration or verified targeting exemption is required.'})
    measurement = conversion_tracking_settings(tracking or {})
    if tracking is None:
        issues.append({'code': 'measurement_settings_unverified',
                       'detail': 'Read account conversion settings before provider preflight.'})
    if measurement['legacy_field_present']:
        issues.append({'code': 'removed_conversion_field', 'detail': 'Read enablement_setting instead of the removed legacy field.'})
    return {'api_version': version, 'capability_snapshot': RELEASE_DATE,
            'passed': not issues, 'issues': issues, 'measurement': measurement,
            'requires_provider_validate_only': True, 'source': RELEASE_NOTES}


def register_currency_capabilities(get_db):
    db = get_db()
    db.execute('''CREATE TABLE IF NOT EXISTS google_ads_currency_capabilities (
        currency TEXT NOT NULL, api_version TEXT NOT NULL,
        minimum_budget_per_day_micros INTEGER NOT NULL, fetched_at TEXT NOT NULL,
        PRIMARY KEY(currency, api_version)
    )''')
    db.commit()
    db.close()


def save_currency_constant(db, row, fetched_at):
    """Internal hook for a future authenticated CurrencyConstant adapter.

    Input uses normalized snake_case field names, including int64 strings.
    """
    currency = row['code'].upper()
    amount = int(row['demand_gen_info']['minimum_budget_per_day_micros'])
    if not re.fullmatch(r'[A-Z]{3}', currency) or amount <= 0 or fetched_at.tzinfo is None:
        raise ValueError('Invalid CurrencyConstant snapshot.')
    db.execute('''INSERT INTO google_ads_currency_capabilities VALUES (?, ?, ?, ?)
        ON CONFLICT(currency, api_version) DO UPDATE SET
        minimum_budget_per_day_micros=excluded.minimum_budget_per_day_micros,
        fetched_at=excluded.fetched_at''', (currency, API_VERSION, amount, fetched_at.isoformat()))
    db.commit()


def load_currency_minimum(get_db, currency):
    db = get_db()
    row = db.execute('''SELECT * FROM google_ads_currency_capabilities
                        WHERE currency = ? AND api_version = ?''',
                     (currency.upper(), API_VERSION)).fetchone()
    db.close()
    if row is None:
        return None
    try:
        return DemandGenMinimum(row['currency'], row['minimum_budget_per_day_micros'],
                                datetime.fromisoformat(row['fetched_at']), row['api_version'])
    except ValueError:
        return None
