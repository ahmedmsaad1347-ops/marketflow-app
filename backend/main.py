import os

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

load_dotenv()

app = FastAPI(
    title="MarketFlow API",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type", "Authorization"],
)

class CampaignPreview(BaseModel):
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
        "status": "online"
    }

@app.post("/api/campaigns/preview")
def campaign_preview(campaign: CampaignPreview):
    return {
        "success": True,
        "campaign": {
            **campaign.dict(),
            "status": "Draft",
            "readyToReview": True
        }
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
