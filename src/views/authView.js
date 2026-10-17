import { brandLogo } from './ui.js';

const arrow = '<svg viewBox="0 0 24 24" fill="none" aria-hidden="true"><path d="M5 12h14m-5-5 5 5-5 5" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round"/></svg>';
const lock = '<svg viewBox="0 0 24 24" fill="none" aria-hidden="true"><rect x="5" y="10" width="14" height="11" rx="3" stroke="currentColor" stroke-width="1.5"/><path d="M8 10V7a4 4 0 0 1 8 0v3m-4 5v2" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/></svg>';
const google = '<svg viewBox="0 0 24 24" aria-hidden="true"><path fill="#4285f4" d="M21.6 12.23c0-.71-.06-1.39-.18-2.05H12v3.88h5.38a4.6 4.6 0 0 1-2 3.02v2.51h3.24c1.89-1.74 2.98-4.3 2.98-7.36Z"/><path fill="#34a853" d="M12 22c2.7 0 4.96-.9 6.62-2.41l-3.24-2.51c-.9.6-2.04.97-3.38.97-2.6 0-4.8-1.76-5.59-4.12H3.07v2.59A10 10 0 0 0 12 22Z"/><path fill="#fbbc05" d="M6.41 13.93a6 6 0 0 1 0-3.86V7.48H3.07a10 10 0 0 0 0 9.04l3.34-2.59Z"/><path fill="#ea4335" d="M12 5.95c1.47 0 2.79.51 3.83 1.52L18.7 4.6A9.6 9.6 0 0 0 12 2a10 10 0 0 0-8.93 5.48l3.34 2.59C7.2 7.71 9.4 5.95 12 5.95Z"/></svg>';
const facebook = '<svg viewBox="0 0 24 24" aria-hidden="true"><path fill="#4599ff" d="M24 12a12 12 0 1 0-13.88 11.85v-8.38H7.08V12h3.04V9.36c0-3 1.79-4.66 4.53-4.66 1.31 0 2.68.24 2.68.24v2.95h-1.51c-1.49 0-1.95.92-1.95 1.87V12h3.32l-.53 3.47h-2.79v8.38A12 12 0 0 0 24 12Z"/></svg>';

function shell(content, mode = 'login') {
  const signup = mode === 'signup';
  return `<main class="mf-auth">
    <header class="mf-auth-nav"><button class="mf-auth-brand" data-route="/" aria-label="MarketFlow home">${brandLogo()}</button><a href="/" data-route="/" class="mf-auth-home">Back to website <span>${arrow}</span></a></header>
    <div class="mf-auth-grid">
      <aside class="mf-auth-story" aria-label="Your MarketFlow workspace">
        <span class="mf-auth-eyebrow"><i></i> YOUR NEXT CHAPTER STARTS HERE</span>
        <h1>A little clarity.<br>A lot more<br><span>momentum.</span></h1>
        <p>Bring your business idea.<br>Leave with a marketing plan you can act on.</p>
        <div class="mf-auth-preview" aria-hidden="true"><div class="mf-auth-preview-top"><span><i></i> Your workspace</span><span>MARKETFLOW</span></div><div class="mf-auth-preview-line"><b>01</b><span><strong>A brief that gets you</strong><small>Your business, audience, and ambition.</small></span><em>✓</em></div><div class="mf-auth-preview-line"><b>02</b><span><strong>A strategy with a reason</strong><small>Channels, budget, and evidence.</small></span><em>✓</em></div><div class="mf-auth-preview-line"><b>03</b><span><strong>A campaign ready to shape</strong><small>Creative drafts. Clear next steps.</small></span><em>${arrow}</em></div><div class="mf-auth-preview-bottom"><span class="mf-auth-avatar">Y</span>Built around your business.</div></div>
        <div class="mf-auth-story-note">${lock}<span>Your workspace stays private.<br>You decide when a campaign goes live.</span></div>
      </aside>
      <section class="mf-auth-panel" aria-label="${signup ? 'Create account' : 'Account access'}">${content}</section>
    </div>
    <footer class="mf-auth-footer"><span>© ${new Date().getFullYear()} MarketFlow</span><span>Thoughtful planning. Confident next steps.</span></footer>
  </main>`;
}

function socials() {
  return `<div class="mf-auth-socials"><button type="button" data-provider="google" disabled>${google}<span>Continue with Google</span></button><button type="button" data-provider="facebook" disabled>${facebook}<span>Continue with Facebook</span></button></div><p id="socialAvailability" class="mf-auth-small" aria-live="polite">Checking sign-in options…</p><div class="mf-auth-divider"><span>or continue with email</span></div>`;
}
function errorBlock() {
  return '<p id="authError" class="mf-auth-error" role="alert" tabindex="-1" hidden></p><p id="authNotice" class="mf-auth-notice" role="status" hidden></p>';
}
export function passwordField(name = 'password', label = 'Password', autocomplete = 'current-password') {
  return `<label class="mf-auth-label" for="auth-${name}">${label}</label><div class="mf-auth-password"><input id="auth-${name}" name="${name}" type="password" autocomplete="${autocomplete}" maxlength="128" ${autocomplete === 'new-password' ? 'minlength="15"' : ''} required placeholder="${autocomplete === 'new-password' ? 'Create a long, memorable passphrase' : 'Enter your password'}"><button type="button" data-toggle-password="auth-${name}" aria-label="Show ${label.toLowerCase()}" aria-pressed="false">Show</button></div>`;
}
function emailField(autocomplete = 'email') {
  return `<label class="mf-auth-label" for="auth-email">Email address</label><input id="auth-email" name="email" type="email" autocomplete="${autocomplete}" inputmode="email" maxlength="254" required placeholder="you@company.com" autocapitalize="none" spellcheck="false">`;
}
const submit = (label) => `<button type="submit" class="mf-auth-submit"><span>${label}</span>${arrow}</button>`;
const security = `<div class="mf-auth-security">${lock}<span>Protected sessions. Your password stays private.</span></div>`;

