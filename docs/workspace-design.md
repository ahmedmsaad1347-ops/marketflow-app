# Workspace and reporting — 2026-10-17

The interior now uses a responsive sidebar, mobile bottom navigation and an accessible additional-tools drawer. Existing strategy editing, research/review, saved versions and campaign actions remain available. Light and Deep Blue apply to all workspace screens and native inputs, while public/auth pages retain their design. The `marketflow:theme` device preference survives reload/logout and synchronizes across tabs. Switching appearance does not replace forms or erase unsaved answers.

The new MarketFlow mark is an original generated PNG in `public/brand/marketflow-mark.png`; HTML typography supplies the wordmark. It is used in the workspace, landing page, authentication, favicon and touch icon. No vector source is supplied.

## Analytics

The Reports page provides 7/30/90/365-day windows, source and currency selection, previous-period comparisons, money/outcomes/traffic chart modes, per-channel spend, campaign breakdowns, and daily CSV export. Refresh re-reads saved imported results; it does not call ad-provider sync endpoints. Empty selections show dashes, not estimates. Failed refreshes keep and label the previous successful report, restore its selected filters, and allow retry. Source campaign names are escaped.

The API aggregates one currency at a time, with no exchange conversion. All metrics, timelines, channels and campaigns share the same user/date/provider/currency filters. ROAS/CPA/CPL/CPC/CTR and conversion rate use aggregate numerators and denominators. Undefined ratios return JSON null and display as —. Missing days are explicit chart gaps and blank CSV metrics; recorded zeros remain zeros. The equal-length preceding calendar window supplies comparisons. Dates are UTC; today's results can be incomplete. Campaign IDs remain distinct across ad accounts. Messages, message leads, leads and conversions remain separate; message leads are a subset of leads. Platform-reported conversions can overlap and are not deduplicated across sources. The current database ingestion contract expects disjoint daily campaign records; provider adapters remain responsible for attribution and correct normalization.

There is no demo-data switch or fabricated revenue in the app. Screenshot evidence is generated using clearly fictional fixtures in a disposable test database. Google/TikTok live ingestion and real email/social-login credentials remain separate integration work.

## Validation

- 87 unit/API checks pass, including six new analytics correctness checks.
- Vite production build passes.
- Workspace browser checks cover both themes at 320/390/768/1024/1440px, existing-chart recoloring, unsaved briefs, mobile tools/keyboard handling, reload, cross-tab changes and logout/login persistence.
- Analytics browser checks reconcile visible totals and CSV, test currency/source/period filters, previous windows, interactive charts, responsive layouts, request failure recovery, escaped campaign names and empty selections.
- Signup/verification/recovery/logout-retry and saved strategy editing/rebuild browser regressions pass. Mail uses private file previews in these checks; live email delivery is not established.
