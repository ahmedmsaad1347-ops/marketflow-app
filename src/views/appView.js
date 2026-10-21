export { campaignsView, campaignFormView, campaignReviewView } from './campaignsView.js';
import { icon, brandLogo, themeChoices } from './ui.js';

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
  const account = typeof user === 'string' ? { email: user } : (user || {});
  const name = campaignEscape(account.name || 'Your workspace');
  const email = campaignEscape(account.email || '');
  const initial = campaignEscape((account.name || account.email || 'M').trim().slice(0, 1).toUpperCase());
  const navigation = [
    ['dashboard', 'home', 'Overview'], ['campaigns', 'campaigns', 'Campaigns'],
    ['ai', 'spark', 'Strategy Agent'], ['reports', 'chart', 'Reports'], ['messages', 'message', 'Messages'],
  ];
  const tools = [['creative', 'file', 'Creative Studio'], ['strategy-history', 'history', 'Strategy history'], ['connections', 'link', 'Connections'], ['settings', 'settings', 'Settings']];
  if(account.platform_role==='owner')tools.push(['owner','shield','Owner console']);
  const navButton = ([page, symbol, label]) => `<button data-page="${page}" class="nav-btn" aria-label="${label}">${icon(symbol)}<span class="workspace-nav-label">${label}</span>${page === 'ai' ? '<span class="workspace-agent-tag">NEW</span>' : ''}</button>`;
  return `
    <div class="app-shell">
      <a href="#pageContent" class="workspace-skip">Skip to workspace</a>
      <button id="workspaceBackdrop" class="workspace-backdrop" aria-label="Close navigation" hidden></button>
      <aside class="workspace-sidebar" id="workspaceSidebar" aria-label="Workspace navigation">
        <div class="workspace-sidebar-brand"><a href="/" aria-label="MarketFlow home">${brandLogo()}</a><button class="workspace-menu-close workspace-icon-button" id="workspaceMenuClose" aria-label="Close navigation">${icon('close')}</button></div>
        <div class="workspace-switcher"><span class="workspace-avatar">${initial}</span><span><strong>Your workspace</strong><small>Marketing, with direction</small></span><span class="workspace-switcher-dot"></span></div>
        <p class="workspace-nav-caption">WORKSPACE</p>
        <nav class="bottom-nav workspace-navigation" aria-label="Main navigation">${navigation.map(navButton).join('')}</nav>
        <div class="workspace-tools"><p class="workspace-nav-caption">MANAGE</p><nav aria-label="Workspace tools">${tools.map(navButton).join('')}</nav></div>
        <div class="workspace-sidebar-bottom"><div class="workspace-draft-note">${icon('shield')}<div><strong>Your decisions come first.</strong><p>Plans become drafts. You stay in control.</p></div></div>${themeChoices('workspace-sidebar-theme')}<div class="workspace-account"><span class="workspace-avatar">${initial}</span><div><strong>${name}</strong><small>${email}</small></div></div></div>
      </aside>
      <div class="workspace-main">
        <header class="topbar">
          <div class="workspace-breadcrumb"><button id="workspaceMenuToggle" class="workspace-icon-button" aria-label="Open navigation" aria-controls="workspaceSidebar" aria-expanded="false">${icon('menu')}</button><span class="workspace-breadcrumb-root">Workspace</span><span class="workspace-breadcrumb-separator">/</span><strong id="workspacePageTitle">Overview</strong></div>
          <div class="topbar-actions">
            <button id="workspaceThemeToggle" class="workspace-icon-button" type="button" aria-label="Switch to light mode">${icon('sun')}</button>
            <button id="notificationBtn" data-page="notifications" class="notification-button workspace-icon-button" aria-label="Notifications">${icon('bell')}<span id="notificationBadge" class="notification-badge" hidden>0</span></button>
            <span class="workspace-header-divider"></span>
            <button id="logoutBtn" class="logout" aria-label="Logout">${icon('logout')}<span>Logout</span></button>
          </div>
        </header>
        <main id="pageContent" tabindex="-1"><div class="workspace-loading" role="status">${icon('spark')}<span>Opening your workspace…</span></div></main>
        <footer class="workspace-footer"><span>MarketFlow <span aria-hidden="true">/</span> Made for your next move.</span><span>Plan thoughtfully. Review before launch.</span></footer>
      </div>
    </div>`;
}


