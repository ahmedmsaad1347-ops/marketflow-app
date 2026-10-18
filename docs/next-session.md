# MarketFlow continuation — 2026-10-18

## Deployment state

The user installed the workspace release through Termux, merged PR #4 and pulled main `70cd4a5`. The workspace, Light/Deep Blue themes, logo and currency-safe analytics are on main. Phone Python3.13/Node24 work; missing httpx/email-validator were installed in `.venv`. Servers use API127.0.0.1:3000 and Vite127.0.0.1:5173; Chrome consistently opens http://localhost:5173/app. This cloud workspace cannot control phone processes.

Email remains local file mode, not Gmail delivery. The user successfully verified by printing the latest private link with `tools/open_auth_email.py` and pasting the complete link into a new ordinary tab in the original Chrome profile. Never request private links or bypass verification. Google/Facebook sign-in and live ad-provider data still require their external configuration.

Cloud Git writes and connector PR creation previously returned 403. Do not retry without new authorization evidence; use the user's working Termux GitHub upload workflow.

## Current authorized work

After Save → Refine repeated old content, the user requested a professional TOFU/MOFU/BOFU content creator, then explicitly asked for a **local, no-AI/no-API engine because no API budget is available**. Do not center an API setup question or claim a key is required. User said they will return tomorrow; finish the authorized work now and leave a concrete handoff. Do not imply background work continues after the turn ends.

Implementation on `codex/creative-refine-fix`, based on main `70cd4a5`:

- Local generation is the default even with an existing API key. It uses standard Python rules/composition, with no external model/network calls and no new dependencies. Explicit optional AI mode is separate.
- 24 industry categories plus custom, auto/manual domain selection, short/standard/long length, user-selected Egyptian Arabic/MSA/English, channel/tone choices. Local composition uses supplied facts in their input language; it is not an arbitrary translator or offline LLM.
- Full funnel = one TOFU, one MOFU, one BOFU. A single stage = three angles. Supplied proof, stage, objective and rationale are retained. No fabricated outcomes/free trials/discounts.
- Eleven local edit controls and common English/Arabic feedback, including compound shorter+clearer. Refine starts from the saved manually edited choice. New hook retains body/headline/CTA/stage; shortening retains complete price/paid/free/negation/offer units. Unsupported/no-op edits explain the limitation and save no duplicate. New angle retains selected CTA and factual condition paragraphs; review is still required.
- Immutable results and saved choices/rating/review/history remain private. Old pre-funnel records work without migration. Nothing publishes to ad platforms or generates an image.

Validation: 105 unit/API checks and the production build pass. Creative browser journey covers local defaults/domains, full/single stage, actual shortening/new hooks, paid-offer retention, no-op handling, original restoration, Arabic RTL, theme persistence, failure recovery and widths320/390/768/1440. Optional AI uses mocks only. The installer/patch must be replayed against the base tree with repeat-install and private-file preservation before final delivery.

## Delivery and next phone step

Artifacts under `/workspace`: `marketflow-creative-update.pyz`, `.patch`, `.zip`, `MarketFlow-Creative-V2-Termux.txt`. Source release generator: `tools/package_creative_release.py`. These are a NEW creative update, not the already-merged workspace installer.

Stop both phone servers; download the new pyz into Android Download and run:

`python /sdcard/Download/marketflow-creative-update.pyz`

Installer creates/resumes `updates/creative-funnel-v2`, applies the release commit and pushes without force. It preserves private `.env`/DB, rejects dirty tracked work and incomplete Git operations. User creates/merges the printed PR from their own account, pulls main, restarts API and Vite separately, opens Creative Studio and leaves Writing engine=Local. No paid key needed. The full guide includes a fictional Arabic FlowDesk example and exact restart commands.

Use short Egyptian Arabic updates and one easy installer command. No subagents without explicit user/AGENTS authorization. Clearly distinguish ready source from deployed phone behavior and avoid claiming that changes were pushed or installed without evidence.
