import "./styles/main.css";
import "./styles/landing.css";
import "./styles/strategy.css";
import "./styles/auth.css";

import { startApp } from "./controllers/appController.js";
import { landingView } from "./views/landingView.js";
import { attachLandingInteractions } from './controllers/landingController.js';
import { loginPageView, signupPageView, verifyEmailView, forgotPasswordView, resetPasswordView } from "./views/authView.js";
import { attachAuthInteractions } from "./controllers/authController.js";
import { getCurrentUser } from "./services/api.js";

const app = document.querySelector("#app");

export async function renderRoute() {
  const path = window.location.pathname;

  if (path === "/") {
    app.innerHTML = landingView();
    attachRouteButtons();
    attachLandingInteractions();
    window.scrollTo(0, 0);
    return;
  }

  const authViews = { '/login': loginPageView, '/signup': signupPageView,
    '/verify-email': verifyEmailView, '/forgot-password': forgotPasswordView, '/reset-password': resetPasswordView };
  if (authViews[path]) {
    app.innerHTML = authViews[path]();
    document.title = `${path === '/signup' ? 'Create your account' : path === '/login' ? 'Sign in' : 'Secure your account'} · MarketFlow`;
    attachRouteButtons();
    attachAuthInteractions(navigate);
    window.scrollTo(0, 0);
    return;
  }

  if (path === "/app") {
    try {
      await getCurrentUser();
      startApp();
    } catch {
      navigate("/login");
    }

    return;
  }

  navigate("/");
}


function navigate(
  path,
  options = {}
) {
  const method =
    options.replace
      ? "replaceState"
      : "pushState";

  window.history[method](
    {},
    "",
    path
  );

  renderRoute();
}


function attachRouteButtons() {
  document
    .querySelectorAll("[data-route]")
    .forEach(button => {

      button.onclick = event => {
        event.preventDefault();
        navigate(button.dataset.route);
      };

    });
}


window.addEventListener(
  "popstate",
  renderRoute
);

renderRoute();
