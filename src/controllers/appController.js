import {
  getCurrentUser,
  logoutUser,
  updateProfile,
  changePassword,
  generateStrategy,
  getLatestStrategy,
  getStrategies,
  getStrategy,
  acceptStrategy,
  startStrategyAgent,
  answerStrategyAgent,
  buildStrategyAgent,
  resumeStrategyAgent,
  reviseStrategyAgent,
  editStrategyAgentAnswers,
  getDashboardOverview,
  getNotifications,
  markNotificationRead,
  markAllNotificationsRead,
  previewCampaign,
  createCampaign,
  getCampaigns,
  getCampaign,
  deleteCampaign,
  updateCampaign,
  duplicateCampaign,
  updateCampaignStatus,
  getAnalytics
} from "../services/api.js";

import {
  appView,
  dashboardView,
  campaignsView,
  campaignFormView,
  messagesView,
  aiView,
  reportsView,
  connectionsView,
  notificationsView,
  settingsView,
  campaignReviewView
} from "../views/appView.js";

import {
  renderAnalyticsCharts
} from "../services/analyticsCharts.js";

import {
  strategyView,
  strategyResultView,
  strategyHistoryView
} from "../views/strategyView.js";

const app = document.querySelector("#app");

let currentUser = null;

let strategyMode = "guided";

let campaignFilters = {
  status: "All",
  q: ""
};

export async function startApp() {
  try {
    const response = await getCurrentUser();

    currentUser = response.user;

    await showApp(currentUser);
  } catch {
    window.history.replaceState({}, "", "/login");
    window.dispatchEvent(new PopStateEvent("popstate"));
  }
}

async function showApp(user) {
  app.innerHTML = appView(user.email);

  const logoutButton =
    document.querySelector("#logoutBtn");

  logoutButton.addEventListener("click", async () => {
    logoutButton.disabled = true;
    try {
      await logoutUser();
    } catch (error) {
      logoutButton.disabled = false;
      logoutButton.textContent = "Retry sign out";
      let message = document.querySelector('#logoutError');
      if (!message) {
        message = document.createElement('p');
        message.id = 'logoutError';
        message.setAttribute('role', 'alert');
        logoutButton.after(message);
      }
      message.textContent = "Sign-out could not be confirmed. Check your connection and retry.";
      return;
    }
    currentUser = null;
    try {
      for (const storage of [localStorage, sessionStorage]) {
        Object.keys(storage).filter(key => key.startsWith('marketflow_')).forEach(key => storage.removeItem(key));
      }
    } catch { /* Server-side logout already succeeded, even if storage is unavailable. */ }
    window.history.replaceState({}, "", "/login");
    window.dispatchEvent(new PopStateEvent("popstate"));
  });

  const state =
    window.history.state || {};

  if (
    !state.marketflowApp ||
    !state.page
  ) {
    window.history.replaceState(
      {
        marketflowApp: true,
        page: "dashboard"
      },
      "",
      "/app"
    );

    await showPage(
      "dashboard",
      false
    );

    return;
  }

  await renderAppHistoryState(
    state
  );
}


function saveAppHistory(
  page,
  extra = {}
) {
  if (
    window.location.pathname !==
    "/app"
  ) {
    return;
  }

  const nextState = {
    marketflowApp: true,
    page,
    ...extra
  };

  const current =
    window.history.state || {};

  const sameState =
    current.marketflowApp &&
    current.page ===
      nextState.page &&
    String(
      current.id || ""
    ) ===
      String(
        nextState.id || ""
      );

  if (sameState) {
    return;
  }

  window.history.pushState(
    nextState,
    "",
    "/app"
  );
}


async function renderAppHistoryState(
  state = {}
) {
  if (state.page === 'strategy-edit' && state.id) {
    await showStrategyEditor({strategyId: state.id}, false);
    return;
  }
  if (state.page === 'strategy-agent-edit' && state.id) {
    await showStrategyEditor({sessionId: state.id}, false);
    return;
  }
  if (
    state.page ===
    "campaign-review" &&
    state.id
  ) {
    await showCampaignReview(
      state.id,
      false
    );

    return;
  }

  if (
    state.page ===
    "campaign-edit" &&
    state.id
  ) {
    await showCampaignEdit(
      state.id,
      false
    );

    return;
  }

  if (
    state.page ===
    "strategy-result"
  ) {
    if (state.id) {
      await showStrategyById(state.id, false);
    } else {
      await showLatestStrategy(false);
    }
    return;
  }

  await showPage(
    state.page || "dashboard",
    false
  );
}


