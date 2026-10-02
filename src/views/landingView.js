export function landingView() {
  return `
    <div class="landing">

      <nav class="landing-nav">
        <a class="landing-logo" href="/">MarketFlow</a>

        <div class="landing-actions">
          <button data-route="/login" class="nav-login">
            Login
          </button>

          <button data-route="/signup" class="nav-cta">
            Start Free
          </button>
        </div>
      </nav>

      <section class="landing-hero">

        <div class="hero-badge">
          ✦ AI-powered marketing platform
        </div>

        <h1>
          Run your marketing
          <span>with AI.</span>
        </h1>

        <p>
          Create campaigns, manage customer conversations
          and grow your business from one intelligent platform.
        </p>

        <div class="hero-actions">
          <button data-route="/signup" class="hero-primary">
            Start Free
          </button>

          <button data-route="/login" class="hero-secondary">
            Login
          </button>
        </div>

      </section>

      <section class="landing-dashboard-preview">

        <div class="preview-top">
          <div>
            <small>MARKETFLOW</small>
            <h2>Marketing Command Center</h2>
          </div>
        </div>

        <div class="preview-grid">
          <div>
            <span>📢</span>
            <strong>Campaigns</strong>
            <small>Create and manage campaigns</small>
          </div>

          <div>
            <span>✦</span>
            <strong>AI Agent</strong>
            <small>Your marketing assistant</small>
          </div>

          <div>
            <span>💬</span>
            <strong>Messages</strong>
            <small>Customer conversations</small>
          </div>

          <div>
            <span>📊</span>
            <strong>Reports</strong>
            <small>Track your growth</small>
          </div>
        </div>

      </section>

    </div>
  `;
}
