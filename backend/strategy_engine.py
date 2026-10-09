import json
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field


CAPABILITY_SNAPSHOT = "2026-10-09"
ENGINE_VERSION = "strategy-v3-business-understanding-2026-10"


class StrategyRequest(BaseModel):
    mode: str = "guided"
    business_name: str = Field(min_length=2, max_length=120)
    product: str = Field(min_length=2, max_length=240)
    offer: str = Field(default="", max_length=300)
    country: str = Field(min_length=2, max_length=120)
    audience: str = Field(min_length=2, max_length=300)
    objective: str = Field(min_length=2, max_length=40)
    demand_type: str = Field(default="mixed", max_length=40)
    sales_channel: str = Field(default="website", max_length=40)
    currency: str = Field(default="USD", min_length=2, max_length=12)
    total_budget: float = Field(gt=0)
    campaign_days: int = Field(default=30, ge=1, le=365)
    price: float = Field(default=0, ge=0)
    gross_margin_percent: float = Field(default=0, ge=0, le=100)
    extra_variable_cost_per_order: float = Field(default=0, ge=0)
    lead_to_sale_rate_percent: float = Field(default=0, ge=0, le=100)
    has_website: bool = False
    has_tracking: bool = False
    has_previous_sales: bool = False
    has_video_creatives: bool = False
    notes: str = Field(default="", max_length=1000)


def _round(value):
    return round(float(value or 0), 2)


def _goal(objective):
    mapping = {
        "sales": "Sales",
        "leads": "Leads",
        "messages": "Messages",
        "traffic": "Website traffic",
        "awareness": "Brand awareness",
    }
    return mapping.get((objective or "").strip().lower(), "Sales")


def _country_code(country):
    value = (country or "").strip().lower()

    aliases = {
        "egypt": "EG",
        "مصر": "EG",
        "united states": "US",
        "usa": "US",
        "us": "US",
        "canada": "CA",
        "united kingdom": "GB",
        "uk": "GB",
        "great britain": "GB",
        "germany": "DE",
        "france": "FR",
        "italy": "IT",
        "spain": "ES",
        "mexico": "MX",
        "brazil": "BR",
        "saudi arabia": "SA",
        "saudi": "SA",
        "السعودية": "SA",
        "australia": "AU",
        "japan": "JP",
    }

    return aliases.get(value, value.upper()[:2])


def _tiktok_search_available(country_code, objective):
    web_conversion = {
        "US", "CA", "GB", "IT", "MX",
        "ES", "DE", "FR", "SA", "AU", "BR",
    }

    traffic = {
        "US", "CA", "GB", "IT", "MX",
        "JP", "ES", "DE", "FR", "SA",
    }

    lead_generation = {"US"}

    if objective == "sales":
        return country_code in web_conversion

    if objective == "traffic":
        return country_code in traffic

    if objective == "leads":
        return country_code in lead_generation

    return False


def _candidate(
    key,
    provider,
    campaign_type,
    score,
    eligible,
    reasons,
    availability_note,
):
    return {
        "key": key,
        "provider": provider,
        "campaign_type": campaign_type,
        "score": max(0, min(int(score), 100)),
        "eligible": bool(eligible),
        "reasons": reasons,
        "availability_note": availability_note,
    }



def _business_profile(data):
    text = " ".join([
        data.business_name,
        data.product,
        data.offer,
        data.audience,
        data.notes,
    ]).lower()

    vertical_terms = {
        "real_estate": ["real estate", "property", "properties", "apartment", "apartments", "villa", "villas", "townhouse", "compound", "residential", "developer"],
        "ecommerce": ["ecommerce", "e-commerce", "online store", "shop", "clothing", "fashion", "shoes", "cosmetics", "skincare", "electronics", "jewelry", "accessories"],
        "saas": ["saas", "software", "platform", "subscription", "crm", "automation software", "cloud software"],
        "education": ["course", "courses", "academy", "school", "university", "training", "tutoring", "education", "bootcamp"],
        "healthcare": ["clinic", "doctor", "medical", "dental", "dentist", "healthcare", "hospital", "physio", "therapy"],
        "hospitality": ["hotel", "resort", "travel", "tour", "booking", "vacation", "holiday", "hospitality"],
        "restaurant": ["restaurant", "cafe", "coffee", "food", "meal", "pizza", "burger", "bakery"],
        "local_service": ["plumbing", "plumber", "electrician", "cleaning", "repair", "maintenance", "painting", "moving", "pest control", "landscaping", "salon", "barber", "home service"],
        "professional_service": ["consulting", "consultant", "agency", "law firm", "lawyer", "accounting", "accountant", "architect", "design studio", "marketing agency", "business service"],
        "automotive": ["car", "cars", "automotive", "vehicle", "garage", "auto repair", "dealership"],
    }

    vertical = "general"
    best_hits = []

    for candidate, terms in vertical_terms.items():
        hits = [term for term in terms if term in text]
        if len(hits) > len(best_hits):
            vertical = candidate
            best_hits = hits

    audience = data.audience.lower()
    b2b_terms = ["business", "businesses", "company", "companies", "enterprise", "brands", "teams", "founders", "managers", "professionals"]
    b2c_terms = ["families", "homeowners", "renters", "shoppers", "students", "patients", "customers", "parents", "individuals", "people"]

    has_b2b = any(term in audience for term in b2b_terms)
    has_b2c = any(term in audience for term in b2c_terms)

    if has_b2b and has_b2c:
        buyer_type = "B2B + B2C"
    elif has_b2b:
        buyer_type = "B2B"
    else:
        buyer_type = "B2C"

    if vertical == "saas" or "subscription" in text or "membership" in text:
        revenue_model = "Subscription / recurring"
    elif vertical in {"professional_service", "local_service", "healthcare"}:
        revenue_model = "Service / appointment"
    elif vertical == "real_estate":
        revenue_model = "High-value deal"
    elif vertical == "education":
        revenue_model = "Enrollment / program"
    elif vertical == "hospitality":
        revenue_model = "Booking"
    elif vertical == "restaurant":
        revenue_model = "Order / visit"
    else:
        revenue_model = "Transaction / sale"

    if vertical in {"real_estate", "professional_service"} or buyer_type == "B2B":
        purchase_cycle = "Long / considered"
    elif vertical in {"saas", "education", "healthcare", "automotive"}:
        purchase_cycle = "Medium / considered"
    else:
        purchase_cycle = "Short / moderate"

    demand = data.demand_type.strip().lower()
    demand_motion = {
        "search": "Intent capture",
        "discovery": "Demand creation",
        "mixed": "Intent capture + demand creation",
    }.get(demand, "Mixed acquisition")

    objective = data.objective.strip().lower()
    conversion_type = {
        "sales": "Purchase / sale",
        "leads": "Qualified lead",
        "messages": "Conversation",
        "traffic": "Qualified visit",
        "awareness": "Qualified attention",
    }.get(objective, "Primary conversion")

    channel = data.sales_channel.strip().lower()
    if channel == "phone":
        conversion_path = "Phone-led"
    elif channel in {"whatsapp", "messages", "dm", "direct messages"}:
        conversion_path = "Conversation-led"
    elif channel == "store":
        conversion_path = "Offline / store"
    elif data.has_website:
        conversion_path = "Website-led"
    else:
        conversion_path = "Lead capture"

    if vertical in {"local_service", "restaurant", "healthcare", "real_estate"}:
        geography_model = "Local / regional"
    elif vertical in {"saas", "ecommerce", "education"}:
        geography_model = "Scalable / broad"
    else:
        geography_model = "Depends on delivery area"

    if demand == "search":
        acquisition_strategy = "Capture existing demand first"
    elif demand == "discovery":
        acquisition_strategy = "Create demand first, then retarget intent"
    else:
        acquisition_strategy = "Blend intent capture with demand creation"

    if purchase_cycle == "Long / considered":
        acquisition_strategy += " with lead qualification and follow-up"

    confidence_points = 2 if best_hits else 0
    confidence_points += 1 if data.demand_type.strip() else 0
    confidence_points += 1 if data.objective.strip() else 0
    confidence_points += 1 if data.sales_channel.strip() else 0
    confidence = "High" if confidence_points >= 4 else "Medium" if confidence_points >= 2 else "Low"

    vertical_label = {
        "real_estate": "Real estate",
        "ecommerce": "E-commerce",
        "saas": "SaaS / software",
        "education": "Education",
        "healthcare": "Healthcare",
        "hospitality": "Hospitality / travel",
        "restaurant": "Restaurant / food",
        "local_service": "Local service",
        "professional_service": "Professional service",
        "automotive": "Automotive",
        "general": "General business",
    }.get(vertical, "General business")

    return {
        "vertical_key": vertical,
        "vertical": vertical_label,
        "buyer_type": buyer_type,
        "revenue_model": revenue_model,
        "purchase_cycle": purchase_cycle,
        "demand_motion": demand_motion,
        "conversion_type": conversion_type,
        "conversion_path": conversion_path,
        "geography_model": geography_model,
        "acquisition_strategy": acquisition_strategy,
        "confidence": confidence,
    }


