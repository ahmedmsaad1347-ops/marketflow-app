import json
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field


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


def _platform(data):
    objective = data.objective.strip().lower()
    demand = data.demand_type.strip().lower()
    channel = data.sales_channel.strip().lower()

    primary = "Meta (Facebook + Instagram)"
    campaign_platform = "Multiple platforms"
    secondary = None
    why = []

    if objective == "messages":
        why.append(
            "Meta is prioritized because the requested action is a direct customer conversation."
        )

    elif objective == "leads":
        if demand == "search" and data.has_website:
            primary = "Google Search"
            campaign_platform = "Google"
            why.append(
                "Google Search is prioritized because customers actively search for the offer and a website is available."
            )
        else:
            primary = "Meta Lead Generation"
            campaign_platform = "Facebook"
            why.append(
                "Meta lead generation is prioritized because it can capture demand without requiring high search intent."
            )

    elif objective == "sales":
        if channel in {"whatsapp", "messages", "dm", "direct messages"} or not data.has_website:
            why.append(
                "Meta is prioritized because the sales path depends on conversations or there is no website checkout."
            )
        elif demand == "search":
            primary = "Google Search"
            campaign_platform = "Google"
            why.append(
                "Google Search is prioritized because the product has active search demand and customers can convert on the website."
            )
        elif demand == "discovery" and data.has_video_creatives:
            primary = "TikTok"
            campaign_platform = "TikTok"
            why.append(
                "TikTok is prioritized because the product is discovery-led and usable video creative is available."
            )
        else:
            why.append(
                "Meta is prioritized as the first sales test because it supports visual discovery, retargeting, and conversion campaigns."
            )

    elif objective == "traffic":
        if demand == "search" and data.has_website:
            primary = "Google Search"
            campaign_platform = "Google"
            why.append(
                "Google Search is prioritized because the audience already expresses intent through search."
            )
        else:
            why.append(
                "Meta is prioritized because discovery is more important than search intent for this first traffic test."
            )

    elif objective == "awareness":
        if data.has_video_creatives:
            primary = "TikTok"
            campaign_platform = "TikTok"
            why.append(
                "TikTok is prioritized for awareness because short-form video creative is already available."
            )
        else:
            why.append(
                "Meta is prioritized for awareness because the current creative setup does not depend on short-form video."
            )

    if primary == "Google Search" and data.has_website:
        secondary = "Meta retargeting after enough qualified traffic is collected."
    elif primary.startswith("Meta") and demand in {"search", "mixed"} and data.has_website:
        secondary = "Google Search after the first offer and conversion baseline is validated."
    elif primary == "TikTok":
        secondary = "Meta after a winning creative angle is identified."

    return primary, campaign_platform, secondary, why


