import {
  getCurrentUser,
  logoutUser,
  getDashboardOverview,
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

const app = document.querySelector("#app");

let currentUser = null;

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
      pageContent.innerHTML =
        notificationsView();
    }

    if (page === "settings") {
      pageContent.innerHTML =
        settingsView(
          currentUser?.email || ""
        );
    }

    setActiveNavigation(page);

    attachNavigation();
    attachCampaignForm();
    attachCampaignDelete();
    attachCampaignReview();
    attachCampaignFilters();
    attachCampaignActions();

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
