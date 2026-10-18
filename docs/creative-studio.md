# Creative Studio

Creative Studio lives in the workspace tools menu and can also be opened from the Strategy Agent or a saved strategy's creative section. Strategy import copies brand/product/audience/offer facts into a new brief; the user supplies a benefit, CTA and content language. There is no fixed default language. Available choices are Egyptian Arabic, Modern Standard Arabic and English, with RTL editing for Arabic.

A brief specifies the goal, channel, tone, facts, offer and brand constraints. Generation saves three alternative directions. Users compare them, select a direction, edit headline/hook/body/CTA/visual suggestion, rate how closely it fits, and save their choice with an optional manual-review checkbox. Feedback creates a new generated version after saving the current choice. The previous generated output, input snapshot and saved selection remain available in the version picker. A reviewed choice is still a draft; nothing is published or sent to an ad platform.

Projects/versions are private SQLite records, isolated by the verified user's ID. Writes require existing CSRF checks, and generation has a per-user limit of 12 requests per 15 minutes. Requests validate language, bounded inputs, three output variants, selection indices and ratings. Private responses use `Cache-Control: no-store`. In-progress brief values are stored in this browser tab's session storage and cleared by existing logout cleanup; generated versions and selections are saved on the server. Character counters flag Google headline/description overruns, but are not full advertising-policy validation.

## Activate the model

Set `OPENAI_API_KEY` privately in the project's ignored `.env`, optionally set `OPENAI_MODEL`, and restart the backend. Never put keys in Vite variables, browser storage, chat, Git patches or screenshots. The default model is `gpt-4.1-mini`; the configured model must support Chat Completions structured JSON output. Generation uses the server's HTTPS OpenAI API call, a bounded timeout, a three-variant schema and only the creative brief/selected draft/feedback as context. It does not send account passwords, emails or ad-provider credentials.

Without a key the studio clearly labels guided templates. They are functional editable drafts, not model responses. Simple shortening can be applied in guided mode, while detailed free-text revisions and brand-rule interpretation require the connected model or manual edits. Provider failures never silently substitute template copy as AI output. The existing legacy `/api/ai/generate` placeholder is unused by this studio and now requires authentication; the functional model route is `/api/creative/generate`.

The prompt prohibits invented prices, discounts, urgency, statistics, testimonials, guarantees, certifications and free trials. Rule-based checks flag numerical claims absent from the brief and some unsupported free-trial wording. These checks do not prove that all claims are true or detect every unsupported statement. The user reviews facts, offer, rights and brand voice before using copy. Visual ideas are production suggestions; no image-generation service is activated by this feature. Ratings reflect actual user input, never a synthetic satisfaction score.

## Validation

Six new unit/API checks cover language selection, all three guided locales, paid-offer preservation, manual edits/rating/review persistence, immutable generated versions, ownership/CSRF, server-side provider request context, generic provider failures, unsupported-number flags, bounds and rate limiting. Provider calls are mocked; a real OpenAI credential has not been available for a live generation test.

Browser checks exercise choosing a language, three alternatives, editing and saving a rated choice, reload restoration, revision history, Arabic RTL, theme changes without losing the brief, request-failure recovery, and 320/390/768/1440px layouts. They run against a disposable database and local verification outbox.

For a private interactive setup in Termux, run `python tools/setup_creative_ai.py` from the project/virtualenv. The key is entered with hidden terminal input. The tool checks model access without generating content, then atomically writes the ignored `.env` with mode 0600 and preserves SMTP/Meta settings. It refuses tracked/symlinked configuration. Model access does not prove that generation permissions, supported schema or billing are ready; the first actual request establishes those. Restart the backend afterward. OpenAI API billing is separate from a ChatGPT subscription.
