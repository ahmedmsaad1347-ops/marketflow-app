# Research quality, strategy editor, and landing page

Base: GitHub `main` commit `63b37da` (the merged V2.1 and Google v26 changes).

## Research quality

- Detect browser/bot challenge pages and exclude them from evidence. Challenge
  text, request IDs, and diagnostic page content are not stored as snippets.
- Prefer article/main content; remove navigation, headers, footers, forms,
  cookie/consent elements, scripts, and hidden text. Reject title-only and
  link-menu-only pages instead of calling them retrieved evidence.
- Allocate results across business background and platform guidance queries.
  Reserve the official seed and its retrieval status so a full list of business
  results cannot prevent the platform query from running.
- Group rejected sources with clear reasons. Collapse extracted text by default
  and distinguish background business context from official platform guidance.
- Preserve a missing-evidence warning if Meta pages cannot be retrieved. This
  change does not bypass a site's access restrictions or establish that a
  retrieved article is relevant or factually correct.

The live check of the user's Sales/Discovery example retrieved two usable
business-background extracts, rejected an F6S browser challenge, and reported
Meta's official seed as unavailable. The review correctly remained
`needs_review` rather than claiming official verification.

## Edit answers

- A running agent session has a **Review / edit answers** action.
- Saved results have **Edit answers & rebuild**, which prepopulates the brief
  with the original fields, numbers, selections, and readiness checkboxes.
- Editing an active/ready session saves corrected answers before rebuilding.
  Completed strategies create a new agent session and a new strategy, retaining
  the old output and its existing campaign link.
- Rebuilding an agent strategy retains web research and review. Guided/quick
  strategies retain their original deterministic generation path.
- Editor navigation can be restored after refresh from the saved server brief.
  Unsaved form changes are not auto-saved; save/build to persist corrections.
- Owners only can read or replace session answers. Building/completed sessions
  reject in-place edits. Input validation remains enforced on the server.

New internal app APIs:

- `POST /api/strategy-agent/revise`: create a new Ready session from a corrected
  `StrategyRequest` brief.
- `PUT /api/strategy-agent/{session_id}/answers`: replace the owner's active or
  ready session brief after validation.
- Resume responses include the owner's saved `answers`.

## Budget example

The user's actual inputs were Sales + Discovery, 3,000 EGP over 30 days,
1,000 EGP order/customer value, 70% gross margin, and 50 EGP variable costs.
The regression test preserves the original Advantage+ Sales recommendation.
Daily budget is 100 EGP, contribution per sale is 650 EGP, and the planning CPA
is 455 EGP. A planning warning now appears alongside the budget, rather than
only at the bottom of the result. The planning CPA is neither an expected
result nor a platform-enforced minimum.

## Landing page

- New English landing page with a dark background, mint/purple accents,
  MarketFlow branding, product narrative, and an interactive example strategy.
- Functional brief/strategy/creative tabs with keyboard navigation, signup and
  login actions, product anchors, FAQ disclosure controls, and mobile layouts.
- Features reflect the implemented workflow. Example numbers are marked as
  examples. There are no invented customer logos, testimonials, user counts,
  performance promises, or working-ad-integration claims.
- Description, social-sharing text, and browser theme metadata are included.
  There is no deployment, live domain, or live advertising in this update.

## Validation

36 offline tests pass, including the original test suite and regressions for
source extraction, challenge exclusion, balanced search coverage, the user's
budget, editor authorization/validation, and preservation of old strategies
and linked campaigns.

Browser checks passed:

- Editing a partially answered session and completing its brief.
- Prefilling and reloading the saved-strategy editor.
- Changing 3,000 → 30,000 EGP and Sales/Discovery → Leads/Search, obtaining a
  different saved result while the original stays intact.
- No JavaScript errors in the editor journey.
- Landing at 320, 390, 768, and 1440 px: layout, keyboard tabs, FAQ, signup/login,
  and visible navigation actions without horizontal overflow.

```sh
python -W ignore -m unittest discover -s tests -v
npm run build
python tests/browser_strategy_editor.py --api http://localhost:3005
python tests/browser_landing.py
```

The editor browser fixture used a disposable database and mocked research.
The independent research check used real public pages. Existing saved results
are not recomputed; build a new result to use the improved extractor.