def _apply_business_profile_to_candidates(candidates, profile, data):
    by_key = {item["key"]: item for item in candidates}

    def adjust(key, delta, reason):
        item = by_key.get(key)
        if not item or not delta:
            return
        item["score"] = max(0, min(100, item["score"] + delta))
        if reason and reason not in item["reasons"]:
            item["reasons"].append(reason)

    vertical = profile["vertical_key"]
    buyer = profile["buyer_type"]
    cycle = profile["purchase_cycle"]
    demand = data.demand_type.strip().lower()
    objective = data.objective.strip().lower()
    channel = data.sales_channel.strip().lower()

    if demand == "search":
        adjust("google_search", 10, "The business profile is intent-led, so existing demand should be captured first.")
    elif demand == "discovery":
        adjust("google_demand_gen", 8, "The business profile requires demand creation before conversion.")
        adjust("tiktok_smart_plus", 6 if data.has_video_creatives else 2, "Discovery-led acquisition benefits from visual creative testing.")
    elif demand == "mixed":
        adjust("google_search", 5, "The business has meaningful search intent alongside discovery demand.")
        adjust("google_demand_gen", 4, "A secondary demand-creation layer can support the mixed acquisition motion.")

    if buyer in {"B2B", "B2B + B2C"} and objective == "leads":
        adjust("google_search", 7, "Considered B2B lead generation benefits from high-intent search traffic.")
        adjust("meta_leads", 4, "Meta lead generation can support additional prospect discovery and remarketing.")

    if cycle == "Long / considered" and objective == "leads":
        if demand in {"search", "mixed"}:
            adjust("google_search", 5, "The purchase cycle is considered, so qualified intent matters more than raw reach.")
        if demand in {"mixed", "discovery"}:
            adjust("meta_leads", 4, "The longer decision cycle supports lead capture and follow-up.")

    if channel in {"whatsapp", "messages", "dm", "direct messages"}:
        adjust("meta_messages", 8, "The conversion path is conversation-led.")

    if vertical == "real_estate" and objective == "leads":
        if demand in {"search", "mixed"}:
            adjust("google_search", 7, "Property buyers often express strong location and inventory intent in search.")
        if data.has_video_creatives:
            adjust("meta_leads", 6, "Property discovery benefits from visual creative and lead capture.")
            adjust("google_demand_gen", 4, "Visual property discovery can support the search-led campaign.")

    elif vertical == "ecommerce" and objective == "sales":
        adjust("google_pmax", 9 if data.has_tracking else 4, "E-commerce sales can benefit from automated inventory-wide conversion optimization.")
        adjust("meta_advantage_sales", 8, "Visual product discovery is a strong complementary sales motion.")
        if data.has_video_creatives:
            adjust("tiktok_smart_plus", 5, "Short-form product creative can support discovery-led sales.")

    elif vertical == "saas":
        if objective in {"leads", "sales", "traffic"} and demand in {"search", "mixed"}:
            adjust("google_search", 7, "Software evaluation often starts with problem-aware or solution-aware search.")

    elif vertical == "local_service":
        if objective in {"leads", "sales", "traffic"} and demand in {"search", "mixed"}:
            adjust("google_search", 8, "Local services usually benefit from capturing immediate service intent.")

    if not data.has_tracking:
        adjust("google_pmax", -8, "Performance Max is de-prioritized until reliable conversion tracking exists.")
    if not data.has_previous_sales:
        adjust("google_pmax", -5, "Limited conversion history reduces confidence in highly automated optimization.")

    candidates.sort(
        key=lambda item: (
            1 if item["eligible"] else 0,
            item["score"],
        ),
        reverse=True,
    )
    return candidates