async function showPage(
  page,
  pushHistory = true
) {
  const pageContent =
    document.querySelector("#pageContent");

  try {
    if (page === "dashboard") {
      const response =
        await getDashboardOverview();

      pageContent.innerHTML =
        dashboardView(response);
    }

    if (page === "strategy") {
      pageContent.innerHTML =
        strategyView(strategyMode);
    }

    if (page === "strategy-history") {
      const response = await getStrategies(50);
      pageContent.innerHTML = strategyHistoryView(response.strategies || []);
    }

    if (page === "campaigns") {
      const response = await getCampaigns(
        campaignFilters.status,
        campaignFilters.q
      );

      pageContent.innerHTML =
        campaignsView(
          response.campaigns,
          campaignFilters
        );
    }

    if (page === "campaign-create") {
      pageContent.innerHTML =
        campaignFormView();
    }

    if (page === "messages") {
      pageContent.innerHTML =
        messagesView();
    }

    if (page === "ai") {
      pageContent.innerHTML =
        aiView();
    }

    if (page === "reports") {
      const analytics =
        await getAnalytics(30);

      pageContent.innerHTML =
        reportsView(
          analytics,
          30
        );

      renderAnalyticsCharts(
        analytics
      );

      attachAnalyticsFilters();
    }

    if (page === "connections") {
      pageContent.innerHTML =
        connectionsView();
    }

    if (page === "notifications") {
      const response =
        await getNotifications();

      pageContent.innerHTML =
        notificationsView(
          response
        );
    }

    if (page === "settings") {
      pageContent.innerHTML =
        settingsView(
          currentUser || {}
        );
    }

    if (pushHistory) {
      saveAppHistory(page);
    }

    setActiveNavigation(page);

    attachNavigation();
    attachStrategyLaunchers();
    attachStrategyLast();
    attachStrategyHistory();
    attachStrategyWizard();
    attachStrategyResultActions();
    attachStrategyAgent();
    attachCampaignForm();
    attachCampaignDelete();
    attachCampaignReview();
    attachCampaignFilters();
    attachCampaignActions();
    attachNotifications();
    attachAccountSettings();

    await refreshNotificationBadge();

    window.scrollTo(0, 0);

  } catch (error) {
    pageContent.innerHTML = `
      <section class="page">

        <div class="empty-card">
          <h2>Connection error</h2>

          <p>${error.message}</p>

          <p>
            Make sure the Python backend is running.
          </p>
        </div>

      </section>
    `;
  }
}


function attachStrategyLaunchers() {
  document.querySelectorAll('[data-edit-strategy]').forEach(button => {
    button.onclick = async () => {
      button.disabled = true;
      try {
        await showStrategyEditor({strategyId: button.dataset.editStrategy});
      } catch (error) {
        button.disabled = false;
        alert(error.message);
      }
    };
  });
  document
    .querySelectorAll("[data-strategy-start]")
    .forEach(button => {
      button.onclick = () => {
        strategyMode = button.dataset.strategyStart || "guided";
        showPage("strategy");
      };
    });
}


async function showStrategyEditor({strategyId, sessionId}, pushHistory = true) {
  let answers;
  let mode = 'agent';
  if (sessionId) {
    const response = await resumeStrategyAgent(sessionId);
    answers = response.answers || {};
    if (response.status === 'Complete' && response.strategy_id) {
      return showStrategyEditor({strategyId: response.strategy_id}, pushHistory);
    }
  } else {
    const response = await getStrategy(strategyId);
    answers = response.strategy.input;
    mode = response.strategy.mode;
  }
  const page = document.querySelector('#pageContent');
  page.innerHTML = strategyView('quick');
  page.querySelector('h1').textContent = 'Review & edit your answers';
  page.querySelector('.subtitle').textContent = 'Change the fields you need, then rebuild. Your previous strategy and campaign stay saved.';
  const form = page.querySelector('#strategyForm');
  form.dataset.editMode = mode;
  if (sessionId) form.dataset.agentSessionId = sessionId;
  for (const [name, value] of Object.entries(answers)) {
    const field = form.elements.namedItem(name);
    if (!field) continue;
    if (field.type === 'checkbox') field.checked = value === true;
    else {
      if (field.tagName === 'SELECT' && value != null && ![...field.options].some(option => option.value === String(value))) {
        field.add(new Option(String(value), String(value)));
      }
      field.value = value ?? '';
    }
  }
  if (pushHistory) saveAppHistory(sessionId ? 'strategy-agent-edit' : 'strategy-edit', {id: sessionId || strategyId});
  setActiveNavigation('strategy');
  attachNavigation();
  attachStrategyLaunchers();
  attachStrategyWizard();
  document.querySelector('#strategyGenerate').textContent = 'Save answers & Build Strategy';
  window.scrollTo(0, 0);
}


