const KEY = "marketflow_campaigns";

export const CampaignModel = {
  getAll() {
    try {
      return JSON.parse(localStorage.getItem(KEY)) || [];
    } catch {
      return [];
    }
  },

  create(data) {
    const campaigns = this.getAll();

    const campaign = {
      id: Date.now(),
      ...data,
      status: "Draft",
      createdAt: new Date().toISOString()
    };

    campaigns.unshift(campaign);
    localStorage.setItem(KEY, JSON.stringify(campaigns));

    return campaign;
  },

  remove(id) {
    const campaigns = this.getAll().filter(
      campaign => campaign.id !== Number(id)
    );

    localStorage.setItem(KEY, JSON.stringify(campaigns));
  }
};
