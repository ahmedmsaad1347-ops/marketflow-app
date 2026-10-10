
import json
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from backend.strategy_engine import StrategyRequest, build_strategy


class AgentAnswer(BaseModel):
    value: object = None


QUESTION_ORDER = [
    "business_name",
    "product",
    "offer",
    "country",
    "audience",
    "objective",
    "demand_type",
    "sales_channel",
    "currency",
    "total_budget",
    "campaign_days",
    "price",
    "gross_margin_percent",
    "extra_variable_cost_per_order",
    "lead_to_sale_rate_percent",
    "has_website",
    "has_tracking",
    "has_previous_sales",
    "has_video_creatives",
]


def _question_for(key, state):
    business = state.get("business_name") or "your business"
    objective = state.get("objective", "")

    questions = {
        "business_name": {
            "label": "What is your business or brand name?",
            "type": "text",
            "placeholder": "Example: FlowDesk AI",
        },
        "product": {
            "label": "What do you actually sell? Describe the product or service clearly.",
            "type": "text",
            "placeholder": "Example: AI customer support software for small online businesses",
        },
        "offer": {
            "label": "What offer should customers see right now?",
            "type": "text",
            "placeholder": "Example: 14-day free trial with no credit card",
            "optional": True,
        },
        "country": {
            "label": f"Which country or market should {business} target first?",
            "type": "text",
            "placeholder": "Example: United States",
        },
        "audience": {
            "label": "Who is the ideal customer? Tell me who buys and what problem they are trying to solve.",
            "type": "text",
            "placeholder": "Example: e-commerce owners and support managers with 5-50 employees",
        },
        "objective": {
            "label": "What business result matters most for this campaign?",
            "type": "choice",
            "options": [
                {"label": "Sales", "value": "sales"},
                {"label": "Qualified leads", "value": "leads"},
                {"label": "Messages", "value": "messages"},
                {"label": "Website traffic", "value": "traffic"},
                {"label": "Awareness", "value": "awareness"},
            ],
        },
        "demand_type": {
            "label": "How does demand behave? This changes which channel I should prioritize.",
            "type": "choice",
            "options": [
                {"label": "People actively search for it", "value": "search"},
                {"label": "People mostly discover it in content/ads", "value": "discovery"},
                {"label": "Both / not sure", "value": "mixed"},
            ],
        },
        "sales_channel": {
            "label": "Where does the real conversion happen?",
            "type": "choice",
            "options": [
                {"label": "Website", "value": "website"},
                {"label": "WhatsApp / messages", "value": "whatsapp"},
                {"label": "Phone call", "value": "phone"},
                {"label": "Physical store", "value": "store"},
            ],
        },
        "currency": {
            "label": "Which currency should I use for the plan?",
            "type": "choice",
            "options": [
                {"label": "EGP", "value": "EGP"},
                {"label": "USD", "value": "USD"},
                {"label": "SAR", "value": "SAR"},
                {"label": "AED", "value": "AED"},
                {"label": "EUR", "value": "EUR"},
                {"label": "GBP", "value": "GBP"},
            ],
        },
        "total_budget": {
            "label": "What is the total paid-media budget for this test?",
            "type": "number",
            "placeholder": "Example: 5000",
        },
        "campaign_days": {
            "label": "How long should the first test run?",
            "type": "choice",
            "options": [
                {"label": "7 days", "value": 7},
                {"label": "14 days", "value": 14},
                {"label": "30 days", "value": 30},
                {"label": "60 days", "value": 60},
                {"label": "90 days", "value": 90},
            ],
        },
        "price": {
            "label": "What is one customer, order, booking or contract worth?",
            "type": "number",
            "placeholder": "Enter 0 if you do not know yet",
            "optional": True,
        },
        "gross_margin_percent": {
            "label": "What is the approximate gross margin %?",
            "type": "number",
            "placeholder": "Example: 80",
            "optional": True,
        },
        "extra_variable_cost_per_order": {
            "label": "Any extra variable cost per sale beyond gross margin?",
            "type": "number",
            "placeholder": "Enter 0 if none / unknown",
            "optional": True,
        },
        "lead_to_sale_rate_percent": {
            "label": "Roughly what % of leads/messages become paying customers?",
            "type": "number",
            "placeholder": "Example: 12",
            "optional": True,
        },
        "has_website": {
            "label": "Do you have a usable website or landing page?",
            "type": "boolean",
        },
        "has_tracking": {
            "label": "Is conversion tracking already verified?",
            "type": "boolean",
        },
        "has_previous_sales": {
            "label": "Does this offer already have real sales or qualified-lead history?",
            "type": "boolean",
        },
        "has_video_creatives": {
            "label": "Do you have usable vertical video creative?",
            "type": "boolean",
        },
    }

    question = dict(questions[key])

    if key == "lead_to_sale_rate_percent" and objective not in {"leads", "messages"}:
        question["skip"] = True

    return question


def _coerce(key, value):
    if key in {
        "total_budget",
        "price",
        "gross_margin_percent",
        "extra_variable_cost_per_order",
        "lead_to_sale_rate_percent",
    }:
        try:
            return float(value or 0)
        except Exception:
            raise HTTPException(status_code=400, detail="Please enter a valid number.")

    if key == "campaign_days":
        try:
            return int(value)
        except Exception:
            raise HTTPException(status_code=400, detail="Please choose a valid campaign duration.")

    if key in {
        "has_website",
        "has_tracking",
        "has_previous_sales",
        "has_video_creatives",
    }:
        if isinstance(value, bool):
            return value
        return str(value).strip().lower() in {"true", "1", "yes", "y"}

    return str(value or "").strip()