def _score_candidates(data):
    objective = data.objective.strip().lower()
    demand = data.demand_type.strip().lower()
    channel = data.sales_channel.strip().lower()
    country_code = _country_code(data.country)

    candidates = []

    # Meta: Messages
    score = 10
    reasons = []

    if objective == "messages":
        score += 75
        reasons.append("The requested outcome is a direct customer conversation.")

    if channel in {"whatsapp", "messages", "dm", "direct messages"}:
        score += 15
        reasons.append("The sales path is conversation-led.")

    candidates.append(
        _candidate(
            "meta_messages",
            "Meta",
            "Meta Messages",
            score,
            objective == "messages" or channel in {
                "whatsapp", "messages", "dm", "direct messages"
            },
            reasons,
            "Meta product availability and messaging destinations should be verified in the ad account at launch.",
        )
    )

    # Meta: Advantage+ Sales
    score = 15
    reasons = []

    if objective == "sales":
        score += 55
        reasons.append("The primary goal is sales.")

    if demand == "discovery":
        score += 15
        reasons.append("The offer is discovery-led.")

    elif demand == "mixed":
        score += 8
        reasons.append("The offer has mixed discovery and intent signals.")

    if data.has_website:
        score += 5

    if data.has_tracking:
        score += 5
        reasons.append("Conversion tracking is available.")

    if data.has_video_creatives:
        score += 5
        reasons.append("Vertical video creative is available.")

    if not data.has_website and objective == "sales":
        score -= 20

    candidates.append(
        _candidate(
            "meta_advantage_sales",
            "Meta",
            "Advantage+ Sales",
            score,
            objective == "sales",
            reasons,
            "Use only after confirming the selected conversion destination and account eligibility.",
        )
    )

    # Meta: Lead Generation
    score = 15
    reasons = []

    if objective == "leads":
        score += 60
        reasons.append("The primary goal is lead generation.")

    if demand in {"discovery", "mixed"}:
        score += 10
        reasons.append("Meta can capture demand before a user actively searches.")

    if not data.has_website:
        score += 10
        reasons.append("An on-platform lead experience reduces website dependency.")

    candidates.append(
        _candidate(
            "meta_leads",
            "Meta",
            "Meta Lead Generation",
            score,
            objective == "leads",
            reasons,
            "Confirm the lead destination and any market-specific lead-ad requirements before launch.",
        )
    )

    # Meta: Awareness
    score = 15
    reasons = []

    if objective == "awareness":
        score += 60
        reasons.append("The primary goal is awareness.")

    if demand == "discovery":
        score += 10

    if data.has_video_creatives:
        score += 8
        reasons.append("Video creative can use Reels placements.")

    candidates.append(
        _candidate(
            "meta_awareness",
            "Meta",
            "Meta Awareness",
            score,
            objective == "awareness",
            reasons,
            "Advantage+ placements can include Facebook, Instagram, Messenger and Audience Network where eligible.",
        )
    )

    # Google Search
    score = 10
    reasons = []

    if objective in {"sales", "leads", "traffic"}:
        score += 35

    if demand == "search":
        score += 40
        reasons.append("Customers actively search for the offer.")

    elif demand == "mixed":
        score += 15

    if data.has_website:
        score += 10
        reasons.append("A website or landing page is available.")

    if data.has_tracking:
        score += 5

    if demand == "discovery":
        score -= 20

    candidates.append(
        _candidate(
            "google_search",
            "Google",
            "Google Search",
            score,
            data.has_website and objective in {"sales", "leads", "traffic"},
            reasons,
            "Search is only recommended here when a usable website or landing page exists.",
        )
    )

    # Google Performance Max
    score = 10
    reasons = []

    if objective == "sales":
        score += 45
        reasons.append("Performance Max can optimize toward purchase value across Google inventory.")

    elif objective == "leads":
        score += 35
        reasons.append("Performance Max can support conversion-focused lead generation.")

    if data.has_website:
        score += 10

    if data.has_tracking:
        score += 15
        reasons.append("Reliable conversion tracking improves automation readiness.")

    if data.has_previous_sales:
        score += 10
        reasons.append("Existing conversion history makes automated optimization more defensible.")

    if data.has_video_creatives:
        score += 5

    candidates.append(
        _candidate(
            "google_pmax",
            "Google",
            "Performance Max",
            score,
            data.has_website and objective in {"sales", "leads"},
            reasons,
            "Asset, feed and account eligibility should be verified before launch.",
        )
    )

    # Google Demand Gen
    score = 10
    reasons = []

    if objective == "awareness":
        score += 45

    elif objective == "traffic":
        score += 35

    elif objective in {"sales", "leads"}:
        score += 25

    if demand == "discovery":
        score += 25
        reasons.append("Demand Gen is suited to visual discovery across Google surfaces.")

    elif demand == "mixed":
        score += 10

    if data.has_video_creatives:
        score += 15
        reasons.append("Video creative improves readiness for YouTube and visual placements.")

    if data.has_website:
        score += 5

    candidates.append(
        _candidate(
            "google_demand_gen",
            "Google",
            "Demand Gen",
            score,
            objective in {"awareness", "traffic", "sales", "leads"},
            reasons,
            "Display campaign creation is moving into Demand Gen; exact account availability should be checked at launch.",
        )
    )

    # TikTok Smart+
    score = 10
    reasons = []

    if objective == "awareness":
        score += 50

    elif objective == "sales":
        score += 40

    elif objective == "leads":
        score += 35

    elif objective == "traffic":
        score += 30

    if demand == "discovery":
        score += 25
        reasons.append("TikTok is strong when the customer discovers the offer through content.")

    elif demand == "mixed":
        score += 10

    if data.has_video_creatives:
        score += 20
        reasons.append("Usable vertical video creative is available.")

    else:
        score -= 15

    if data.has_tracking and objective in {"sales", "leads"}:
        score += 10

    if data.has_previous_sales:
        score += 5

    candidates.append(
        _candidate(
            "tiktok_smart_plus",
            "TikTok",
            "TikTok Smart+",
            score,
            objective in {"awareness", "traffic", "sales", "leads"},
            reasons,
            "Smart+ availability and supported automation controls vary by account and market; verify at launch.",
        )
    )

    # TikTok Search Ads Campaign
    supported = _tiktok_search_available(country_code, objective)
    score = 10
    reasons = []

    if objective in {"sales", "traffic", "leads"}:
        score += 35

    if demand == "search":
        score += 40
        reasons.append("The offer has explicit search intent.")

    elif demand == "mixed":
        score += 15

    if data.has_website:
        score += 10

    if data.has_video_creatives:
        score += 5

    availability_note = (
        f"TikTok Search Ads Campaign is supported for this objective in {data.country.strip()} "
        f"according to the {CAPABILITY_SNAPSHOT} capability snapshot."
        if supported
        else (
            f"TikTok Search Ads Campaign is not treated as launch-eligible for "
            f"{data.country.strip()} + {objective} in the {CAPABILITY_SNAPSHOT} snapshot. "
            "Market availability must be rechecked before recommending it."
        )
    )

    candidates.append(
        _candidate(
            "tiktok_search",
            "TikTok",
            "TikTok Search Ads Campaign",
            score,
            supported and data.has_website and objective in {"sales", "traffic", "leads"},
            reasons,
            availability_note,
        )
    )

    candidates.sort(
        key=lambda item: (
            1 if item["eligible"] else 0,
            item["score"],
        ),
        reverse=True,
    )

    return candidates


def _automation_plan(candidate, data):
    key = candidate["key"]

    plans = {
        "meta_messages": {
            "automation_mode": "Automated delivery with controlled messaging destination",
            "audience_approach": "Broad/Advantage+ audience with only necessary business constraints",
            "placements": "Advantage+ placements where compatible with the messaging destination",
        },
        "meta_advantage_sales": {
            "automation_mode": "Advantage+ sales automation",
            "audience_approach": "Advantage+ audience; keep hard constraints only where they are truly required",
            "placements": "Advantage+ placements",
        },
        "meta_leads": {
            "automation_mode": "Automated lead delivery with controlled form/destination",
            "audience_approach": "Broad/Advantage+ audience plus useful first-party exclusions",
            "placements": "Advantage+ placements where compatible",
        },
        "meta_awareness": {
            "automation_mode": "Automated reach/delivery",
            "audience_approach": "Broad audience with essential geo/brand constraints",
            "placements": "Advantage+ placements",
        },
        "google_search": {
            "automation_mode": "AI-powered Search + Smart Bidding",
            "audience_approach": "Search intent first; audience signals are secondary to query/keyword intent",
            "placements": "Google Search",
        },
        "google_pmax": {
            "automation_mode": "High automation across Performance Max inventory",
            "audience_approach": "Audience signals guide automation; they are not treated as narrow hard targeting",
            "placements": "Performance Max inventory across eligible Google surfaces",
        },
        "google_demand_gen": {
            "automation_mode": "AI-assisted Demand Gen",
            "audience_approach": "Use audience signals/suggestions and first-party data instead of excessive manual narrowing",
            "placements": "YouTube, Discover, Gmail, Maps and Google Display Network where eligible",
        },
        "tiktok_smart_plus": {
            "automation_mode": "Smart+ automation",
            "audience_approach": "Automatic targeting with audience controls/suggestions where available",
            "placements": "TikTok automated placements supported by the selected objective",
        },
        "tiktok_search": {
            "automation_mode": "Search campaign with keyword-level control",
            "audience_approach": "Keyword/search intent first, then relevant targeting controls",
            "placements": "TikTok Search results",
        },
    }

    return plans.get(
        key,
        {
            "automation_mode": "Platform automation",
            "audience_approach": "Broad first, then refine from real data",
            "placements": "Platform-recommended placements",
        },
    )


