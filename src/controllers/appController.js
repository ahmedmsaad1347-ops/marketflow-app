import { AuthModel } from "../models/authModel.js";

import {
  previewCampaign,
  createCampaign,
  getCampaigns,
  getCampaign,
  deleteCampaign
} from "../services/api.js";

import {
  loginView,
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

const app = document.querySelector("#app");

export function startApp() {
  const user = AuthModel.getUser();

  if (user) {
    showApp(user);
  } else {
    showLogin();
  }
}

function showLogin() {
  app.innerHTML = loginView();

  document
    .querySelector("#loginForm")
    .addEventListener("submit", event => {
      event.preventDefault();

      const email =
        document.querySelector("#email").value;

      const password =
        document.querySelector("#password").value;

      const result =
        AuthModel.login(email, password);

      if (result.success) {
        showApp(result.user);
      }
    });
}

function showApp(user) {
  app.innerHTML = appView(user);

  document
    .querySelector("#logoutBtn")
    .addEventListener("click", () => {
      AuthModel.logout();
      showLogin();
    });

  showPage("dashboard");
}

async function showPage(page) {
  const pageContent =
    document.querySelector("#pageContent");

  try {
    if (page === "dashboard") {
      const response = await getCampaigns();

      pageContent.innerHTML =
        dashboardView(response.campaigns);
    }

    if (page === "campaigns") {
      const response = await getCampaigns();

      pageContent.innerHTML =
        campaignsView(response.campaigns);
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
      pageContent.innerHTML =
        reportsView();
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
        settingsView(AuthModel.getUser());
    }

    setActiveNavigation(page);

    attachNavigation();
    attachCampaignForm();
    attachCampaignDelete();
    attachCampaignReview();

    window.scrollTo(0, 0);

  } catch (error) {
    pageContent.innerHTML = `
      <section class="page">
        <div class="empty-card">
          <h2>Connection error</h2>
          <p>${error.message}</p>
          <p>Make sure the Python backend is running.</p>
        </div>
      </section>
    `;
  }
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
    document.querySelector("#campaignForm");

  if (!form) return;

  form.addEventListener("submit", async event => {
    event.preventDefault();

    const submitButton =
      form.querySelector('button[type="submit"]');

    submitButton.disabled = true;
    submitButton.textContent = "Saving campaign...";

    const formData = new FormData(form);

    const payload = {
      name: formData.get("name"),
      product: formData.get("product"),
      audience: formData.get("audience"),
      country: formData.get("country"),
      platform: formData.get("platform"),
      budget: formData.get("budget"),
      goal: formData.get("goal")
    };

    try {
      await previewCampaign(payload);

      const response =
        await createCampaign(payload);

      await showCampaignReview(
        response.campaign.id
      );

    } catch (error) {
      alert(
        "Campaign could not be saved.\n\n" +
        error.message
      );

      submitButton.disabled = false;
      submitButton.textContent = "Save Campaign";
    }
  });
}

function attachCampaignDelete() {
  document
    .querySelectorAll("[data-delete-campaign]")
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
    .querySelectorAll("[data-review-campaign]")
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
      campaignReviewView(response.campaign);

    setActiveNavigation("campaigns");
    attachNavigation();

    window.scrollTo(0, 0);

  } catch (error) {
    alert(error.message);
  }
}

function setActiveNavigation(page) {
  const activePage =
    page === "campaign-create"
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
