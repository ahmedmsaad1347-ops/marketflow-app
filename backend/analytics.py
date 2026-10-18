"""Read-only reporting: one currency per report, weighted ratios, UTC date windows."""
from datetime import datetime, timedelta

FIELDS = ('impressions', 'reach', 'clicks', 'messages', 'message_leads',
          'leads', 'conversions', 'spend', 'revenue')
SUMS = ', '.join(f'COALESCE(SUM({field}), 0) AS {field}' for field in FIELDS)
CURRENCY = "UPPER(COALESCE(NULLIF(TRIM(currency), ''), 'UNKNOWN'))"


def metrics(row):
    result = {field: row[field] or 0 for field in FIELDS}
    # Use the underlying totals for ratios; never average per-row ratios.
    for name, numerator, denominator, factor in (
        ('roas', 'revenue', 'spend', 1), ('cpa', 'spend', 'conversions', 1),
        ('cpl', 'spend', 'leads', 1), ('cpc', 'spend', 'clicks', 1),
        ('ctr', 'clicks', 'impressions', 100),
        ('conversion_rate', 'conversions', 'clicks', 100),
    ):
        result[name] = round(result[numerator] / result[denominator] * factor, 2) if result[denominator] else None
    for field in ('spend', 'revenue'):
        result[field] = round(result[field], 2)
    return result


def percent_change(current, previous):
    if current is None or previous is None or previous == 0:
        return 0 if current == previous == 0 else None
    return round((current - previous) / abs(previous) * 100, 2)


def overview(db, user_id, days=30, provider='all', currency='', today=None):
    if days not in (7, 30, 90, 365):
        raise ValueError('days must be 7, 30, 90 or 365')
    today = today or datetime.utcnow().date()
    start = today - timedelta(days=days - 1)
    previous_end = start - timedelta(days=1)
    previous_start = previous_end - timedelta(days=days - 1)
    sources = db.execute(f'''SELECT DISTINCT provider, {CURRENCY} AS currency
        FROM analytics_daily WHERE user_id = ? ORDER BY provider, currency''', (user_id,)).fetchall()
    providers = sorted({row['provider'] for row in sources})
    currencies = sorted({row['currency'] for row in sources})
    if provider != 'all' and provider not in providers:
        raise ValueError('Choose a data source available in your workspace')
    currency = currency.strip().upper()
    if currency and currency not in currencies:
        raise ValueError('Choose a currency available in your workspace')
    if not currency:
        currency = 'EGP' if 'EGP' in currencies else ('USD' if 'USD' in currencies else next(iter(currencies), None))

    where, parameters = 'user_id = ?', [user_id]
    if provider != 'all':
        where += ' AND provider = ?'
        parameters.append(provider)
    if currency:
        where += f' AND {CURRENCY} = ?'
        parameters.append(currency)

    def window(first, last):
        return where + ' AND date >= ? AND date <= ?', [*parameters, first.isoformat(), last.isoformat()]

    current_where, current_parameters = window(start, today)
    previous_where, previous_parameters = window(previous_start, previous_end)
    current = metrics(db.execute(f'SELECT {SUMS} FROM analytics_daily WHERE {current_where}', current_parameters).fetchone())
    previous = metrics(db.execute(f'SELECT {SUMS} FROM analytics_daily WHERE {previous_where}', previous_parameters).fetchone())
    status = dict(db.execute(f'''SELECT COUNT(*) AS records, COUNT(DISTINCT provider) AS providers,
        COUNT(DISTINCT date) AS days_with_data, MAX(updated_at) AS last_updated
        FROM analytics_daily WHERE {current_where}''', current_parameters).fetchone())
    previous_records = db.execute(f'SELECT COUNT(*) FROM analytics_daily WHERE {previous_where}', previous_parameters).fetchone()[0]
    daily = {row['date']: metrics(row) for row in db.execute(
        f'SELECT date, {SUMS} FROM analytics_daily WHERE {current_where} GROUP BY date ORDER BY date', current_parameters)}
    timeline = []
    for offset in range(days):
        key = (start + timedelta(days=offset)).isoformat()
        timeline.append({'date': key, 'has_data': key in daily,
                         **daily.get(key, metrics({field: 0 for field in FIELDS}))})
    platforms = [{'provider': row['provider'], **metrics(row)} for row in db.execute(
        f'''SELECT provider, {SUMS} FROM analytics_daily WHERE {current_where}
            GROUP BY provider ORDER BY revenue DESC, spend DESC, provider''', current_parameters)]
    campaigns = [{'provider': row['provider'], 'account_id': row['account_id'],
                  'campaign_id': row['campaign_id'], 'name': row['name'], **metrics(row)}
                 for row in db.execute(f'''SELECT provider, account_id, campaign_id,
                    COALESCE(NULLIF(MAX(campaign_name), ''), campaign_id) AS name, {SUMS}
                    FROM analytics_daily WHERE {current_where} AND campaign_id != ''
                    GROUP BY provider, account_id, campaign_id
                    ORDER BY revenue DESC, spend DESC, provider, account_id, campaign_id LIMIT 10''', current_parameters)]
    return {
        'success': True,
        'period': {'days': days, 'start': start.isoformat(), 'end': today.isoformat(),
                   'previous_start': previous_start.isoformat(), 'previous_end': previous_end.isoformat(), 'timezone': 'UTC'},
        'filters': {'provider': provider, 'currency': currency, 'providers': providers, 'currencies': currencies},
        'currency': currency, 'has_data': status['records'] > 0, 'has_any_data': bool(sources),
        'data_status': {**status, 'previous_records': previous_records},
        'summary': current, 'previous': previous,
        'comparison': {key: percent_change(current[key], previous[key]) for key in current},
        'timeline': timeline, 'platforms': platforms, 'top_campaigns': campaigns,
    }