def _bidding_plan(candidate, data):
    key = candidate["key"]
    objective = data.objective.strip().lower()

    if key.startswith("google_"):
        if objective == "sales":
            if data.has_tracking and data.has_previous_sales and data.price > 0:
                return (
                    "Start with Maximize conversion value. Consider Target ROAS only after "
                    "sufficient conversion-value history and campaign eligibility are confirmed."
                )

            return (
                "Start with Maximize conversions until reliable purchase-value data exists, "
                "then evaluate Maximize conversion value or Target ROAS."
            )

        if objective == "leads":
            if data.has_tracking and data.has_previous_sales:
                return (
                    "Start with Maximize conversions. Consider Target CPA only after a stable "
                    "qualified-lead cost baseline and enough conversion history exist."
                )

            return (
                "Start with Maximize conversions and measure qualified leads. "
                "Do not set an aggressive Target CPA before a reliable baseline exists."
            )

        if objective == "traffic":
            return (
                "Use a traffic-focused bid strategy only if traffic itself is the real goal. "
                "If a downstream conversion matters, switch optimization to that conversion instead."
            )

        return "Use the bidding strategy that matches the selected conversion or awareness goal."

    if key.startswith("meta_"):
        if objective in {"sales", "leads", "messages"}:
            return (
                "Start with conversion/volume-focused automated delivery. "
                "Add cost controls only after a stable real-world CPA or cost-per-result baseline exists."
            )

        return "Use automated delivery focused on the selected awareness outcome."

    if key.startswith("tiktok_"):
        if objective in {"sales", "leads"}:
            return (
                "Start with automated delivery / maximum-result bidding in the selected TikTok workflow. "
                "Introduce target-cost controls only after a stable cost baseline exists."
            )

        return "Use automated delivery aligned to the selected traffic or awareness objective."

    return "Use automated bidding aligned to the business outcome."


def _trim_asset(text, limit):
    value = " ".join(str(text or "").split()).strip()

    if len(value) <= limit:
        return value

    clipped = value[:limit + 1]
    clipped = clipped.rsplit(" ", 1)[0].strip()

    return clipped if clipped else value[:limit].strip()


def _unique_assets(items, limit=None):
    seen = set()
    result = []

    for item in items:
        value = " ".join(str(item or "").split()).strip()

        if not value:
            continue

        if limit:
            value = _trim_asset(value, limit)

        key = value.lower()

        if key in seen:
            continue

        seen.add(key)
        result.append(value)

    return result


def _extract_geo_hint(data):
    sources = [
        data.product.strip(),
        data.audience.strip(),
        data.offer.strip(),
    ]

    stop_markers = [
        " with ",
        " for ",
        " who ",
        " looking ",
        " and ",
        ",",
        ".",
    ]

    for source in sources:
        lower = source.lower()

        if " in " not in lower:
            continue

        start = lower.find(" in ") + 4
        tail = source[start:].strip()
        tail_lower = tail.lower()

        end = len(tail)

        for marker in stop_markers:
            idx = tail_lower.find(marker)
            if idx != -1:
                end = min(end, idx)

        candidate = tail[:end].strip(" -,")

        if 2 <= len(candidate) <= 40:
            return candidate

    return data.country.strip()


def _infer_business_vertical(data):
    haystack = " ".join([
        data.business_name,
        data.product,
        data.audience,
        data.offer,
    ]).lower()

    real_estate_terms = [
        "apartment", "apartments", "property", "properties",
        "real estate", "residential", "villa", "villas",
        "townhouse", "townhouses", "compound", "compounds",
        "developer", "home for sale", "house for sale",
        "unit for sale",
    ]

    ecommerce_terms = [
        "ecommerce", "e-commerce", "online store", "clothing",
        "fashion", "shoes", "cosmetics", "skincare",
        "electronics", "product store",
    ]

    local_service_terms = [
        "plumbing", "plumber", "electrician", "cleaning",
        "repair", "maintenance", "painting", "salon",
        "moving", "pest control", "landscaping",
    ]

    if any(term in haystack for term in real_estate_terms):
        return "real_estate"

    if any(term in haystack for term in ecommerce_terms):
        return "ecommerce"

    if any(term in haystack for term in local_service_terms):
        return "local_service"

    return "generic"


def _real_estate_subject(data):
    haystack = f"{data.product} {data.audience}".lower()

    options = [
        ("townhouse", "Townhouses"),
        ("villa", "Villas"),
        ("apartment", "Apartments"),
        ("home", "Homes"),
        ("house", "Homes"),
        ("unit", "Units"),
    ]

    for token, label in options:
        if token in haystack:
            return label

    return "Properties"


def _short_service_name(product):
    value = " ".join(str(product or "").split()).strip()

    for separator in [
        " and ",
        " with ",
        " for ",
        " including ",
        ",",
        "/",
    ]:
        if separator in value.lower():
            index = value.lower().find(separator)
            value = value[:index].strip()
            break

    words = value.split()

    if len(words) > 4:
        value = " ".join(words[:4])

    return _trim_asset(value, 24)


def _offer_parts(offer):
    value = " ".join(str(offer or "").split()).strip()

    if not value:
        return []

    parts = [value]

    for separator in [" with ", " and ", ","]:
        expanded = []

        for item in parts:
            if separator in item.lower():
                lower = item.lower()
                index = lower.find(separator)

                expanded.append(item[:index].strip())
                expanded.append(item[index + len(separator):].strip())
            else:
                expanded.append(item)

        parts = expanded

    return _unique_assets(parts, 30)


def _cta_for(data, vertical):
    objective = data.objective.strip().lower()

    if vertical == "real_estate":
        return {
            "awareness": "View Properties",
            "traffic": "View Units",
            "messages": "Send Message",
            "leads": "Request Details",
            "sales": "View Units",
        }.get(objective, "Request Details")

    return {
        "awareness": "Learn More",
        "traffic": "Learn More",
        "messages": "Send Message",
        "leads": "Get Quote",
        "sales": "Shop Now",
    }.get(objective, "Learn More")


def _real_estate_search_pack(data, cta):
    business = data.business_name.strip()
    location = _extract_geo_hint(data)
    subject = _real_estate_subject(data)
    singular = {
        "Apartments": "Apartment",
        "Villas": "Villa",
        "Townhouses": "Townhouse",
        "Homes": "Home",
        "Units": "Unit",
        "Properties": "Property",
    }.get(subject, "Property")

    offer = data.offer.strip()
    offer_parts = _offer_parts(offer)

    headlines = [
        f"{location} {subject}",
        f"{subject} For Sale",
        f"{subject} In {location}",
        business,
        "View Available Units",
        "Request Property Details",
        "Flexible Payment Plans",
        "Book A Consultation",
        f"{location} Property",
        f"Buy In {location}",
        cta,
    ]

    headlines.extend(offer_parts)
    headlines = _unique_assets(headlines, 30)[:15]

    descriptions = _unique_assets([
        f"Explore {subject.lower()} in {location}. {offer or 'Request current availability and payment details.'}",
        f"View available {subject.lower()} in {location}. Request current prices, availability and payment details.",
        f"Compare {singular.lower()} options and payment plans with {business}. Request property details.",
        f"Looking to buy in {location}? View property details and book a consultation.",
    ], 90)[:4]

    keyword_groups = {
        "Core property intent": _unique_assets([
            f"{location} {subject}".lower(),
            f"{subject} for sale {location}".lower(),
            f"{location} property for sale".lower(),
            f"{location} real estate".lower(),
        ]),
        "Payment intent": _unique_assets([
            f"{location} {subject} installment".lower(),
            f"{location} {singular} payment plan".lower(),
            f"{location} {subject} price".lower(),
        ]),
        "Commercial intent": _unique_assets([
            f"buy {singular} in {location}".lower(),
            f"{subject} for sale in {location}".lower(),
            f"{location} property prices".lower(),
        ]),
        "Brand": _unique_assets([
            business.lower(),
        ]),
    }

    if "invest" in data.audience.lower():
        keyword_groups["Investment intent"] = _unique_assets([
            f"{location} investment property".lower(),
            f"property investment {location}".lower(),
        ])

    negative_ideas = [
        "jobs",
        "careers",
        "salary",
        "course",
        "training",
        "definition",
    ]

    match_type_plan = (
        "Conversion tracking is confirmed. Keep ad groups tightly themed. "
        "Use Smart Bidding and test broad match where conversion quality is reliable; "
        "keep exact/phrase terms for brand and high-value location intent. "
        "Review Search Terms before adding negatives."
        if data.has_tracking
        else (
            "Conversion tracking is not confirmed. Start with tighter phrase/exact property "
            "and location intent, then expand only after measurement is reliable."
        )
    )

    return {
        "headlines": headlines,
        "descriptions": descriptions,
        "keyword_groups": keyword_groups,
        "negative_keyword_ideas": negative_ideas,
        "match_type_plan": match_type_plan,
        "headline_limit": 30,
        "description_limit": 90,
    }


