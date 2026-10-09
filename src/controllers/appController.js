import {
  getCurrentUser,
  logoutUser,
  updateProfile,
  changePassword,
  generateStrategy,
  acceptStrategy,
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
  strategyResultView
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

    showApp(currentUser);
  } catch {
    window.history.pushState({}, "", "/login");
    window.dispatchEvent(new PopStateEvent("popstate"));
  }
}

function showApp(user) {
  app.innerHTML = appView(user.email);

  const logoutButton =
    document.querySelector("#logoutBtn");

  logoutButton.addEventListener("click", async () => {
    try {
      await logoutUser();
    } catch {}

    currentUser = null;

    window.history.pushState({}, "", "/");

    window.dispatchEvent(
      new PopStateEvent("popstate")
    );
  });

  showPage("dashboard");
}

async function showPage(page) {
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

    setActiveNavigation(page);

    attachNavigation();
    attachStrategyLaunchers();
    attachStrategyWizard();
    attachStrategyResultActions();
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
  document
    .querySelectorAll("[data-strategy-start]")
    .forEach(button => {
      button.onclick = () => {
        strategyMode = button.dataset.strategyStart || "guided";
        showPage("strategy");
      };
    });
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
      const response = await generateStrategy(payload);
      const pageContent = document.querySelector("#pageContent");
      pageContent.innerHTML = strategyResultView(response);

      setActiveNavigation("strategy");
      attachNavigation();
      attachStrategyLaunchers();
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


async function showCampaignEdit(id) {
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

async function showCampaignReview(id) {
  const pageContent =
    document.querySelector("#pageContent");

  try {
    const response =
      await getCampaign(id);

    pageContent.innerHTML =
      campaignReviewView(
        response.campaign
      );

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
