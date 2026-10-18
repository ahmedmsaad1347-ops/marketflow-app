# Creative Studio — local content engine

Creative Studio creates editable marketing content without an AI account, API key or paid model call. The **local content engine is the default**, even when a server-side AI key is configured. It composes user-supplied facts with industry-specific writing rules. It is a bounded rules/templates system, not an offline language model; unsupported instructions return an explanation rather than an unchanged saved version. Generating and editing local content makes no external network requests. Installing dependencies, GitHub operations and other connected features may still need internet.

## Brief and funnel

The user chooses Egyptian Arabic, Modern Standard Arabic or English; there is no fixed default content language. Arabic editing uses RTL. In local mode, enter product facts in the desired content language: this engine does not translate arbitrary source text.

A brief supplies brand, product/service, audience, benefit, exact offer, CTA, channel, tone, goal, constraints and optional proof. Proof is user-supplied context, not independently verified evidence. Short, standard and long length choices are available. Supported channels are Instagram, Meta, TikTok, LinkedIn, Google and email. TikTok uses a spoken-script structure, email has a greeting/subject/closing, and initial Google descriptions/headlines fit 90/30 characters. A long offer is never cut mid-condition to meet Google limits; the interface flags missing full terms for review.

Full funnel produces one TOFU awareness ad, one MOFU consideration ad and one BOFU decision ad. Selecting one stage produces three different angles for that stage. TOFU introduces the topic/benefit with a low-pressure CTA. MOFU explains product fit and includes supplied proof; absent proof leads to product explanation and a question to evaluate. BOFU includes the stated offer and primary CTA. Cards and saved selections retain the stage, objective and rationale.

## Industry context

There are 24 industry categories plus Other/custom: software/SaaS, online stores, fashion, beauty, food, education, healthcare, fitness, real estate, finance, travel, professional services, home services, automotive, events, industry/B2B, local retail, entertainment, pets, children/family, handmade/design, nonprofit, energy and logistics. Auto-detection uses brief keywords; users can override it. Unknown projects use the custom category and supplied facts.

Categories provide topics, decision criteria and visual/production suggestions, never invented features, results or prices. Hooks, headlines, body frames and CTAs vary through independent selections; tone, language, channel, stage and length shape the result. Random variation is finite and does not guarantee that every new generation is unique.

## Editing and history

Users compare directions, edit the headline/hook/body/CTA/visual suggestion, rate fit, and save a choice with an optional manual-review checkbox. Refine saves the current selection first, then works from that selected, manually edited copy. Local edits include shorter, longer, clearer, calmer, bolder, benefit first, new hook, new angle, different CTA, formal and friendly. Buttons specify the action; common English/Arabic instructions and supported compound requests also work.

A new hook changes the hook while retaining the selected headline, body, CTA and stage. Shortening removes complete units while protecting the opening and numeric/paid/free/negation/offer conditions. A new angle rebuilds the stage-specific message and retains the manually selected CTA and condition-bearing paragraphs; inspect the result before use. Other edits alter the requested fields through explicit rules. Arbitrary semantic instructions and brand constraints are not fully understood by the local engine; use supported controls or manual editing. Changed brief facts require fresh funnel content before local refinement, avoiding a revision based on stale terms.

Unchanged prior copy, angle-label-only changes and duplicate candidates do not create new saved versions. Revisions can contain one to three changed choices. The immutable generated result and previously saved selections remain accessible through history. Old pre-funnel versions still load and refine, with missing stage shown as General draft. No database migration or account reset is required. Nothing is published or sent to an ad platform.

Projects/versions are private SQLite records isolated by verified user ID. Writes require existing CSRF checks. Rate limits are 60 local generations or 12 AI generations per user per 15 minutes. Inputs, output lengths, available indices and ratings are validated. Private responses use `Cache-Control: no-store`. In-progress brief values use this tab's session storage and existing logout cleanup; saved versions/selections live on the server.

## Optional AI

AI is an explicit optional mode. It requires a privately configured server `OPENAI_API_KEY`; choosing local never consumes that key. An unconfigured AI request returns a clear error without saving a version. Existing `python tools/setup_creative_ai.py` can configure a key through hidden terminal input in the virtualenv, followed by a backend restart. No key is needed for the local engine. Never share keys in chat, browser variables, screenshots or Git.

The optional provider receives only the brief/selected copy/feedback over HTTPS and returns structured output. Stage coverage and copy changes are validated. Provider failures preserve saved drafts and never silently substitute local content as AI output. Real provider calls have not been tested with the user's account; contract/error tests use mocks.

## Review and verification

The engine uses supplied facts; it does not verify their truth. Numerical/free-trial checks flag some unsupported wording, and Google character limits are not full policy validation. Review offer terms, claims, brand voice and rights before publishing. Visual ideas are textual production suggestions; this feature does not create images. Ratings come from the user, not synthetic satisfaction scores.

Validation: 105 unit/API tests pass, including cross-industry/language/channel output checks, maximum inputs, factual paid-offer preservation, default-local behavior with a configured key and zero provider calls, compound Arabic feedback, meaningful variation, no-op handling, history, ownership/CSRF, rate limits and legacy records. Production build passes. The browser journey checks full/single-stage generation, saved manual edits, actual shortening/new-hook changes, original restoration, local defaults/domain choices, Arabic RTL, request recovery, themes and 320/390/768/1440px layouts using a disposable account/database.