def _generic_google_search_pack(data, cta):
    business = data.business_name.strip()
    product = data.product.strip()
    country = data.country.strip()
    offer = data.offer.strip()
    service = _short_service_name(product)

    offer_parts = _offer_parts(offer)

    urgent_signal = any(
        word in f"{product} {offer}".lower()
        for word in [
            "emergency",
            "urgent",
            "same-day",
            "same day",
            "fast",
        ]
    )

    pricing_signal = any(
        word in f"{product} {offer}".lower()
        for word in [
            "quote",
            "price",
            "pricing",
            "cost",
            "estimate",
        ]
    )

    headlines = [
        service.title(),
        f"{service} {country}".title(),
        business,
        cta,
        f"Local {service}".title(),
        "Fast Local Service",
        "Clear Next Steps",
    ]

    action_headline = (
        f"Book {service}"
        if any(word in product.lower() for word in ["service", "repair", "plumb", "clean"])
        else f"Explore {service}"
    )
    headlines.append(action_headline)
    headlines.extend(offer_parts)

    if urgent_signal:
        headlines.extend([
            "Emergency Help Available",
            "Same-Day Service",
            "Fast Response Available",
        ])

    if pricing_signal:
        headlines.extend([
            "Upfront Quote",
            "Clear Pricing",
        ])

    headlines = _unique_assets(headlines, 30)[:15]

    descriptions = _unique_assets([
        f"{business} offers {product}. {offer or 'Check availability and next steps.'}",
        f"Need {service}? Check availability, details and pricing with {business}.",
        f"Serving customers in {country}. Ask about {service} and the next step.",
        f"Compare the service, proof and offer before you decide. Contact {business}.",
    ], 90)[:4]

    keyword_groups = {
        "Core service": _unique_assets([
            service.lower(),
            product.lower(),
        ]),
        "Local intent": _unique_assets([
            f"{service} near me".lower(),
            f"{service} {country}".lower(),
        ]),
        "Commercial intent": _unique_assets([
            f"{service} quote".lower(),
            f"{service} price".lower(),
            f"{service} cost".lower(),
        ]),
        "Brand": _unique_assets([
            business.lower(),
        ]),
    }

    if urgent_signal:
        keyword_groups["Urgent intent"] = _unique_assets([
            f"emergency {service}".lower(),
            f"urgent {service}".lower(),
        ])

    negative_ideas = [
        "jobs",
        "careers",
        "salary",
        "course",
        "training",
        "diy",
        "definition",
    ]

    match_type_plan = (
        "Conversion tracking is confirmed. Start with Smart Bidding and test broad match "
        "on tightly themed ad groups. Keep phrase/exact terms for brand or queries that "
        "need tighter control. Review Search Terms before adding negatives."
        if data.has_tracking
        else (
            "Without confirmed conversion tracking, start with tighter phrase/exact targeting "
            "and avoid aggressive broad-match expansion until measurement is reliable."
        )
    )

    return {
        "headlines": headlines,
        "descriptions": descriptions,
        "keyword_groups": keyword_groups,
        "negative_keyword_ideas": negative_ideas,
        "match_type_plan": match_type_plan,
        "headline_limit": 30,
        "description_limit": 90,
    }


def _google_search_pack(data, vertical, cta):
    if vertical == "real_estate":
        return _real_estate_search_pack(data, cta)

    return _generic_google_search_pack(data, cta)