function attachStrategyLast() {
  document
    .querySelectorAll(
      "[data-strategy-last]"
    )
    .forEach(button => {

      button.onclick =
        async () => {
          const oldText =
            button.textContent;

          button.disabled = true;
          button.textContent =
            "Loading...";

          try {
            await showLatestStrategy();
          } catch (error) {
            button.disabled = false;
            button.textContent =
              oldText;

            alert(error.message);
          }
        };

    });
}


async function showLatestStrategy(
  pushHistory = true
) {
  const response =
    await getLatestStrategy();

  const latest =
    response.strategy;

  if (!latest) {
    alert(
      "No saved strategy yet. Build your first strategy first."
    );

    return;
  }

  const pageContent =
    document.querySelector(
      "#pageContent"
    );

  pageContent.innerHTML =
    strategyResultView({
      strategy_id:
        latest.id,
      strategy:
        latest.output,
      status:
        latest.status,
      campaign_id:
        latest.campaign_id
    });

  if (pushHistory) {
    saveAppHistory(
      "strategy-result",
      { id: latest.id }
    );
  }

  setActiveNavigation(
    "strategy"
  );

  attachNavigation();
  attachStrategyLaunchers();
  attachStrategyLast();
  attachStrategyResultActions();

  window.scrollTo(
    0,
    0
  );
}



function attachStrategyHistory() {
  document.querySelectorAll("[data-view-strategy]").forEach(button => {
    button.onclick = async () => {
      const oldText = button.textContent;
      button.disabled = true;
      button.textContent = "Loading...";
      try {
        await showStrategyById(button.dataset.viewStrategy);
      } catch (error) {
        button.disabled = false;
        button.textContent = oldText;
        alert(error.message);
      }
    };
  });
}

async function showStrategyById(id, pushHistory = true) {
  const response = await getStrategy(id);
  const saved = response.strategy;
  if (!saved) {
    alert("Strategy not found.");
    return;
  }

  const pageContent = document.querySelector("#pageContent");
  pageContent.innerHTML = strategyResultView({
    strategy_id: saved.id,
    strategy: saved.output,
    status: saved.status,
    campaign_id: saved.campaign_id
  });

  if (pushHistory) {
    saveAppHistory("strategy-result", { id: saved.id });
  }

  setActiveNavigation("strategy");
  attachNavigation();
  attachStrategyLaunchers();
  attachStrategyLast();
  attachStrategyHistory();
  attachStrategyResultActions();
  window.scrollTo(0, 0);
}

