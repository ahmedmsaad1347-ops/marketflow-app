import os
import sqlite3
import secrets
import hashlib
import hmac
import base64
import json
import urllib.parse
import urllib.request
import urllib.error

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
from fastapi.responses import RedirectResponse
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

    db.execute("""
        CREATE TABLE IF NOT EXISTS analytics_daily (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            date TEXT NOT NULL,

            provider TEXT NOT NULL,
            account_id TEXT NOT NULL DEFAULT '',
            campaign_id TEXT NOT NULL DEFAULT '',
            campaign_name TEXT,

            impressions INTEGER NOT NULL DEFAULT 0,
            reach INTEGER NOT NULL DEFAULT 0,
            clicks INTEGER NOT NULL DEFAULT 0,
            messages INTEGER NOT NULL DEFAULT 0,
            leads INTEGER NOT NULL DEFAULT 0,
            conversions INTEGER NOT NULL DEFAULT 0,

            spend REAL NOT NULL DEFAULT 0,
            revenue REAL NOT NULL DEFAULT 0,

            currency TEXT NOT NULL DEFAULT 'USD',

            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,

            UNIQUE(
                user_id,
                date,
                provider,
                account_id,
                campaign_id
            )
        )
    """)

    db.execute("""
        CREATE INDEX IF NOT EXISTS
        idx_analytics_user_date
        ON analytics_daily(user_id, date)
    """)

    db.execute("""
        CREATE INDEX IF NOT EXISTS
        idx_analytics_provider
        ON analytics_daily(user_id, provider)
    """)

    db.execute("""
        CREATE TABLE IF NOT EXISTS meta_tokens (
            user_id INTEGER PRIMARY KEY,
            access_token TEXT NOT NULL,
            expires_at TEXT,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )
    """)

    db.execute("""
        CREATE TABLE IF NOT EXISTS meta_ad_accounts (
            user_id INTEGER NOT NULL,
            account_id TEXT NOT NULL,
            account_name TEXT,
            currency TEXT,
            account_status TEXT,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,

            PRIMARY KEY (
                user_id,
                account_id
            )
        )
    """)

    db.execute("""
        CREATE TABLE IF NOT EXISTS oauth_states (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            provider TEXT NOT NULL,
            state_hash TEXT UNIQUE NOT NULL,
            expires_at TEXT NOT NULL,
            created_at TEXT NOT NULL
        )
    """)

    db.execute("""
        CREATE TABLE IF NOT EXISTS campaign_events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            campaign_id INTEGER NOT NULL,
            event_type TEXT NOT NULL,
            message TEXT NOT NULL,
            created_at TEXT NOT NULL
        )
    """)

    db.execute("""
        CREATE INDEX IF NOT EXISTS
        idx_campaign_events
        ON campaign_events(
            user_id,
            campaign_id,
            created_at
        )
    """)

    db.execute("""
        CREATE TABLE IF NOT EXISTS notification_reads (
            user_id INTEGER NOT NULL,
            event_id INTEGER NOT NULL,
            read_at TEXT NOT NULL,

            PRIMARY KEY (
                user_id,
                event_id
            )
        )
    """)

    db.execute("""
        CREATE INDEX IF NOT EXISTS
        idx_notification_reads_user
        ON notification_reads(
            user_id,
            event_id
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

    if "updated_at" not in columns:
        db.execute(
            "ALTER TABLE campaigns ADD COLUMN updated_at TEXT"
        )

        db.execute("""
            UPDATE campaigns
            SET updated_at = created_at
            WHERE updated_at IS NULL
        """)

    db.execute("""
        CREATE TRIGGER IF NOT EXISTS
        campaign_created_event
        AFTER INSERT ON campaigns
        BEGIN

            UPDATE campaigns
            SET updated_at = NEW.created_at
            WHERE id = NEW.id;

            INSERT INTO campaign_events (
                user_id,
                campaign_id,
                event_type,
                message,
                created_at
            )
            VALUES (
                NEW.user_id,
                NEW.id,
                'Created',
                'Campaign created',
                NEW.created_at
            );

        END
    """)

    db.execute("""
        CREATE TRIGGER IF NOT EXISTS
        campaign_edited_event
        AFTER UPDATE OF
            name,
            product,
            audience,
            country,
            platform,
            budget,
            goal
        ON campaigns
        BEGIN

            UPDATE campaigns
            SET updated_at =
                strftime(
                    '%Y-%m-%dT%H:%M:%fZ',
                    'now'
                )
            WHERE id = NEW.id;

            INSERT INTO campaign_events (
                user_id,
                campaign_id,
                event_type,
                message,
                created_at
            )
            VALUES (
                NEW.user_id,
                NEW.id,
                'Edited',
                'Campaign details updated',
                strftime(
                    '%Y-%m-%dT%H:%M:%fZ',
                    'now'
                )
            );

        END
    """)

    db.execute("""
        CREATE TRIGGER IF NOT EXISTS
        campaign_status_event
        AFTER UPDATE OF status
        ON campaigns
        WHEN OLD.status != NEW.status
        BEGIN

            UPDATE campaigns
            SET updated_at =
                strftime(
                    '%Y-%m-%dT%H:%M:%fZ',
                    'now'
                )
            WHERE id = NEW.id;

            INSERT INTO campaign_events (
                user_id,
                campaign_id,
                event_type,
                message,
                created_at
            )
            VALUES (
                NEW.user_id,
                NEW.id,
                'Status changed',
                'Status changed from '
                    || OLD.status
                    || ' to '
                    || NEW.status,
                strftime(
                    '%Y-%m-%dT%H:%M:%fZ',
                    'now'
                )
            );

        END
    """)

    db.execute("""
        CREATE TRIGGER IF NOT EXISTS
        campaign_delete_history
        BEFORE DELETE ON campaigns
        BEGIN

            DELETE FROM campaign_events
            WHERE campaign_id = OLD.id
            AND user_id = OLD.user_id;

        END
    """)

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


class ProfileUpdateData(BaseModel):
    name: str = Field(
        min_length=2,
        max_length=80
    )

    email: str = Field(
        min_length=5,
        max_length=150
    )

    current_password: str = Field(
        min_length=8,
        max_length=128
    )


class PasswordChangeData(BaseModel):
    current_password: str = Field(
        min_length=8,
        max_length=128
    )

    new_password: str = Field(
        min_length=8,
        max_length=128
    )


class CampaignData(BaseModel):
    name: str
    product: str
    audience: str
    country: str
    platform: str
    budget: str
    goal: str


class CampaignUpdateData(BaseModel):
    name: str
    product: str
    audience: str
    country: str
    platform: str
    budget: str
    goal: str


class CampaignStatusData(BaseModel):
    status: str


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


@app.put("/api/account/profile")
def update_profile(
    data: ProfileUpdateData,
    user=Depends(get_current_user)
):
    name = data.name.strip()
    email = data.email.strip().lower()

    if len(name) < 2:
        raise HTTPException(
            status_code=400,
            detail="Name is too short"
        )

    if (
        "@" not in email
        or "." not in email.split("@")[-1]
    ):
        raise HTTPException(
            status_code=400,
            detail="Enter a valid email address"
        )

    db = get_db()

    account = db.execute("""
        SELECT *
        FROM users
        WHERE id = ?
    """, (
        user["id"],
    )).fetchone()

    if not account:
        db.close()

        raise HTTPException(
            status_code=404,
            detail="Account not found"
        )

    if not verify_password(
        data.current_password,
        account["password_hash"],
        account["password_salt"]
    ):
        db.close()

        raise HTTPException(
            status_code=401,
            detail="Current password is incorrect"
        )

    duplicate = db.execute("""
        SELECT id
        FROM users
        WHERE email = ?
        AND id != ?
    """, (
        email,
        user["id"]
    )).fetchone()

    if duplicate:
        db.close()

        raise HTTPException(
            status_code=409,
            detail="Email is already in use"
        )

    db.execute("""
        UPDATE users
        SET
            name = ?,
            email = ?
        WHERE id = ?
    """, (
        name,
        email,
        user["id"]
    ))

    db.commit()
    db.close()

    return {
        "success": True,
        "user": {
            "id": user["id"],
            "name": name,
            "email": email
        }
    }


@app.put("/api/account/password")
def change_password(
    data: PasswordChangeData,
    request: Request,
    response: Response,
    user=Depends(get_current_user)
):
    if (
        data.current_password ==
        data.new_password
    ):
        raise HTTPException(
            status_code=400,
            detail=(
                "New password must be "
                "different from the current password"
            )
        )

    db = get_db()

    account = db.execute("""
        SELECT *
        FROM users
        WHERE id = ?
    """, (
        user["id"],
    )).fetchone()

    if not account:
        db.close()

        raise HTTPException(
            status_code=404,
            detail="Account not found"
        )

    if not verify_password(
        data.current_password,
        account["password_hash"],
        account["password_salt"]
    ):
        db.close()

        raise HTTPException(
            status_code=401,
            detail="Current password is incorrect"
        )

    password_hash, salt = hash_password(
        data.new_password
    )

    db.execute("""
        UPDATE users
        SET
            password_hash = ?,
            password_salt = ?
        WHERE id = ?
    """, (
        password_hash,
        salt,
        user["id"]
    ))

    # Log out all old sessions
    db.execute("""
        DELETE FROM sessions
        WHERE user_id = ?
    """, (
        user["id"],
    ))

    db.commit()

    # Create one fresh session
    new_token = create_session(
        db,
        user["id"]
    )

    db.close()

    set_session_cookie(
        response,
        new_token
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
    status: str = "",
    q: str = "",
    user=Depends(get_current_user)
):
    db = get_db()

    sql = """
        SELECT *
        FROM campaigns
        WHERE user_id = ?
    """

    params = [user["id"]]

    if status and status != "All":
        sql += " AND status = ?"
        params.append(status)

    if q.strip():
        search = f"%{q.strip()}%"

        sql += """
            AND (
                name LIKE ?
                OR product LIKE ?
                OR country LIKE ?
                OR platform LIKE ?
                OR goal LIKE ?
            )
        """

        params.extend([
            search,
            search,
            search,
            search,
            search
        ])

    sql += " ORDER BY id DESC"

    rows = db.execute(
        sql,
        tuple(params)
    ).fetchall()

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


@app.put("/api/campaigns/{campaign_id}")
def update_campaign(
    campaign_id: int,
    campaign: CampaignUpdateData,
    user=Depends(get_current_user)
):
    db = get_db()

    exists = db.execute("""
        SELECT id
        FROM campaigns
        WHERE id = ?
        AND user_id = ?
    """, (
        campaign_id,
        user["id"]
    )).fetchone()

    if not exists:
        db.close()

        raise HTTPException(
            status_code=404,
            detail="Campaign not found"
        )

    db.execute("""
        UPDATE campaigns
        SET
            name = ?,
            product = ?,
            audience = ?,
            country = ?,
            platform = ?,
            budget = ?,
            goal = ?
        WHERE id = ?
        AND user_id = ?
    """, (
        campaign.name,
        campaign.product,
        campaign.audience,
        campaign.country,
        campaign.platform,
        campaign.budget,
        campaign.goal,
        campaign_id,
        user["id"]
    ))

    db.commit()

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


@app.post("/api/campaigns/{campaign_id}/duplicate")
def duplicate_campaign(
    campaign_id: int,
    user=Depends(get_current_user)
):
    db = get_db()

    original = db.execute("""
        SELECT *
        FROM campaigns
        WHERE id = ?
        AND user_id = ?
    """, (
        campaign_id,
        user["id"]
    )).fetchone()

    if not original:
        db.close()

        raise HTTPException(
            status_code=404,
            detail="Campaign not found"
        )

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
        original["name"] + " Copy",
        original["product"],
        original["audience"],
        original["country"],
        original["platform"],
        original["budget"],
        original["goal"],
        "Draft",
        datetime.utcnow().isoformat()
    ))

    db.commit()

    new_id = cursor.lastrowid

    row = db.execute("""
        SELECT *
        FROM campaigns
        WHERE id = ?
        AND user_id = ?
    """, (
        new_id,
        user["id"]
    )).fetchone()

    db.close()

    return {
        "success": True,
        "campaign": dict(row)
    }


@app.patch("/api/campaigns/{campaign_id}/status")
def update_campaign_status(
    campaign_id: int,
    data: CampaignStatusData,
    user=Depends(get_current_user)
):
    allowed = [
        "Draft",
        "Ready",
        "Archived"
    ]

    if data.status not in allowed:
        raise HTTPException(
            status_code=400,
            detail=(
                "Status must be Draft, "
                "Ready or Archived"
            )
        )

    db = get_db()

    cursor = db.execute("""
        UPDATE campaigns
        SET status = ?
        WHERE id = ?
        AND user_id = ?
    """, (
        data.status,
        campaign_id,
        user["id"]
    ))

    db.commit()

    if cursor.rowcount == 0:
        db.close()

        raise HTTPException(
            status_code=404,
            detail="Campaign not found"
        )

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


@app.get("/api/campaigns/{campaign_id}/history")
def get_campaign_history(
    campaign_id: int,
    user=Depends(get_current_user)
):
    db = get_db()

    campaign = db.execute("""
        SELECT *
        FROM campaigns
        WHERE id = ?
        AND user_id = ?
    """, (
        campaign_id,
        user["id"]
    )).fetchone()

    if not campaign:
        db.close()

        raise HTTPException(
            status_code=404,
            detail="Campaign not found"
        )

    rows = db.execute("""
        SELECT
            id,
            event_type,
            message,
            created_at
        FROM campaign_events
        WHERE campaign_id = ?
        AND user_id = ?
        ORDER BY id DESC
    """, (
        campaign_id,
        user["id"]
    )).fetchall()

    db.close()

    return {
        "success": True,
        "campaign_id": campaign_id,
        "updated_at": campaign["updated_at"],
        "history": [
            dict(row)
            for row in rows
        ]
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



def analytics_divide(a, b):
    if not b:
        return 0

    return round(a / b, 4)


def analytics_percent_change(current, previous):
    if previous == 0:
        if current == 0:
            return 0
        return None

    return round(
        ((current - previous) / previous) * 100,
        2
    )


def build_analytics_metrics(row):
    impressions = row["impressions"] or 0
    clicks = row["clicks"] or 0
    leads = row["leads"] or 0
    conversions = row["conversions"] or 0
    spend = row["spend"] or 0
    revenue = row["revenue"] or 0

    return {
        "impressions": impressions,
        "reach": row["reach"] or 0,
        "clicks": clicks,
        "messages": row["messages"] or 0,
        "leads": leads,
        "conversions": conversions,
        "spend": round(spend, 2),
        "revenue": round(revenue, 2),

        "roas": round(
            analytics_divide(revenue, spend),
            2
        ),

        "cpa": round(
            analytics_divide(spend, conversions),
            2
        ),

        "cpl": round(
            analytics_divide(spend, leads),
            2
        ),

        "cpc": round(
            analytics_divide(spend, clicks),
            2
        ),

        "ctr": round(
            analytics_divide(
                clicks * 100,
                impressions
            ),
            2
        ),

        "conversion_rate": round(
            analytics_divide(
                conversions * 100,
                clicks
            ),
            2
        )
    }


def analytics_sum(
    db,
    user_id,
    start_date,
    end_date
):
    row = db.execute("""
        SELECT
            COALESCE(SUM(impressions), 0)
                AS impressions,
            COALESCE(SUM(reach), 0)
                AS reach,
            COALESCE(SUM(clicks), 0)
                AS clicks,
            COALESCE(SUM(messages), 0)
                AS messages,
            COALESCE(SUM(leads), 0)
                AS leads,
            COALESCE(SUM(conversions), 0)
                AS conversions,
            COALESCE(SUM(spend), 0)
                AS spend,
            COALESCE(SUM(revenue), 0)
                AS revenue
        FROM analytics_daily
        WHERE user_id = ?
        AND date >= ?
        AND date <= ?
    """, (
        user_id,
        start_date,
        end_date
    )).fetchone()

    return build_analytics_metrics(row)


@app.get("/api/notifications")
def get_notifications(
    limit: int = 50,
    user=Depends(get_current_user)
):
    limit = max(
        1,
        min(limit, 100)
    )

    db = get_db()

    unread_row = db.execute("""
        SELECT
            COUNT(*) AS unread
        FROM campaign_events AS events

        LEFT JOIN notification_reads AS reads
        ON reads.event_id = events.id
        AND reads.user_id = events.user_id

        WHERE events.user_id = ?
        AND reads.event_id IS NULL
    """, (
        user["id"],
    )).fetchone()

    rows = db.execute("""
        SELECT
            events.id,
            events.campaign_id,
            events.event_type,
            events.message,
            events.created_at,

            COALESCE(
                campaigns.name,
                'Campaign'
            ) AS campaign_name,

            CASE
                WHEN reads.event_id IS NULL
                THEN 0
                ELSE 1
            END AS is_read

        FROM campaign_events AS events

        LEFT JOIN campaigns
        ON campaigns.id =
            events.campaign_id
        AND campaigns.user_id =
            events.user_id

        LEFT JOIN notification_reads AS reads
        ON reads.event_id =
            events.id
        AND reads.user_id =
            events.user_id

        WHERE events.user_id = ?

        ORDER BY events.id DESC

        LIMIT ?
    """, (
        user["id"],
        limit
    )).fetchall()

    db.close()

    return {
        "success": True,
        "unread_count":
            unread_row["unread"] or 0,

        "notifications": [
            dict(row)
            for row in rows
        ]
    }


@app.post(
    "/api/notifications/{event_id}/read"
)
def mark_notification_read(
    event_id: int,
    user=Depends(get_current_user)
):
    db = get_db()

    event = db.execute("""
        SELECT id
        FROM campaign_events
        WHERE id = ?
        AND user_id = ?
    """, (
        event_id,
        user["id"]
    )).fetchone()

    if not event:
        db.close()

        raise HTTPException(
            status_code=404,
            detail="Notification not found"
        )

    db.execute("""
        INSERT OR IGNORE
        INTO notification_reads (
            user_id,
            event_id,
            read_at
        )
        VALUES (?, ?, ?)
    """, (
        user["id"],
        event_id,
        datetime.utcnow().isoformat()
    ))

    db.commit()
    db.close()

    return {
        "success": True
    }


@app.post("/api/notifications/read-all")
def mark_all_notifications_read(
    user=Depends(get_current_user)
):
    db = get_db()

    now = datetime.utcnow().isoformat()

    db.execute("""
        INSERT OR IGNORE
        INTO notification_reads (
            user_id,
            event_id,
            read_at
        )

        SELECT
            ?,
            id,
            ?

        FROM campaign_events

        WHERE user_id = ?
    """, (
        user["id"],
        now,
        user["id"]
    ))

    db.commit()
    db.close()

    return {
        "success": True
    }


@app.get("/api/dashboard/overview")
def dashboard_overview(
    user=Depends(get_current_user)
):
    db = get_db()

    counts = db.execute("""
        SELECT
            COUNT(*) AS total,
            COALESCE(
                SUM(
                    CASE
                        WHEN status = 'Draft'
                        THEN 1
                        ELSE 0
                    END
                ),
                0
            ) AS draft,
            COALESCE(
                SUM(
                    CASE
                        WHEN status = 'Ready'
                        THEN 1
                        ELSE 0
                    END
                ),
                0
            ) AS ready,
            COALESCE(
                SUM(
                    CASE
                        WHEN status = 'Archived'
                        THEN 1
                        ELSE 0
                    END
                ),
                0
            ) AS archived
        FROM campaigns
        WHERE user_id = ?
    """, (
        user["id"],
    )).fetchone()

    recent_campaigns = db.execute("""
        SELECT
            id,
            name,
            product,
            platform,
            country,
            budget,
            goal,
            status,
            created_at,
            updated_at
        FROM campaigns
        WHERE user_id = ?
        ORDER BY
            COALESCE(
                updated_at,
                created_at
            ) DESC
        LIMIT 5
    """, (
        user["id"],
    )).fetchall()

    recent_activity = db.execute("""
        SELECT
            campaign_events.id,
            campaign_events.campaign_id,
            campaign_events.event_type,
            campaign_events.message,
            campaign_events.created_at,
            campaigns.name AS campaign_name
        FROM campaign_events
        JOIN campaigns
        ON campaigns.id =
            campaign_events.campaign_id
        WHERE campaign_events.user_id = ?
        AND campaigns.user_id = ?
        ORDER BY campaign_events.id DESC
        LIMIT 8
    """, (
        user["id"],
        user["id"]
    )).fetchall()

    db.close()

    return {
        "success": True,

        "campaigns": {
            "total": counts["total"] or 0,
            "draft": counts["draft"] or 0,
            "ready": counts["ready"] or 0,
            "archived": counts["archived"] or 0
        },

        "recent_campaigns": [
            dict(row)
            for row in recent_campaigns
        ],

        "recent_activity": [
            dict(row)
            for row in recent_activity
        ]
    }


@app.get("/api/analytics/overview")
def analytics_overview(
    days: int = 30,
    user=Depends(get_current_user)
):
    allowed_days = [7, 30, 90, 365]

    if days not in allowed_days:
        raise HTTPException(
            status_code=400,
            detail="days must be 7, 30, 90 or 365"
        )

    today = datetime.utcnow().date()

    start = (
        today -
        timedelta(days=days - 1)
    )

    previous_end = start - timedelta(days=1)

    previous_start = (
        previous_end -
        timedelta(days=days - 1)
    )

    db = get_db()

    current = analytics_sum(
        db,
        user["id"],
        start.isoformat(),
        today.isoformat()
    )

    previous = analytics_sum(
        db,
        user["id"],
        previous_start.isoformat(),
        previous_end.isoformat()
    )

    comparison = {}

    for key in [
        "revenue",
        "spend",
        "leads",
        "conversions",
        "clicks",
        "impressions"
    ]:
        comparison[key] = analytics_percent_change(
            current[key],
            previous[key]
        )

    daily_rows = db.execute("""
        SELECT
            date,
            COALESCE(SUM(spend), 0)
                AS spend,
            COALESCE(SUM(revenue), 0)
                AS revenue,
            COALESCE(SUM(leads), 0)
                AS leads,
            COALESCE(SUM(conversions), 0)
                AS conversions,
            COALESCE(SUM(clicks), 0)
                AS clicks,
            COALESCE(SUM(impressions), 0)
                AS impressions
        FROM analytics_daily
        WHERE user_id = ?
        AND date >= ?
        AND date <= ?
        GROUP BY date
        ORDER BY date ASC
    """, (
        user["id"],
        start.isoformat(),
        today.isoformat()
    )).fetchall()

    by_date = {
        row["date"]: dict(row)
        for row in daily_rows
    }

    timeline = []

    for offset in range(days):
        day = (
            start +
            timedelta(days=offset)
        )

        key = day.isoformat()

        row = by_date.get(key)

        timeline.append({
            "date": key,
            "spend": round(
                row["spend"] if row else 0,
                2
            ),
            "revenue": round(
                row["revenue"] if row else 0,
                2
            ),
            "leads":
                row["leads"] if row else 0,
            "conversions":
                row["conversions"] if row else 0,
            "clicks":
                row["clicks"] if row else 0,
            "impressions":
                row["impressions"] if row else 0
        })

    platform_rows = db.execute("""
        SELECT
            provider,
            COALESCE(SUM(spend), 0)
                AS spend,
            COALESCE(SUM(revenue), 0)
                AS revenue,
            COALESCE(SUM(leads), 0)
                AS leads,
            COALESCE(SUM(conversions), 0)
                AS conversions,
            COALESCE(SUM(clicks), 0)
                AS clicks,
            COALESCE(SUM(impressions), 0)
                AS impressions
        FROM analytics_daily
        WHERE user_id = ?
        AND date >= ?
        AND date <= ?
        GROUP BY provider
        ORDER BY revenue DESC
    """, (
        user["id"],
        start.isoformat(),
        today.isoformat()
    )).fetchall()

    platforms = []

    for row in platform_rows:
        spend = row["spend"] or 0
        revenue = row["revenue"] or 0

        platforms.append({
            "provider": row["provider"],
            "spend": round(spend, 2),
            "revenue": round(revenue, 2),
            "leads": row["leads"] or 0,
            "conversions":
                row["conversions"] or 0,
            "clicks": row["clicks"] or 0,
            "impressions":
                row["impressions"] or 0,
            "roas": round(
                analytics_divide(
                    revenue,
                    spend
                ),
                2
            )
        })

    campaign_rows = db.execute("""
        SELECT
            provider,
            campaign_id,
            COALESCE(
                MAX(campaign_name),
                campaign_id
            ) AS campaign_name,
            COALESCE(SUM(spend), 0)
                AS spend,
            COALESCE(SUM(revenue), 0)
                AS revenue,
            COALESCE(SUM(leads), 0)
                AS leads,
            COALESCE(SUM(conversions), 0)
                AS conversions
        FROM analytics_daily
        WHERE user_id = ?
        AND date >= ?
        AND date <= ?
        AND campaign_id != ''
        GROUP BY provider, campaign_id
        ORDER BY revenue DESC
        LIMIT 10
    """, (
        user["id"],
        start.isoformat(),
        today.isoformat()
    )).fetchall()

    top_campaigns = []

    for row in campaign_rows:
        spend = row["spend"] or 0
        revenue = row["revenue"] or 0

        top_campaigns.append({
            "provider": row["provider"],
            "campaign_id": row["campaign_id"],
            "name": row["campaign_name"],
            "spend": round(spend, 2),
            "revenue": round(revenue, 2),
            "leads": row["leads"] or 0,
            "conversions":
                row["conversions"] or 0,
            "roas": round(
                analytics_divide(
                    revenue,
                    spend
                ),
                2
            )
        })

    status = db.execute("""
        SELECT
            COUNT(*) AS records,
            COUNT(DISTINCT provider)
                AS providers,
            MAX(updated_at)
                AS last_updated
        FROM analytics_daily
        WHERE user_id = ?
    """, (
        user["id"],
    )).fetchone()

    db.close()

    return {
        "success": True,
        "period": {
            "days": days,
            "start": start.isoformat(),
            "end": today.isoformat()
        },

        "has_data":
            status["records"] > 0,

        "data_status": {
            "records":
                status["records"],
            "providers":
                status["providers"],
            "last_updated":
                status["last_updated"]
        },

        "summary": current,
        "previous": previous,
        "comparison": comparison,
        "timeline": timeline,
        "platforms": platforms,
        "top_campaigns": top_campaigns
    }


def upsert_analytics_record(
    db,
    user_id,
    *,
    date,
    provider,
    account_id="",
    campaign_id="",
    campaign_name=None,
    impressions=0,
    reach=0,
    clicks=0,
    messages=0,
    leads=0,
    conversions=0,
    spend=0,
    revenue=0,
    currency="USD"
):
    """
    Internal analytics ingestion function.

    Meta / Google / TikTok / CRM connectors
    will call this function after fetching
    verified provider data.

    It is intentionally NOT exposed as a
    public API endpoint.
    """

    now = datetime.utcnow().isoformat()

    db.execute("""
        INSERT INTO analytics_daily (
            user_id,
            date,
            provider,
            account_id,
            campaign_id,
            campaign_name,
            impressions,
            reach,
            clicks,
            messages,
            leads,
            conversions,
            spend,
            revenue,
            currency,
            created_at,
            updated_at
        )
        VALUES (
            ?, ?, ?, ?, ?, ?, ?, ?, ?,
            ?, ?, ?, ?, ?, ?, ?, ?
        )

        ON CONFLICT(
            user_id,
            date,
            provider,
            account_id,
            campaign_id
        )

        DO UPDATE SET
            campaign_name =
                excluded.campaign_name,
            impressions =
                excluded.impressions,
            reach =
                excluded.reach,
            clicks =
                excluded.clicks,
            messages =
                excluded.messages,
            leads =
                excluded.leads,
            conversions =
                excluded.conversions,
            spend =
                excluded.spend,
            revenue =
                excluded.revenue,
            currency =
                excluded.currency,
            updated_at =
                excluded.updated_at
    """, (
        user_id,
        date,
        provider,
        account_id,
        campaign_id,
        campaign_name,
        impressions,
        reach,
        clicks,
        messages,
        leads,
        conversions,
        spend,
        revenue,
        currency,
        now,
        now
    ))

    db.commit()



# =========================================
# MARKETFLOW META CONNECTOR
# =========================================

def get_meta_config():
    config = {
        "app_id":
            os.getenv("META_APP_ID"),
        "app_secret":
            os.getenv("META_APP_SECRET"),
        "version":
            os.getenv("META_GRAPH_VERSION"),
        "redirect_uri":
            os.getenv("META_REDIRECT_URI"),
        "frontend_url":
            os.getenv(
                "FRONTEND_URL",
                "http://localhost:5173"
            ),
        "config_id":
            os.getenv("META_CONFIG_ID")
    }

    required = [
        "app_id",
        "app_secret",
        "version",
        "redirect_uri"
    ]

    missing = [
        key
        for key in required
        if not config[key]
    ]

    if missing:
        raise HTTPException(
            status_code=503,
            detail=(
                "Meta integration is not configured: "
                + ", ".join(missing)
            )
        )

    return config


def meta_api_get(
    path_or_url,
    access_token=None,
    params=None
):
    config = get_meta_config()

    params = dict(params or {})

    if access_token:
        params["access_token"] = access_token

    if path_or_url.startswith("http"):
        url = path_or_url
    else:
        url = (
            "https://graph.facebook.com/"
            f'{config["version"]}/'
            f'{path_or_url.lstrip("/")}'
        )

    if params:
        separator = (
            "&"
            if "?" in url
            else "?"
        )

        url += (
            separator
            + urllib.parse.urlencode(
                params
            )
        )

    try:
        with urllib.request.urlopen(
            url,
            timeout=45
        ) as response:

            return json.loads(
                response.read().decode()
            )

    except urllib.error.HTTPError as error:
        try:
            payload = json.loads(
                error.read().decode()
            )

            message = (
                payload
                .get("error", {})
                .get(
                    "message",
                    "Meta API request failed"
                )
            )

        except Exception:
            message = (
                "Meta API request failed"
            )

        raise HTTPException(
            status_code=502,
            detail=message
        )

    except Exception:
        raise HTTPException(
            status_code=502,
            detail=(
                "Could not connect to Meta API"
            )
        )


def meta_exchange_code(code):
    config = get_meta_config()

    token = meta_api_get(
        "oauth/access_token",
        params={
            "client_id":
                config["app_id"],

            "client_secret":
                config["app_secret"],

            "redirect_uri":
                config["redirect_uri"],

            "code":
                code
        }
    )

    short_token = token.get(
        "access_token"
    )

    if not short_token:
        raise HTTPException(
            status_code=502,
            detail=(
                "Meta did not return "
                "an access token"
            )
        )

    # Exchange for longer-lived token
    long_token = meta_api_get(
        "oauth/access_token",
        params={
            "grant_type":
                "fb_exchange_token",

            "client_id":
                config["app_id"],

            "client_secret":
                config["app_secret"],

            "fb_exchange_token":
                short_token
        }
    )

    return {
        "access_token":
            long_token.get(
                "access_token",
                short_token
            ),

        "expires_in":
            long_token.get(
                "expires_in",
                token.get("expires_in")
            )
    }


def get_all_meta_ad_accounts(
    access_token
):
    payload = meta_api_get(
        "me/adaccounts",
        access_token,
        {
            "fields":
                (
                    "id,name,"
                    "account_status,"
                    "currency"
                ),

            "limit": 100
        }
    )

    accounts = []

    while True:
        accounts.extend(
            payload.get(
                "data",
                []
            )
        )

        next_url = (
            payload
            .get("paging", {})
            .get("next")
        )

        if not next_url:
            break

        payload = meta_api_get(
            next_url
        )

    return accounts


@app.get("/api/meta/connect-url")
def meta_connect_url(
    user=Depends(get_current_user)
):
    config = get_meta_config()

    state = secrets.token_urlsafe(40)

    state_hash = hash_session_token(
        state
    )

    now = datetime.utcnow()

    expires = (
        now +
        timedelta(minutes=10)
    )

    db = get_db()

    db.execute("""
        DELETE FROM oauth_states
        WHERE user_id = ?
        AND provider = 'meta'
    """, (
        user["id"],
    ))

    db.execute("""
        INSERT INTO oauth_states (
            user_id,
            provider,
            state_hash,
            expires_at,
            created_at
        )
        VALUES (?, ?, ?, ?, ?)
    """, (
        user["id"],
        "meta",
        state_hash,
        expires.isoformat(),
        now.isoformat()
    ))

    db.commit()
    db.close()

    params = {
        "client_id":
            config["app_id"],

        "redirect_uri":
            config["redirect_uri"],

        "response_type":
            "code",

        "scope":
            "ads_read,business_management",

        "state":
            state
    }

    if config["config_id"]:
        params["config_id"] = (
            config["config_id"]
        )

    auth_url = (
        "https://www.facebook.com/"
        f'{config["version"]}/dialog/oauth?'
        + urllib.parse.urlencode(params)
    )

    return {
        "success": True,
        "url": auth_url
    }


@app.get("/api/meta/callback")
def meta_callback(
    code: str,
    state: str
):
    state_hash = hash_session_token(
        state
    )

    db = get_db()

    state_row = db.execute("""
        SELECT *
        FROM oauth_states
        WHERE provider = 'meta'
        AND state_hash = ?
    """, (
        state_hash,
    )).fetchone()

    if not state_row:
        db.close()

        raise HTTPException(
            status_code=400,
            detail="Invalid OAuth state"
        )

    if datetime.fromisoformat(
        state_row["expires_at"]
    ) < datetime.utcnow():

        db.execute(
            """
            DELETE FROM oauth_states
            WHERE id = ?
            """,
            (state_row["id"],)
        )

        db.commit()
        db.close()

        raise HTTPException(
            status_code=400,
            detail="OAuth state expired"
        )

    user_id = state_row["user_id"]

    db.execute(
        """
        DELETE FROM oauth_states
        WHERE id = ?
        """,
        (state_row["id"],)
    )

    db.commit()
    db.close()

    token_data = meta_exchange_code(
        code
    )

    access_token = (
        token_data["access_token"]
    )

    expires_in = (
        token_data.get("expires_in")
    )

    expires_at = None

    if expires_in:
        expires_at = (
            datetime.utcnow()
            + timedelta(
                seconds=int(
                    expires_in
                )
            )
        ).isoformat()

    accounts = (
        get_all_meta_ad_accounts(
            access_token
        )
    )

    now = datetime.utcnow().isoformat()

    db = get_db()

    db.execute("""
        INSERT INTO meta_tokens (
            user_id,
            access_token,
            expires_at,
            created_at,
            updated_at
        )
        VALUES (?, ?, ?, ?, ?)

        ON CONFLICT(user_id)
        DO UPDATE SET
            access_token =
                excluded.access_token,
            expires_at =
                excluded.expires_at,
            updated_at =
                excluded.updated_at
    """, (
        user_id,
        access_token,
        expires_at,
        now,
        now
    ))

    db.execute("""
        DELETE FROM meta_ad_accounts
        WHERE user_id = ?
    """, (
        user_id,
    ))

    for account in accounts:
        db.execute("""
            INSERT INTO meta_ad_accounts (
                user_id,
                account_id,
                account_name,
                currency,
                account_status,
                created_at,
                updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            user_id,
            account.get("id"),
            account.get("name"),
            account.get("currency"),
            str(
                account.get(
                    "account_status",
                    ""
                )
            ),
            now,
            now
        ))

    db.commit()
    db.close()

    config = get_meta_config()

    return RedirectResponse(
        url=(
            config["frontend_url"]
            + "/app?meta=connected"
        )
    )