def _creative_plan(data, candidate):
    provider = candidate["provider"]
    campaign_type = candidate["campaign_type"]

    business = data.business_name.strip()
    product = data.product.strip()
    audience = data.audience.strip()
    country = data.country.strip()
    offer = data.offer.strip()

    vertical = _infer_business_vertical(data)
    location_hint = _extract_geo_hint(data)
    cta = _cta_for(data, vertical)

    offer_line = (
        offer
        if offer
        else "Ask about availability, pricing and the next step."
    )

    if vertical == "real_estate":
        subject = _real_estate_subject(data)

        angles = [
            {
                "name": "Property fit",
                "idea": (
                    f"Lead with {subject.lower()} in {location_hint}, then help the buyer "
                    "compare location, unit fit, availability and the next step."
                ),
            },
            {
                "name": "Payment plan",
                "idea": (
                    f"Explain the payment structure clearly: {offer_line} "
                    "Do not imply financing terms that are not verified."
                ),
            },
            {
                "name": "Proof & availability",
                "idea": (
                    "Use real unit availability, floor plans, project/developer information, "
                    "delivery details and other facts the business can substantiate."
                ),
            },
        ]
    else:
        angles = [
            {
                "name": "Problem → Solution",
                "idea": (
                    f"Show the real situation faced by {audience}, then demonstrate "
                    f"how {product} helps without making unverified claims."
                ),
            },
            {
                "name": "Proof",
                "idea": (
                    "Use real demonstrations, real customer proof, credentials, process evidence "
                    "or other facts that can be substantiated."
                ),
            },
            {
                "name": "Offer",
                "idea": offer_line,
            },
        ]

    hooks = [
        f"Looking for {product} in {country}?",
        f"Need a clear next step for {product}?",
        f"Before you choose {product}, check what actually matters.",
        f"{business}: a practical way to get started with {product}.",
        (
            f"{offer} — here is what to know before you act."
            if offer
            else f"Considering {product}? Start with the facts that matter."
        ),
    ]

    headlines = [
        business,
        product,
        f"{product} in {country}",
        cta,
    ]

    primary_texts = [
        (
            f"{business} offers {product} for {audience}. "
            f"{offer_line} {cta}."
        ),
        (
            f"Looking for {product} in {country}? "
            f"See the details, understand the next step, and decide whether "
            f"{business} is the right fit. {cta}."
        ),
    ]

    descriptions = []
    keyword_themes = []
    negative_keyword_ideas = []
    video_scripts = []
    search_pack = None

    if campaign_type == "Google Search":
        search_pack = _google_search_pack(
            data,
            vertical,
            cta,
        )

        headlines = search_pack["headlines"]
        descriptions = search_pack["descriptions"]
        primary_texts = []
        keyword_themes = [
            keyword
            for group in search_pack["keyword_groups"].values()
            for keyword in group
        ]
        negative_keyword_ideas = search_pack["negative_keyword_ideas"]

        formats = [
            "Responsive Search Ad headlines are capped at 30 characters.",
            "Responsive Search Ad descriptions are capped at 90 characters.",
            "Keep assets distinct so Google can test useful combinations.",
            "Match ad language tightly to the search intent and landing page.",
        ]

    elif provider == "Meta":
        formats = [
            "Prioritize 9:16 vertical video with audio and key messages inside the safe zone for Reels-ready creative.",
            "Keep multiple creative angles live instead of relying on one ad.",
            "Use static/carousel support assets when they add useful product or proof detail.",
        ]

        video_scripts = [
            {
                "name": "Problem → Solution video",
                "hook": hooks[1],
                "shots": [
                    "Show the real customer situation/problem in the first seconds.",
                    f"Show {product} being used, delivered or explored.",
                    "Show real proof, process or other substantiated evidence.",
                    f"Finish with the offer/next step: {offer_line}",
                ],
                "on_screen_text": [
                    product,
                    offer_line,
                    cta,
                ],
            },
        ]

    elif campaign_type == "TikTok Search Ads Campaign":
        formats = [
            "Use search-intent creative that directly matches the keyword/query intent.",
            "Prepare video or carousel assets aligned with the search ad workflow.",
            "Keep keyword, creative and landing-page message tightly aligned.",
        ]

        keyword_themes = [
            product,
            f"{product} {country}",
            f"{product} near me",
            business,
        ]

        negative_keyword_ideas = [
            "jobs",
            "careers",
            "course",
            "training",
        ]

        video_scripts = [
            {
                "name": "Search answer video",
                "hook": f"Searching for {product}?",
                "shots": [
                    "Answer the search intent immediately.",
                    f"Show what {business} actually offers.",
                    "Show verifiable proof or process evidence.",
                    f"Close with {cta}.",
                ],
                "on_screen_text": [
                    product,
                    offer_line,
                    cta,
                ],
            },
        ]

    elif provider == "TikTok":
        formats = [
            "Use native-feeling 9:16 vertical video.",
            "Prepare multiple hooks and creator-style variations.",
            "Use captions/on-screen text so the message works in fast-scroll viewing.",
        ]

        video_scripts = [
            {
                "name": "Native problem/solution",
                "hook": hooks[1],
                "shots": [
                    "Open on the real customer need, not a logo screen.",
                    f"Show {product}.",
                    "Use a real demonstration or proof point.",
                    f"End with {cta}.",
                ],
                "on_screen_text": [
                    hooks[1],
                    offer_line,
                    cta,
                ],
            },
        ]

    elif campaign_type == "Demand Gen":
        formats = [
            "Prepare both video and image assets for Google's visual surfaces.",
            "Use strong opening frames and benefit-led messaging.",
            "Keep creative variations broad enough for visual inventory.",
        ]

        video_scripts = [
            {
                "name": "Discovery story",
                "hook": hooks[2],
                "shots": [
                    "Open with the customer situation.",
                    f"Introduce {product} naturally.",
                    "Show real product/service detail and proof.",
                    f"Close with {cta}.",
                ],
                "on_screen_text": [
                    product,
                    offer_line,
                    cta,
                ],
            },
        ]

    else:
        formats = [
            "Prepare diverse image and video assets for automated asset testing.",
            "Keep product, proof and offer assets separate so automation has meaningful combinations.",
            "Use real brand assets and avoid invented performance claims.",
        ]

    business_context = {
        "vertical": {
            "real_estate": "Real estate",
            "local_service": "Local service",
            "ecommerce": "E-commerce",
            "generic": "General business",
        }.get(vertical, "General business"),
        "location": location_hint,
        "subject": (
            _real_estate_subject(data)
            if vertical == "real_estate"
            else _short_service_name(product)
        ),
    }

    policy_note = ""

    if (
        vertical == "real_estate"
        and data.country.strip().lower()
        in {"united states", "usa", "us", "canada"}
    ):
        policy_note = (
            "Housing targeting rules are stricter in the United States and Canada. "
            "Do not build the launch plan around age, gender, parental status, marital status "
            "or ZIP-code targeting; re-check current Google Ads policy before launch."
        )

    return {
        "angles": angles,
        "formats": formats,
        "hooks": hooks,
        "headlines": headlines,
        "primary_texts": primary_texts,
        "descriptions": descriptions,
        "keyword_themes": keyword_themes,
        "negative_keyword_ideas": negative_keyword_ideas,
        "video_scripts": video_scripts,
        "search_pack": search_pack,
        "cta": cta,
        "business_context": business_context,
        "policy_note": policy_note,
        "safety_note": (
            "These are campaign drafts, not verified factual claims. "
            "Only publish prices, guarantees, credentials, testimonials, results or availability "
            "that the business can substantiate."
        ),
    }


def _economics(data, currency):
    objective = data.objective.strip().lower()

    result = {
        "available": False,
        "cards": [],
        "threshold_label": None,
        "note": (
            "Numeric business-economics thresholds require both order/customer value "
            "and gross margin."
        ),
    }

    if data.price <= 0 or data.gross_margin_percent <= 0:
        return result, 0, None

    margin_rate = data.gross_margin_percent / 100
    gross_profit = data.price * margin_rate

    extra_variable_cost = min(
        data.extra_variable_cost_per_order,
        gross_profit,
    )

    contribution_per_sale = max(
        gross_profit - extra_variable_cost,
        0,
    )

    contribution_margin_rate = (
        contribution_per_sale / data.price
        if data.price > 0
        else 0
    )

    cards = [
        {
            "label": "Gross profit / sale",
            "value": _round(gross_profit),
            "suffix": currency,
        },
        {
            "label": "Extra variable cost / sale",
            "value": _round(data.extra_variable_cost_per_order),
            "suffix": currency,
        },
        {
            "label": "Contribution / sale",
            "value": _round(contribution_per_sale),
            "suffix": currency,
        },
    ]

    result = {
        "available": True,
        "currency": currency,
        "price": _round(data.price),
        "gross_margin_percent": _round(data.gross_margin_percent),
        "extra_variable_cost_per_order": _round(
            data.extra_variable_cost_per_order
        ),
        "contribution_per_sale": _round(contribution_per_sale),
        "contribution_margin_percent": _round(
            contribution_margin_rate * 100
        ),
        "cards": cards,
        "threshold_label": None,
        "note": (
            "Planning thresholds use contribution margin after the extra variable "
            "cost entered by the user. They are not performance forecasts."
        ),
    }

    if contribution_per_sale <= 0:
        result["note"] = (
            "Contribution per sale is zero or negative after variable costs, "
            "so MarketFlow cannot recommend a paid-acquisition threshold yet."
        )
        return result, 0, None

    if objective == "sales":
        break_even_cpa = contribution_per_sale
        planning_target_cpa = break_even_cpa * 0.70
        break_even_roas = (
            1 / contribution_margin_rate
            if contribution_margin_rate > 0
            else 0
        )
        planning_target_roas = (
            break_even_roas / 0.70
            if break_even_roas > 0
            else 0
        )

        result["cards"].extend([
            {
                "label": "Break-even CPA",
                "value": _round(break_even_cpa),
                "suffix": currency,
            },
            {
                "label": "Planning CPA",
                "value": _round(planning_target_cpa),
                "suffix": currency,
            },
            {
                "label": "Break-even ROAS",
                "value": _round(break_even_roas),
                "suffix": "x",
            },
            {
                "label": "Planning ROAS",
                "value": _round(planning_target_roas),
                "suffix": "x",
            },
        ])

        result["threshold_label"] = "planning CPA"
        return (
            result,
            planning_target_cpa,
            "planning CPA",
        )

    if objective in {"leads", "messages"}:
        close_rate = (
            data.lead_to_sale_rate_percent / 100
        )

        if close_rate <= 0:
            result["note"] = (
                "Contribution per sale is available, but a lead/message-to-sale "
                "conversion rate is required before MarketFlow can calculate a "
                "break-even cost per lead or conversation."
            )
            return result, 0, None

        break_even_result_cost = (
            contribution_per_sale * close_rate
        )
        planning_result_cost = (
            break_even_result_cost * 0.70
        )

        unit = (
            "lead"
            if objective == "leads"
            else "conversation"
        )

        result["cards"].extend([
            {
                "label": "Lead/message → sale rate",
                "value": _round(
                    data.lead_to_sale_rate_percent
                ),
                "suffix": "%",
            },
            {
                "label": f"Break-even cost / {unit}",
                "value": _round(
                    break_even_result_cost
                ),
                "suffix": currency,
            },
            {
                "label": f"Planning cost / {unit}",
                "value": _round(
                    planning_result_cost
                ),
                "suffix": currency,
            },
        ])

        result["threshold_label"] = (
            f"planning cost per {unit}"
        )

        return (
            result,
            planning_result_cost,
            result["threshold_label"],
        )

    result["note"] = (
        "Contribution margin is calculated, but MarketFlow does not force a "
        "CPA/ROAS threshold for traffic or awareness because the selected "
        "objective is not the final business outcome."
    )

    return result, 0, None