function campaignEscape(value = "") {
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


export function dashboardView(data = {}, user = {}) {
  const stats = data.campaigns || {};
  const recent = data.recent_campaigns || [];
  const activity = (data.recent_activity || []).slice(0, 4);
  const firstName = campaignEscape((user.name || 'there').trim().split(/\s+/)[0]);
  const counts = [
    ['Total campaigns', stats.total || 0, 'campaigns', 'All your campaign plans', 'blue'],
    ['Drafts', stats.draft || 0, 'file', 'Space to shape your next idea', 'purple'],
    ['Ready to review', stats.ready || 0, 'check', 'Review before any launch', 'mint'],
    ['Archived', stats.archived || 0, 'archive', 'Saved for future reference', 'slate'],
  ];
  const recentCards = recent.length ? recent.map(campaign => `<button class="dashboard-campaign-card" data-review-campaign="${campaign.id}"><span class="workspace-campaign-icon">${icon('campaigns')}</span><div><small>${campaignEscape(campaign.platform)}</small><strong>${campaignEscape(campaign.name)}</strong><span>${campaignEscape(campaign.product)}</span></div><span class="campaign-status status-${campaignEscape(campaign.status.toLowerCase())}">${campaignEscape(campaign.status)}</span><span class="workspace-row-arrow">${icon('arrow')}</span></button>`).join('')
    : `<div class="workspace-empty"><span class="workspace-empty-icon">${icon('campaigns')}</span><h3>A little planning goes a long way.</h3><p>Your campaign drafts will appear here. Start with your business and let the strategy guide your first move.</p><button data-strategy-start="guided" class="workspace-text-action">Build your first strategy ${icon('arrow')}</button></div>`;
  const activityRows = activity.length ? activity.map(item => `<article class="dashboard-activity-row"><span class="workspace-activity-icon">${icon('check')}</span><div><strong>${campaignEscape(item.campaign_name)}</strong><p>${campaignEscape(item.message)}</p><small>${campaignEscape(new Date(item.created_at).toLocaleString())}</small></div></article>`).join('')
    : `<div class="workspace-activity-empty"><span class="workspace-activity-icon">${icon('history')}</span><div><strong>Every move, in one place.</strong><p>Campaign updates will appear here as you build and refine your plans.</p></div></div>`;
  return `<section class="page workspace-dashboard">
    <div class="workspace-page-heading"><div><p class="workspace-eyebrow">YOUR MARKETING, IN FOCUS</p><h1>Welcome back, ${firstName}<span class="workspace-heading-dot">.</span></h1><p class="subtitle">A clear view of your plans. A confident next step.</p></div><button data-page="campaign-create" class="workspace-create-button" aria-label="New campaign">${icon('plus')}<span>New campaign</span></button></div>
    <div class="workspace-dashboard-top">
      <section class="workspace-strategy-hero"><div class="workspace-hero-grid" aria-hidden="true"></div><div class="workspace-hero-copy"><span class="workspace-hero-badge">${icon('spark')} MARKETFLOW STRATEGY ENGINE</span><h2>Big ideas deserve<br>a clear <span>next move.</span></h2><p>Turn your business brief into a channel recommendation, a thoughtful budget, and a campaign you can build on.</p><div class="workspace-hero-actions"><button data-strategy-start="guided" class="workspace-mint-button">Guide Me ${icon('arrow')}</button><button data-strategy-start="quick" class="workspace-hero-secondary">I Know What I Want</button></div><small>${icon('shield')} Every recommendation starts with your business.</small></div><div class="workspace-flow-art" aria-hidden="true"><div class="workspace-flow-pill">${icon('file')}<span>YOUR BRIEF</span><i>01</i></div><div class="workspace-flow-connector"></div><div class="workspace-flow-core">${icon('spark')}<strong>A plan with purpose.</strong><span>Channel · Budget · Creative</span><div><i></i><i></i><i></i><i></i><i></i><i></i><i></i><i></i><i></i></div></div><div class="workspace-flow-connector"></div><div class="workspace-flow-pill workspace-flow-draft">${icon('check')}<span>YOUR NEXT CAMPAIGN</span><i>Draft</i></div></div></section>
      <section class="workspace-next-card"><div class="workspace-card-kicker">FROM IDEA TO ACTION <span>01 → 03</span></div><h2>A good plan starts here.</h2><ol class="workspace-workflow"><li><span>01</span><div><strong>Tell your story</strong><p>Your offer, audience, and ambition.</p></div></li><li><span>02</span><div><strong>Find your direction</strong><p>Understand the channel and the numbers.</p></div></li><li><span>03</span><div><strong>Make it your own</strong><p>Refine the strategy. Review your draft.</p></div></li></ol><button data-page="strategy-history" class="workspace-text-action">Explore your strategy history ${icon('arrow')}</button></section>
    </div>
    <div class="workspace-stat-grid">${counts.map(([label, count, symbol, help, accent]) => `<article class="workspace-stat-card"><div><span class="workspace-stat-label">${label}</span><span class="workspace-stat-icon workspace-accent-${accent}">${icon(symbol)}</span></div><strong>${Number(count).toLocaleString()}</strong><small>${help}</small></article>`).join('')}</div>
    <div class="workspace-dashboard-bottom"><section class="workspace-panel workspace-campaign-panel"><div class="workspace-panel-head"><div><p class="workspace-eyebrow">KEEP THE MOMENTUM</p><h2>Recent campaigns</h2></div><button data-page="campaigns" class="workspace-text-action">View all ${icon('arrow')}</button></div><div class="dashboard-recent-list">${recentCards}</div></section><section class="workspace-panel workspace-activity-panel"><div class="workspace-panel-head"><div><p class="workspace-eyebrow">YOUR WORKSPACE PULSE</p><h2>Recent activity</h2></div><span class="workspace-live-dot"></span></div><div class="dashboard-activity-card">${activityRows}</div><div class="workspace-safety-note">${icon('shield')}<span>Accepting a strategy saves a campaign draft. Review it before any future launch.</span></div></section></div>
    <div class="workspace-quick-links"><span>Make your next move</span><button data-workspace-agent>${icon('spark')} Strategy Agent ${icon('arrow')}</button><button data-page="connections">${icon('link')} Connect your channels ${icon('arrow')}</button><button data-page="reports">${icon('chart')} Explore your reports ${icon('arrow')}</button><button data-strategy-last>${icon('history')} Last strategy ${icon('arrow')}</button></div>
  </section>`;
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
    <section class="page strategy-agent-page">
      <p class="review-kicker">MARKETFLOW RESEARCH STRATEGY AGENT V2</p>
      <h1>Your built-in marketing strategist</h1>
      <p class="subtitle">
        Start with your business. Research public sources, review the recommendation, and shape a plan you understand.
      </p>
      <button data-page="creative" class="workspace-create-button">${icon('file')} Open Creative Studio · write and refine content</button>

      <section class="strategy-agent-card">
        <div class="strategy-agent-status">
          <span class="status-dot"></span>
          Built-in research & decision agent
        </div>

        <div id="strategyAgentChat" class="strategy-agent-chat">
          <article class="agent-bubble">
            <strong>MarketFlow Agent</strong>
            <p>
              I will ask only the questions that affect the marketing decision,
              then choose the primary campaign and explain the plan.
            </p>
          </article>
        </div>

        <button id="reviewAgentAnswersBtn" class="strategy-secondary" type="button" hidden>Review / edit answers</button>
        <div id="strategyAgentComposer" class="strategy-agent-composer">
          <button id="startStrategyAgentBtn" class="primary-action">
            Start Strategy Agent
          </button>
        </div>
      </section>
    </section>
  `;
}

export { reportsView } from './analyticsView.js';

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

export function notificationsView(
  data = {}
) {
  const notifications =
    data.notifications || [];

  const unread =
    data.unread_count || 0;

  const formatDate = value => {
    if (!value) return "";

    let normalized = value;

    if (
      !value.endsWith("Z") &&
      !/[+-]\d\d:\d\d$/.test(value)
    ) {
      normalized = value + "Z";
    }

    const date =
      new Date(normalized);

    if (
      Number.isNaN(
        date.getTime()
      )
    ) {
      return value;
    }

    return date.toLocaleString();
  };

  const iconFor = type => {
    if (type === "Created") {
      return "✨";
    }

    if (type === "Edited") {
      return "✏️";
    }

    if (type === "Status changed") {
      return "🔄";
    }

    return "🔔";
  };

  const list =
    notifications.length
      ? notifications.map(item => `
          <button
            class="
              notification-item
              ${
                item.is_read
                  ? ""
                  : "unread"
              }
            "
            data-notification-id="${item.id}"
            data-campaign-id="${
              item.campaign_id || ""
            }"
          >

            <span
              class="notification-icon"
            >
              ${iconFor(
                item.event_type
              )}
            </span>

            <span
              class="notification-content"
            >

              <span
                class="notification-title"
              >
                ${campaignEscape(
                  item.campaign_name
                )}
              </span>

              <span
                class="notification-message"
              >
                ${campaignEscape(
                  item.message
                )}
              </span>

              <small>
                ${formatDate(
                  item.created_at
                )}
              </small>

            </span>

            ${
              item.is_read
                ? ""
                : `
                  <span
                    class="notification-unread-dot"
                  ></span>
                `
            }

          </button>
        `).join("")
      : `
        <div class="empty-card">
          <div class="big-icon">
            🔔
          </div>

          <h2>No notifications yet</h2>

          <p>
            Campaign activity will
            appear here automatically.
          </p>
        </div>
      `;

  return `
    <section
      class="page notifications-page"
    >

      <div
        class="notifications-header"
      >

        <div>
          <p class="review-kicker">
            ACTIVITY CENTER
          </p>

          <h1>Notifications</h1>

          <p class="subtitle">
            ${
              unread
                ? `${unread} unread notifications`
                : "You're all caught up."
            }
          </p>
        </div>

        ${
          unread
            ? `
              <button
                id="markAllNotifications"
                class="mark-all-notifications"
              >
                Mark all read
              </button>
            `
            : ""
        }

      </div>

      <div
        class="notifications-list"
      >
        ${list}
      </div>

    </section>
  `;
}


export function settingsView(
  user = {}
) {
  return `
    <section class="page settings-page">

      <p class="review-kicker">
        ACCOUNT
      </p>

      <h1>Settings</h1>

      <p class="subtitle">
        Manage your MarketFlow account
        and security.
      </p>

      <section class="settings-card workspace-appearance-card"><div class="settings-card-head"><div><p class="workspace-eyebrow">MAKE IT YOURS</p><h2>Appearance</h2><p>A calm canvas for the way you work. Saved on this device.</p></div>${icon('sun')}</div><div class="workspace-theme-previews"><button type="button" data-theme-choice="light" aria-pressed="false"><span class="workspace-theme-preview workspace-theme-preview-light"><i></i><span><b></b><em></em><em></em></span></span><strong>Light</strong><small>A bright, clear workspace</small></button><button type="button" data-theme-choice="dark" aria-pressed="false"><span class="workspace-theme-preview workspace-theme-preview-dark"><i></i><span><b></b><em></em><em></em></span></span><strong>Deep Blue</strong><small>A rich navy workspace</small></button></div></section>

      <section class="settings-card">

        <div class="settings-card-head">
          <div>
            <h2>Profile</h2>

            <p>
              Update your display name. Your verified email identifies this account.
            </p>
          </div>

          <span>👤</span>
        </div>

        ${user.password_enabled === false ? '<p class="subtitle">You signed in with a social account. <a href="/forgot-password">Set an account password</a> to manage your profile or use email sign-in.</p>' : ''}
        <form
          id="profileSettingsForm"
          class="campaign-form"
        >

          <label>
            Name

            <input
              name="name"
              value="${campaignEscape(
                user.name || ""
              )}"
              required
              minlength="2"
            >
          </label>

          <label>
            Email

            <input
              name="email"
              type="email"
              readonly
              aria-readonly="true"
              value="${campaignEscape(
                user.email || ""
              )}"
              required
            >
          </label>

          <label>
            Current password

            <input
              name="current_password"
              type="password"
              autocomplete="current-password"
              placeholder="Confirm your password"
              required
            >
          </label>

          <button
            type="submit"
            class="primary-action"
          >
            Save Profile
          </button>

          <p
            id="profileSettingsMessage"
            class="settings-message"
          ></p>

        </form>

      </section>


      <section class="settings-card">

        <div class="settings-card-head">
          <div>
            <h2>Security</h2>

            <p>
              Use a unique passphrase with at least 15 characters.
            </p>
          </div>

          <span>🔐</span>
        </div>

        <form
          id="passwordSettingsForm"
          class="campaign-form"
        >

          <label>
            Current password

            <input
              name="current_password"
              type="password"
              autocomplete="current-password"
              required
            >
          </label>

          <label>
            New password

            <input
              name="new_password"
              type="password"
              autocomplete="new-password"
              minlength="15"
              maxlength="128"
              required
            >
          </label>

          <label>
            Confirm new password

            <input
              name="confirm_password"
              type="password"
              autocomplete="new-password"
              minlength="15"
              maxlength="128"
              required
            >
          </label>

          <button
            type="submit"
            class="primary-action"
          >
            Change Password
          </button>

          <p
            id="passwordSettingsMessage"
            class="settings-message"
          ></p>

        </form>

      </section>

      <section class="settings-security-note">
        <strong>Security note</strong>

        <p>
          Changing your password signs out
          old MarketFlow sessions for your
          account.
        </p>
      </section>

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
