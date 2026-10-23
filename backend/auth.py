"""
auth.py - Authentication & Security Context Module for Agentic Travel Assistant
Implements:
- JWT Token Generation & Verification (HS256)
- Bcrypt Password Hashing
- User management in Neon PostgreSQL
- FastAPI Security Context Dependency (`get_security_context`)
- Guest Session Handling (2-hour TTL)
"""

import os
import uuid
import logging
from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, Any

import jwt
import bcrypt
import psycopg
from fastapi import Request, HTTPException, Security, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, Field

from config import get_secret, DATABASE_URL

logger = logging.getLogger("travel_auth")

# ── Security Configuration ───────────────────────────────────────────────────
JWT_SECRET = get_secret(
    "JWT_SECRET_KEY", 
    default="e7a083fef05830ea1d59841722f5777ed9361a0dcd20e4836a74363ecd05f4ff"
)
JWT_ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_HOURS = 24
GUEST_TOKEN_EXPIRE_HOURS = 2  # 2 hours for Phase 5 TTL Reaper alignment

security_bearer = HTTPBearer(auto_error=False)


# ── Schemas ───────────────────────────────────────────────────────────────────
class UserRegisterRequest(BaseModel):
    email: str = Field(..., description="User email address")
    password: str = Field(..., min_length=6, description="Password (min 6 characters)")
    name: Optional[str] = Field(default="", description="Optional full name")
    role: Optional[str] = Field(default="user", description="user or admin")


class UserLoginRequest(BaseModel):
    email: str = Field(..., description="User email address")
    password: str = Field(..., description="User password")


class SecurityContext(BaseModel):
    user_id: str
    email: Optional[str] = None
    name: Optional[str] = None
    role: str = "guest"  # "admin", "user", "guest"
    tenant_id: str
    is_guest: bool = True

    @property
    def is_admin(self) -> bool:
        return self.role == "admin"


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in_hours: int
    user: Dict[str, Any]


# ── Cryptography Helpers ──────────────────────────────────────────────────────
def hash_password(plain_password: str) -> str:
    """Hash password using bcrypt with standard salt generation."""
    salt = bcrypt.gensalt(rounds=12)
    return bcrypt.hashpw(plain_password.encode("utf-8"), salt).decode("utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify password against bcrypt hash."""
    try:
        return bcrypt.checkpw(plain_password.encode("utf-8"), hashed_password.encode("utf-8"))
    except Exception as e:
        logger.error(f"Password verification error: {e}")
        return False


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """Generate signed JWT token with expiry timestamp and claims."""
    to_encode = data.copy()
    now = datetime.now(timezone.utc)
    if expires_delta:
        expire = now + expires_delta
    else:
        expire = now + timedelta(hours=ACCESS_TOKEN_EXPIRE_HOURS)

    to_encode.update({"iat": now, "exp": expire})
    return jwt.encode(to_encode, JWT_SECRET, algorithm=JWT_ALGORITHM)


def decode_access_token(token: str) -> Dict[str, Any]:
    """Decode and validate JWT token signature and expiration."""
    try:
        return jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Authentication token has expired.")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid authentication token signature.")


# ── Database Operations ───────────────────────────────────────────────────────
def get_db_connection():
    if not DATABASE_URL:
        raise HTTPException(status_code=500, detail="Database URL is not configured.")
    return psycopg.connect(DATABASE_URL)


def register_user(req: UserRegisterRequest) -> Dict[str, Any]:
    email = req.email.strip().lower()
    if not email or "@" not in email:
        raise HTTPException(status_code=400, detail="Invalid email address.")

    user_id = f"usr_{uuid.uuid4().hex[:12]}"
    tenant_id = user_id  # Each registered user is assigned an isolated tenant_id
    pwd_hash = hash_password(req.password)
    
    # Automatically promote admin if email starts with admin@ or explicitly requested
    role = req.role if req.role in ("user", "admin") else "user"
    if email.startswith("admin@"):
        role = "admin"

    try:
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT id FROM users WHERE email = %s;", (email,))
                if cur.fetchone():
                    raise HTTPException(status_code=409, detail="A user with this email already exists.")

                cur.execute(
                    """
                    INSERT INTO users (id, email, password_hash, name, role, tenant_id, is_guest, created_at, last_login)
                    VALUES (%s, %s, %s, %s, %s, %s, FALSE, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
                    RETURNING id, email, name, role, tenant_id, is_guest;
                    """,
                    (user_id, email, pwd_hash, req.name or "", role, tenant_id)
                )
                row = cur.fetchone()
                conn.commit()

                return {
                    "id": row[0],
                    "email": row[1],
                    "name": row[2],
                    "role": row[3],
                    "tenant_id": row[4],
                    "is_guest": row[5],
                }
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Database error registering user: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to create user: {str(e)}")


