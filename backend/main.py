import os
import sqlite3
import secrets
import hashlib
import hmac
import base64

from datetime import datetime, timedelta

from dotenv import load_dotenv
from fastapi import (
    FastAPI,
    HTTPException,
    Request,
    Response,
    Depends
)
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

load_dotenv()

DATABASE = "marketflow.db"
SESSION_COOKIE = "marketflow_session"
SESSION_DAYS = 30

app = FastAPI(
    title="MarketFlow API",
    version="1.2.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"]
)


def get_db():
    db = sqlite3.connect(DATABASE)
    db.row_factory = sqlite3.Row
    return db


def init_db():
    db = get_db()

    db.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            password_salt TEXT NOT NULL,
            created_at TEXT NOT NULL
        )
    """)

    db.execute("""
        CREATE TABLE IF NOT EXISTS sessions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            token_hash TEXT UNIQUE NOT NULL,
            expires_at TEXT NOT NULL,
            created_at TEXT NOT NULL
        )
    """)

    db.execute("""
        CREATE TABLE IF NOT EXISTS campaigns (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
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

    columns = [
        row["name"]
        for row in db.execute(
            "PRAGMA table_info(campaigns)"
        ).fetchall()
    ]

    if "user_id" not in columns:
        db.execute(
            "ALTER TABLE campaigns ADD COLUMN user_id INTEGER"
        )

    db.commit()
    db.close()


init_db()


def hash_password(password, salt=None):
    if salt is None:
        salt_bytes = secrets.token_bytes(32)
        salt = base64.urlsafe_b64encode(
            salt_bytes
        ).decode()
    else:
        salt_bytes = base64.urlsafe_b64decode(
            salt.encode()
        )

    result = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode(),
        salt_bytes,
        250000
    )

    password_hash = base64.urlsafe_b64encode(
        result
    ).decode()

    return password_hash, salt


def verify_password(password, stored_hash, salt):
    calculated_hash, _ = hash_password(
        password,
        salt
    )

    return hmac.compare_digest(
        calculated_hash,
        stored_hash
    )


def hash_session_token(token):
    return hashlib.sha256(
        token.encode()
    ).hexdigest()


def create_session(db, user_id):
    token = secrets.token_urlsafe(48)

    token_hash = hash_session_token(token)

    now = datetime.utcnow()

    expires = now + timedelta(
        days=SESSION_DAYS
    )

    db.execute("""
        INSERT INTO sessions (
            user_id,
            token_hash,
            expires_at,
            created_at
        )
        VALUES (?, ?, ?, ?)
    """, (
        user_id,
        token_hash,
        expires.isoformat(),
        now.isoformat()
    ))

    db.commit()

    return token


def set_session_cookie(response, token):
    response.set_cookie(
        key=SESSION_COOKIE,
        value=token,
        httponly=True,
        samesite="lax",
        secure=False,
        max_age=60 * 60 * 24 * SESSION_DAYS,
        path="/"
    )


def get_current_user(request: Request):
    token = request.cookies.get(
        SESSION_COOKIE
    )

    if not token:
        raise HTTPException(
            status_code=401,
            detail="Not authenticated"
        )

    token_hash = hash_session_token(token)

    db = get_db()

    row = db.execute("""
        SELECT
            users.id,
            users.name,
            users.email,
            sessions.expires_at
        FROM sessions
        JOIN users
        ON users.id = sessions.user_id
        WHERE sessions.token_hash = ?
    """, (token_hash,)).fetchone()

    db.close()

    if not row:
        raise HTTPException(
            status_code=401,
            detail="Invalid session"
        )

    if datetime.fromisoformat(
        row["expires_at"]
    ) < datetime.utcnow():

        raise HTTPException(
            status_code=401,
            detail="Session expired"
        )

    return {
        "id": row["id"],
        "name": row["name"],
        "email": row["email"]
    }


class SignupData(BaseModel):
    name: str = Field(
        min_length=2,
        max_length=80
    )

    email: str = Field(
        min_length=5,
        max_length=150
    )

    password: str = Field(
        min_length=8,
        max_length=128
    )


class LoginData(BaseModel):
    email: str
    password: str


class CampaignData(BaseModel):
    name: str
    product: str
    audience: str
    country: str
    platform: str
    budget: str
    goal: str


class AIRequest(BaseModel):
    prompt: str = Field(
        min_length=1,
        max_length=4000
    )


@app.get("/api/health")
def health():
    return {
        "success": True,
        "service": "MarketFlow Python API",
        "database": "online",
        "auth": "online",
        "status": "online"
    }


