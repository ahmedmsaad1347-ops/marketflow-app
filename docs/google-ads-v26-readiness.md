# Google Ads v26 readiness — 2026-10-16

Google's [release notes](https://developers.google.com/google-ads/api/docs/release-notes#v26_2026-10-14)
confirm the v26 release on 2026-10-14. This change prepares local validation
and measurement semantics; it does not activate a Google Ads connection.

## Implemented

- `backend/google_ads_capabilities.py` provides version-scoped checks for
  Demand Gen currency minimums, Local Services PMax required settings,
  Enhanced Conversions field migration, and political-ad declarations based on
  targeting. A successful local check still requires Google `validate_only`.
- Guided, quick, and agent-generated strategies exclude Demand Gen when its
  currency minimum is unavailable, mismatched, older than 24 hours, or above
  the proposed daily budget. Strategy results explain the exclusion.
- Trusted provider minimums have a versioned SQLite cache. A future adapter
  supplies normalized CurrencyConstant data through the internal
  `save_currency_constant` hook after a successful provider read. There is no
  public API allowing a brief to overwrite provider facts.
- Analytics stores and reports `message_leads` separately from raw messages,
  including summaries, comparisons, daily series, platforms, and campaigns.
  Existing databases receive an additive migration with zero for old records.
- `backend/google_ads_measurement.py` maps message interest into a lead subset,
  not sales or revenue. `QUALIFIED_LEAD` remains a distinct concept. Unknown
  categories stay unclassified; fractional attribution is preserved. `CLICK`
  is retained as an attribution dimension, not counted again as a sale/click.

## Provider contracts

### Currency minimum

Read `CurrencyConstant.demand_gen_info.minimum_budget_per_day_micros` in the
account currency. Cache the provider value and a timezone-aware retrieval time.
The 24-hour cache duration is MarketFlow policy, not a Google API guarantee.
The final provider preflight must refresh/recheck the value before mutation.

Daily-budget comparison uses integer micros and rounds down. The tests use
synthetic currency values, not published production minimums. Until Google is
connected and supplies facts, Demand Gen is excluded rather than assumed valid.

Official field reference:
[DemandGenInfo](https://developers.google.com/google-ads/api/reference/rpc/v26/CurrencyConstant.DemandGenInfo).

### Measurement

Read `conversion_tracking_status`, `enablement_setting`, and
`effective_enablement_setting` from the account. The conversion tracking ID
does not establish tracking readiness. Preserve unspecified/unknown settings;
do not interpret them as enabled. The removed
`enhanced_conversions_for_leads_enabled` field is flagged by v26 validation.
Enhanced Conversions being disabled is not itself treated as an API error.

The reporting helper expects disjoint conversion-category report rows in one
currency. Do not combine aggregate conversion totals with their segmented
rows. It does not deduplicate individual users or infer CRM qualification.
Pass its `message_leads`, `leads`, `conversions`, and `revenue` to the internal
analytics upsert; supply raw messages independently.

Official field reference:
[ConversionTrackingSetting](https://developers.google.com/google-ads/api/reference/rpc/v26/ConversionTrackingSetting).

### Local Services and regulatory checks

Local Services PMax requires an uppercase two-letter `country_code` and
an int64 Business Profile `listing_id`. These checks do not prove listing
ownership, market availability, category eligibility, or account agreements.
Those must be checked by the provider adapter before campaign creation.

EU-declaration exemptions depend on positive targeting and the provider's
`require_eu_political_advertising_declaration` flags. Negative EU exclusions
are not positive EU targeting. Proximity/location-group targets require the
declaration. Upgraded Demand Gen uses every active ad group's targeting, and
no active groups is an explicit exemption. Unknown geography does not prove
an exemption. This is API request validation, not approval of political ads.

Official field reference:
[LocalServicesPmaxCampaignSettings](https://developers.google.com/google-ads/api/reference/rpc/v26/Campaign.LocalServicesPmaxCampaignSettings).

## Validation and remaining integration

Twenty-seven automated tests pass, including migration of an old analytics
schema, currency-cache persistence, exact budget boundaries, stale/mismatched
facts, campaign selection, required settings, targeting exemptions, and lead
versus purchase reporting. The frontend production build and rendering checks
pass.

Remaining: Google OAuth/developer-token setup, live CurrencyConstant reads,
account conversion-settings reads, Google reporting ingestion, bidding and
full policy/asset validation, and the final provider `validate_only` request.
There is no Google campaign creation or launch route in this change. No live
Google account readiness or full bidding compatibility has been established.
