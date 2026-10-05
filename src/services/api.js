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