@app.post("/api/auth/signup")
def signup(
    data: SignupData,
    response: Response
):
    email = data.email.strip().lower()
    name = data.name.strip()

    db = get_db()

    exists = db.execute(
        "SELECT id FROM users WHERE email = ?",
        (email,)
    ).fetchone()

    if exists:
        db.close()

        raise HTTPException(
            status_code=409,
            detail="Email already registered"
        )

    password_hash, salt = hash_password(
        data.password
    )

    cursor = db.execute("""
        INSERT INTO users (
            name,
            email,
            password_hash,
            password_salt,
            created_at
        )
        VALUES (?, ?, ?, ?, ?)
    """, (
        name,
        email,
        password_hash,
        salt,
        datetime.utcnow().isoformat()
    ))

    user_id = cursor.lastrowid

    db.commit()

    token = create_session(
        db,
        user_id
    )

    db.close()

    set_session_cookie(
        response,
        token
    )

    return {
        "success": True,
        "user": {
            "id": user_id,
            "name": name,
            "email": email
        }
    }


@app.post("/api/auth/login")
def login(
    data: LoginData,
    response: Response
):
    email = data.email.strip().lower()

    db = get_db()

    user = db.execute("""
        SELECT *
        FROM users
        WHERE email = ?
    """, (email,)).fetchone()

    if not user:
        db.close()

        raise HTTPException(
            status_code=401,
            detail="Invalid email or password"
        )

    if not verify_password(
        data.password,
        user["password_hash"],
        user["password_salt"]
    ):
        db.close()

        raise HTTPException(
            status_code=401,
            detail="Invalid email or password"
        )

    token = create_session(
        db,
        user["id"]
    )

    db.close()

    set_session_cookie(
        response,
        token
    )

    return {
        "success": True,
        "user": {
            "id": user["id"],
            "name": user["name"],
            "email": user["email"]
        }
    }


@app.get("/api/auth/me")
def auth_me(
    user=Depends(get_current_user)
):
    return {
        "success": True,
        "user": user
    }


@app.post("/api/auth/logout")
def logout(
    request: Request,
    response: Response
):
    token = request.cookies.get(
        SESSION_COOKIE
    )

    if token:
        db = get_db()

        db.execute(
            "DELETE FROM sessions WHERE token_hash = ?",
            (hash_session_token(token),)
        )

        db.commit()
        db.close()

    response.delete_cookie(
        SESSION_COOKIE,
        path="/"
    )

    return {
        "success": True
    }


@app.post("/api/campaigns/preview")
def campaign_preview(
    campaign: CampaignData,
    user=Depends(get_current_user)
):
    return {
        "success": True,
        "campaign": {
            **campaign.dict(),
            "status": "Draft",
            "readyToReview": True
        }
    }


@app.post("/api/campaigns")
def create_campaign(
    campaign: CampaignData,
    user=Depends(get_current_user)
):
    db = get_db()

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
            created_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        user["id"],
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

    row = db.execute("""
        SELECT *
        FROM campaigns
        WHERE id = ?
        AND user_id = ?
    """, (
        campaign_id,
        user["id"]
    )).fetchone()

    db.close()

    return {
        "success": True,
        "campaign": dict(row)
    }


@app.get("/api/campaigns")
def get_campaigns(
    user=Depends(get_current_user)
):
    db = get_db()

    rows = db.execute("""
        SELECT *
        FROM campaigns
        WHERE user_id = ?
        ORDER BY id DESC
    """, (
        user["id"],
    )).fetchall()

    db.close()

    return {
        "success": True,
        "campaigns": [
            dict(row)
            for row in rows
        ]
    }


@app.get("/api/campaigns/{campaign_id}")
def get_campaign(
    campaign_id: int,
    user=Depends(get_current_user)
):
    db = get_db()

    row = db.execute("""
        SELECT *
        FROM campaigns
        WHERE id = ?
        AND user_id = ?
    """, (
        campaign_id,
        user["id"]
    )).fetchone()

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
def delete_campaign(
    campaign_id: int,
    user=Depends(get_current_user)
):
    db = get_db()

    cursor = db.execute("""
        DELETE FROM campaigns
        WHERE id = ?
        AND user_id = ?
    """, (
        campaign_id,
        user["id"]
    ))

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
    if not os.getenv(
        "OPENAI_API_KEY"
    ):
        raise HTTPException(
            status_code=503,
            detail=(
                "AI is ready but API "
                "access is not configured yet."
            )
        )

    raise HTTPException(
        status_code=501,
        detail=(
            "AI provider will be activated "
            "when API access is configured."
        )
    )


@app.get("/")
def root():
    return {
        "name": "MarketFlow Backend",
        "status": "running"
    }
