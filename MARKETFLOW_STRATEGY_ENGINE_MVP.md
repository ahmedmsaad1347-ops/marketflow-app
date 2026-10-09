# MarketFlow Strategy Engine MVP

## Core journey

Dashboard → Guide Me / I Know What I Want → Business brief → Strategy recommendation → Accept Strategy → Draft Campaign

## Included in this MVP

- Guided four-step marketing brief.
- Quick-mode brief for experienced users.
- Platform recommendation.
- Funnel-stage recommendation.
- Objective and optimization-event recommendation.
- Single-channel-first budget logic.
- Break-even CPA and ROAS planning when price + gross margin are provided.
- Audience plan.
- Creative-angle plan.
- CTA recommendation.
- Tracking checklist.
- First-test logic.
- Launch-readiness warnings.
- Strategy persistence per authenticated user.
- One-click creation of a user-owned Draft campaign.

## Decision philosophy

This MVP uses deterministic marketing rules + business economics. It does not pretend to predict performance and does not need a paid AI API.

AI can later be layered on top for richer explanation, ad copy, scripts, creative concepts, competitor synthesis, and conversational follow-up.

## Safety behavior

Accepting a recommendation creates a Draft only. It does not publish an ad and does not spend money.


## Strategy Engine V2

- Candidate scoring instead of one direct platform rule.
- Campaign-type recommendation, not just platform name.
- Automation, audience, placement and bidding recommendations.
- Google Search / Performance Max / Demand Gen support.
- Meta Advantage+ campaign logic.
- TikTok Smart+ plus market-aware Search Ads eligibility.
- Versioned capability snapshot.
- Channel fit scorecard.
- Gross-margin CPA/ROAS is explicitly treated as a planning threshold until contribution-margin inputs are added.
