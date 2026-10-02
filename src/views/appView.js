export function loginView() {
  return `
    <main class="login-page">
      <section class="login-card">
        <div class="logo">M</div>
        <h1>MarketFlow</h1>
        <p>Your AI marketing command center</p>

        <form id="loginForm">
          <input id="email" type="email" placeholder="Email address" required>
          <input id="password" type="password" placeholder="Password" required>
          <button type="submit">Sign in</button>
        </form>

        <p id="message"></p>
      </section>
    </main>
  `;
}

export function appView(user) {
  return `
    <div class="app-shell">

      <header class="topbar">
        <div>
          <span class="brand">MarketFlow</span>
          <small>${user}</small>
        </div>

        <button id="logoutBtn" class="logout">
          Logout
        </button>
      </header>

      <main id="pageContent"></main>

      <nav class="bottom-nav">

        <button data-page="dashboard" class="nav-btn">
          <span>⌂</span>
          Home
        </button>

        <button data-page="messages" class="nav-btn">
          <span>💬</span>
          Messages
        </button>

        <button data-page="campaigns" class="nav-btn">
          <span>📢</span>
          Campaigns
        </button>

        <button data-page="ai" class="nav-btn">
          <span>✦</span>
          AI
        </button>

        <button data-page="reports" class="nav-btn">
          <span>📊</span>
          Reports
        </button>

      </nav>

    </div>
  `;
}

export function dashboardView(campaigns) {
  return `
    <section class="page">

      <div class="hero">
        <p>Welcome back 👋</p>

        <h1>
          Marketing<br>
          Dashboard
        </h1>

        <span>
          Everything you need in one place.
        </span>
      </div>

      <div class="stats">

        <article>
          <strong>0</strong>
          <span>Messages</span>
        </article>

        <article>
          <strong>${campaigns.length}</strong>
          <span>Campaigns</span>
        </article>

        <article>
          <strong>0</strong>
          <span>Leads</span>
        </article>

      </div>

      <h2 class="section-title">
        Quick actions
      </h2>

      <div class="quick-grid">

        <button data-page="campaign-create">
          <span>📢</span>
          New Campaign
        </button>

        <button data-page="ai">
          <span>✦</span>
          Ask AI
        </button>

        <button data-page="messages">
          <span>💬</span>
          Messages
        </button>

        <button data-page="reports">
          <span>📊</span>
          Reports
        </button>

        <button data-page="connections">
          <span>🔗</span>
          Connections
        </button>

        <button data-page="notifications">
          <span>🔔</span>
          Notifications
        </button>

        <button data-page="settings">
          <span>⚙️</span>
          Settings
        </button>

      </div>

    </section>
  `;
}

export function campaignsView(campaigns) {
  const list = campaigns.length
    ? campaigns.map(campaign => `
        <article class="campaign-card">

          <div class="campaign-card-top">
            <div>
              <small>${campaign.platform}</small>
              <h3>${campaign.name}</h3>
            </div>

            <span class="campaign-status">
              ${campaign.status}
            </span>
          </div>

          <p>
            ${campaign.product}
          </p>

          <div class="campaign-meta">
            <span>🌍 ${campaign.country}</span>
            <span>💰 ${campaign.budget}</span>
          </div>

          <div class="campaign-actions">

            <button
              class="review-campaign"
              data-review-campaign="${campaign.id}"
            >
              Review & Launch
            </button>

            <button
              class="delete-campaign"
              data-delete-campaign="${campaign.id}"
            >
              Delete
            </button>

          </div>

        </article>
      `).join("")
    : `
      <div class="empty-card">
        <div class="big-icon">📢</div>

        <h2>No campaigns yet</h2>

        <p>
          Your active and scheduled campaigns
          will appear here.
        </p>
      </div>
    `;

  return `
    <section class="page">

      <h1>Campaigns</h1>

      <p class="subtitle">
        Create and manage your marketing campaigns.
      </p>

      <button
        data-page="campaign-create"
        class="primary-action"
      >
        + Create Campaign
      </button>

      <div class="campaign-list">
        ${list}
      </div>

    </section>
  `;
}