def authenticate_user(req: UserLoginRequest) -> Dict[str, Any]:
    email = req.email.strip().lower()
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT id, email, password_hash, name, role, tenant_id, is_guest
                    FROM users
                    WHERE email = %s;
                    """,
                    (email,)
                )
                row = cur.fetchone()
                if not row:
                    raise HTTPException(status_code=401, detail="Invalid email or password.")

                user_id, email, pwd_hash, name, role, tenant_id, is_guest = row
                if not verify_password(req.password, pwd_hash):
                    raise HTTPException(status_code=401, detail="Invalid email or password.")

                cur.execute("UPDATE users SET last_login = CURRENT_TIMESTAMP WHERE id = %s;", (user_id,))
                conn.commit()

                return {
                    "id": user_id,
                    "email": email,
                    "name": name,
                    "role": role,
                    "tenant_id": tenant_id or user_id,
                    "is_guest": bool(is_guest),
                }
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Database error authenticating user: {e}")
        raise HTTPException(status_code=500, detail=f"Login failed: {str(e)}")


def create_guest_session() -> Dict[str, Any]:
    """Generates an ephemeral guest identity with 2-hour validity."""
    guest_id = f"guest_{uuid.uuid4().hex[:10]}"
    return {
        "id": guest_id,
        "email": None,
        "name": "Guest Traveler",
        "role": "guest",
        "tenant_id": guest_id,
        "is_guest": True,
    }


# ── FastAPI Security Context Dependency ───────────────────────────────────────
async def get_security_context(
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security_bearer)
) -> SecurityContext:
    """
    Extracts, decodes, and validates the SecurityContext from:
    1. Authorization: Bearer <token>
    2. Fallback: X-Guest-Id header
    3. Ephemeral Guest session fallback if anonymous
    """
    # 1. Bearer Token Check
    if credentials and credentials.credentials:
        token = credentials.credentials
        try:
            payload = decode_access_token(token)
            return SecurityContext(
                user_id=payload.get("sub", payload.get("user_id")),
                email=payload.get("email"),
                name=payload.get("name"),
                role=payload.get("role", "user"),
                tenant_id=payload.get("tenant_id") or payload.get("sub"),
                is_guest=payload.get("is_guest", False),
            )
        except HTTPException:
            raise
        except Exception as e:
            logger.warning(f"Token decode error: {e}")
            raise HTTPException(status_code=401, detail="Invalid authentication credentials.")

    # 2. X-Guest-Id Header Check
    guest_header = request.headers.get("X-Guest-Id")
    if guest_header and guest_header.strip():
        guest_id = guest_header.strip()
        return SecurityContext(
            user_id=guest_id,
            email=None,
            name="Guest Traveler",
            role="guest",
            tenant_id=guest_id,
            is_guest=True,
        )

    # 3. Ephemeral Guest Fallback (Allows smooth frictionless first-time usage)
    anon_guest = f"guest_{uuid.uuid4().hex[:8]}"
    return SecurityContext(
        user_id=anon_guest,
        email=None,
        name="Guest Traveler",
        role="guest",
        tenant_id=anon_guest,
        is_guest=True,
    )


async def require_admin(context: SecurityContext = Depends(get_security_context)) -> SecurityContext:
    """Admin-only route guard for sensitive operations like document ingestion."""
    if not context.is_admin:
        raise HTTPException(
            status_code=403, 
            detail="Admin privileges required to access this resource."
        )
    return context
