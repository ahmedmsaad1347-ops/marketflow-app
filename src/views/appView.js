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

        <div class="topbar-actions">

          <button
            id="notificationBtn"
            data-page="notifications"
            class="notification-button"
            aria-label="Notifications"
          >
            🔔

            <span
              id="notificationBadge"
              class="notification-badge"
              hidden
            >
              0
            </span>
          </button>

          <button
            id="logoutBtn"
            class="logout"
          >
            Logout
          </button>

        </div>
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


export function dashboardView(data = {}) {
  const stats =
    data.campaigns || {};

  const recent =
    data.recent_campaigns || [];

  const activity =
    data.recent_activity || [];

  const recentCards = recent.length
    ? recent.map(campaign => `
        <button
          class="dashboard-campaign-card"
          data-review-campaign="${campaign.id}"
        >
          <div>
            <small>
              ${campaignEscape(
                campaign.platform
              )}
            </small>

            <strong>
              ${campaignEscape(
                campaign.name
              )}
            </strong>

            <span>
              ${campaignEscape(
                campaign.product
              )}
            </span>
          </div>

          <span
            class="
              campaign-status
              status-${campaign.status.toLowerCase()}
            "
          >
            ${campaignEscape(
              campaign.status
            )}
          </span>
        </button>
      `).join("")
    : `
      <div class="empty-card">
        No campaigns yet.
      </div>
    `;

  const activityRows = activity.length
    ? activity.map(item => `
        <article class="dashboard-activity-row">
          <div class="campaign-event-dot"></div>

          <div>
            <strong>
              ${campaignEscape(
                item.campaign_name
              )}
            </strong>

            <p>
              ${campaignEscape(
                item.message
              )}
            </p>

            <small>
              ${
                new Date(
                  item.created_at
                ).toLocaleString()
              }
            </small>
          </div>
        </article>
      `).join("")
    : `
      <div class="campaign-history-empty">
        No activity yet.
      </div>
    `;

  return `
    <section class="page">

      <section class="strategy-engine-hero">
        <div class="strategy-engine-badge">✦ MARKETFLOW STRATEGY ENGINE</div>

        <h1>
          Not sure what campaign to run?
          <span>MarketFlow will build the plan with you.</span>
        </h1>

        <p>
          Answer a few business questions. MarketFlow will recommend the objective,
          channel, budget logic, audience, creative plan, tracking checklist and first test —
          then create the campaign draft for you.
        </p>

        <div class="strategy-engine-actions">
          <button data-strategy-start="guided" class="strategy-primary">Guide Me</button>
          <button data-strategy-start="quick" class="strategy-secondary">I Know What I Want</button>
          <button data-strategy-last class="strategy-secondary">View Last Strategy</button>
        </div>

        <small>
          Recommendations are based on your inputs and business economics. Performance is never guaranteed.
        </small>
      </section>

      <div class="hero">
        <p>Welcome back 👋</p>

        <h1>
          Marketing<br>
          Dashboard
        </h1>

        <span>
          Your MarketFlow workspace.
        </span>
      </div>

      <div class="dashboard-campaign-stats">

        <article>
          <small>Total</small>
          <strong>
            ${stats.total || 0}
          </strong>
        </article>

        <article>
          <small>Draft</small>
          <strong>
            ${stats.draft || 0}
          </strong>
        </article>

        <article>
          <small>Ready</small>
          <strong>
            ${stats.ready || 0}
          </strong>
        </article>

        <article>
          <small>Archived</small>
          <strong>
            ${stats.archived || 0}
          </strong>
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

        <button data-page="campaigns">
          <span>🗂️</span>
          Campaigns
        </button>

        <button data-page="reports">
          <span>📊</span>
          Analytics
        </button>

        <button data-page="connections">
          <span>🔗</span>
          Connections
        </button>

      </div>

      <div class="dashboard-section-head">
        <div>
          <p class="review-kicker">
            RECENT
          </p>

          <h2>Recent Campaigns</h2>
        </div>

        <button
          data-page="campaigns"
          class="dashboard-view-all"
        >
          View all
        </button>
      </div>

      <div class="dashboard-recent-list">
        ${recentCards}
      </div>

      <div class="dashboard-section-head">
        <div>
          <p class="review-kicker">
            ACTIVITY
          </p>

          <h2>Recent Activity</h2>
        </div>
      </div>

      <div class="dashboard-activity-card">
        ${activityRows}
      </div>

    </section>
  `;
}


