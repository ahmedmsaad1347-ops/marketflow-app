const API_BASE = "http://localhost:3000";

async function request(path, options = {}) {
  const response = await fetch(`${API_BASE}${path}`, {
    credentials: "include",
    headers: {
      "Content-Type": "application/json",
      ...(options.headers || {})
    },
    ...options
  });

  const data = await response.json();

  if (!response.ok) {
    throw new Error(data.detail || "MarketFlow API request failed");
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

export function getCampaigns() {
  return request("/api/campaigns");
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