export function campaignFormView() {
  return `
    <section class="page">

      <button
        data-page="campaigns"
        class="back-button"
      >
        ← Back
      </button>

      <h1>Create Campaign</h1>

      <p class="subtitle">
        Tell MarketFlow what you want to promote.
      </p>

      <form id="campaignForm" class="campaign-form">

        <label>
          Campaign name
          <input
            name="name"
            placeholder="Summer Campaign"
            required
          >
        </label>

        <label>
          Product or service
          <input
            name="product"
            placeholder="Men's clothing store"
            required
          >
        </label>

        <label>
          Target audience
          <input
            name="audience"
            placeholder="Men aged 18-35"
            required
          >
        </label>

        <label>
          Target country
          <input
            name="country"
            placeholder="Egypt"
            required
          >
        </label>

        <label>
          Platform

          <select name="platform" required>
            <option value="">Choose platform</option>
            <option>Facebook</option>
            <option>Instagram</option>
            <option>TikTok</option>
            <option>Google</option>
            <option>Multiple platforms</option>
          </select>
        </label>

        <label>
          Budget

          <input
            name="budget"
            placeholder="100 USD"
            required
          >
        </label>

        <label>
          Campaign goal

          <select name="goal" required>
            <option value="">Choose goal</option>
            <option>Sales</option>
            <option>Leads</option>
            <option>Messages</option>
            <option>Website traffic</option>
            <option>Brand awareness</option>
          </select>
        </label>

        <button
          type="submit"
          class="primary-action"
        >
          Save Campaign
        </button>

      </form>

    </section>
  `;
}

export function messagesView() {
  return `
    <section class="page">

      <h1>Messages</h1>

      <p class="subtitle">
        Manage customer conversations.
      </p>

      <div class="empty-card">

        <div class="big-icon">
          💬
        </div>

        <h2>No conversations yet</h2>

        <p>
          Instagram, Facebook and other
          channels will appear here.
        </p>

      </div>

    </section>
  `;
}

export function aiView() {
  return `
    <section class="page">

      <h1>AI Agent</h1>

      <p class="subtitle">
        Your marketing assistant.
      </p>

      <div class="ai-card">

        <div class="ai-status">
          <span class="status-dot"></span>
          AI Agent Ready
        </div>

        <h2>
          What should we market today?
        </h2>

        <textarea
          placeholder="Example: Create a campaign for my clothing store..."
        ></textarea>

        <button class="primary-action">
          Generate with AI
        </button>

      </div>

    </section>
  `;
}

