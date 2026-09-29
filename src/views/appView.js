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

          <button
            class="delete-campaign"
            data-delete-campaign="${campaign.id}"
          >
            Delete
          </button>

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

export function reportsView() {
  return `
    <section class="page">

      <h1>Reports</h1>

      <p class="subtitle">
        Track performance across your channels.
      </p>

      <div class="empty-card">

        <div class="big-icon">
          📊
        </div>

        <h2>No data yet</h2>

        <p>
          Campaign performance and customer
          activity will appear here.
        </p>

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