function attachStrategyWizard() {
  const form = document.querySelector("#strategyForm");
  if (!form) return;

  const guided = form.dataset.strategyMode === "guided";
  let step = 1;
  const totalSteps = 4;

  const renderStep = () => {
    if (!guided) return;

    form.querySelectorAll("[data-strategy-step]").forEach(section => {
      section.hidden = Number(section.dataset.strategyStep) !== step;
    });

    const text = document.querySelector("#strategyProgressText");
    const bar = document.querySelector("#strategyProgressBar");
    const back = document.querySelector("#strategyBack");
    const next = document.querySelector("#strategyNext");
    const generate = document.querySelector("#strategyGenerate");

    if (text) text.textContent = `Step ${step} of ${totalSteps}`;
    if (bar) bar.style.width = `${(step / totalSteps) * 100}%`;
    if (back) back.hidden = step === 1;
    if (next) next.hidden = step === totalSteps;
    if (generate) generate.hidden = step !== totalSteps;
  };

  const validateCurrentStep = () => {
    const current = form.querySelector(`[data-strategy-step="${step}"]`);
    if (!current) return true;

    const fields = [...current.querySelectorAll("input, select, textarea")];
    for (const field of fields) {
      if (!field.checkValidity()) {
        field.reportValidity();
        return false;
      }
    }
    return true;
  };

  const next = document.querySelector("#strategyNext");
  const back = document.querySelector("#strategyBack");

  if (next) {
    next.onclick = () => {
      if (!validateCurrentStep()) return;
      step = Math.min(totalSteps, step + 1);
      renderStep();
      window.scrollTo(0, 0);
    };
  }

  if (back) {
    back.onclick = () => {
      step = Math.max(1, step - 1);
      renderStep();
      window.scrollTo(0, 0);
    };
  }

  form.onsubmit = async event => {
    event.preventDefault();
    if (guided && !validateCurrentStep()) return;

    const button = document.querySelector("#strategyGenerate");
    const data = new FormData(form);
    const numberOrZero = name => Number(data.get(name) || 0);

    const payload = {
      mode: form.dataset.strategyMode,
      business_name: data.get("business_name"),
      product: data.get("product"),
      offer: data.get("offer") || "",
      country: data.get("country"),
      audience: data.get("audience"),
      objective: data.get("objective"),
      demand_type: data.get("demand_type"),
      sales_channel: data.get("sales_channel"),
      currency: data.get("currency"),
      total_budget: numberOrZero("total_budget"),
      campaign_days: Number(data.get("campaign_days") || 30),
      price: numberOrZero("price"),
      gross_margin_percent: numberOrZero("gross_margin_percent"),
      extra_variable_cost_per_order:
        numberOrZero("extra_variable_cost_per_order"),
      lead_to_sale_rate_percent:
        numberOrZero("lead_to_sale_rate_percent"),
      has_website: data.get("has_website") === "on",
      has_tracking: data.get("has_tracking") === "on",
      has_previous_sales: data.get("has_previous_sales") === "on",
      has_video_creatives: data.get("has_video_creatives") === "on",
      notes: data.get("notes") || ""
    };

    if (button) {
      button.disabled = true;
      button.textContent = "Building your strategy...";
    }

    try {
      let response;
      if (form.dataset.editMode === 'agent') {
        let sid = form.dataset.agentSessionId;
        if (sid) {
          await editStrategyAgentAnswers(sid, payload);
        } else {
          const session = await reviseStrategyAgent(payload);
          sid = session.session_id;
          form.dataset.agentSessionId = sid;
          saveAppHistory('strategy-agent-edit', {id: sid});
        }
        response = await buildStrategyAgent(sid);
        if (String(localStorage.getItem('marketflow_strategy_agent_session')) === String(sid)) {
          localStorage.removeItem('marketflow_strategy_agent_session');
          localStorage.removeItem('marketflow_strategy_agent_chat');
          localStorage.removeItem('marketflow_strategy_agent_draft');
        }
      } else {
        response = await generateStrategy(payload);
      }
      const pageContent = document.querySelector("#pageContent");
      pageContent.innerHTML = strategyResultView(response);

      saveAppHistory(
        "strategy-result",
        { id: response.strategy_id }
      );

      setActiveNavigation("strategy");
      attachNavigation();
      attachStrategyLaunchers();
      attachStrategyLast();
      attachStrategyResultActions();
      window.scrollTo(0, 0);
    } catch (error) {
      alert("Strategy could not be generated.\n\n" + error.message);
      if (button) {
        button.disabled = false;
        button.textContent = "Build My Strategy";
      }
    }
  };

  renderStep();
}


function attachStrategyResultActions() {
  const button = document.querySelector("#acceptStrategyBtn");
  if (!button) return;

  button.onclick = async () => {
    const id = button.dataset.strategyId;
    button.disabled = true;
    button.textContent = "Creating campaign draft...";

    try {
      const response = await acceptStrategy(id);
      if (!response.campaign) {
        throw new Error("Campaign draft was not returned");
      }

      await showCampaignReview(response.campaign.id);
      await refreshNotificationBadge();
    } catch (error) {
      button.disabled = false;
      button.textContent = "Accept Strategy & Create Draft";
      alert(error.message);
    }
  };
}


function attachAnalyticsFilters() {
  document
    .querySelectorAll(
      "[data-analytics-days]"
    )
    .forEach(button => {

      button.onclick = async () => {
        const days =
          Number(
            button.dataset.analyticsDays
          );

        const response =
          await getAnalytics(days);

        const pageContent =
          document.querySelector(
            "#pageContent"
          );

        pageContent.innerHTML =
          reportsView(
            response,
            days
          );

        renderAnalyticsCharts(
          response
        );

        attachNavigation();
        attachAnalyticsFilters();

        setActiveNavigation(
          "reports"
        );
      };

    });
}



function attachNavigation() {
  document
    .querySelectorAll("[data-page]")
    .forEach(button => {

      button.onclick = () => {
        showPage(button.dataset.page);
      };

    });
}




