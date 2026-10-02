const API_BASE = "http://localhost:3000";

async function request(path, options = {}) {
  const response = await fetch(`${API_BASE}${path}`, {
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

export function previewCampaign(campaign) {
  return request("/api/campaigns/preview", {
    method: "POST",
    body: JSON.stringify(campaign)
  });
}

export function checkBackend() {
  return request("/api/health");
}