def build_strategy(data):
    objective = data.objective.strip().lower()
    currency = data.currency.strip().upper()
    days = max(data.campaign_days, 1)

    primary, campaign_platform, secondary, why = _platform(data)

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
        "sales": "Purchase",
    }.get(objective, "Primary conversion")

    cta = {
        "awareness": "Learn More",
        "traffic": "Learn More",
        "messages": "Send Message",
        "leads": "Get Quote",
        "sales": "Shop Now",
    }.get(objective, "Learn More")

    daily_budget = data.total_budget / days
    target_cpa = 0

    economics = {
        "available": False,
        "note": "Numeric CPA/ROAS planning thresholds require both price and gross margin.",
    }

    if data.price > 0 and data.gross_margin_percent > 0:
        margin_rate = data.gross_margin_percent / 100
        gross_profit = data.price * margin_rate
        break_even_cpa = gross_profit
        target_cpa = break_even_cpa * 0.70
        break_even_roas = 1 / margin_rate
        target_roas = break_even_roas / 0.70

        economics = {
            "available": True,
            "currency": currency,
            "price": _round(data.price),
            "gross_margin_percent": _round(data.gross_margin_percent),
            "gross_profit_per_order": _round(gross_profit),
            "break_even_cpa": _round(break_even_cpa),
            "planning_target_cpa": _round(target_cpa),
            "break_even_roas": _round(break_even_roas),
            "planning_target_roas": _round(target_roas),
            "note": (
                "Planning thresholds, not a performance forecast. Replace them with real contribution-margin "
                "and conversion data when available."
            ),
        }

    tracking = []
    risks = []

    if data.has_website:
        tracking.append("Use UTMs on every ad and campaign link.")
        if data.has_tracking:
            tracking.append(
                "Verify the platform pixel/tag fires on the real conversion event before launch."
            )
        else:
            tracking.append(
                "Install and verify platform tracking before optimizing for website conversions."
            )
            risks.append(
                "Website tracking is not confirmed, so conversion optimization and attribution are not launch-ready."
            )
    else:
        tracking.append(
            "Use platform lead/message tracking and record lead outcomes in a CRM or structured sheet."
        )

    if objective == "sales":
        tracking.append(
            "Track Purchase value, currency, order ID, and refunds where the sales system supports them."
        )
    if objective == "leads":
        tracking.append(
            "Track lead quality and closed sales, not only form submissions."
        )

    tracking.append(
        "Choose one reporting source of truth so conversions are not double-counted across platforms."
    )

    if not data.has_previous_sales:
        risks.append(
            "There is no confirmed sales baseline yet; validate the offer and creative before aggressive scaling."
        )
    if not data.offer.strip():
        risks.append(
            "No clear offer was provided. The campaign needs a concrete reason for the customer to act."
        )
    if target_cpa > 0 and daily_budget < target_cpa:
        risks.append(
            "Daily budget is below the planning target CPA, so learning may be slow and results may be noisy."
        )

    website_channel = data.sales_channel.strip().lower() == "website"
    if objective in {"sales", "traffic"} and website_channel and not data.has_website:
        risks.append(
            "The selected sales channel is a website, but no website was confirmed."
        )

    launch_ready = True
    if objective == "sales" and data.has_website and not data.has_tracking:
        launch_ready = False
    if objective in {"sales", "traffic"} and website_channel and not data.has_website:
        launch_ready = False

    audience_plan = [
        "Start with the stated core audience: " + data.audience.strip(),
        "Use geography that matches the real service or delivery area: " + data.country.strip(),
        "Avoid adding narrow interests unless there is evidence they improve qualified conversions.",
        "Build retargeting only after enough real visitors, leads, or engagers exist.",
    ]

    creative_angles = [
        {
            "name": "Problem → Solution",
            "idea": (
                f"Show the problem faced by {data.audience.strip()}, then demonstrate how "
                f"{data.product.strip()} solves it."
            ),
        },
        {
            "name": "Proof",
            "idea": (
                "Use real demonstrations, customer proof, or evidence that can be substantiated. "
                "Avoid invented claims."
            ),
        },
        {
            "name": "Offer",
            "idea": (
                data.offer.strip()
                if data.offer.strip()
                else "Make the value and next step clear, then strengthen the offer before scaling spend."
            ),
        },
    ]

    formats = (
        ["Short vertical video", "Product/service demonstration", "Customer proof or testimonial"]
        if data.has_video_creatives
        else ["Static benefit-led creative", "Simple product/service demonstration", "Proof-focused creative"]
    )

    budget_plan = {
        "currency": currency,
        "total_budget": _round(data.total_budget),
        "campaign_days": days,
        "daily_budget": _round(daily_budget),
        "primary_channel_share_percent": 100,
        "primary_channel": primary,
        "secondary_channel": secondary,
        "note": (
            "MVP recommendation: concentrate the first test on one primary channel. "
            "Add a second channel only after a useful baseline is established."
        ),
    }

    why.append(
        "The first test is concentrated on one primary channel to reduce budget fragmentation and make learning easier to interpret."
    )
    if not data.has_previous_sales:
        why.append(
            "Because prior sales data is limited or unavailable, the plan prioritizes validation before scaling."
        )

    goal = _goal(data.objective)
    campaign_name = f"{data.business_name.strip()} | {goal} | {primary}"[:120]

    campaign_draft = {
        "name": campaign_name,
        "product": data.product.strip(),
        "audience": data.audience.strip(),
        "country": data.country.strip(),
        "platform": campaign_platform,
        "budget": f"{_round(data.total_budget)} {currency} / {days} days",
        "goal": goal,
    }

    return {
        "version": "strategy-mvp-1",
        "engine": "Rules + business economics",
        "disclaimer": (
            "This is a planning recommendation based on the business inputs provided. "
            "It is not a guarantee of advertising performance."
        ),
        "requested_objective": goal,
        "funnel_stage": funnel,
        "recommended_platform": primary,
        "secondary_platform": secondary,
        "optimization_event": optimization,
        "cta": cta,
        "launch_readiness": (
            "Ready for draft creation" if launch_ready else "Setup required before launch"
        ),
        "why": why,
        "budget_plan": budget_plan,
        "economics": economics,
        "audience_plan": audience_plan,
        "creative_plan": {
            "angles": creative_angles,
            "formats": formats,
            "cta": cta,
        },
        "tracking_checklist": tracking,
        "test_plan": {
            "principle": "Change one major variable at a time so the result is interpretable.",
            "creative_variants": 3,
            "test_order": [
                "Creative angle",
                "Offer / message",
                "Landing or lead experience",
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
    def generate_strategy(data: StrategyRequest, user=Depends(get_current_user)):
        mode = data.mode.strip().lower()
        if mode not in {"guided", "quick"}:
            raise HTTPException(status_code=400, detail="mode must be guided or quick")

        objective = data.objective.strip().lower()
        if objective not in {"sales", "leads", "messages", "traffic", "awareness"}:
            raise HTTPException(
                status_code=400,
                detail="objective must be sales, leads, messages, traffic or awareness",
            )

        result = build_strategy(data)
        now = datetime.utcnow().isoformat()
        db = get_db()
        cursor = db.execute("""
            INSERT INTO marketing_strategies (
                user_id, mode, input_json, output_json,
                status, campaign_id, created_at, updated_at
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
    def latest_strategy(user=Depends(get_current_user)):
        db = get_db()
        row = db.execute("""
            SELECT * FROM marketing_strategies
            WHERE user_id = ?
            ORDER BY id DESC
            LIMIT 1
        """, (user["id"],)).fetchone()
        db.close()

        if not row:
            return {"success": True, "strategy": None}

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
    def accept_strategy(strategy_id: int, user=Depends(get_current_user)):
        db = get_db()
        row = db.execute("""
            SELECT * FROM marketing_strategies
            WHERE id = ? AND user_id = ?
        """, (strategy_id, user["id"])).fetchone()

        if not row:
            db.close()
            raise HTTPException(status_code=404, detail="Strategy not found")

        if row["campaign_id"]:
            campaign = db.execute("""
                SELECT * FROM campaigns
                WHERE id = ? AND user_id = ?
            """, (row["campaign_id"], user["id"])).fetchone()
            db.close()
            return {
                "success": True,
                "already_created": True,
                "campaign": dict(campaign) if campaign else None,
            }

        output = json.loads(row["output_json"])
        draft = output.get("campaign_draft", {})
        required = ["name", "product", "audience", "country", "platform", "budget", "goal"]
        if any(not draft.get(key) for key in required):
            db.close()
            raise HTTPException(status_code=500, detail="Strategy draft is incomplete")

        now = datetime.utcnow().isoformat()
        cursor = db.execute("""
            INSERT INTO campaigns (
                user_id, name, product, audience, country,
                platform, budget, goal, status, created_at, updated_at
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
            SET status = 'Accepted', campaign_id = ?, updated_at = ?
            WHERE id = ? AND user_id = ?
        """, (campaign_id, now, strategy_id, user["id"]))
        db.commit()

        campaign = db.execute("""
            SELECT * FROM campaigns
            WHERE id = ? AND user_id = ?
        """, (campaign_id, user["id"])).fetchone()
        db.close()

        return {
            "success": True,
            "already_created": False,
            "campaign": dict(campaign),
        }

    app.include_router(router)
