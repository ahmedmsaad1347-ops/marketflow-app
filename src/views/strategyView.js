import { budgetExtraFields, budgetAdviceView } from './budgetPlannerView.js';
function escapeHtml(value = "") {
  return String(value).replace(
    /[&<>"']/g,
    char => ({
      "&": "&amp;",
      "<": "&lt;",
      ">": "&gt;",
      '"': "&quot;",
      "'": "&#039;"
    })[char]
  );
}


export function strategyView(mode = "guided") {
  const guided = mode !== "quick";

  return `
    <section class="page strategy-page">
      <button data-page="dashboard" class="back-button">← Dashboard</button>

      <p class="review-kicker">MARKETFLOW STRATEGY ENGINE</p>
      <h1>${guided ? "Let MarketFlow guide you" : "Build your campaign strategy"}</h1>
      <p class="subtitle">
        ${guided
          ? "We will ask the important questions one step at a time."
          : "Complete the brief and MarketFlow will turn it into a campaign plan."}
      </p>

      <form
        id="strategyForm"
        class="strategy-form ${guided ? "guided" : "quick"}"
        data-strategy-mode="${guided ? "guided" : "quick"}"
      >
        <div class="strategy-progress">
          <span id="strategyProgressText">${guided ? "Step 1 of 4" : "Campaign brief"}</span>
          ${guided ? `
            <div class="strategy-progress-track">
              <div id="strategyProgressBar" class="strategy-progress-bar" style="width:25%"></div>
            </div>
          ` : ""}
        </div>

        <section class="strategy-step" data-strategy-step="1">
          <h2>1. Business & offer</h2>

          <label>
            Business name
            <input name="business_name" placeholder="Example: Nova Furniture" required>
          </label>

          <label>
            What do you sell?
            <textarea name="product" placeholder="Describe the product or service clearly" required></textarea>
          </label>

          <label>
            What is the offer?
            <textarea name="offer" placeholder="Discount, bundle, free consultation, fast delivery... Leave blank if you do not have one yet."></textarea>
          </label>

          <label>
            Country / market
            <input name="country" placeholder="Egypt" required>
          </label>
        </section>

        <section class="strategy-step" data-strategy-step="2" ${guided ? "hidden" : ""}>
          <h2>2. Business economics</h2>

          <div class="strategy-field-grid">
            <label>
              Order / customer value
              <input name="price" type="number" min="0" step="0.01" placeholder="Optional">
            </label>

            <label>
              Gross margin %
              <input name="gross_margin_percent" type="number" min="0" max="100" step="0.1" placeholder="Optional">
            </label>
          </div>

          <div class="strategy-field-grid">
            <label>
              Extra variable cost per sale
              <input
                name="extra_variable_cost_per_order"
                type="number"
                min="0"
                step="0.01"
                placeholder="Shipping, fees, returns allowance..."
              >
            </label>

            <label>
              Lead / message → sale rate %
              <input
                name="lead_to_sale_rate_percent"
                type="number"
                min="0"
                max="100"
                step="0.1"
                placeholder="For leads/messages"
              >
            </label>
          </div>

          <label>Budget choice<select name="budget_mode"><option value="manual">I have a budget</option><option value="recommend">Recommend a budget for me</option></select></label>
          <div class="strategy-field-grid">
            <label>
              Total campaign budget
              <input name="total_budget" type="number" min="0.01" step="0.01" required>
            </label>

            <label>
              Currency
              <select name="currency" required>
                <option>EGP</option>
                <option>USD</option>
                <option>SAR</option>
                <option>AED</option>
                <option>EUR</option>
                <option>GBP</option>
              </select>
            </label>
          </div>

          <label>
            Campaign duration
            <select name="campaign_days" required>
              <option value="7">7 days</option>
              <option value="14">14 days</option>
              <option value="30" selected>30 days</option>
              <option value="60">60 days</option>
              <option value="90">90 days</option>
            </select>
          </label>

          <div class="strategy-budget-options">${budgetExtraFields()}</div>
          <label>Main benefit for the proposed ad<textarea name="benefit" maxlength="1000" placeholder="Optional: a benefit you can support"></textarea></label>
          <p class="strategy-inline-note">
            MarketFlow now calculates contribution per sale after extra variable costs.
            For Leads or Messages, add the real lead/message-to-sale rate so the engine
            can calculate a financially grounded break-even CPL/conversation cost.
          </p>
        </section>

        <section class="strategy-step" data-strategy-step="3" ${guided ? "hidden" : ""}>
          <h2>3. Customer & objective</h2>

          <label>
            Who is the ideal customer?
            <textarea name="audience" placeholder="Who buys, where they live, what problem they have, and anything you already know about them." required></textarea>
          </label>

          <label>
            Main business objective
            <select name="objective" required>
              <option value="">Choose objective</option>
              <option value="sales">Sales</option>
              <option value="leads">Leads</option>
              <option value="messages">Messages</option>
              <option value="traffic">Website traffic</option>
              <option value="awareness">Brand awareness</option>
            </select>
          </label>

          <label>
            How do customers usually discover this?
            <select name="demand_type" required>
              <option value="mixed">Mixed / not sure</option>
              <option value="search">They actively search for it</option>
              <option value="discovery">They usually discover it in content or ads</option>
            </select>
          </label>

          <label>
            Where does the sale / lead happen?
            <select name="sales_channel" required>
              <option value="website">Website</option>
              <option value="whatsapp">WhatsApp / messages</option>
              <option value="phone">Phone call</option>
              <option value="store">Physical store</option>
            </select>
          </label>
        </section>

        <section class="strategy-step" data-strategy-step="4" ${guided ? "hidden" : ""}>
          <h2>4. Marketing readiness</h2>

          <div class="strategy-checks">
            <label><input type="checkbox" name="has_website"> I have a website / landing page</label>
            <label><input type="checkbox" name="has_tracking"> Pixel / tag / conversion tracking is verified</label>
            <label><input type="checkbox" name="has_previous_sales"> This offer already has real sales or qualified leads</label>
            <label><input type="checkbox" name="has_video_creatives"> I have usable vertical video creative</label>
          </div>

          <label>
            Anything else MarketFlow should know?
            <textarea name="notes" placeholder="Seasonality, competitors, delivery limits, previous campaign results..."></textarea>
          </label>
        </section>

        ${guided ? `
          <div class="strategy-step-actions">
            <button type="button" id="strategyBack" class="strategy-secondary" hidden>Back</button>
            <button type="button" id="strategyNext" class="strategy-primary">Next</button>
            <button type="submit" id="strategyGenerate" class="strategy-primary" hidden>Build My Strategy</button>
          </div>
        ` : `
          <button type="submit" id="strategyGenerate" class="strategy-primary strategy-generate-full">
            Build My Strategy
          </button>
        `}
      </form>
    </section>
  `;
}


export function strategyResultView(response) {
  const strategy = response.strategy || {};
  const budget = strategy.budget_plan || {};
  const economics = strategy.economics || {};
  const creative = strategy.creative_plan || {};
  const automation = strategy.automation_plan || {};
  const scorecard = strategy.channel_scorecard || [];
  const research = strategy.research_evidence || {};
  const agentReview = strategy.agent_review || {};
  const profile = strategy.business_profile || creative.business_profile || {};
  const sources = research.sources || [];
  const challengeSource = source => /checking your browser|we think you might be a bot|verify (that )?you are human|enable javascript and cookies to continue|sorry, you have been blocked|unusual traffic from your computer network/i.test(source.snippet || "");
  const usableSources = sources.filter(source =>
    source.retrieval_status === "retrieved" && source.snippet && !challengeSource(source)
  );
  const excludedSources = sources.filter(source => !usableSources.includes(source));
  const sourceUrl = value => /^https?:\/\//i.test(value || "") ? escapeHtml(value) : "#";
  const excludedReason = source => challengeSource(source) ? "The site returned a browser or bot-verification page." : source.retrieval_reason || ({
    blocked: "The site returned a browser or bot-verification page.",
    insufficient_content: "No substantial page text could be extracted.",
    unavailable: "The page could not be retrieved."
  }[source.retrieval_status] || "Content has not been verified.");

  const list = items =>
    (items || []).length
      ? items.map(item => `<li>${escapeHtml(item)}</li>`).join("")
      : "<li>No additional items.</li>";

  const angles = (creative.angles || []).map(item => `
    <article class="strategy-angle">
      <strong>${escapeHtml(item.name)}</strong>
      <p>${escapeHtml(item.idea)}</p>
    </article>
  `).join("");

  const creativeCards = items =>
    (items || []).length
      ? items.map(item => `
          <article class="creative-draft-card">
            <p>${escapeHtml(item)}</p>
          </article>
        `).join("")
      : "";

  const videoScripts = (creative.video_scripts || []).map(script => `
    <article class="creative-script-card">
      <small>VIDEO CONCEPT</small>
      <h3>${escapeHtml(script.name || "")}</h3>

      <div class="creative-script-hook">
        <span>Hook</span>
        <strong>${escapeHtml(script.hook || "")}</strong>
      </div>

      <ol>
        ${(script.shots || [])
          .map(shot => `<li>${escapeHtml(shot)}</li>`)
          .join("")}
      </ol>

      ${(script.on_screen_text || []).length ? `
        <div class="creative-tags">
          ${(script.on_screen_text || [])
            .map(item => `<span>${escapeHtml(item)}</span>`)
            .join("")}
        </div>
      ` : ""}
    </article>
  `).join("");

  const scores = scorecard.map(item => `
    <article class="strategy-score-row ${item.eligible ? "" : "not-eligible"}">
      <div class="strategy-score-head">
        <div>
          <strong>${escapeHtml(item.campaign_type)}</strong>
          <small>${escapeHtml(item.provider)}</small>
        </div>
        <span>${item.score}/100</span>
      </div>

      <div class="strategy-score-track">
        <div class="strategy-score-fill" style="width:${Math.max(0, Math.min(100, item.score))}%"></div>
      </div>

      ${item.eligible
        ? ""
        : `<small class="strategy-score-note">Not launch-eligible from the current inputs / capability snapshot.</small>`}
    </article>
  `).join("");

  return `
    <section class="page strategy-result-page">
      <button data-edit-strategy="${escapeHtml(response.strategy_id)}" class="back-button">← Edit answers & rebuild</button>

      <p class="review-kicker">MARKETFLOW STRATEGY ENGINE V3</p>

      <section class="strategy-recommendation-hero">
        <span>RECOMMENDED CAMPAIGN</span>

        <h1>${escapeHtml(strategy.recommended_campaign_type || strategy.recommended_platform || "")}</h1>

        <p>
          ${escapeHtml(strategy.recommended_platform || "")}
          · ${escapeHtml(strategy.requested_objective || "")}
          · Fit ${escapeHtml(strategy.fit_score || 0)}/100
        </p>

        <small>
          Capability snapshot: ${escapeHtml(strategy.capability_snapshot || "")}
        </small>
      </section>

      <p class="subtitle">${escapeHtml(strategy.disclaimer || "")}</p>

      <section class="strategy-card">
        <p class="review-kicker">BUSINESS UNDERSTANDING</p>
        <div class="strategy-decision-card">
          <div><small>Business type</small><strong>${escapeHtml(profile.vertical || "")}</strong></div>
          <div><small>Product type</small><strong>${escapeHtml(profile.product_type || "")}</strong></div>
          <div><small>Target industry</small><strong>${escapeHtml(profile.target_industry || "")}</strong></div>
          <div><small>Buyer</small><strong>${escapeHtml(profile.buyer_type || "")}</strong></div>
          <div><small>Revenue model</small><strong>${escapeHtml(profile.revenue_model || "")}</strong></div>
          <div><small>Purchase cycle</small><strong>${escapeHtml(profile.purchase_cycle || "")}</strong></div>
          <div><small>Demand motion</small><strong>${escapeHtml(profile.demand_motion || "")}</strong></div>
          <div><small>Conversion</small><strong>${escapeHtml(profile.conversion_type || "")}</strong></div>
        </div>
        <p class="strategy-note">
          ${escapeHtml(profile.acquisition_strategy || "")}
          ${profile.confidence ? " · Understanding confidence: " + escapeHtml(profile.confidence) : ""}
        </p>
      </section>

      <section class="strategy-decision-card">
        <div><small>Platform</small><strong>${escapeHtml(strategy.recommended_platform || "")}</strong></div>
        <div><small>Campaign type</small><strong>${escapeHtml(strategy.recommended_campaign_type || "")}</strong></div>
        <div><small>Funnel stage</small><strong>${escapeHtml(strategy.funnel_stage || "")}</strong></div>
        <div><small>Optimize for</small><strong>${escapeHtml(strategy.optimization_event || "")}</strong></div>
      </section>

      ${strategy.google_ads_capabilities?.demand_gen_budget && !strategy.google_ads_capabilities.demand_gen_budget.passed ? `
        <section class="strategy-card">
          <p class="review-kicker">CHANNEL ELIGIBILITY</p>
          <p>Demand Gen excluded: ${escapeHtml(strategy.google_ads_capabilities.demand_gen_budget.detail)}</p>
        </section>
      ` : ""}

      <section class="strategy-card">
        <p class="review-kicker">AGENT RESEARCH & REVIEW</p>
        <h2>${escapeHtml(agentReview.summary || "Strategy review")}</h2>
        <p class="strategy-note">Review: ${escapeHtml(agentReview.status || "n/a")} · Confidence: ${escapeHtml(agentReview.confidence || "n/a")} · Usable page extracts: ${escapeHtml(usableSources.length)}</p>
        ${(agentReview.corrections || []).length ? `<div class="strategy-review-warnings"><strong>Reviewer flags</strong><ul>${list(agentReview.corrections || [])}</ul></div>` : ""}
        ${(agentReview.applied_corrections || []).length ? `<div class="strategy-review-warnings"><strong>Corrections applied</strong><ul>${list(agentReview.applied_corrections.map(change => `${change.field}: ${change.previous_value || "(empty)"} → ${change.value}. ${change.reason}`))}</ul></div>` : ""}
        ${(agentReview.evidence_gaps || []).length ? `<div class="strategy-review-warnings"><strong>Evidence to verify</strong><ul>${list(agentReview.evidence_gaps)}</ul></div>` : ""}
        <p class="strategy-note">Business background pages do not verify the platform recommendation. Retrieved text still needs review for relevance.</p>
        ${usableSources.length ? `<div class="strategy-research-sources"><h3>Usable research sources</h3>${usableSources.map(source => `
          <article class="strategy-research-source">
            <a href="${sourceUrl(source.url)}" target="_blank" rel="noopener noreferrer"><strong>${escapeHtml(source.title || source.url || "Source")}</strong></a>
            <small>${escapeHtml(source.official_provider ? "Official " + source.official_provider + " source" : source.purpose || "Business background")}</small>
            <details><summary>Read extracted text</summary><p>${escapeHtml(source.snippet)}</p></details>
          </article>`).join("")}</div>` : `<p class="strategy-note">No usable page content was extracted in this run; internal rules still produced the strategy.</p>`}
        ${excludedSources.length ? `<details class="strategy-research-excluded"><summary>Sources not used (${excludedSources.length})</summary>${excludedSources.map(source => `
          <article class="strategy-research-source">
            <a href="${sourceUrl(source.url)}" target="_blank" rel="noopener noreferrer"><strong>${escapeHtml(source.title || source.url || "Source")}</strong></a>
            <p>${escapeHtml(excludedReason(source))}</p>
          </article>`).join("")}</details>` : ""}
      </section>

      <section class="strategy-card">
        <p class="review-kicker">AUTOMATION & BIDDING</p>

        <div class="strategy-automation-grid">
          <div>
            <small>Automation</small>
            <strong>${escapeHtml(automation.automation_mode || "")}</strong>
          </div>

          <div>
            <small>Audience</small>
            <strong>${escapeHtml(automation.audience_approach || "")}</strong>
          </div>

          <div>
            <small>Placements</small>
            <strong>${escapeHtml(automation.placements || "")}</strong>
          </div>
        </div>

        <div class="strategy-bidding-box">
          <small>Bidding recommendation</small>
          <p>${escapeHtml(automation.bidding || "")}</p>
        </div>
      </section>

      <section class="strategy-card">
        <p class="review-kicker">CHANNEL FIT SCORECARD</p>
        <p class="strategy-note">
          These are internal fit scores from the current inputs — not performance forecasts.
        </p>
        <div class="strategy-score-list">${scores}</div>
      </section>

      <section class="strategy-card">
        <p class="review-kicker">AVAILABILITY CHECK</p>
        <p>${escapeHtml(strategy.availability_note || "")}</p>
      </section>

      <section class="strategy-card">
        <p class="review-kicker">WHY THIS PLAN</p>
        <ul class="strategy-list">${list(strategy.why)}</ul>
      </section>

      <section class="strategy-card">
        <p class="review-kicker">BUDGET</p>
        <h2>${escapeHtml(budget.total_budget || 0)} ${escapeHtml(budget.currency || "")}</h2>
        <p>${escapeHtml(budget.daily_budget || 0)} ${escapeHtml(budget.currency || "")} / day · ${escapeHtml(budget.campaign_days || "")} days</p>
        <p>${escapeHtml(budget.note || "")}</p>
        ${budgetAdviceView(budget.recommendation, strategy.ad_concept)}
        ${budget.planning_warning ? `<div class="strategy-review-warnings"><strong>Budget planning</strong><p>${escapeHtml(budget.planning_warning)}</p></div>` : ""}
      </section>

      ${economics.available ? `
        <section class="strategy-card">
          <p class="review-kicker">BUSINESS ECONOMICS</p>

          <div class="strategy-metrics">
            ${
              (economics.cards || []).length
                ? economics.cards.map(card => `
                    <div>
                      <small>${escapeHtml(card.label || "")}</small>
                      <strong>
                        ${escapeHtml(card.value ?? "")}
                        ${escapeHtml(card.suffix || "")}
                      </strong>
                    </div>
                  `).join("")
                : `
                    <div><small>Break-even CPA</small><strong>${economics.break_even_cpa} ${escapeHtml(economics.currency)}</strong></div>
                    <div><small>Planning CPA</small><strong>${economics.planning_target_cpa} ${escapeHtml(economics.currency)}</strong></div>
                    <div><small>Break-even ROAS</small><strong>${economics.break_even_roas}x</strong></div>
                    <div><small>Planning ROAS</small><strong>${economics.planning_target_roas}x</strong></div>
                  `
            }
          </div>

          <p class="strategy-note">${escapeHtml(economics.note || "")}</p>
        </section>
      ` : `
        <section class="strategy-card">
          <p class="review-kicker">BUSINESS ECONOMICS</p>
          <p>${escapeHtml(economics.note || "")}</p>
        </section>
      `}

      <section class="strategy-card">
        <p class="review-kicker">AUDIENCE PLAN</p>
        <ul class="strategy-list">${list(strategy.audience_plan)}</ul>
      </section>

      <section class="strategy-card creative-engine-card">
        <p class="review-kicker">CREATIVE ENGINE V1.3</p>
        <h2>Platform-ready campaign drafts</h2>
        <button type="button" class="workspace-create-button" data-creative-strategy="${response.strategy_id}">Open this business in Creative Studio →</button>
        <p class="strategy-note">
          MarketFlow adapts the creative output to the selected campaign type.
          Review facts and brand voice before publishing.
        </p>

        ${creative.business_context ? `
          <div class="creative-match-plan">
            <strong>${escapeHtml(creative.business_context.vertical || "")}</strong>
            · ${escapeHtml(creative.business_context.subject || "")}
            · ${escapeHtml(creative.business_context.location || "")}
          </div>
        ` : ""}

        ${creative.policy_note ? `
          <div class="creative-safety-note">
            <strong>Targeting policy check</strong>
            <p>${escapeHtml(creative.policy_note)}</p>
          </div>
        ` : ""}

        ${creative.search_pack ? `
          <section class="creative-search-pack">
            <p class="review-kicker">GOOGLE SEARCH AD PACK</p>

            <h3>RSA headlines</h3>
            <div class="creative-asset-list">
              ${(creative.search_pack.headlines || []).map(item => `
                <div class="creative-asset-row">
                  <span>${escapeHtml(item)}</span>
                  <small>${String(item).length}/${creative.search_pack.headline_limit || 30}</small>
                </div>
              `).join("")}
            </div>

            <h3>RSA descriptions</h3>
            <div class="creative-asset-list">
              ${(creative.search_pack.descriptions || []).map(item => `
                <div class="creative-asset-row">
                  <span>${escapeHtml(item)}</span>
                  <small>${String(item).length}/${creative.search_pack.description_limit || 90}</small>
                </div>
              `).join("")}
            </div>

            <h3>Keyword groups</h3>
            <div class="creative-keyword-groups">
              ${Object.entries(creative.search_pack.keyword_groups || {}).map(([name, items]) => `
                <article>
                  <strong>${escapeHtml(name)}</strong>
                  <div class="creative-tags">
                    ${(items || []).map(item => `<span>${escapeHtml(item)}</span>`).join("")}
                  </div>
                </article>
              `).join("")}
            </div>

            <h3>Match-type plan</h3>
            <div class="creative-match-plan">
              ${escapeHtml(creative.search_pack.match_type_plan || "")}
            </div>

            <h3>Negative keyword ideas — review before applying</h3>
            <div class="creative-tags">
              ${(creative.search_pack.negative_keyword_ideas || [])
                .map(item => `<span>${escapeHtml(item)}</span>`)
                .join("")}
            </div>
          </section>
        ` : `
          <h3>Hooks</h3>
          <div class="creative-draft-grid">
            ${creativeCards(creative.hooks)}
          </div>

          <h3>Headlines</h3>
          <div class="creative-tags creative-tags-large">
            ${(creative.headlines || [])
              .map(item => `<span>${escapeHtml(item)}</span>`)
              .join("")}
          </div>

          ${(creative.primary_texts || []).length ? `
            <h3>Primary ad copy</h3>
            <div class="creative-draft-grid">
              ${creativeCards(creative.primary_texts)}
            </div>
          ` : ""}

          ${(creative.descriptions || []).length ? `
            <h3>Descriptions</h3>
            <div class="creative-draft-grid">
              ${creativeCards(creative.descriptions)}
            </div>
          ` : ""}

          ${videoScripts ? `
            <h3>Video concepts</h3>
            <div class="creative-script-grid">
              ${videoScripts}
            </div>
          ` : ""}
        `}

        <h3>Strategic angles</h3>
        <div class="strategy-angle-grid">${angles}</div>

        <h3>Platform requirements</h3>
        <ul class="strategy-list">${list(creative.formats)}</ul>

        <p><strong>CTA:</strong> ${escapeHtml(creative.cta || "")}</p>

        ${creative.safety_note ? `
          <div class="creative-safety-note">
            <strong>Before publishing</strong>
            <p>${escapeHtml(creative.safety_note)}</p>
          </div>
        ` : ""}
      </section>

      <section class="strategy-card">
        <p class="review-kicker">TRACKING CHECKLIST</p>
        <ul class="strategy-list">${list(strategy.tracking_checklist)}</ul>
      </section>

      ${(strategy.risks || []).length ? `
        <section class="strategy-card strategy-risks">
          <p class="review-kicker">BEFORE YOU LAUNCH</p>
          <ul class="strategy-list">${list(strategy.risks)}</ul>
        </section>
      ` : ""}

      <section class="strategy-final-card">
        <div>
          <p class="review-kicker">NEXT STEP</p>
          <h2>${escapeHtml(strategy.launch_readiness || "")}</h2>
          <p>
            Accepting this plan creates a Draft campaign.
            Nothing is published and no money is spent.
          </p>
        </div>

        <button
          id="acceptStrategyBtn"
          data-strategy-id="${response.strategy_id}"
          class="strategy-primary"
        >
          Accept Strategy & Create Draft
        </button>
      </section>
    </section>
  `;
}


export function strategyHistoryView(strategies = []) {
  const cards = strategies.length
    ? strategies.map(item => `
        <article class="strategy-history-card">
          <div>
            <small>${escapeHtml(new Date(item.created_at).toLocaleString())}</small>
            <h3>${escapeHtml(item.business_name || "Saved strategy")}</h3>
            <p>${escapeHtml(item.product || "")}</p>
            <div class="creative-tags">
              <span>${escapeHtml(item.platform || "")}</span>
              <span>${escapeHtml(item.campaign_type || "")}</span>
              <span>${escapeHtml(item.objective || "")}</span>
              <span>Fit ${escapeHtml(item.fit_score || 0)}/100</span>
            </div>
          </div>
          <button class="strategy-primary strategy-history-view" data-view-strategy="${escapeHtml(item.id)}">
            View Full Strategy
          </button>
        </article>
      `).join("")
    : `<div class="empty-card"><h2>No saved strategies yet</h2><p>Generate a strategy and it will appear here automatically.</p></div>`;

  return `
    <section class="page strategy-page">
      <button data-page="dashboard" class="back-button">← Dashboard</button>
      <p class="review-kicker">STRATEGY HISTORY</p>
      <h1>Saved strategies</h1>
      <p class="subtitle">Every generated strategy is saved. Open any one to see the complete original result.</p>
      <div class="strategy-history-list">${cards}</div>
    </section>
  `;
}