export function reportsView(
  analytics,
  days = 30
) {
  const money = value =>
    Number(value || 0)
      .toLocaleString(
        undefined,
        {
          minimumFractionDigits: 0,
          maximumFractionDigits: 2
        }
      );

  const number = value =>
    Number(value || 0)
      .toLocaleString();

  const summary =
    analytics.summary || {};

  const comparison =
    analytics.comparison || {};

  const change = key => {
    const value = comparison[key];

    if (value === null) {
      return "New";
    }

    if (!value) {
      return "0%";
    }

    return `${value > 0 ? "+" : ""}${value}%`;
  };

  const topCampaigns =
    analytics.top_campaigns || [];

  const campaignRows =
    topCampaigns.length
      ? topCampaigns.map(
          campaign => `
            <div class="analytics-table-row">
              <div>
                <strong>${campaign.name}</strong>
                <small>${campaign.provider}</small>
              </div>

              <span>
                $${money(campaign.spend)}
              </span>

              <span>
                $${money(campaign.revenue)}
              </span>

              <span>
                ${campaign.roas}x
              </span>
            </div>
          `
        ).join("")
      : `
        <div class="analytics-empty-row">
          No campaign performance data yet.
        </div>
      `;

  return `
    <section class="page analytics-page">

      <div class="analytics-header">
        <div>
          <p class="analytics-kicker">
            BUSINESS INTELLIGENCE
          </p>

          <h1>Business Analytics</h1>

          <p class="subtitle">
            Performance across your connected
            marketing and sales channels.
          </p>
        </div>

        <div class="analytics-period">
          <button
            data-analytics-days="7"
            class="${days === 7 ? "active" : ""}"
          >
            7D
          </button>

          <button
            data-analytics-days="30"
            class="${days === 30 ? "active" : ""}"
          >
            30D
          </button>

          <button
            data-analytics-days="90"
            class="${days === 90 ? "active" : ""}"
          >
            90D
          </button>
        </div>
      </div>

      ${
        !analytics.has_data
          ? `
            <div class="analytics-no-data">
              <div class="big-icon">📊</div>

              <h2>No analytics data yet</h2>

              <p>
                The analytics engine is ready.
                Real results will appear here
                after a marketing, sales or
                advertising account is connected.
              </p>

              <button
                data-page="connections"
                class="primary-action"
              >
                Connect Data Source
              </button>
            </div>
          `
          : ""
      }

      <div class="analytics-kpis">

        <article>
          <small>Revenue</small>
          <strong>
            $${money(summary.revenue)}
          </strong>
          <span>
            ${change("revenue")}
          </span>
        </article>

        <article>
          <small>Ad Spend</small>
          <strong>
            $${money(summary.spend)}
          </strong>
          <span>
            ${change("spend")}
          </span>
        </article>

        <article>
          <small>ROAS</small>
          <strong>
            ${summary.roas || 0}x
          </strong>
          <span>Return on ad spend</span>
        </article>

        <article>
          <small>Conversions</small>
          <strong>
            ${number(summary.conversions)}
          </strong>
          <span>
            ${change("conversions")}
          </span>
        </article>

        <article>
          <small>Leads</small>
          <strong>
            ${number(summary.leads)}
          </strong>
          <span>
            ${change("leads")}
          </span>
        </article>

        <article>
          <small>CPA</small>
          <strong>
            $${money(summary.cpa)}
          </strong>
          <span>Cost per conversion</span>
        </article>

        <article>
          <small>CPC</small>
          <strong>
            $${money(summary.cpc)}
          </strong>
          <span>Cost per click</span>
        </article>

        <article>
          <small>CTR</small>
          <strong>
            ${summary.ctr || 0}%
          </strong>
          <span>
            ${number(summary.clicks)} clicks
          </span>
        </article>

      </div>

      <div class="analytics-chart-card">
        <div class="analytics-card-title">
          <div>
            <h2>Revenue vs Spend</h2>
            <p>
              Daily financial performance
            </p>
          </div>
        </div>

        <div class="analytics-chart-wrap">
          <canvas id="moneyChart"></canvas>
        </div>
      </div>

      <div class="analytics-chart-card">
        <div class="analytics-card-title">
          <div>
            <h2>Leads & Conversions</h2>
            <p>
              Business acquisition trend
            </p>
          </div>
        </div>

        <div class="analytics-chart-wrap">
          <canvas id="funnelChart"></canvas>
        </div>
      </div>

      <div class="analytics-chart-card">
        <div class="analytics-card-title">
          <div>
            <h2>Channel Performance</h2>
            <p>
              Revenue contribution by source
            </p>
          </div>
        </div>

        <div class="analytics-chart-wrap analytics-chart-small">
          <canvas id="platformChart"></canvas>
        </div>
      </div>

      <div class="analytics-chart-card">

        <div class="analytics-card-title">
          <div>
            <h2>Top Campaigns</h2>
            <p>
              Ranked by generated revenue
            </p>
          </div>
        </div>

        <div class="analytics-table-head">
          <span>Campaign</span>
          <span>Spend</span>
          <span>Revenue</span>
          <span>ROAS</span>
        </div>

        ${campaignRows}

      </div>

      <div class="analytics-data-status">
        <span>
          ${
            analytics.data_status?.providers || 0
          } connected data sources
        </span>

        <span>
          ${
            analytics.data_status?.last_updated
              ? `Last sync: ${
                  new Date(
                    analytics.data_status.last_updated
                  ).toLocaleString()
                }`
              : "Waiting for first data sync"
          }
        </span>
      </div>

    </section>
  `;
}


export function connectionsView() {
  return `
    <section class="page">
      <h1>Connections</h1>

      <p class="subtitle">
        Connect your marketing accounts to MarketFlow.
      </p>

      <div class="connection-list">

        <article class="connection-card">
          <div>
            <strong>Facebook & Instagram</strong>
            <p>Meta Business and advertising accounts</p>
          </div>

          <button id="connectMetaBtn">
            Connect
          </button>
        </article>

        <article class="connection-card">
          <div>
            <strong>Google Ads</strong>
            <p>Coming soon</p>
          </div>

          <button disabled>
            Soon
          </button>
        </article>

        <article class="connection-card">
          <div>
            <strong>TikTok Ads</strong>
            <p>Coming soon</p>
          </div>

          <button disabled>
            Soon
          </button>
        </article>

      </div>
    </section>
  `;
}