function attachStrategyAgent() {
  const startButton = document.querySelector("#startStrategyAgentBtn");
  if (!startButton) return;

  const chat = document.querySelector("#strategyAgentChat");
  const composer = document.querySelector("#strategyAgentComposer");
  const reviewButton = document.querySelector('#reviewAgentAnswersBtn');

  const SESSION_KEY = "marketflow_strategy_agent_session";
  const CHAT_KEY = "marketflow_strategy_agent_chat";
  const DRAFT_KEY = "marketflow_strategy_agent_draft";

  let sessionId = null;
  if (reviewButton) reviewButton.onclick = () => {
    showStrategyEditor({sessionId}).catch(error => alert(error.message));
  };

  const saveChat = () => {
    const items = Array.from(
      chat.querySelectorAll(".agent-bubble")
    ).map(node => ({
      role: node.classList.contains("user") ? "user" : "agent",
      text: node.querySelector("p")?.textContent || ""
    }));

    localStorage.setItem(
      CHAT_KEY,
      JSON.stringify(items)
    );
  };

  const restoreChat = () => {
    const raw = localStorage.getItem(CHAT_KEY);
    if (!raw) return false;

    try {
      const items = JSON.parse(raw);

      chat.innerHTML = "";

      items.forEach(item => {
        const article = document.createElement("article");
        article.className =
          item.role === "user"
            ? "agent-bubble user"
            : "agent-bubble";

        article.innerHTML = `
          <strong>${item.role === "user" ? "You" : "MarketFlow Agent"}</strong>
          <p></p>
        `;

        article.querySelector("p").textContent =
          String(item.text || "");

        chat.appendChild(article);
      });

      return items.length > 0;
    } catch {
      return false;
    }
  };

  const addBubble = (role, text) => {
    const article = document.createElement("article");
    article.className =
      role === "user"
        ? "agent-bubble user"
        : "agent-bubble";

    article.innerHTML = `
      <strong>${role === "user" ? "You" : "MarketFlow Agent"}</strong>
      <p></p>
    `;

    article.querySelector("p").textContent =
      String(text || "");

    chat.appendChild(article);
    saveChat();

    article.scrollIntoView({
      behavior: "smooth",
      block: "end"
    });
  };

  const clearSavedAgent = () => {
    localStorage.removeItem(SESSION_KEY);
    localStorage.removeItem(CHAT_KEY);
    localStorage.removeItem(DRAFT_KEY);
  };

  const showBuildButton = message => {
    if (message) {
      addBubble("agent", message);
    }

    composer.innerHTML = "";
    localStorage.removeItem(DRAFT_KEY);

    const button = document.createElement("button");
    button.type = "button";
    button.className = "primary-action";
    button.textContent = "Build Strategy";

    button.onclick = async () => {
      button.disabled = true;
      if (reviewButton) reviewButton.disabled = true;
      button.textContent =
        "Researching, reviewing & building...";

      try {
        const response =
          await buildStrategyAgent(sessionId);

        clearSavedAgent();

        const pageContent =
          document.querySelector("#pageContent");

        pageContent.innerHTML =
          strategyResultView(response);

        saveAppHistory(
          "strategy-result",
          { id: response.strategy_id }
        );

        setActiveNavigation("strategy");
        attachNavigation();
        attachStrategyLaunchers();
        attachStrategyLast();

        if (
          typeof attachStrategyHistory
          === "function"
        ) {
          attachStrategyHistory();
        }

        attachStrategyResultActions();
        window.scrollTo(0, 0);

      } catch (error) {
        button.disabled = false;
        if (reviewButton) reviewButton.disabled = false;
        button.textContent = "Build Strategy";

        addBubble(
          "agent",
          "I could not build the strategy: "
          + error.message
        );
      }
    };

    composer.appendChild(button);
  };

  const renderQuestion = question => {
    if (!question) return;

    const lastAgentText =
      chat.lastElementChild
        ?.querySelector("p")
        ?.textContent;

    if (lastAgentText !== question.label) {
      addBubble("agent", question.label);
    }

    composer.innerHTML = "";

    const submitValue = async value => {
      if (
        value === ""
        && !question.optional
      ) {
        alert("Please answer this question.");
        return;
      }

      addBubble(
        "user",
        value === true
          ? "Yes"
          : value === false
            ? "No"
            : value === ""
              ? "Skip"
              : value
      );

      localStorage.removeItem(DRAFT_KEY);

      composer.innerHTML = `
        <button
          class="primary-action"
          disabled
        >
          Thinking...
        </button>
      `;

      try {
        const response =
          await answerStrategyAgent(
            sessionId,
            value
          );

        if (response.ready_to_build) {
          showBuildButton(
            response.message
          );
          return;
        }

        renderQuestion(
          response.question
        );

      } catch (error) {
        addBubble(
          "agent",
          "I could not process that answer: "
          + error.message
        );

        renderQuestion(question);
      }
    };

    if (question.type === "choice") {
      const grid =
        document.createElement("div");

      grid.className =
        "strategy-agent-options";

      (question.options || [])
        .forEach(option => {
          const button =
            document.createElement("button");

          button.type = "button";
          button.className =
            "strategy-secondary";
          button.textContent =
            option.label;

          button.onclick =
            () => submitValue(
              option.value
            );

          grid.appendChild(button);
        });

      composer.appendChild(grid);
      return;
    }

    if (question.type === "boolean") {
      const grid =
        document.createElement("div");

      grid.className =
        "strategy-agent-options";

      [["Yes", true], ["No", false]]
        .forEach(([label, value]) => {
          const button =
            document.createElement("button");

          button.type = "button";
          button.className =
            "strategy-secondary";
          button.textContent = label;

          button.onclick =
            () => submitValue(value);

          grid.appendChild(button);
        });

      composer.appendChild(grid);
      return;
    }

    const input =
      document.createElement(
        question.type === "number"
          ? "input"
          : "textarea"
      );

    if (question.type === "number") {
      input.type = "number";
      input.step = "0.01";
      input.min = "0";
    }

    input.placeholder =
      question.placeholder || "";

    const savedDraft =
      localStorage.getItem(DRAFT_KEY);

    if (savedDraft) {
      input.value = savedDraft;
    }

    input.addEventListener(
      "input",
      () => {
        localStorage.setItem(
          DRAFT_KEY,
          input.value
        );
      }
    );

    const button =
      document.createElement("button");

    button.type = "button";
    button.className =
      "primary-action";

    button.textContent =
      question.optional
        ? "Continue"
        : "Send";

    button.onclick =
      () => submitValue(
        input.value.trim()
      );

    composer.appendChild(input);
    composer.appendChild(button);

    if (question.optional) {
      const skip =
        document.createElement("button");

      skip.type = "button";
      skip.className =
        "strategy-secondary";
      skip.textContent = "Skip";

      skip.onclick =
        () => submitValue("");

      composer.appendChild(skip);
    }

    input.focus();
  };

  const resumeSavedSession = async () => {
    const savedSession =
      localStorage.getItem(SESSION_KEY);

    if (!savedSession) {
      return false;
    }

    sessionId = savedSession;
    restoreChat();

    startButton.disabled = true;
    startButton.textContent =
      "Restoring session...";

    try {
      const response =
        await resumeStrategyAgent(
          sessionId
        );

      startButton.style.display =
        "none";
      if (reviewButton) reviewButton.hidden = false;

      if (
        response.status === "Complete"
        && response.strategy_id
        && response.strategy
      ) {
        clearSavedAgent();

        const pageContent =
          document.querySelector(
            "#pageContent"
          );

        pageContent.innerHTML =
          strategyResultView({
            strategy_id:
              response.strategy_id,
            strategy:
              response.strategy,
            status:
              "Generated"
          });

        saveAppHistory("strategy-result", { id: response.strategy_id });

        attachNavigation();
        attachStrategyLaunchers();
        attachStrategyLast();

        if (
          typeof attachStrategyHistory
          === "function"
        ) {
          attachStrategyHistory();
        }

        attachStrategyResultActions();
        return true;
      }

      if (response.ready_to_build) {
        showBuildButton(
          response.message
        );
        return true;
      }

      renderQuestion(
        response.question
      );

      return true;

    } catch (error) {
      startButton.disabled = false;
      startButton.style.display = "";
      if (error.status === 404) {
        clearSavedAgent();
        startButton.textContent = "Start Strategy Agent";
        addBubble("agent", "The saved session is no longer available. Start a new one.");
      } else {
        // A temporary outage must not discard the saved session or typed draft.
        startButton.textContent = "Retry restoring session";
        startButton.onclick = () => resumeSavedSession();
        addBubble("agent", "Your session is saved. I could not restore it right now; retry when the connection is available.");
      }

      return false;
    }
  };

  startButton.onclick = async () => {
    clearSavedAgent();

    startButton.disabled = true;
    startButton.textContent =
      "Starting...";

    try {
      const response =
        await startStrategyAgent();

      sessionId =
        response.session_id;
      if (reviewButton) reviewButton.hidden = false;

      localStorage.setItem(
        SESSION_KEY,
        String(sessionId)
      );

      startButton.style.display =
        "none";

      if (response.message) {
        addBubble(
          "agent",
          response.message
        );
      }

      renderQuestion(
        response.question
      );

    } catch (error) {
      startButton.disabled = false;
      startButton.textContent =
        "Start Strategy Agent";

      alert(error.message);
    }
  };

  resumeSavedSession();
}