def build_strategy(data):
    objective = data.objective.strip().lower()
    currency = data.currency.strip().upper()
    days = max(data.campaign_days, 1)
    daily_budget = data.total_budget / days

    business_profile = _business_profile(data)

    candidates = _score_candidates(data)
    candidates = _apply_business_profile_to_candidates(
        candidates,
        business_profile,
        data,
    )

    eligible = [item for item in candidates if item["eligible"]]

    if not eligible:
        raise HTTPException(
            status_code=400,
            detail="No launch-eligible campaign type could be selected from the current inputs.",
        )

    winner = eligible[0]
    runner_up = eligible[1] if len(eligible) > 1 else None

    automation = _automation_plan(winner, data)
    bidding = _bidding_plan(winner, data)
    economics, target_metric, target_metric_label = _economics(
        data,
        currency,
    )

    funnel = {
        "awareness": "Awareness",
        "traffic": "Consideration",
        "messages": "Conversion",
        "leads": "Conversion",
        "sales": "Conversion",
    }.get(objective, "Conversion")

    optimization = {
        "awareness": "Reach / qualified attention",
        "traffic": "Landing page views",
        "messages": "Messaging conversations",
        "leads": "Qualified leads",
        "sales": "Purchase / conversion value",
    }.get(objective, "Primary conversion")

    cta = {
        "awareness": "Learn More",
        "traffic": "Learn More",
        "messages": "Send Message",
        "leads": "Get Quote",
        "sales": "Shop Now",
    }.get(objective, "Learn More")

    why = list(winner["reasons"])

    if runner_up:
        why.append(
            f"{winner['campaign_type']} scored {winner['score']}/100 versus "
            f"{runner_up['campaign_type']} at {runner_up['score']}/100 on the current inputs."
        )

    why.append(
        "The first test is concentrated on one primary campaign type to reduce budget fragmentation "
        "and make learning easier to interpret."
    )

    if not data.has_previous_sales:
        why.append(
            "Because prior sales or qualified-lead history is limited, the plan prioritizes validation before scaling."
        )

    tracking = []
    sales_channel = data.sales_channel.strip().lower()

    if data.has_website:
        tracking.append(
            "Use UTMs on every ad and campaign link."
        )

        if data.has_tracking:
            tracking.append(
                "Verify the website conversion event and its value/parameters before launch."
            )
            tracking.append(
                "Where supported, add a server-side conversion signal so measurement "
                "is not dependent on browser tracking alone."
            )
        else:
            tracking.append(
                "Install and verify the relevant website conversion tracking before "
                "optimizing for website conversions."
            )

    if sales_channel == "phone":
        tracking.append(
            "Track phone calls as conversions, define what counts as a qualified call, "
            "and connect closed-sale outcomes back to the campaign where possible."
        )

    elif sales_channel in {
        "whatsapp",
        "messages",
        "dm",
        "direct messages",
    }:
        tracking.append(
            "Track messaging-conversation starts and record qualified/closed outcomes "
            "in a CRM or structured sales system."
        )

    elif sales_channel == "store":
        tracking.append(
            "Capture offline/store outcomes and import attributable conversions where "
            "the platform and account support it."
        )

    elif not data.has_website:
        tracking.append(
            "Record lead outcomes in a CRM or structured sheet so ad-platform results "
            "can be compared with real sales."
        )

    if objective == "sales":
        tracking.append(
            "Track purchase value, currency, order ID and refunds where the sales system supports them."
        )

        if winner["provider"] == "Google":
            tracking.append(
                "Send reliable conversion values before considering value-based bidding such as Target ROAS."
            )

    if objective in {"leads", "messages"}:
        tracking.append(
            "Track qualified results and closed sales, not only raw leads or conversations."
        )

    tracking.append(
        "Choose one reporting source of truth so conversions are not double-counted across platforms."
    )

    risks = []

    if data.has_website and objective in {"sales", "leads"} and not data.has_tracking:
        risks.append(
            "Website tracking is not confirmed, so conversion optimization and attribution are not launch-ready."
        )

    if not data.has_previous_sales:
        risks.append(
            "There is no confirmed performance baseline yet; validate the offer and creative before aggressive scaling."
        )

    if not data.offer.strip():
        risks.append(
            "No clear offer was provided. The campaign needs a concrete reason for the customer to act."
        )

    if (
        target_metric > 0
        and daily_budget < target_metric
    ):
        risks.append(
            f"Daily budget is below the {target_metric_label} threshold, "
            "so the campaign may generate fewer than one planned result per day "
            "and learning may be slow or noisy."
        )

    if (
        objective in {"leads", "messages"}
        and data.price > 0
        and data.gross_margin_percent > 0
        and data.lead_to_sale_rate_percent <= 0
    ):
        risks.append(
            "Lead/message-to-sale rate was not provided, so MarketFlow cannot "
            "calculate a financially grounded cost-per-lead/conversation threshold."
        )

    website_channel = data.sales_channel.strip().lower() == "website"

    if objective in {"sales", "traffic"} and website_channel and not data.has_website:
        risks.append(
            "The selected sales channel is a website, but no website was confirmed."
        )

    if not winner["eligible"]:
        risks.append(winner["availability_note"])

    launch_ready = True

    if objective == "sales" and data.has_website and not data.has_tracking:
        launch_ready = False

    if objective in {"sales", "traffic"} and website_channel and not data.has_website:
        launch_ready = False

    creative = _creative_plan(data, winner)
    creative["business_profile"] = business_profile

    audience_plan = [
        "Start with the stated core audience: " + data.audience.strip(),
        "Use geography that matches the real service or delivery area: " + data.country.strip(),
        automation["audience_approach"],
        "Use first-party exclusions/retargeting only when enough real data exists.",
    ]

    budget_plan = {
        "currency": currency,
        "total_budget": _round(data.total_budget),
        "campaign_days": days,
        "daily_budget": _round(daily_budget),
        "primary_channel_share_percent": 100,
        "primary_channel": winner["provider"],
        "primary_campaign_type": winner["campaign_type"],
        "secondary_channel": (
            f"{runner_up['provider']} — {runner_up['campaign_type']}"
            if runner_up
            else None
        ),
        "note": (
            "V2 recommendation: concentrate the first test on one primary campaign type. "
            "Add a second channel only after a useful baseline is established."
        ),
    }

    goal = _goal(data.objective)
    campaign_name = (
        f"{data.business_name.strip()} | {goal} | {winner['campaign_type']}"
    )[:120]

    campaign_draft = {
        "name": campaign_name,
        "product": data.product.strip(),
        "audience": data.audience.strip(),
        "country": data.country.strip(),
        "platform": winner["provider"],
        "budget": f"{_round(data.total_budget)} {currency} / {days} days",
        "goal": goal,
    }

    scorecard = [
        {
            "provider": item["provider"],
            "campaign_type": item["campaign_type"],
            "score": item["score"],
            "eligible": item["eligible"],
            "availability_note": item["availability_note"],
        }
        for item in candidates[:6]
    ]

    return {
        "version": ENGINE_VERSION,
        "capability_snapshot": CAPABILITY_SNAPSHOT,
        "engine": "Business understanding + candidate scoring + platform rules + business economics",
        "disclaimer": (
            "This is a planning recommendation based on the business inputs provided and a versioned "
            "platform-capability snapshot. It is not a guarantee of advertising performance. "
            "Market/account availability must be rechecked before launch."
        ),
        "business_profile": business_profile,
        "requested_objective": goal,
        "funnel_stage": funnel,
        "recommended_platform": winner["provider"],
        "recommended_campaign_type": winner["campaign_type"],
        "fit_score": winner["score"],
        "secondary_recommendation": (
            {
                "provider": runner_up["provider"],
                "campaign_type": runner_up["campaign_type"],
                "score": runner_up["score"],
            }
            if runner_up
            else None
        ),
        "optimization_event": optimization,
        "cta": cta,
        "automation_plan": {
            **automation,
            "bidding": bidding,
        },
        "availability_note": winner["availability_note"],
        "channel_scorecard": scorecard,
        "launch_readiness": (
            "Ready for draft creation"
            if launch_ready
            else "Setup required before launch"
        ),
        "why": why,
        "budget_plan": budget_plan,
        "economics": economics,
        "audience_plan": audience_plan,
        "creative_plan": creative,
        "tracking_checklist": tracking,
        "test_plan": {
            "principle": "Change one major variable at a time so the result is interpretable.",
            "creative_variants": 3,
            "test_order": [
                "Creative angle",
                "Offer / message",
                "Landing or lead experience",
                "Automation/bid controls only after enough real data exists",
                "Audience refinements only after enough data exists",
            ],
        },
        "risks": risks,
        "campaign_draft": campaign_draft,
    }


