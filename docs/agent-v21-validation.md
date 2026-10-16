# Research Strategy Agent V2.1 validation

Requested sequence: persisted session → one Build Strategy button → web
research → review/correction → final saved result.

## Changes made after exercising the sequence

1. **Session persistence:** keep the session, conversation, and typed draft
   after a temporary resume failure. Offer retry instead of deleting saved
   work. A confirmed missing session (HTTP 404) can still be reset.
2. **One build:** retain the single disabled button while building. Claim the
   session in SQLite before research so a concurrent request returns HTTP 409
   rather than generating a second strategy. Failed builds release the claim;
   claims abandoned after a process crash can be reclaimed after three minutes.
   Timestamp ownership prevents an expired build overwriting a newer build.
3. **Research:** exercise the real DuckDuckGo and source-page retrieval path.
   Discovered links and retrieved page content remain distinct; general
   documentation is not treated as verification of every campaign claim.
4. **Review/correction:** show unresolved flags and evidence gaps. Apply the
   bounded CTA correction supported by an explicit trial offer, and record
   old/new values and the reason. Tracking or channel-justification issues
   remain unresolved flags rather than pretending to repair external setup.
5. **Final result:** use the same CTA in the main strategy and creative plan.
   Paid or unspecified-cost trials must not become “Free Trial.” Recover the
   completed result and browser history if the original build response was
   lost before the UI switched pages.

## Repeatable offline checks

```sh
python -m pip install -r requirements-dev.txt
python -W ignore -m unittest discover -s tests -v
npm run build
```

Fourteen offline tests cover evidence handling, correction, paid/free/no-trial
offers, session resume, retry after build failure, concurrent build rejection,
result persistence, repeated acceptance, Draft status, and user isolation.

## Browser and live-research check

Install Playwright and Chromium, then start Vite and the backend with a fresh
temporary database. This check creates a test user and strategy; do not point
it at a production database.

```sh
python -m pip install playwright
python -m playwright install chromium
python tests/browser_agent_v21.py --api http://localhost:3000
```

The browser check runs the complete sequence, including a simulated HTTP 503
on resume, refreshes during answering and before Build, a concurrent Build
request, actual web research, result reload, and recovery from a lost build
response. It writes a report, saved strategy JSON, and screenshot to
`/tmp/marketflow-v21-report` by default. Source availability can vary between
runs. Correction-specific cases are deterministic offline tests; the live
example may correctly have no corrections to apply.

## Remaining limits

- The research reviewer performs deterministic checks, not a general-purpose
  semantic fact-check of every ad claim.
- Research still runs synchronously with per-request timeouts. A job queue
  and overall deadline would improve responsiveness under slow networks.
- The build claim prevents concurrent duplicate strategies. Concurrent
  acceptance of a strategy into campaigns is a separate follow-up concern.
- These changes do not implement ad publishing or spend money.