export function notificationsView() {
  return `
    <section class="page">
      <h1>Notifications</h1>
      <p class="subtitle">
        Important updates from your campaigns and accounts.
      </p>

      <div class="empty-card">
        <div class="big-icon">🔔</div>
        <h2>No notifications yet</h2>
        <p>
          Campaign alerts, budget warnings and new lead notifications
          will appear here.
        </p>
      </div>
    </section>
  `;
}

export function settingsView(user) {
  return `
    <section class="page">
      <h1>Settings</h1>
      <p class="subtitle">
        Manage your MarketFlow account.
      </p>

      <div class="campaign-form">

        <label>
          Account email
          <input value="${user}" disabled>
        </label>

        <label>
          Default currency
          <select>
            <option>USD</option>
            <option>EUR</option>
            <option>EGP</option>
            <option>SAR</option>
          </select>
        </label>

        <label>
          Default language
          <select>
            <option>English</option>
            <option>Arabic</option>
          </select>
        </label>

        <button class="primary-action">
          Save Settings
        </button>

      </div>
    </section>
  `;
}

export function campaignReviewView(campaign) {
  if (!campaign) {
    return `
      <section class="page">
        <button data-page="campaigns" class="back-button">← Back</button>

        <div class="empty-card">
          <h2>Campaign not found</h2>
        </div>
      </section>
    `;
  }

  return `
    <section class="page">

      <button data-page="campaigns" class="back-button">
        ← Back
      </button>

      <p class="review-kicker">
        REVIEW BEFORE LAUNCH
      </p>

      <h1>${campaign.name}</h1>

      <p class="subtitle">
        Check everything before publishing.
      </p>

      <div class="review-warning">
        <strong>No money will be spent yet.</strong>

        <span>
          Your advertising account must be connected
          before final launch.
        </span>
      </div>

      <div class="review-card">

        <div class="review-row">
          <span>Product</span>
          <strong>${campaign.product}</strong>
        </div>

        <div class="review-row">
          <span>Audience</span>
          <strong>${campaign.audience}</strong>
        </div>

        <div class="review-row">
          <span>Country</span>
          <strong>${campaign.country}</strong>
        </div>

        <div class="review-row">
          <span>Platform</span>
          <strong>${campaign.platform}</strong>
        </div>

        <div class="review-row">
          <span>Budget</span>
          <strong>${campaign.budget}</strong>
        </div>

        <div class="review-row">
          <span>Goal</span>
          <strong>${campaign.goal}</strong>
        </div>

      </div>

      <div class="launch-checklist">
        <h2>Launch checklist</h2>

        <p>✅ Campaign validated by MarketFlow API</p>
        <p>✅ Campaign saved as Draft</p>
        <p>○ Advertising account connection required</p>
        <p>○ Final launch confirmation required</p>
      </div>

      <button
        data-page="connections"
        class="primary-action"
      >
        Connect Account to Launch
      </button>

    </section>
  `;
}

