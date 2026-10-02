import "./styles/main.css";
import "./styles/landing.css";

import { startApp } from "./controllers/appController.js";
import { landingView } from "./views/landingView.js";
import {
  loginPageView,
  signupPageView
} from "./views/authView.js";

import {
  loginUser,
  signupUser,
  getCurrentUser
} from "./services/api.js";

const app = document.querySelector("#app");

export async function renderRoute() {
  const path = window.location.pathname;

  if (path === "/") {
    app.innerHTML = landingView();
    attachRouteButtons();
    window.scrollTo(0, 0);
    return;
  }

  if (path === "/login") {
    app.innerHTML = loginPageView();
    attachRouteButtons();
    attachLogin();
    return;
  }

  if (path === "/signup") {
    app.innerHTML = signupPageView();
    attachRouteButtons();
    attachSignup();
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


function navigate(path) {
  window.history.pushState({}, "", path);
  renderRoute();
}


function attachRouteButtons() {
  document
    .querySelectorAll("[data-route]")
    .forEach(button => {

      button.onclick = () => {
        navigate(button.dataset.route);
      };

    });
}


function attachLogin() {
  const form =
    document.querySelector("#realLoginForm");

  if (!form) return;

  form.addEventListener("submit", async event => {
    event.preventDefault();

    const data = new FormData(form);
    const error = document.querySelector("#authError");
    const button = form.querySelector('button[type="submit"]');

    error.textContent = "";
    button.disabled = true;
    button.textContent = "Signing in...";

    try {
      await loginUser({
        email: data.get("email"),
        password: data.get("password")
      });

      navigate("/app");

    } catch (err) {
      error.textContent = err.message;
      button.disabled = false;
      button.textContent = "Sign in";
    }
  });
}


function attachSignup() {
  const form =
    document.querySelector("#signupForm");

  if (!form) return;

  form.addEventListener("submit", async event => {
    event.preventDefault();

    const data = new FormData(form);
    const error = document.querySelector("#authError");
    const button = form.querySelector('button[type="submit"]');

    error.textContent = "";
    button.disabled = true;
    button.textContent = "Creating account...";

    try {
      await signupUser({
        name: data.get("name"),
        email: data.get("email"),
        password: data.get("password")
      });

      navigate("/app");

    } catch (err) {
      error.textContent = err.message;
      button.disabled = false;
      button.textContent = "Create account";
    }
  });
}


window.addEventListener(
  "popstate",
  renderRoute
);

renderRoute();
