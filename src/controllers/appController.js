import { AuthModel } from "../models/authModel.js";
import { loginView, dashboardView } from "../views/appView.js";

const app = document.querySelector("#app");

export function startApp() {
  const user = AuthModel.getUser();

  if (user) {
    showDashboard(user);
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
      showDashboard(result.user);
    } else {
      document.querySelector("#message").textContent = result.message;
    }
  });
}

function showDashboard(user) {
  app.innerHTML = dashboardView(user);

  document.querySelector("#logoutBtn").addEventListener("click", () => {
    AuthModel.logout();
    showLogin();
  });
}
