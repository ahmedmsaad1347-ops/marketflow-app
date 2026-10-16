import { getAuthConfig, loginUser, signupUser, authAction, providerSignInURL } from '../services/api.js';

let pendingEmail = '';
const messages = {
  invalid_state: 'This sign-in request expired or belongs to another browser. Please try again.',
  cancelled: 'Sign-in was cancelled. You can try again or use your email.',
  provider_failed: 'We could not complete social sign-in. Facebook needs to share your email; you can also use email sign-in.',
  existing_account: 'An account already uses this email. Sign in with your existing method, or reset your password. Accounts are never linked automatically.',
  provider_unavailable: 'This sign-in option is not available yet. Please use your email.',
  email_delivery: 'We could not send your confirmation email. Please try signing in again shortly.'
};

export function attachAuthInteractions(navigate) {
  const root = document.querySelector('.mf-auth');
  if (!root) return;
  let signupStep = 1;
  let currentToken = new URLSearchParams(location.hash.slice(1)).get('token') || '';
  const queryError = new URLSearchParams(location.search).get('error');
  // Keep secret links out of browser history, analytics and outgoing referrers.
  if (location.hash || location.search) history.replaceState({}, '', location.pathname);
  const showError = (message) => {
    const target = root.querySelector('#authError');
    if (target) { target.textContent = message; target.hidden = false; target.focus(); }
  };
  const notice = (message, id = 'authNotice') => {
    const target = root.querySelector(`#${id}`);
    if (target) { target.textContent = message; target.hidden = false; }
  };
  if (queryError) showError(messages[queryError] || 'We could not complete sign-in. Please try again.');

  root.querySelectorAll('[data-toggle-password]').forEach(button => {
    button.onclick = () => {
      const input = root.querySelector(`#${button.dataset.togglePassword}`);
      const visible = input.type === 'password';
      input.type = visible ? 'text' : 'password';
      button.textContent = visible ? 'Hide' : 'Show';
      button.setAttribute('aria-pressed', String(visible));
      button.setAttribute('aria-label', `${visible ? 'Hide' : 'Show'} ${input.name === 'confirm_password' ? 'confirm password' : 'password'}`);
    };
  });
  const password = root.querySelector('[name="password"]');
  password?.addEventListener('input', () => {
    const hint = root.querySelector('#passwordHint');
    if (hint) {
      const valid = [...password.value].length >= 15;
      hint.classList.toggle('is-valid', valid);
      hint.textContent = valid ? '✓ Length requirement met. Keep it unique to MarketFlow.' : 'Use 15 or more characters. A few unrelated words work well.';
    }
  });

  getAuthConfig().then(config => {
    if (!root.isConnected) return;
    let enabled = 0;
    root.querySelectorAll('[data-provider]').forEach(button => {
      const active = Boolean(config.providers[button.dataset.provider]);
      button.disabled = !active;
      button.title = active ? `Sign in with ${button.dataset.provider}` : 'This sign-in option is not available yet';
      if (active) enabled++;
      button.onclick = () => { location.assign(providerSignInURL(button.dataset.provider)); };
    });
    const availability = root.querySelector('#socialAvailability');
    if (availability) {
      availability.hidden = enabled === 2;
      availability.textContent = enabled === 0 ? 'Social sign-in is coming soon. You can continue with email.' : 'Additional sign-in options will be available soon.';
    }
    const local = root.querySelector('#localEmailNote');
    if (local) local.hidden = !config.local_email_preview;
  }).catch(() => showError('Cannot reach MarketFlow. Check that the API is running, then try again.'));

  const setStep = step => {
    signupStep = step;
    const details = root.querySelector('#signupDetails');
    const security = root.querySelector('#signupPassword');
    details.hidden = step !== 1; details.disabled = step !== 1;
    security.hidden = step !== 2; security.disabled = step !== 2;
    root.querySelector('#signupSocials').hidden = step !== 1;
    root.querySelectorAll('.mf-auth-steps li').forEach((item, index) => {
      item.removeAttribute('aria-current');
      if (index === step - 1) item.setAttribute('aria-current', 'step');
      item.classList.toggle('is-done', index < step - 1);
    });
    root.querySelector('#signupForm button[type="submit"] span').textContent = step === 1 ? 'Continue with email' : 'Create my account';
    root.querySelector('#signupEmailSummary').textContent = root.querySelector('[name="email"]').value;
    (step === 1 ? details.querySelector('input') : security.querySelector('input')).focus();
    const error = root.querySelector('#authError');
    error.hidden = true;
  };
  root.querySelector('#editSignupDetails')?.addEventListener('click', () => setStep(1));

  async function perform(form, job) {
    const button = form.querySelector('button[type="submit"]');
    const error = root.querySelector('#authError');
    if (error) error.hidden = true;
    const label = button.innerHTML;
    button.disabled = true;
    button.textContent = 'Please wait…';
    form.setAttribute('aria-busy', 'true');
    try { await job(); }
    catch (err) {
      if (form.id === 'resendVerificationForm') notice(err.message, 'resendMessage');
      else showError(err.message);
    } finally {
      if (root.isConnected) { button.disabled = false; button.innerHTML = label; form.removeAttribute('aria-busy'); }
    }
  }
  root.querySelector('#realLoginForm')?.addEventListener('submit', event => {
    event.preventDefault();
    const form = event.currentTarget;
    perform(form, async () => {
      const email = form.elements.email.value.trim();
      const result = await loginUser({ email, password: form.elements.password.value });
      form.elements.password.value = '';
      pendingEmail = email;
      navigate(result.verification_required ? '/verify-email' : '/app', { replace: true });
    });
  });
  root.querySelector('#signupForm')?.addEventListener('submit', event => {
    event.preventDefault();
    const form = event.currentTarget;
    if (signupStep === 1) { setStep(2); return; }
    if (form.elements.password.value !== form.elements.confirm_password.value) { showError('The two passwords do not match.'); return; }
    perform(form, async () => {
      const result = await signupUser({name: form.elements.name.value, email: form.elements.email.value, password: form.elements.password.value});
      pendingEmail = form.elements.email.value.trim();
      form.elements.password.value = ''; form.elements.confirm_password.value = '';
      if (result.verification_required) navigate('/verify-email', { replace: true });
    });
  });
  const verify = root.querySelector('#verifyEmailForm');
  if (verify) {
    verify.hidden = !currentToken;
    const resend = root.querySelector('#resendVerificationForm');
    resend.elements.email.value = pendingEmail;
    verify.addEventListener('submit', event => {
      event.preventDefault();
      perform(verify, async () => {
        await authAction('verify-email', { token: currentToken });
        currentToken = ''; pendingEmail = '';
        navigate('/app', { replace: true });
      });
    });
    resend.addEventListener('submit', event => {
      event.preventDefault();
      perform(resend, async () => {
        await authAction('resend-verification', {email: resend.elements.email.value});
        notice('If eligible, a fresh link is on its way. Only the latest link works. If you changed browsers, sign in again first.', 'resendMessage');
      });
    });
  }
  root.querySelector('#forgotPasswordForm')?.addEventListener('submit', event => {
    event.preventDefault();
    const form = event.currentTarget;
    perform(form, async () => {
      const result = await authAction('forgot-password', {email: form.elements.email.value});
      notice(result.message + ' Check your spam folder too.');
    });
  });
  const reset = root.querySelector('#resetPasswordForm');
  if (reset) {
    if (!currentToken) {
      showError('Open the reset link from your email, or request a new one below.');
      reset.querySelector('button[type="submit"]').disabled = true;
    }
    reset.addEventListener('submit', event => {
      event.preventDefault();
      if (reset.elements.password.value !== reset.elements.confirm_password.value) { showError('The two passwords do not match.'); return; }
      perform(reset, async () => {
        await authAction('reset-password', {token: currentToken, password: reset.elements.password.value});
        currentToken = ''; reset.reset();
        navigate('/login', { replace: true });
        const feedback = document.querySelector('#authNotice');
        if (feedback) { feedback.textContent = 'Password updated. Sign in with your new password.'; feedback.hidden = false; }
      });
    });
  }
}
