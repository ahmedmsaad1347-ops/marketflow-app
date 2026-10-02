import os
import sqlite3
from datetime import datetime

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

load_dotenv()

DATABASE = "marketflow.db"

app = FastAPI(
    title="MarketFlow API",
    version="1.1.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=True,
    allow_methods=["GET", "POST", "DELETE"],
    allow_headers=["Content-Type", "Authorization"],
)


def get_db():
    connection = sqlite3.connect(DATABASE)
    connection.row_factory = sqlite3.Row
    return connection


def init_db():
    db = get_db()

    db.execute("""
        CREATE TABLE IF NOT EXISTS campaigns (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            product TEXT NOT NULL,
            audience TEXT NOT NULL,
            country TEXT NOT NULL,
            platform TEXT NOT NULL,
            budget TEXT NOT NULL,
            goal TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'Draft',
            created_at TEXT NOT NULL
        )
    """)

    db.commit()
    db.close()


init_db()


class CampaignData(BaseModel):
    name: str
    product: str
    audience: str
    country: str
    platform: str
    budget: str
    goal: str


class AIRequest(BaseModel):
    prompt: str = Field(min_length=1, max_length=4000)


@app.get("/api/health")
def health():
    return {
        "success": True,
        "service": "MarketFlow Python API",
        "database": "online",
        "status": "online"
    }


@app.post("/api/campaigns/preview")
def campaign_preview(campaign: CampaignData):
    return {
        "success": True,
        "campaign": {
            **campaign.dict(),
            "status": "Draft",
            "readyToReview": True
        }
    }


@app.post("/api/campaigns")
def create_campaign(campaign: CampaignData):
    db = get_db()

    cursor = db.execute("""
        INSERT INTO campaigns (
            name,
            product,
            audience,
            country,
            platform,
            budget,
            goal,
            status,
            created_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        campaign.name,
        campaign.product,
        campaign.audience,
        campaign.country,
        campaign.platform,
        campaign.budget,
        campaign.goal,
        "Draft",
        datetime.utcnow().isoformat()
    ))

    db.commit()

    campaign_id = cursor.lastrowid

    row = db.execute(
        "SELECT * FROM campaigns WHERE id = ?",
        (campaign_id,)
    ).fetchone()

    db.close()

    return {
        "success": True,
        "campaign": dict(row)
    }


@app.get("/api/campaigns")
def get_campaigns():
    db = get_db()

    rows = db.execute("""
        SELECT *
        FROM campaigns
        ORDER BY id DESC
    """).fetchall()

    db.close()

    return {
        "success": True,
        "campaigns": [dict(row) for row in rows]
    }


@app.get("/api/campaigns/{campaign_id}")
def get_campaign(campaign_id: int):
    db = get_db()

    row = db.execute(
        "SELECT * FROM campaigns WHERE id = ?",
        (campaign_id,)
    ).fetchone()

    db.close()

    if not row:
        raise HTTPException(
            status_code=404,
            detail="Campaign not found"
        )

    return {
        "success": True,
        "campaign": dict(row)
    }


@app.delete("/api/campaigns/{campaign_id}")
def delete_campaign(campaign_id: int):
    db = get_db()

    cursor = db.execute(
        "DELETE FROM campaigns WHERE id = ?",
        (campaign_id,)
    )

    db.commit()
    deleted = cursor.rowcount
    db.close()

    if not deleted:
        raise HTTPException(
            status_code=404,
            detail="Campaign not found"
        )

    return {
        "success": True
    }


@app.post("/api/ai/generate")
def ai_generate(request: AIRequest):
    if not os.getenv("OPENAI_API_KEY"):
        raise HTTPException(
            status_code=503,
            detail="AI is ready but API billing/key is not configured yet."
        )

    raise HTTPException(
        status_code=501,
        detail="AI provider will be activated when API access is configured."
    )


@app.get("/")
def root():
    return {
        "name": "MarketFlow Backend",
        "status": "running"
    }