function attachCampaignForm() {
  const form =
    document.querySelector(
      "#campaignForm"
    );

  if (!form) return;

  form.addEventListener(
    "submit",
    async event => {

      event.preventDefault();

      const campaignId =
        form.dataset.campaignId;

      const submitButton =
        form.querySelector(
          'button[type="submit"]'
        );

      submitButton.disabled = true;

      submitButton.textContent =
        campaignId
          ? "Saving changes..."
          : "Saving campaign...";

      const formData =
        new FormData(form);

      const payload = {
        name:
          formData.get("name"),
        product:
          formData.get("product"),
        audience:
          formData.get("audience"),
        country:
          formData.get("country"),
        platform:
          formData.get("platform"),
        budget:
          formData.get("budget"),
        goal:
          formData.get("goal")
      };

      try {
        await previewCampaign(
          payload
        );

        let response;

        if (campaignId) {
          response =
            await updateCampaign(
              campaignId,
              payload
            );
        } else {
          response =
            await createCampaign(
              payload
            );
        }

        await showCampaignReview(
          response.campaign.id
        );

      } catch (error) {

        alert(
          "Campaign could not be saved.\n\n"
          + error.message
        );

        submitButton.disabled = false;

        submitButton.textContent =
          campaignId
            ? "Save Changes"
            : "Save Campaign";
      }
    }
  );
}