export function loginPageView() {
  return shell(`<span class="mf-auth-kicker">GOOD TO SEE YOU AGAIN</span><h2>Welcome back.</h2><p class="mf-auth-lede">Sign in to pick up where you left off.</p>${socials()}<form id="realLoginForm">${emailField('username')}<div class="mf-auth-label-row"><span></span><button type="button" data-route="/forgot-password">Forgot password?</button></div>${passwordField()}${errorBlock()}${submit('Sign in to MarketFlow')}</form><p class="mf-auth-switch">New here? <button data-route="/signup">Create an account ${arrow}</button></p>${security}`);
}

export function signupPageView() {
  return shell(`<span class="mf-auth-kicker">MAKE ROOM FOR YOUR NEXT BIG IDEA</span><h2>Start your next move.</h2><p class="mf-auth-lede">One account. A clearer path from idea to campaign.</p><ol class="mf-auth-steps" aria-label="Account creation progress"><li aria-current="step"><b>1</b>Details</li><li><b>2</b>Password</li><li><b>3</b>Verify</li></ol><div id="signupSocials">${socials()}</div><form id="signupForm"><fieldset id="signupDetails"><legend class="mf-auth-sr">Your details</legend><label class="mf-auth-label" for="auth-name">Your name</label><input id="auth-name" name="name" autocomplete="name" minlength="2" maxlength="80" required placeholder="What should we call you?">${emailField()}</fieldset><fieldset id="signupPassword" hidden disabled><legend class="mf-auth-sr">Secure your account</legend><p class="mf-auth-summary"><span id="signupEmailSummary"></span><button type="button" id="editSignupDetails">Edit</button></p>${passwordField('password', 'Create a password', 'new-password')}<p class="mf-auth-password-hint" id="passwordHint">Use 15 or more characters. A few unrelated words work well.</p>${passwordField('confirm_password', 'Confirm password', 'new-password')}</fieldset>${errorBlock()}${submit('Continue with email')}</form><p class="mf-auth-switch">Already have an account? <button data-route="/login">Sign in ${arrow}</button></p>${security}`, 'signup');
}

export function verifyEmailView() {
  return shell(`<div class="mf-auth-state-icon"><svg viewBox="0 0 24 24" fill="none" aria-hidden="true"><rect x="3" y="5" width="18" height="14" rx="3" stroke="currentColor" stroke-width="1.5"/><path d="m4 7 8 6 8-6" stroke="currentColor" stroke-width="1.5" stroke-linejoin="round"/></svg></div><span class="mf-auth-kicker">ONE LAST STEP</span><h2 id="verificationHeading">Confirm your email.</h2><p id="verificationDescription" class="mf-auth-lede">Confirm your email to open your workspace. Use the link in the same browser where you requested it.</p><ol class="mf-auth-steps"><li class="is-done"><b>✓</b>Details</li><li class="is-done"><b>✓</b>Password</li><li aria-current="step"><b>3</b>Verify</li></ol><div id="localEmailNote" class="mf-auth-local" hidden>Local preview: the email is saved in the private <code>.marketflow-mail</code> folder on your device. No message was sent to Gmail. In Termux, run <code>python tools/open_auth_email.py --open</code> from your project, or configure SMTP to receive real email.</div><form id="verifyEmailForm" hidden>${errorBlock()}${submit('Confirm email & continue')}</form><form id="resendVerificationForm">${emailField()}<p id="verificationHelp" class="mf-auth-small">Check spam too. Need a new link? Enter your email below; you must have started sign-up or signed in in this browser.</p><p id="resendMessage" class="mf-auth-notice" role="status" hidden></p><button class="mf-auth-secondary" type="submit">Resend verification email</button></form><p class="mf-auth-switch"><button data-route="/login">← Back to sign in</button></p>${security}`);
}

export function forgotPasswordView() {
  return shell(`<div class="mf-auth-state-icon">${lock}</div><span class="mf-auth-kicker">LET’S GET YOU BACK IN</span><h2>Forgot your password?</h2><p class="mf-auth-lede">Enter your email. We’ll send a single-use link to choose a new password.</p><form id="forgotPasswordForm">${emailField()}${errorBlock()}${submit('Send reset link')}</form><div id="localEmailNote" class="mf-auth-local" hidden>Local preview: emails are saved in the private <code>.marketflow-mail</code> folder on your device.</div><p class="mf-auth-switch"><button data-route="/login">← Back to sign in</button></p>${security}`);
}

export function resetPasswordView() {
  return shell(`<div class="mf-auth-state-icon">${lock}</div><span class="mf-auth-kicker">A FRESH START</span><h2>Choose a new password.</h2><p class="mf-auth-lede">Use a unique passphrase. Updating it signs out every existing session.</p><form id="resetPasswordForm">${passwordField('password', 'New password', 'new-password')}<p class="mf-auth-password-hint">Use 15–128 characters. Spaces and password managers are welcome.</p>${passwordField('confirm_password', 'Confirm password', 'new-password')}${errorBlock()}${submit('Update password')}</form><p class="mf-auth-switch"><button data-route="/forgot-password">Request a new reset link ${arrow}</button></p>${security}`);
}
