import { AuthModel } from "../models/authModel.js";
import { CampaignModel } from "../models/campaignModel.js";

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
  settingsView
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

function showPage(page) {
  const pageContent =
    document.querySelector("#pageContent");

  const campaigns =
    CampaignModel.getAll();

  if (page === "dashboard") {
    pageContent.innerHTML =
      dashboardView(campaigns);
  }

  if (page === "campaigns") {
    pageContent.innerHTML =
      campaignsView(campaigns);
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
    pageContent.innerHTML = reportsView();
  }

  if (page === "connections") {
    pageContent.innerHTML = connectionsView();
  }

  if (page === "notifications") {
    pageContent.innerHTML = notificationsView();
  }

  if (page === "settings") {
    pageContent.innerHTML = settingsView(AuthModel.getUser());
  }

  setActiveNavigation(page);

  attachNavigation();
  attachCampaignForm();
  attachCampaignDelete();

  window.scrollTo(0, 0);
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

  form.addEventListener("submit", event => {

    event.preventDefault();

    const formData =
      new FormData(form);

    CampaignModel.create({
      name: formData.get("name"),
      product: formData.get("product"),
      audience: formData.get("audience"),
      country: formData.get("country"),
      platform: formData.get("platform"),
      budget: formData.get("budget"),
      goal: formData.get("goal")
    });

    showPage("campaigns");
  });
}

function attachCampaignDelete() {
  document
    .querySelectorAll("[data-delete-campaign]")
    .forEach(button => {

      button.onclick = () => {

        const id =
          button.dataset.deleteCampaign;

        CampaignModel.remove(id);

        showPage("campaigns");
      };

    });
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
