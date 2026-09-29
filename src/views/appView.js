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
        <button id="logoutBtn" class="logout">Logout</button>
      </header>

      <main id="pageContent"></main>

      <nav class="bottom-nav">
        <button data-page="dashboard" class="nav-btn active">
          <span>⌂</span>Home
        </button>

        <button data-page="messages" class="nav-btn">
          <span>💬</span>Messages
        </button>

        <button data-page="campaigns" class="nav-btn">
          <span>📢</span>Campaigns
        </button>

        <button data-page="ai" class="nav-btn">
          <span>✦</span>AI
        </button>

        <button data-page="reports" class="nav-btn">
          <span>📊</span>Reports
        </button>
      </nav>
    </div>
  `;
}

export function pageView(page) {
  if (page === "messages") {
    return `
      <section class="page">
        <h1>Messages</h1>
        <p class="subtitle">Manage customer conversations.</p>

        <div class="empty-card">
          <div class="big-icon">💬</div>
          <h2>No conversations yet</h2>
          <p>Instagram, Facebook and other channels will appear here.</p>
        </div>
      </section>
    `;
  }

  if (page === "campaigns") {
    return `
      <section class="page">
        <h1>Campaigns</h1>
        <p class="subtitle">Create and manage your marketing campaigns.</p>

        <button id="createCampaignBtn" class="primary-action">
          + Create Campaign
        </button>

        <div class="empty-card">
          <div class="big-icon">📢</div>
          <h2>No campaigns yet</h2>
          <p>Your active and scheduled campaigns will appear here.</p>
        </div>
      </section>
    `;
  }

  if (page === "ai") {
    return `
      <section class="page">
        <h1>AI Agent</h1>
        <p class="subtitle">Your marketing assistant.</p>

        <div class="ai-card">
          <div class="ai-status">
            <span class="status-dot"></span>
            AI Agent Ready
          </div>

          <h2>What should we market today?</h2>

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

  if (page === "reports") {
    return `
      <section class="page">
        <h1>Reports</h1>
        <p class="subtitle">Track performance across your channels.</p>

        <div class="empty-card">
          <div class="big-icon">📊</div>
          <h2>No data yet</h2>
          <p>Campaign performance and customer activity will appear here.</p>
        </div>
      </section>
    `;
  }

  return `
    <section class="page">
      <div class="hero">
        <p>Welcome back 👋</p>
        <h1>Marketing Dashboard</h1>
        <span>Everything you need in one place.</span>
      </div>

      <div class="stats">
        <article>
          <strong>0</strong>
          <span>Messages</span>
        </article>

        <article>
          <strong>0</strong>
          <span>Campaigns</span>
        </article>

        <article>
          <strong>0</strong>
          <span>Leads</span>
        </article>
      </div>

      <h2 class="section-title">Quick actions</h2>

      <div class="quick-grid">
        <button data-page="campaigns">
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
      </div>
    </section>
  `;
}