export function landingView() {
  return `
    <div class="landing">

      <header class="landing-nav">
        <div class="landing-brand">
          <div class="mini-logo">M</div>
          <strong>MarketFlow</strong>
        </div>

        <div class="landing-nav-actions">
          <button data-route="/login" class="nav-login">
            Login
          </button>

          <button data-route="/signup" class="nav-start">
            Start Free
          </button>
        </div>
      </header>

      <main>

        <section class="landing-hero">

          <div class="hero-badge">
            ✦ AI-powered marketing workspace
          </div>

          <h1>
            Run your marketing
            <span>from one intelligent platform.</span>
          </h1>

          <p>
            Create campaigns, manage customer conversations,
            connect your advertising accounts and track performance
            with AI helping at every step.
          </p>

          <div class="hero-actions">
            <button data-route="/signup" class="landing-primary">
              Start Free
            </button>

            <button data-route="/login" class="landing-secondary">
              Login to MarketFlow
            </button>
          </div>

          <div class="hero-proof">
            <span>✓ Campaign management</span>
            <span>✓ AI marketing assistant</span>
            <span>✓ Unified messages</span>
          </div>

        </section>

        <section class="landing-dashboard-preview">

          <div class="preview-top">
            <span>MarketFlow Dashboard</span>
            <span class="preview-status">● AI Ready</span>
          </div>

          <div class="preview-stats">
            <article>
              <strong>24</strong>
              <span>Campaigns</span>
            </article>

            <article>
              <strong>318</strong>
              <span>Leads</span>
            </article>

            <article>
              <strong>1.4K</strong>
              <span>Messages</span>
            </article>
          </div>

          <div class="preview-card">
            <span>Campaign performance</span>
            <strong>+32.4%</strong>
          </div>

        </section>

        <section class="landing-section">
          <div class="section-heading">
            <span>ONE WORKSPACE</span>
            <h2>Everything your marketing needs.</h2>
            <p>
              Stop jumping between tools. MarketFlow puts the main
              parts of your marketing workflow in one place.
            </p>
          </div>

          <div class="feature-grid">

            <article class="feature-card">
              <div>📢</div>
              <h3>Campaigns</h3>
              <p>
                Build, review and launch campaigns from one workflow.
              </p>
            </article>

            <article class="feature-card">
              <div>✦</div>
              <h3>AI Agent</h3>
              <p>
                Generate ideas, ad copy, targeting suggestions
                and marketing plans.
              </p>
            </article>

            <article class="feature-card">
              <div>💬</div>
              <h3>Messages</h3>
              <p>
                Bring customer conversations together and respond faster.
              </p>
            </article>

            <article class="feature-card">
              <div>📊</div>
              <h3>Reports</h3>
              <p>
                Understand spend, leads, campaigns and performance.
              </p>
            </article>

          </div>
        </section>

        <section class="landing-section integrations-section">

          <div class="section-heading">
            <span>CONNECTIONS</span>
            <h2>Connect the platforms you already use.</h2>
          </div>

          <div class="integration-grid">
            <div>Facebook</div>
            <div>Instagram</div>
            <div>Google Ads</div>
            <div>TikTok</div>
          </div>

        </section>

        <section class="how-section">

          <div class="section-heading">
            <span>HOW IT WORKS</span>
            <h2>From idea to campaign in four steps.</h2>
          </div>

          <div class="steps-grid">

            <article>
              <strong>01</strong>
              <h3>Create</h3>
              <p>Tell MarketFlow what you want to promote.</p>
            </article>

            <article>
              <strong>02</strong>
              <h3>Improve</h3>
              <p>Use AI recommendations to improve the campaign.</p>
            </article>

            <article>
              <strong>03</strong>
              <h3>Review</h3>
              <p>Check audience, budget and campaign details.</p>
            </article>

            <article>
              <strong>04</strong>
              <h3>Launch</h3>
              <p>Connect your advertising account and publish.</p>
            </article>

          </div>
        </section>

        <section class="landing-cta">
          <span>MARKETING, SIMPLIFIED.</span>
          <h2>Ready to build your next campaign?</h2>

          <button data-route="/signup" class="landing-primary">
            Start with MarketFlow
          </button>
        </section>

      </main>

      <footer class="landing-footer">
        <strong>MarketFlow</strong>
        <span>AI-powered marketing platform</span>
      </footer>

    </div>
  `;
}


export function signupView() {
  return `
    <main class="login-page">

      <section class="login-card">

        <button data-route="/" class="auth-back">
          ← Home
        </button>

        <div class="logo">M</div>

        <h1>Create account</h1>

        <p>Start using MarketFlow.</p>

        <form id="signupForm">

          <input
            id="signupName"
            placeholder="Full name"
            required
          >

          <input
            id="signupEmail"
            type="email"
            placeholder="Email address"
            required
          >

          <input
            id="signupPassword"
            type="password"
            placeholder="Password"
            minlength="6"
            required
          >

          <button type="submit">
            Create account
          </button>

        </form>

        <p class="auth-switch">
          Already have an account?
          <button data-route="/login">
            Login
          </button>
        </p>

      </section>

    </main>
  `;
}