def register_strategy_engine(app, get_db, get_current_user):
    db = get_db()

    db.execute("""
        CREATE TABLE IF NOT EXISTS marketing_strategies (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            mode TEXT NOT NULL,
            input_json TEXT NOT NULL,
            output_json TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'Generated',
            campaign_id INTEGER,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )
    """)

    db.execute("""
        CREATE INDEX IF NOT EXISTS idx_marketing_strategies_user
        ON marketing_strategies(user_id, created_at)
    """)

    db.commit()
    db.close()

    router = APIRouter()

    @router.post("/api/strategy/generate")
    def generate_strategy(
        data: StrategyRequest,
        user=Depends(get_current_user),
    ):
        mode = data.mode.strip().lower()

        if mode not in {"guided", "quick"}:
            raise HTTPException(
                status_code=400,
                detail="mode must be guided or quick",
            )

        objective = data.objective.strip().lower()

        if objective not in {
            "sales",
            "leads",
            "messages",
            "traffic",
            "awareness",
        }:
            raise HTTPException(
                status_code=400,
                detail=(
                    "objective must be sales, leads, messages, "
                    "traffic or awareness"
                ),
            )

        result = build_strategy(data)
        now = datetime.utcnow().isoformat()
        db = get_db()

        cursor = db.execute("""
            INSERT INTO marketing_strategies (
                user_id,
                mode,
                input_json,
                output_json,
                status,
                campaign_id,
                created_at,
                updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            user["id"],
            mode,
            json.dumps(data.dict(), ensure_ascii=False),
            json.dumps(result, ensure_ascii=False),
            "Generated",
            None,
            now,
            now,
        ))

        db.commit()
        strategy_id = cursor.lastrowid
        db.close()

        return {
            "success": True,
            "strategy_id": strategy_id,
            "status": "Generated",
            "strategy": result,
        }

    @router.get("/api/strategy/latest")
    def latest_strategy(
        user=Depends(get_current_user),
    ):
        db = get_db()

        row = db.execute("""
            SELECT *
            FROM marketing_strategies
            WHERE user_id = ?
            ORDER BY id DESC
            LIMIT 1
        """, (
            user["id"],
        )).fetchone()

        db.close()

        if not row:
            return {
                "success": True,
                "strategy": None,
            }

        return {
            "success": True,
            "strategy": {
                "id": row["id"],
                "mode": row["mode"],
                "status": row["status"],
                "campaign_id": row["campaign_id"],
                "input": json.loads(row["input_json"]),
                "output": json.loads(row["output_json"]),
                "created_at": row["created_at"],
                "updated_at": row["updated_at"],
            },
        }

    @router.post("/api/strategy/{strategy_id}/accept")
    def accept_strategy(
        strategy_id: int,
        user=Depends(get_current_user),
    ):
        db = get_db()

        row = db.execute("""
            SELECT *
            FROM marketing_strategies
            WHERE id = ?
            AND user_id = ?
        """, (
            strategy_id,
            user["id"],
        )).fetchone()

        if not row:
            db.close()

            raise HTTPException(
                status_code=404,
                detail="Strategy not found",
            )

        if row["campaign_id"]:
            campaign = db.execute("""
                SELECT *
                FROM campaigns
                WHERE id = ?
                AND user_id = ?
            """, (
                row["campaign_id"],
                user["id"],
            )).fetchone()

            db.close()

            return {
                "success": True,
                "already_created": True,
                "campaign": (
                    dict(campaign)
                    if campaign
                    else None
                ),
            }

        output = json.loads(
            row["output_json"]
        )

        draft = output.get(
            "campaign_draft",
            {},
        )

        required = [
            "name",
            "product",
            "audience",
            "country",
            "platform",
            "budget",
            "goal",
        ]

        if any(
            not draft.get(key)
            for key in required
        ):
            db.close()

            raise HTTPException(
                status_code=500,
                detail="Strategy draft is incomplete",
            )

        now = datetime.utcnow().isoformat()

        cursor = db.execute("""
            INSERT INTO campaigns (
                user_id,
                name,
                product,
                audience,
                country,
                platform,
                budget,
                goal,
                status,
                created_at,
                updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            user["id"],
            draft["name"],
            draft["product"],
            draft["audience"],
            draft["country"],
            draft["platform"],
            draft["budget"],
            draft["goal"],
            "Draft",
            now,
            now,
        ))

        campaign_id = cursor.lastrowid

        db.execute("""
            UPDATE marketing_strategies
            SET
                status = 'Accepted',
                campaign_id = ?,
                updated_at = ?
            WHERE id = ?
            AND user_id = ?
        """, (
            campaign_id,
            now,
            strategy_id,
            user["id"],
        ))

        db.commit()

        campaign = db.execute("""
            SELECT *
            FROM campaigns
            WHERE id = ?
            AND user_id = ?
        """, (
            campaign_id,
            user["id"],
        )).fetchone()

        db.close()

        return {
            "success": True,
            "already_created": False,
            "campaign": dict(campaign),
        }

    app.include_router(router)
