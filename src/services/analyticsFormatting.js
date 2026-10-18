export const providerName = value => ({meta: 'Meta Ads', google: 'Google Ads', tiktok: 'TikTok Ads'}[value] || value);

export function formatNumber(value, digits = 2) {
  if (value === null || value === undefined || !Number.isFinite(Number(value))) return '—';
  return Number(value).toLocaleString(undefined, {maximumFractionDigits: digits});
}

export function formatMoney(value, currency) {
  return value === null || value === undefined ? '—' : `${formatNumber(value)}${currency ? ` ${currency}` : ''}`;
}

export function analyticsCSV(data) {
  const fields = ['date', 'has_data', 'spend', 'revenue', 'impressions', 'clicks', 'leads', 'message_leads', 'messages', 'conversions', 'roas', 'cpa', 'cpl', 'cpc', 'ctr', 'conversion_rate'];
  const quote = value => {
    const text = typeof value === 'string' && /^[\s]*[=+\-@]/.test(value) ? "'" + value : String(value ?? '');
    return `"${text.replaceAll('"', '""')}"`;
  };
  const rows = [['currency', 'provider', ...fields], ...data.timeline.map(row => [data.currency || '',
    data.filters?.provider || 'all', ...fields.map(key => row.has_data ? row[key] : (key === 'date' ? row.date : key === 'has_data' ? false : ''))])];
  return '\uFEFF' + rows.map(row => row.map(quote).join(',')).join('\r\n');
}