function attachCampaignFilters() {
  const form =
    document.querySelector(
      "#campaignSearchForm"
    );

  if (form) {
    form.onsubmit = event => {
      event.preventDefault();

      campaignFilters.q =
        document
          .querySelector(
            "#campaignSearch"
          )
          .value
          .trim();

      showPage("campaigns");
    };
  }

  const clearButton =
    document.querySelector(
      "[data-clear-campaign-search]"
    );

  if (clearButton) {
    clearButton.onclick = () => {
      campaignFilters.q = "";

      showPage("campaigns");
    };
  }

  document
    .querySelectorAll(
      "[data-campaign-filter]"
    )
    .forEach(button => {

      button.onclick = () => {
        campaignFilters.status =
          button.dataset.campaignFilter;

        showPage("campaigns");
      };

    });
}


function attachCampaignActions() {

  document
    .querySelectorAll(
      "[data-edit-campaign]"
    )
    .forEach(button => {

      button.onclick = () => {
        showCampaignEdit(
          button.dataset.editCampaign
        );
      };

    });


  document
    .querySelectorAll(
      "[data-duplicate-campaign]"
    )
    .forEach(button => {

      button.onclick = async () => {

        const oldText =
          button.textContent;

        button.disabled = true;
        button.textContent =
          "Duplicating...";

        try {
          await duplicateCampaign(
            button.dataset
              .duplicateCampaign
          );

          await showPage(
            "campaigns"
          );

        } catch (error) {
          button.disabled = false;
          button.textContent =
            oldText;

          alert(error.message);
        }
      };

    });


  document
    .querySelectorAll(
      "[data-campaign-status]"
    )
    .forEach(button => {

      button.onclick = async () => {

        try {
          await updateCampaignStatus(
            button.dataset
              .campaignStatus,
            button.dataset.status
          );

          await showPage(
            "campaigns"
          );

        } catch (error) {
          alert(error.message);
        }
      };

    });
}


async function showCampaignEdit(
  id,
  pushHistory = true
) {
  const pageContent =
    document.querySelector(
      "#pageContent"
    );

  try {
    const response =
      await getCampaign(id);

    pageContent.innerHTML =
      campaignFormView(
        response.campaign
      );

    if (pushHistory) {
      saveAppHistory(
        "campaign-edit",
        { id }
      );
    }

    setActiveNavigation(
      "campaign-edit"
    );

    attachNavigation();
    attachCampaignForm();

    window.scrollTo(
      0,
      0
    );

  } catch (error) {
    alert(error.message);
  }
}


function attachCampaignDelete() {
  document
    .querySelectorAll(
      "[data-delete-campaign]"
    )
    .forEach(button => {

      button.onclick = async () => {
        try {
          await deleteCampaign(
            button.dataset.deleteCampaign
          );

          await showPage("campaigns");

        } catch (error) {
          alert(error.message);
        }
      };

    });
}

