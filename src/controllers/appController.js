import { AuthModel } from "../models/authModel.js";
import { loginView, appView, pageView } from "../views/appView.js";

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

  document.querySelector("#loginForm").addEventListener("submit", (e) => {
    e.preventDefault();

    const email = document.querySelector("#email").value;
    const password = document.querySelector("#password").value;

    const result = AuthModel.login(email, password);

    if (result.success) {
      showApp(result.user);
    }
  });
}

function showApp(user) {
  app.innerHTML = appView(user);

  document.querySelector("#logoutBtn").addEventListener("click", () => {
    AuthModel.logout();
    showLogin();
  });

  showPage("dashboard");
}

function showPage(page) {
  document.querySelector("#pageContent").innerHTML = pageView(page);

  document.querySelectorAll(".nav-btn").forEach((btn) => {
    btn.classList.toggle("active", btn.dataset.page === page);
  });

  document.querySelectorAll("[data-page]").forEach((btn) => {
    btn.onclick = () => showPage(btn.dataset.page);
  });

  const createBtn = document.querySelector("#createCampaignBtn");

  if (createBtn) {
    createBtn.onclick = () => {
      alert("Campaign Builder is the next step.");
    };
  }
}
