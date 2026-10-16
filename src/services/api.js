const API_BASE = (import.meta.env.VITE_API_BASE_URL || "http://localhost:3000").replace(/\/$/, "");
let authConfigPromise;

export function getAuthConfig() {
  if (!authConfigPromise) {
    authConfigPromise = fetch(`${API_BASE}/api/auth/config`, {credentials: 'include', cache: 'no-store'})
      .then(async response => {
        if (!response.ok) throw new Error('Cannot load sign-in options');
        return response.json();
      }).catch(error => { authConfigPromise = undefined; throw error; });
  }
  return authConfigPromise;
}

export function providerSignInURL(provider) {
  return `${API_BASE}/api/auth/${encodeURIComponent(provider)}/start`;
}

export function authAction(action, data) {
  return request(`/api/auth/${action}`, {method: 'POST', body: JSON.stringify(data)});
}

async function request(path, options = {}, retry = true) {
  const unsafe = !['GET', 'HEAD', 'OPTIONS'].includes((options.method || 'GET').toUpperCase());
  const csrf = unsafe ? (await getAuthConfig()).csrf_token : '';
  const response = await fetch(`${API_BASE}${path}`, {
    ...options,
    credentials: 'include',
    headers: {'Content-Type': 'application/json', ...(options.headers || {}), ...(unsafe ? {'X-CSRF-Token': csrf} : {})}
  });
  let data;
  try { data = await response.json(); }
  catch { throw new Error('Cannot reach MarketFlow. Check your connection and try again.'); }
  if (!response.ok) {
    if (unsafe && retry && response.status === 403 && data.code === 'csrf_failed') {
      authConfigPromise = undefined;
      return request(path, options, false);
    }
    const detail = Array.isArray(data.detail) ? data.detail.map(item => item.msg).join('. ') : data.detail;
    const error = new Error(detail || 'MarketFlow API request failed');
    error.status = response.status;
    throw error;
  }
  return data;
}

export function signupUser(data) {
  return request("/api/auth/signup", {
    method: "POST",
    body: JSON.stringify(data)
  });
}

export function loginUser(data) {
  return request("/api/auth/login", {
    method: "POST",
    body: JSON.stringify(data)
  });
}

export function getCurrentUser() {
  return request("/api/auth/me");
}

export function logoutUser() {
  return request("/api/auth/logout", {
    method: "POST"
  });
}

export function checkBackend() {
  return request("/api/health");
}

export function previewCampaign(campaign) {
  return request("/api/campaigns/preview", {
    method: "POST",
    body: JSON.stringify(campaign)
  });
}

export function createCampaign(campaign) {
  return request("/api/campaigns", {
    method: "POST",
    body: JSON.stringify(campaign)
  });
}

export function getCampaigns(
  status = "All",
  q = ""
) {
  const params = new URLSearchParams();

  if (status && status !== "All") {
    params.set("status", status);
  }

  if (q.trim()) {
    params.set("q", q.trim());
  }

  const query = params.toString();

  return request(
    `/api/campaigns${query ? `?${query}` : ""}`
  );
}

export function getCampaign(id) {
  return request(`/api/campaigns/${id}`);
}

export function deleteCampaign(id) {
  return request(`/api/campaigns/${id}`, {
    method: "DELETE"
  });
}

export function getAnalytics(days = 30) {
  return request(
    `/api/analytics/overview?days=${days}`
  );
}


export function updateCampaign(id, campaign) {
  return request(`/api/campaigns/${id}`, {
    method: "PUT",
    body: JSON.stringify(campaign)
  });
}

export function duplicateCampaign(id) {
  return request(
    `/api/campaigns/${id}/duplicate`,
    {
      method: "POST"
    }
  );
}

export function updateCampaignStatus(
  id,
  status
) {
  return request(
    `/api/campaigns/${id}/status`,
    {
      method: "PATCH",
      body: JSON.stringify({ status })
    }
  );
}

export function getCampaignHistory(id) {
  return request(
    `/api/campaigns/${id}/history`
  );
}

export function getDashboardOverview() {
  return request(
    "/api/dashboard/overview"
  );
}

export function getNotifications(
  limit = 50
) {
  return request(
    `/api/notifications?limit=${limit}`
  );
}

export function markNotificationRead(id) {
  return request(
    `/api/notifications/${id}/read`,
    {
      method: "POST"
    }
  );
}

export function markAllNotificationsRead() {
  return request(
    "/api/notifications/read-all",
    {
      method: "POST"
    }
  );
}

export function updateProfile(data) {
  return request(
    "/api/account/profile",
    {
      method: "PUT",
      body: JSON.stringify(data)
    }
  );
}

export function changePassword(data) {
  return request(
    "/api/account/password",
    {
      method: "PUT",
      body: JSON.stringify(data)
    }
  );
}


export function generateStrategy(data) {
  return request("/api/strategy/generate", {
    method: "POST",
    body: JSON.stringify(data)
  });
}

export function getLatestStrategy() {
  return request("/api/strategy/latest");
}

export function getStrategies(limit = 50) {
  return request(`/api/strategy?limit=${limit}`);
}

export function getStrategy(id) {
  return request(`/api/strategy/${id}`);
}

export function acceptStrategy(id) {
  return request(`/api/strategy/${id}/accept`, {
    method: "POST"
  });
}


export function startStrategyAgent() {
  return request("/api/strategy-agent/start", { method: "POST" });
}

export function answerStrategyAgent(sessionId, value) {
  return request(`/api/strategy-agent/${sessionId}/answer`, {
    method: "POST",
    body: JSON.stringify({ value })
  });
}


export function buildStrategyAgent(sessionId) {
  return request(`/api/strategy-agent/${sessionId}/build`, {
    method: "POST"
  });
}


export function resumeStrategyAgent(sessionId) {
  return request(`/api/strategy-agent/${sessionId}/resume`);
}

export function reviseStrategyAgent(data) {
  return request('/api/strategy-agent/revise', {method: 'POST', body: JSON.stringify(data)});
}

export function editStrategyAgentAnswers(sessionId, data) {
  return request(`/api/strategy-agent/${sessionId}/answers`, {method: 'PUT', body: JSON.stringify(data)});
}
