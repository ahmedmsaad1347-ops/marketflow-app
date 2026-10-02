export function loginPageView() {
  return `
    <main class="auth-page">
      <section class="auth-card">

        <button data-route="/" class="auth-back">
          ← MarketFlow
        </button>

        <div class="logo">M</div>

        <h1>Welcome back</h1>

        <p>
          Sign in to your MarketFlow workspace.
        </p>

        <form id="realLoginForm">

          <label>
            Email
            <input
              name="email"
              type="email"
              placeholder="you@company.com"
              required
            >
          </label>

          <label>
            Password
            <input
              name="password"
              type="password"
              placeholder="Your password"
              required
            >
          </label>

          <p id="authError" class="auth-error"></p>

          <button type="submit" class="primary-action">
            Sign in
          </button>

        </form>

        <p class="auth-switch">
          New to MarketFlow?
          <button data-route="/signup">
            Create account
          </button>
        </p>

      </section>
    </main>
  `;
}


export function signupPageView() {
  return `
    <main class="auth-page">
      <section class="auth-card">

        <button data-route="/" class="auth-back">
          ← MarketFlow
        </button>

        <div class="logo">M</div>

        <h1>Create your account</h1>

        <p>
          Start building your MarketFlow workspace.
        </p>

        <form id="signupForm">

          <label>
            Name
            <input
              name="name"
              placeholder="Your name"
              minlength="2"
              required
            >
          </label>

          <label>
            Email
            <input
              name="email"
              type="email"
              placeholder="you@company.com"
              required
            >
          </label>

          <label>
            Password
            <input
              name="password"
              type="password"
              placeholder="At least 8 characters"
              minlength="8"
              required
            >
          </label>

          <p id="authError" class="auth-error"></p>

          <button type="submit" class="primary-action">
            Create account
          </button>

        </form>

        <p class="auth-switch">
          Already have an account?
          <button data-route="/login">
            Sign in
          </button>
        </p>

      </section>
    </main>
  `;
}