def _next_key(state):
    for key in QUESTION_ORDER:
        if key in state:
            continue

        question = _question_for(key, state)

        if question.get("skip"):
            state[key] = 0
            continue

        return key

    return None


def _agent_summary(strategy):
    profile = strategy.get("business_profile") or {}
    campaign = strategy.get("recommended_campaign_type") or "campaign"
    platform = strategy.get("recommended_platform") or ""
    fit = strategy.get("fit_score") or 0

    identity = profile.get("vertical") or "business"
    target = profile.get("target_industry") or ""

    text = f"I understand this as {identity}"
    if target:
        text += f" selling into {target}"

    return (
        text
        + f". I selected {platform} {campaign} as the primary test "
        + f"with a fit score of {fit}/100."
    )


def register_strategy_agent(app, get_db, get_current_user):
    db = get_db()

    db.execute("""
        CREATE TABLE IF NOT EXISTS strategy_agent_sessions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            state_json TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'Active',
            strategy_id INTEGER,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )
    """)

    db.execute("""
        CREATE INDEX IF NOT EXISTS idx_strategy_agent_user
        ON strategy_agent_sessions(user_id, id)
    """)

    db.commit()
    db.close()

    router = APIRouter()

    @router.post("/api/strategy-agent/start")
    def start_agent(user=Depends(get_current_user)):
        now = datetime.utcnow().isoformat()
        state = {"mode": "guided"}

        db = get_db()
        cursor = db.execute("""
            INSERT INTO strategy_agent_sessions (
                user_id, state_json, status, strategy_id, created_at, updated_at
            )
            VALUES (?, ?, 'Active', NULL, ?, ?)
        """, (
            user["id"],
            json.dumps(state, ensure_ascii=False),
            now,
            now,
        ))
        db.commit()
        session_id = cursor.lastrowid
        db.close()

        key = _next_key(state)

        return {
            "success": True,
            "session_id": session_id,
            "message": (
                "I will build the strategy with you. "
                "I will only ask for information that changes the marketing decision."
            ),
            "question": {
                "key": key,
                **_question_for(key, state),
            },
        }

    @router.post("/api/strategy-agent/{session_id}/answer")
    def answer_agent(
        session_id: int,
        answer: AgentAnswer,
        user=Depends(get_current_user),
    ):
        db = get_db()

        row = db.execute("""
            SELECT *
            FROM strategy_agent_sessions
            WHERE id = ?
            AND user_id = ?
        """, (
            session_id,
            user["id"],
        )).fetchone()

        if not row:
            db.close()
            raise HTTPException(status_code=404, detail="Agent session not found.")

        if row["status"] != "Active":
            db.close()
            raise HTTPException(status_code=400, detail="This agent session is already complete.")

        state = json.loads(row["state_json"])
        key = _next_key(state)

        if not key:
            db.close()
            raise HTTPException(status_code=400, detail="No pending question.")

        question = _question_for(key, state)
        value = _coerce(key, answer.value)

        if not question.get("optional"):
            if key == "total_budget" and float(value or 0) <= 0:
                db.close()
                raise HTTPException(status_code=400, detail="Budget must be greater than zero.")
            if isinstance(value, str) and not value:
                db.close()
                raise HTTPException(status_code=400, detail="This answer is required.")

        state[key] = value
        next_key = _next_key(state)
        now = datetime.utcnow().isoformat()

        if next_key:
            db.execute("""
                UPDATE strategy_agent_sessions
                SET state_json = ?, updated_at = ?
                WHERE id = ? AND user_id = ?
            """, (
                json.dumps(state, ensure_ascii=False),
                now,
                session_id,
                user["id"],
            ))
            db.commit()
            db.close()

            return {
                "success": True,
                "session_id": session_id,
                "complete": False,
                "question": {
                    "key": next_key,
                    **_question_for(next_key, state),
                },
            }

        defaults = {
            "offer": "",
            "price": 0,
            "gross_margin_percent": 0,
            "extra_variable_cost_per_order": 0,
            "lead_to_sale_rate_percent": 0,
            "has_website": False,
            "has_tracking": False,
            "has_previous_sales": False,
            "has_video_creatives": False,
            "notes": "Generated through MarketFlow Strategy Agent V1.",
        }

        payload = {**defaults, **state}
        payload["mode"] = "guided"

        try:
            request = StrategyRequest(**payload)
            result = build_strategy(request)
        except Exception as exc:
            db.close()
            detail = getattr(exc, "detail", None) or str(exc)
            raise HTTPException(status_code=400, detail=detail)

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
            "agent",
            json.dumps(request.dict(), ensure_ascii=False),
            json.dumps(result, ensure_ascii=False),
            "Generated",
            None,
            now,
            now,
        ))

        strategy_id = cursor.lastrowid

        db.execute("""
            UPDATE strategy_agent_sessions
            SET state_json = ?, status = 'Complete', strategy_id = ?, updated_at = ?
            WHERE id = ? AND user_id = ?
        """, (
            json.dumps(state, ensure_ascii=False),
            strategy_id,
            now,
            session_id,
            user["id"],
        ))

        db.commit()
        db.close()

        return {
            "success": True,
            "session_id": session_id,
            "complete": True,
            "strategy_id": strategy_id,
            "status": "Generated",
            "agent_summary": _agent_summary(result),
            "strategy": result,
        }

    app.include_router(router)