export function campaignsView(
  campaigns,
  filters = {}
) {
  const state = {
    q: filters.q || "",
    status: filters.status || "All"
  };

  const statuses = [
    "All",
    "Draft",
    "Ready",
    "Archived"
  ];

  const filterButtons = statuses
    .map(status => `
      <button
        type="button"
        data-campaign-filter="${status}"
        class="campaign-filter ${
          state.status === status
            ? "active"
            : ""
        }"
      >
        ${status}
      </button>
    `)
    .join("");

  const list = campaigns.length
    ? campaigns.map(campaign => {

        const archived =
          campaign.status === "Archived";

        const ready =
          campaign.status === "Ready";

        return `
          <article class="campaign-card">

            <div class="campaign-card-top">
              <div>
                <small>
                  ${campaignEscape(
                    campaign.platform
                  )}
                </small>

                <h3>
                  ${campaignEscape(
                    campaign.name
                  )}
                </h3>
              </div>

              <span
                class="campaign-status status-${campaign.status.toLowerCase()}"
              >
                ${campaignEscape(
                  campaign.status
                )}
              </span>
            </div>

            <p>
              ${campaignEscape(
                campaign.product
              )}
            </p>

            <div class="campaign-meta">
              <span>
                🌍 ${campaignEscape(
                  campaign.country
                )}
              </span>

              <span>
                💰 ${campaignEscape(
                  campaign.budget
                )}
              </span>
            </div>

            <div class="campaign-management">

              <button
                data-review-campaign="${campaign.id}"
                class="campaign-main-action"
              >
                Review
              </button>

              <button
                data-edit-campaign="${campaign.id}"
              >
                ✏️ Edit
              </button>

              <button
                data-duplicate-campaign="${campaign.id}"
              >
                ⧉ Duplicate
              </button>

              ${
                !ready && !archived
                  ? `
                    <button
                      data-campaign-status="${campaign.id}"
                      data-status="Ready"
                    >
                      ✓ Ready
                    </button>
                  `
                  : ""
              }

              ${
                archived
                  ? `
                    <button
                      data-campaign-status="${campaign.id}"
                      data-status="Draft"
                    >
                      ↩ Restore
                    </button>
                  `
                  : `
                    <button
                      data-campaign-status="${campaign.id}"
                      data-status="Archived"
                    >
                      Archive
                    </button>
                  `
              }

              <button
                data-delete-campaign="${campaign.id}"
                class="campaign-danger-action"
              >
                Delete
              </button>

            </div>

          </article>
        `;
      }).join("")
    : `
      <div class="empty-card">
        <div class="big-icon">📢</div>

        <h2>No campaigns found</h2>

        <p>
          ${
            state.q ||
            state.status !== "All"
              ? "Try another search or filter."
              : "Create your first campaign to get started."
          }
        </p>
      </div>
    `;

  return `
    <section class="page">

      <div class="campaign-page-head">
        <div>
          <h1>Campaigns</h1>

          <p class="subtitle">
            Create, organize and manage
            your marketing campaigns.
          </p>
        </div>

        <button
          data-page="campaign-create"
          class="primary-action"
        >
          + New Campaign
        </button>
      </div>

      <div class="campaign-toolbar">

        <form
          id="campaignSearchForm"
          class="campaign-search"
        >
          <input
            id="campaignSearch"
            type="search"
            placeholder="Search campaigns..."
            value="${campaignEscape(
              state.q
            )}"
          >

          <button type="submit">
            Search
          </button>

          ${
            state.q
              ? `
                <button
                  type="button"
                  data-clear-campaign-search
                  class="campaign-clear"
                >
                  Clear
                </button>
              `
              : ""
          }
        </form>

        <div class="campaign-filters">
          ${filterButtons}
        </div>

      </div>

      <div class="campaign-list">
        ${list}
      </div>

    </section>
  `;
}


