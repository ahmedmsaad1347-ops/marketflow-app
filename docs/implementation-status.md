# MarketFlow implementation handoff — 2026-10-16

## Sources and scope

Reviewed GitHub `main` at `848a81a` (2026-10-12, “Upgrade Research Strategy
Agent and persist sessions”) and the supplied
[Strategy Engine specification](https://app.notion.com/p/3f2ef14a17958115b1f2cfa1f455ecf1).
The separate ChatGPT conversation referred to as “تغير منصات 2” is not
available in this workspace. The future stages below are proposals based on
the repository and specification, not a reconstruction of that conversation.

## Existing implementation

- Guided and quick strategy briefs; deterministic channel scoring and
  campaign-type selection.
- Contribution-margin and lead economics; domain-aware creative generation.
- Saved strategy history and acceptance into a Draft campaign.
- Conversational Strategy Agent with persisted answers and resume/build flow.
- Best-effort web research, source snippets, and a rule-based strategy reviewer.

## Completed in this change

- Count only sources with retrieved content as evidence. Unreachable official
  seed links no longer pass the official-evidence check.
- Derive the official provider from the source hostname instead of trusting
  stored provider labels.
- Distinguish discovered links from retrieved pages and show retrieval state
  in the strategy result.
- Keep confidence limited: snippet retrieval does not verify every campaign
  claim. Missing evidence and unresolved flags require review; flags are not
  described as corrections already applied to the recommendation.
- Carry unresolved evidence and review issues into the risks and launch
  readiness shown with the strategy. Accept still creates a Draft only.
- Add offline regression tests and an isolated-database API journey test.

## Validation

```sh
python -m pip install -r requirements-dev.txt
python -m unittest discover -s tests -v
npm ci
npm run build
```

The API journey covers answering and resuming questions, rejecting premature
builds, saving and resuming the completed result, repeat builds, repeat
acceptance, Draft creation, and isolation between two users. Research is mocked
so the test is repeatable and makes no provider calls. Live research quality,
browser interaction, and real ad-provider integration are not established by
these tests.

## Proposed next stages, pending the other conversation's requirements

1. **Research reliability:** cap overall request duration and source work;
   expose research failure/partial completion; reject login, challenge, and
   consent pages as substantive evidence. Cite specific campaign claims to
   relevant documentation instead of treating general help pages as proof.
2. **Agent input and recovery:** validate each answer against allowed choices
   and numeric bounds before saving; support editing earlier answers and
   invalidating dependent results. Make concurrent build and accept requests
   produce one saved result and one campaign.
3. **Business reuse:** persist reusable business profiles and offers per user,
   prefill briefs, and retain the input snapshot for each generated strategy.
4. **Provider preparation:** finish the Meta connection interface, verify
   account/tracking readiness, then prepare provider-specific campaign payloads.
   Actual publishing requires a separate explicit launch confirmation, as the
   specification requires.

Each stage needs its own acceptance checks before being called complete.
