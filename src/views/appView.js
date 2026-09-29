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

        <p id="message" class="message"></p>
      </section>
    </main>
  `;
}

export function dashboardView(user) {
  return `
    <div class="dashboard">
      <header>
        <div>
          <h2>MarketFlow</h2>
          <small>${user}</small>
        </div>
        <button id="logoutBtn" class="logout">Logout</button>
      </header>

      <section class="welcome">
        <h1>Marketing Dashboard</h1>
        <p>Manage your marketing from one place.</p>
      </section>

      <section class="cards">
        <article>
          <span>💬</span>
          <h3>Messages</h3>
          <p>0 conversations</p>
        </article>

        <article>
          <span>📢</span>
          <h3>Campaigns</h3>
          <p>0 active campaigns</p>
        </article>

        <article>
          <span>🤖</span>
          <h3>AI Agent</h3>
          <p>Ready</p>
        </article>

        <article>
          <span>📊</span>
          <h3>Reports</h3>
          <p>No reports yet</p>
        </article>
      </section>

      <button class="primary-action">+ Create Campaign</button>
    </div>
  `;
}