export function campaignFormView(
  campaign = null
) {
  const item = campaign || {};

  const editing = Boolean(item.id);

  const selected = value =>
    item.platform === value ||
    item.goal === value
      ? "selected"
      : "";

  return `
    <section class="page">

      <button
        data-page="campaigns"
        class="back-button"
      >
        ← Back
      </button>

      <p class="review-kicker">
        ${
          editing
            ? "EDIT CAMPAIGN"
            : "NEW CAMPAIGN"
        }
      </p>

      <h1>
        ${
          editing
            ? "Edit Campaign"
            : "Create Campaign"
        }
      </h1>

      <p class="subtitle">
        ${
          editing
            ? "Update the campaign details below."
            : "Tell MarketFlow what you want to promote."
        }
      </p>

      <form
        id="campaignForm"
        class="campaign-form"
        data-campaign-id="${
          editing
            ? item.id
            : ""
        }"
      >

        <label>
          Campaign name

          <input
            name="name"
            value="${campaignEscape(
              item.name || ""
            )}"
            placeholder="Summer Campaign"
            required
          >
        </label>

        <label>
          Product or service

          <input
            name="product"
            value="${campaignEscape(
              item.product || ""
            )}"
            placeholder="Men's clothing store"
            required
          >
        </label>

        <label>
          Target audience

          <input
            name="audience"
            value="${campaignEscape(
              item.audience || ""
            )}"
            placeholder="Men aged 18-35"
            required
          >
        </label>

        <label>
          Target country

          <input
            name="country"
            value="${campaignEscape(
              item.country || ""
            )}"
            placeholder="Egypt"
            required
          >
        </label>

        <label>
          Platform

          <select
            name="platform"
            required
          >
            <option value="">
              Choose platform
            </option>

            <option
              ${selected("Facebook")}
            >
              Facebook
            </option>

            <option
              ${selected("Instagram")}
            >
              Instagram
            </option>

            <option
              ${selected("TikTok")}
            >
              TikTok
            </option>

            <option
              ${selected("Google")}
            >
              Google
            </option>

            <option
              ${selected(
                "Multiple platforms"
              )}
            >
              Multiple platforms
            </option>
          </select>
        </label>

        <label>
          Budget

          <input
            name="budget"
            value="${campaignEscape(
              item.budget || ""
            )}"
            placeholder="100 USD"
            required
          >
        </label>

        <label>
          Campaign goal

          <select
            name="goal"
            required
          >
            <option value="">
              Choose goal
            </option>

            <option ${selected("Sales")}>
              Sales
            </option>

            <option ${selected("Leads")}>
              Leads
            </option>

            <option ${selected("Messages")}>
              Messages
            </option>

            <option
              ${selected(
                "Website traffic"
              )}
            >
              Website traffic
            </option>

            <option
              ${selected(
                "Brand awareness"
              )}
            >
              Brand awareness
            </option>
          </select>
        </label>

        <button
          type="submit"
          class="primary-action"
        >
          ${
            editing
              ? "Save Changes"
              : "Save Campaign"
          }
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

      <section class="settings-card">

        <div class="settings-card-head">
          <div>
            <h2>Profile</h2>

            <p>
              Update your account details.
            </p>
          </div>

          <span>👤</span>
        </div>

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
              Change your account password.
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
              minlength="8"
              required
            >
          </label>

          <label>
            Confirm new password

            <input
              name="confirm_password"
              type="password"
              autocomplete="new-password"
              minlength="8"
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