@app.get("/api/meta/status")
def meta_status(
    user=Depends(get_current_user)
):
    db = get_db()

    token = db.execute("""
        SELECT expires_at
        FROM meta_tokens
        WHERE user_id = ?
    """, (
        user["id"],
    )).fetchone()

    accounts = db.execute("""
        SELECT
            account_id,
            account_name,
            currency,
            account_status
        FROM meta_ad_accounts
        WHERE user_id = ?
        ORDER BY account_name ASC
    """, (
        user["id"],
    )).fetchall()

    db.close()

    return {
        "success": True,
        "connected":
            token is not None,

        "expires_at":
            (
                token["expires_at"]
                if token
                else None
            ),

        "accounts": [
            dict(account)
            for account in accounts
        ]
    }


def meta_action_value(
    values,
    action_types
):
    if not values:
        return 0

    lookup = {
        item.get("action_type"):
            item.get("value")
        for item in values
    }

    for action_type in action_types:
        if action_type in lookup:
            try:
                return float(
                    lookup[action_type]
                )
            except Exception:
                return 0

    return 0


@app.post("/api/meta/sync")
def meta_sync(
    days: int = 90,
    user=Depends(get_current_user)
):
    if days not in [
        7,
        30,
        90,
        365
    ]:
        raise HTTPException(
            status_code=400,
            detail=(
                "days must be "
                "7, 30, 90 or 365"
            )
        )

    if "upsert_analytics_record" not in globals():
        raise HTTPException(
            status_code=500,
            detail=(
                "Analytics engine "
                "is not installed"
            )
        )

    db = get_db()

    token_row = db.execute("""
        SELECT *
        FROM meta_tokens
        WHERE user_id = ?
    """, (
        user["id"],
    )).fetchone()

    if not token_row:
        db.close()

        raise HTTPException(
            status_code=400,
            detail=(
                "Meta account "
                "is not connected"
            )
        )

    if token_row["expires_at"]:
        expires = datetime.fromisoformat(
            token_row["expires_at"]
        )

        if expires < datetime.utcnow():
            db.close()

            raise HTTPException(
                status_code=401,
                detail=(
                    "Meta access expired. "
                    "Reconnect your account."
                )
            )

    accounts = db.execute("""
        SELECT *
        FROM meta_ad_accounts
        WHERE user_id = ?
    """, (
        user["id"],
    )).fetchall()

    access_token = (
        token_row["access_token"]
    )

    today = datetime.utcnow().date()

    start = (
        today -
        timedelta(days=days - 1)
    )

    imported = 0

    purchase_types = [
        "omni_purchase",
        "purchase",
        "offsite_conversion.fb_pixel_purchase"
    ]

    lead_types = [
        "lead",
        "onsite_conversion.lead_grouped",
        "offsite_conversion.fb_pixel_lead"
    ]

    message_types = [
        (
            "onsite_conversion."
            "messaging_conversation_started_7d"
        ),
        (
            "messaging_conversation_"
            "started_7d"
        )
    ]

    for account in accounts:

        payload = meta_api_get(
            f'{account["account_id"]}/insights',
            access_token,
            {
                "level":
                    "campaign",

                "time_increment":
                    1,

                "time_range":
                    json.dumps({
                        "since":
                            start.isoformat(),

                        "until":
                            today.isoformat()
                    }),

                "fields":
                    (
                        "date_start,"
                        "date_stop,"
                        "campaign_id,"
                        "campaign_name,"
                        "impressions,"
                        "reach,"
                        "clicks,"
                        "spend,"
                        "actions,"
                        "action_values,"
                        "account_currency"
                    ),

                "limit":
                    500
            }
        )

        while True:

            for row in payload.get(
                "data",
                []
            ):

                actions = row.get(
                    "actions",
                    []
                )

                values = row.get(
                    "action_values",
                    []
                )

                purchases = (
                    meta_action_value(
                        actions,
                        purchase_types
                    )
                )

                leads = (
                    meta_action_value(
                        actions,
                        lead_types
                    )
                )

                messages = (
                    meta_action_value(
                        actions,
                        message_types
                    )
                )

                revenue = (
                    meta_action_value(
                        values,
                        purchase_types
                    )
                )

                upsert_analytics_record(
                    db,
                    user["id"],

                    date=
                        row.get(
                            "date_start"
                        ),

                    provider="meta",

                    account_id=
                        account[
                            "account_id"
                        ],

                    campaign_id=
                        row.get(
                            "campaign_id",
                            ""
                        ),

                    campaign_name=
                        row.get(
                            "campaign_name"
                        ),

                    impressions=
                        int(
                            float(
                                row.get(
                                    "impressions",
                                    0
                                )
                            )
                        ),

                    reach=
                        int(
                            float(
                                row.get(
                                    "reach",
                                    0
                                )
                            )
                        ),

                    clicks=
                        int(
                            float(
                                row.get(
                                    "clicks",
                                    0
                                )
                            )
                        ),

                    messages=
                        int(messages),

                    leads=
                        int(leads),

                    conversions=
                        int(purchases),

                    spend=
                        float(
                            row.get(
                                "spend",
                                0
                            )
                        ),

                    revenue=
                        float(revenue),

                    currency=
                        row.get(
                            "account_currency"
                        )
                        or account[
                            "currency"
                        ]
                        or "USD"
                )

                imported += 1

            next_url = (
                payload
                .get("paging", {})
                .get("next")
            )

            if not next_url:
                break

            payload = meta_api_get(
                next_url
            )

    db.close()

    return {
        "success": True,
        "provider": "meta",
        "accounts":
            len(accounts),
        "rows_imported":
            imported,
        "period": {
            "start":
                start.isoformat(),
            "end":
                today.isoformat()
        }
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
