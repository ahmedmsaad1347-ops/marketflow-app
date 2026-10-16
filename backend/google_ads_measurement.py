"""Normalize disjoint Google conversion report rows without counting leads as sales."""
import math


def summarize_conversion_rows(rows):
    result = dict(message_leads=0, leads=0, qualified_leads=0,
                  conversions=0, revenue=0, unclassified_conversions=0)
    attribution = {}
    lead_categories = {'SUBMIT_LEAD_FORM', 'PHONE_CALL_LEAD', 'REQUEST_QUOTE',
                       'IMPORTED_LEAD', 'QUALIFIED_LEAD', 'CONVERTED_LEAD', 'MESSAGE_LEAD'}
    for row in rows:
        category = row.get('category', 'UNKNOWN')
        count = float(row.get('count', 0))
        value = float(row.get('value', 0))
        if not math.isfinite(count) or count < 0 or not math.isfinite(value):
            raise ValueError('Conversion metrics must be finite and counts non-negative.')
        if category in lead_categories:
            result['leads'] += count
            if category == 'MESSAGE_LEAD':
                result['message_leads'] += count
            if category == 'QUALIFIED_LEAD':
                result['qualified_leads'] += count
        elif category in {'PURCHASE', 'STORE_SALE'}:
            result['conversions'] += count
            result['revenue'] += value
        else:
            result['unclassified_conversions'] += count
        event = row.get('attribution_event_type', 'UNKNOWN')
        # CLICK describes attribution; it is not an additional sale or click.
        attribution[event] = attribution.get(event, 0) + count
    result['attribution_event_types'] = attribution
    return result
