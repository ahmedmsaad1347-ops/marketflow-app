const mark = `<svg viewBox="0 0 32 32" fill="none" aria-hidden="true"><path d="M5 22V10l7 8 7-12v16l8-11v15" stroke="currentColor" stroke-width="3" stroke-linecap="round" stroke-linejoin="round"/></svg>`;
const arrow = `<svg viewBox="0 0 24 24" fill="none" aria-hidden="true"><path d="M5 12h14m-6-6 6 6-6 6" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round"/></svg>`;
const check = `<svg viewBox="0 0 20 20" fill="none" aria-hidden="true"><path d="m5 10 3 3 7-7" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round"/></svg>`;

export function landingView() {
  return `
    <div class="mf-landing">
      <a class="mf-skip" href="#mf-main">Skip to content</a>
      <header class="mf-nav-shell">
        <nav class="mf-nav mf-container" aria-label="Main navigation">
          <a class="mf-brand" href="/" aria-label="MarketFlow home"><span class="mf-logo-mark">${mark}</span>MarketFlow</a>
          <div class="mf-nav-links"><a href="#product">Product</a><a href="#how-it-works">How it works</a><a href="#questions">FAQs</a></div>
          <div class="mf-nav-actions"><button data-route="/login" class="mf-login">Sign in</button><button data-route="/signup" class="mf-button mf-button-small mf-button-outline">Get started ${arrow}</button></div>
        </nav>
      </header>
      <main id="mf-main">
        <section class="mf-hero mf-container" aria-labelledby="mf-hero-title">
          <div class="mf-hero-copy">
            <a href="#product" class="mf-announcement"><span class="mf-live-dot"></span>Meet your marketing decision engine ${arrow}</a>
            <h1 id="mf-hero-title">Your ambition.<br>Your business.<br><span>A clearer plan.</span></h1>
            <p class="mf-hero-description">Turn what you know about your business into a marketing strategy you can understand, edit, and build on.</p>
            <div class="mf-hero-actions"><button data-route="/signup" class="mf-button mf-button-light">Build my first strategy ${arrow}</button><a href="#product" class="mf-button mf-button-outline">Explore the product ${arrow}</a></div>
            <p class="mf-hero-note">${check} Start with your business. Stay in control of the campaign.</p>
          </div>
          <div class="mf-hero-visual" aria-label="Interactive example of a MarketFlow strategy">
            <div class="mf-orbit mf-orbit-one"></div><div class="mf-orbit mf-orbit-two"></div>
            <div class="mf-demo-window">
              <div class="mf-window-bar"><span class="mf-window-dots" aria-hidden="true"><i></i><i></i><i></i></span><span>your-next-campaign.flow</span><span class="mf-example-tag">EXAMPLE</span></div>
              <div class="mf-demo-top"><span class="mf-mini-mark">${mark}</span><div><strong>A good plan starts with you.</strong><small>FlowDesk · Customer support software</small></div><span class="mf-demo-status">Draft</span></div>
              <div class="mf-demo-tabs" role="tablist" aria-label="Example strategy stages">
                <button id="mf-tab-brief" role="tab" aria-controls="mf-panel-brief" aria-selected="false" tabindex="-1" data-mf-tab="brief">01 Brief</button>
                <button id="mf-tab-strategy" role="tab" aria-controls="mf-panel-strategy" aria-selected="true" tabindex="0" data-mf-tab="strategy">02 Strategy</button>
                <button id="mf-tab-creative" role="tab" aria-controls="mf-panel-creative" aria-selected="false" tabindex="-1" data-mf-tab="creative">03 Creative</button>
              </div>
              <div class="mf-demo-panel" id="mf-panel-brief" role="tabpanel" aria-labelledby="mf-tab-brief" tabindex="0" data-mf-panel="brief" hidden>
                <p class="mf-code-label">THE BUSINESS BRIEF</p>
                <div class="mf-brief-line"><span>What do you sell?</span><strong>Customer support software</strong></div>
                <div class="mf-brief-line"><span>Who is it for?</span><strong>Small online businesses</strong></div>
                <div class="mf-brief-line"><span>What matters most?</span><strong>Qualified leads</strong></div>
                <div class="mf-brief-line"><span>How do buyers find you?</span><strong>They actively search</strong></div>
                <p class="mf-demo-helper">A few useful questions. A plan shaped around your answers.</p>
              </div>
              <div class="mf-demo-panel" id="mf-panel-strategy" role="tabpanel" aria-labelledby="mf-tab-strategy" tabindex="0" data-mf-panel="strategy">
                <p class="mf-code-label"><span class="mf-live-dot"></span> RECOMMENDED FIRST TEST</p>
                <div class="mf-recommendation"><span class="mf-google-symbol" aria-hidden="true">G</span><div><h2>Google Search</h2><p>Meet demand that already exists.</p></div>${arrow}</div>
                <div class="mf-demo-metrics"><div><small>Objective</small><strong>Qualified leads</strong></div><div><small>Example budget</small><strong>1,000 <em>EGP / day</em></strong></div></div>
                <div class="mf-reason"><span aria-hidden="true">↳</span><p>Your buyers are already searching for a solution. Start with one channel and learn from real lead quality.</p></div>
                <div class="mf-demo-check">${check}<span>Check conversion tracking before launch</span></div>
              </div>
              <div class="mf-demo-panel" id="mf-panel-creative" role="tabpanel" aria-labelledby="mf-tab-creative" tabindex="0" data-mf-panel="creative" hidden>
                <p class="mf-code-label">A STARTING POINT FOR YOUR CREATIVE</p><span class="mf-ad-label">Problem → solution</span>
                <h2 class="mf-ad-headline">Less repetition.<br>More human support.</h2>
                <p class="mf-demo-helper">Still answering the same questions? See how FlowDesk fits into your team's customer support workflow.</p>
                <div class="mf-creative-tags"><span>Product demo</span><span>Real workflow proof</span><span>Clear next step</span></div>
              </div>
              <div class="mf-demo-footer"><span>${check} Your plan. Your review. Your decision.</span><span>Nothing publishes automatically.</span></div>
            </div>
            <div class="mf-floating-note"><span class="mf-note-icon" aria-hidden="true">✦</span><div><strong>A recommendation with a reason.</strong><span>Clarity before your next campaign.</span></div></div>
          </div>
        </section>
        <div class="mf-channels mf-container"><p>PLAN AROUND THE CHANNELS YOUR CUSTOMERS USE</p><div><span class="mf-channel-meta">∞ <b>Meta</b></span><span><b class="mf-channel-google">G</b> Google Ads</span><span><b class="mf-channel-tiktok">♪</b> TikTok Ads</span></div><small>Strategy recommendations. Account and market eligibility checked before launch.</small></div>
        <section id="how-it-works" class="mf-section mf-container" aria-labelledby="mf-workflow-title">
          <div class="mf-section-heading"><p class="mf-eyebrow"><span></span> A LITTLE INPUT. A LOT MORE DIRECTION.</p><h2 id="mf-workflow-title">From “where do I start?”<br><span>to a next step that makes sense.</span></h2></div>
          <div class="mf-workflow">
            <article><span class="mf-step-number">01</span><div class="mf-step-line"></div><h3>Tell us about your business.</h3><p>Your offer, your customers, your budget. Follow a guided conversation or go straight to the brief.</p></article>
            <article><span class="mf-step-number">02</span><div class="mf-step-line"></div><h3>Understand the recommendation.</h3><p>See which channel to test, why it fits, what the numbers mean, and what still needs checking.</p></article>
            <article><span class="mf-step-number">03</span><div class="mf-step-line"></div><h3>Make the plan your own.</h3><p>Edit an answer, rebuild the strategy, then turn the plan you accept into a campaign draft.</p></article>
          </div>
        </section>
        <section id="product" class="mf-section mf-container" aria-labelledby="mf-product-title">
          <div class="mf-section-heading mf-heading-row"><div><p class="mf-eyebrow"><span></span> BUILT FOR THE DECISIONS THAT MATTER</p><h2 id="mf-product-title">More than a dashboard.<br><span>A way forward.</span></h2></div><p>Your next campaign needs more than another empty form. Bring the strategy, the numbers, and the creative into one connected workflow.</p></div>
          <div class="mf-feature-grid">
            <article class="mf-feature mf-feature-research"><span class="mf-feature-icon" aria-hidden="true">⌕</span><h3>See the thinking.<br>Check the sources.</h3><p>Research public sources, understand the decision rules, and see evidence gaps before you move forward.</p><div class="mf-source-preview"><div><span class="mf-source-dot"></span><span>Platform guidance</span><small>Official source</small></div><div><span class="mf-source-dot mf-source-purple"></span><span>Business background</span><small>Context to review</small></div><div><span class="mf-source-dot mf-source-amber"></span><span>Unverified page</span><small>Excluded from evidence</small></div></div></article>
            <article class="mf-feature mf-feature-economics"><span class="mf-feature-icon mf-icon-diagonal" aria-hidden="true">${arrow}</span><h3>Know your numbers.<br>Then plan your test.</h3><p>Put contribution margin, daily budget, and break-even thresholds alongside your campaign recommendation.</p><div class="mf-economics-preview"><div><small>Example contribution / sale</small><strong>650 <span>EGP</span></strong></div><div class="mf-economics-line"><i></i><i></i><i></i><i></i><i></i><i></i><i></i><i></i><i></i><i></i></div><small>Planning thresholds, not promised results.</small></div></article>
            <article class="mf-feature mf-feature-edit"><span class="mf-feature-icon" aria-hidden="true">↻</span><h3>Changed an answer?<br>Change the plan.</h3><p>Reopen your saved brief with its answers already filled in. Adjust what matters and create a new strategy version.</p><div class="mf-edit-preview"><div><span>Campaign objective</span><span>Sales <i>→</i> <b>Qualified leads</b></span></div><div><span>Business brief</span><span class="mf-mint-text">Answers saved ${check}</span></div><div class="mf-edit-preview-footer">Previous strategy stays in your history.</div></div></article>
            <article class="mf-feature mf-feature-creative"><span class="mf-feature-icon" aria-hidden="true">✦</span><h3>A strategy that gives<br>your creative direction.</h3><p>Get angles, hooks, draft copy, and video-script ideas shaped around your business and chosen campaign.</p><div class="mf-copy-preview"><span>YOUR NEXT CREATIVE ANGLE</span><p>Show the problem.<br>Prove the solution.<br><strong>Make the next step clear.</strong></p><div><span>Hooks</span><span>Ad copy</span><span>Video scripts</span></div></div></article>
          </div>
        </section>
        <section class="mf-control mf-container" aria-labelledby="mf-control-title"><div class="mf-control-symbol" aria-hidden="true">${mark}</div><div><p class="mf-eyebrow">CONFIDENCE COMES FROM CLARITY</p><h2 id="mf-control-title">You stay in the driver's seat.</h2><p>Accepting a strategy creates a draft. Review the creative, verify tracking, and check account eligibility before any future launch.</p></div><span class="mf-control-badge">${check} Draft first. Review always.</span></section>
        <section id="questions" class="mf-section mf-faq mf-container" aria-labelledby="mf-faq-title"><div><p class="mf-eyebrow"><span></span> A FEW GOOD QUESTIONS</p><h2 id="mf-faq-title">Before you<br><span>get started.</span></h2><p>Already have a workspace?<br><button data-route="/login" class="mf-text-button">Sign in to MarketFlow ${arrow}</button></p></div><div class="mf-faq-items">
          <details><summary>Do I need to know how to run ads?<span aria-hidden="true">+</span></summary><p>No marketing brief required to begin. The guided agent asks about your business and explains the recommended channel, objective, and first test.</p></details>
          <details><summary>Can I change my answers later?<span aria-hidden="true">+</span></summary><p>Yes. Review and edit your answers before building, or reopen a saved strategy and rebuild it with corrected inputs. Your previous strategy stays saved.</p></details>
          <details><summary>Will MarketFlow publish ads or spend money?<span aria-hidden="true">+</span></summary><p>Accepting a strategy only creates a campaign draft. Direct ad publishing requires a separate provider integration and explicit launch approval.</p></details>
          <details><summary>Are the budget numbers guaranteed results?<span aria-hidden="true">+</span></summary><p>No. The financial calculations are planning thresholds based on your inputs. Campaign performance depends on the offer, creative, market, tracking, and real test results.</p></details>
        </div></section>
        <section class="mf-final mf-container"><div class="mf-final-glow" aria-hidden="true"></div><p class="mf-eyebrow">YOUR NEXT CHAPTER STARTS WITH A PLAN</p><h2>Less guesswork.<br><span>More forward.</span></h2><p>Bring your business. Find your next marketing move.</p><button data-route="/signup" class="mf-button mf-button-light">Get started with MarketFlow ${arrow}</button></section>
      </main>
      <footer class="mf-footer mf-container"><a class="mf-brand" href="/">${mark}MarketFlow</a><span>© ${new Date().getFullYear()} MarketFlow</span><div><a href="#product">Product</a><a href="#questions">FAQs</a><button data-route="/login">Sign in</button></div></footer>
    </div>`;
}