function attachCampaignReview() {
  document
    .querySelectorAll(
      "[data-review-campaign]"
    )
    .forEach(button => {

      button.onclick = () => {
        showCampaignReview(
          button.dataset.reviewCampaign
        );
      };

    });
}

async function showCampaignReview(
  id,
  pushHistory = true
) {
  const pageContent =
    document.querySelector("#pageContent");

  try {
    const response =
      await getCampaign(id);

    pageContent.innerHTML =
      campaignReviewView(
        response.campaign
      );

    if (pushHistory) {
      saveAppHistory(
        "campaign-review",
        { id }
      );
    }

    setActiveNavigation("campaigns");

    attachNavigation();

    window.scrollTo(0, 0);

  } catch (error) {
    alert(error.message);
  }
}

async function refreshNotificationBadge() {
  const badge =
    document.querySelector(
      "#notificationBadge"
    );

  if (!badge) return;

  try {
    const response =
      await getNotifications(1);

    const count =
      response.unread_count || 0;

    badge.textContent =
      count > 99
        ? "99+"
        : String(count);

    badge.hidden =
      count === 0;

  } catch {
    badge.hidden = true;
  }
}


function attachNotifications() {

  const markAllButton =
    document.querySelector(
      "#markAllNotifications"
    );

  if (markAllButton) {
    markAllButton.onclick =
      async () => {

        try {
          await markAllNotificationsRead();

          await showPage(
            "notifications"
          );

        } catch (error) {
          alert(error.message);
        }
      };
  }


  document
    .querySelectorAll(
      "[data-notification-id]"
    )
    .forEach(button => {

      button.onclick =
        async () => {

          try {
            await markNotificationRead(
              button.dataset
                .notificationId
            );

            await refreshNotificationBadge();

            const campaignId =
              button.dataset
                .campaignId;

            if (campaignId) {
              await showCampaignReview(
                campaignId
              );
            } else {
              await showPage(
                "notifications"
              );
            }

          } catch (error) {
            alert(error.message);
          }
        };

    });
}


function attachAccountSettings() {

  const profileForm =
    document.querySelector(
      "#profileSettingsForm"
    );

  if (profileForm) {

    profileForm.onsubmit =
      async event => {

        event.preventDefault();

        const button =
          profileForm.querySelector(
            'button[type="submit"]'
          );

        const message =
          document.querySelector(
            "#profileSettingsMessage"
          );

        const data =
          new FormData(profileForm);

        button.disabled = true;
        button.textContent =
          "Saving...";

        message.textContent = "";

        try {
          const response =
            await updateProfile({
              name:
                data.get("name"),
              email:
                data.get("email"),
              current_password:
                data.get(
                  "current_password"
                )
            });

          currentUser =
            response.user;

          const headerEmail =
            document.querySelector(
              ".topbar small"
            );

          if (headerEmail) {
            headerEmail.textContent =
              currentUser.email;
          }

          message.textContent =
            "Profile updated successfully.";

          profileForm
            .querySelector(
              '[name="current_password"]'
            )
            .value = "";

        } catch (error) {
          message.textContent =
            error.message;
        }

        button.disabled = false;
        button.textContent =
          "Save Profile";
      };
  }


  const passwordForm =
    document.querySelector(
      "#passwordSettingsForm"
    );

  if (passwordForm) {

    passwordForm.onsubmit =
      async event => {

        event.preventDefault();

        const button =
          passwordForm.querySelector(
            'button[type="submit"]'
          );

        const message =
          document.querySelector(
            "#passwordSettingsMessage"
          );

        const data =
          new FormData(passwordForm);

        const newPassword =
          data.get("new_password");

        const confirmPassword =
          data.get(
            "confirm_password"
          );

        message.textContent = "";

        if (
          newPassword !==
          confirmPassword
        ) {
          message.textContent =
            "New passwords do not match.";

          return;
        }

        button.disabled = true;
        button.textContent =
          "Changing password...";

        try {
          await changePassword({
            current_password:
              data.get(
                "current_password"
              ),
            new_password:
              newPassword
          });

          passwordForm.reset();

          message.textContent =
            "Password changed successfully.";

        } catch (error) {
          message.textContent =
            error.message;
        }

        button.disabled = false;
        button.textContent =
          "Change Password";
      };
  }
}


function setActiveNavigation(page) {
  const activePage =
    (
      page === "campaign-create" ||
      page === "campaign-edit"
    )
      ? "campaigns"
      : page;

  document
    .querySelectorAll(".nav-btn")
    .forEach(button => {

      button.classList.toggle(
        "active",
        button.dataset.page === activePage
      );

    });
}
