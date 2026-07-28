"""Authentication module - Google OAuth, session management, and auth helpers."""

from fastapi import APIRouter, HTTPException, Request, Response, Depends
from fastapi.responses import RedirectResponse
from typing import Optional
import secrets
import uuid
from datetime import datetime, timezone, timedelta
import httpx
from urllib.parse import urlencode

from config import (
    db, logger,
    GOOGLE_CLIENT_ID, GOOGLE_CLIENT_SECRET,
    GOOGLE_REDIRECT_URI, FRONTEND_URL,
    GOOGLE_AUTH_URL, GOOGLE_TOKEN_URL, GOOGLE_USERINFO_URL,
)
from models import User, UpdateUserProfileRequest

router = APIRouter(prefix="/api/auth", tags=["auth"])


async def get_current_user(request: Request) -> User:
    """Get current user from session token (cookie or Authorization header)."""
    session_token = request.cookies.get("session_token")

    if not session_token:
        auth_header = request.headers.get("Authorization")
        if auth_header and auth_header.startswith("Bearer "):
            session_token = auth_header.split(" ")[1]

    if not session_token:
        raise HTTPException(status_code=401, detail="Not authenticated")

    session_doc = await db.user_sessions.find_one(
        {"session_token": session_token},
        {"_id": 0}
    )

    if not session_doc:
        raise HTTPException(status_code=401, detail="Invalid session")

    expires_at = session_doc["expires_at"]
    if isinstance(expires_at, str):
        expires_at = datetime.fromisoformat(expires_at)
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)
    if expires_at < datetime.now(timezone.utc):
        raise HTTPException(status_code=401, detail="Session expired")

    user_doc = await db.users.find_one(
        {"user_id": session_doc["user_id"]},
        {"_id": 0}
    )

    if not user_doc:
        raise HTTPException(status_code=401, detail="User not found")

    return User(**user_doc)


# ==================== GOOGLE OAUTH ENDPOINTS ====================


@router.get("/google/login")
async def google_login():
    """Initiate Google OAuth login flow."""
    if not GOOGLE_CLIENT_ID:
        raise HTTPException(
            status_code=500,
            detail="Google OAuth not configured (GOOGLE_CLIENT_ID missing)"
        )

    params = {
        "client_id": GOOGLE_CLIENT_ID,
        "redirect_uri": GOOGLE_REDIRECT_URI,
        "response_type": "code",
        "scope": "openid email profile",
        "access_type": "offline",
        "state": secrets.token_urlsafe(32),
        "prompt": "select_account",
    }

    auth_url = f"{GOOGLE_AUTH_URL}?{urlencode(params)}"
    return RedirectResponse(url=auth_url)


@router.get("/google/callback")
async def google_callback(
    request: Request,
    code: str = None,
    error: str = None,
    state: str = None,
):
    """Handle Google OAuth callback."""
    if error:
        logger.error(f"Google OAuth error: {error}")
        return RedirectResponse(url=f"{FRONTEND_URL}/?error={error}")

    if not code:
        raise HTTPException(status_code=400, detail="Authorization code required")

    if not GOOGLE_CLIENT_ID or not GOOGLE_CLIENT_SECRET:
        raise HTTPException(status_code=500, detail="Google OAuth not configured")

    try:
        # Exchange authorization code for tokens
        async with httpx.AsyncClient() as client_http:
            token_response = await client_http.post(
                GOOGLE_TOKEN_URL,
                data={
                    "code": code,
                    "client_id": GOOGLE_CLIENT_ID,
                    "client_secret": GOOGLE_CLIENT_SECRET,
                    "redirect_uri": GOOGLE_REDIRECT_URI,
                    "grant_type": "authorization_code",
                },
                headers={"Accept": "application/json"},
            )

            if token_response.status_code != 200:
                logger.error(f"Token exchange failed: {token_response.text}")
                return RedirectResponse(
                    url=f"{FRONTEND_URL}/?error=token_exchange_failed"
                )

            token_data = token_response.json()
            access_token = token_data.get("access_token")

            if not access_token:
                logger.error("No access_token in token response")
                return RedirectResponse(
                    url=f"{FRONTEND_URL}/?error=no_access_token"
                )

            # Get user info from Google
            user_response = await client_http.get(
                GOOGLE_USERINFO_URL,
                headers={"Authorization": f"Bearer {access_token}"},
            )

            if user_response.status_code != 200:
                logger.error(f"Failed to get user info: {user_response.text}")
                return RedirectResponse(
                    url=f"{FRONTEND_URL}/?error=userinfo_failed"
                )

            user_data = user_response.json()
            email = user_data.get("email")
            name = user_data.get("name", email.split("@")[0] if email else "Unknown")
            picture = user_data.get("picture")
            google_id = user_data.get("id")

        # Check if user exists by email or google_id
        existing_user = await db.users.find_one(
            {"$or": [{"email": email}, {"google_id": google_id}]},
            {"_id": 0},
        )

        if existing_user:
            user_id = existing_user["user_id"]
            await db.users.update_one(
                {"user_id": user_id},
                {"$set": {
                    "name": name,
                    "picture": picture,
                    "google_id": google_id,
                    "last_login": datetime.now(timezone.utc).isoformat(),
                }},
            )
        else:
            user_id = f"user_{uuid.uuid4().hex[:12]}"
            new_user = {
                "user_id": user_id,
                "email": email,
                "name": name,
                "picture": picture,
                "google_id": google_id,
                "created_at": datetime.now(timezone.utc).isoformat(),
                "last_login": datetime.now(timezone.utc).isoformat(),
            }
            await db.users.insert_one(new_user)

        # Create session
        session_token = f"st_{secrets.token_urlsafe(32)}"
        expires_at = datetime.now(timezone.utc) + timedelta(days=30)

        session_doc = {
            "user_id": user_id,
            "session_token": session_token,
            "expires_at": expires_at.isoformat(),
            "created_at": datetime.now(timezone.utc).isoformat(),
        }

        await db.user_sessions.delete_many({"user_id": user_id})
        await db.user_sessions.insert_one(session_doc)

        # Redirect to frontend with token
        redirect_url = f"{FRONTEND_URL}/auth/callback?token={session_token}"
        response = RedirectResponse(url=redirect_url)

        response.set_cookie(
            key="session_token",
            value=session_token,
            httponly=True,
            secure=False,  # Set to True in production
            samesite="lax",
            path="/",
            max_age=30 * 24 * 60 * 60,
        )

        return response

    except Exception as e:
        logger.error(f"Google OAuth callback error: {e}")
        return RedirectResponse(url=f"{FRONTEND_URL}/?error=internal_error")


# ==================== SESSION ENDPOINTS ====================


@router.post("/session")
async def create_session(request: Request, response: Response):
    """Exchange session_id for session_token (legacy Emergent auth)."""
    body = await request.json()
    session_id = body.get("session_id")

    if not session_id:
        raise HTTPException(status_code=400, detail="session_id required")

    async with httpx.AsyncClient() as client_http:
        auth_response = await client_http.get(
            "https://demobackend.emergentagent.com/auth/v1/env/oauth/session-data",
            headers={"X-Session-ID": session_id},
        )

        if auth_response.status_code != 200:
            raise HTTPException(status_code=401, detail="Invalid session_id")

        user_data = auth_response.json()

    # Check if user exists
    existing_user = await db.users.find_one(
        {"email": user_data["email"]}, {"_id": 0}
    )

    if existing_user:
        user_id = existing_user["user_id"]
        await db.users.update_one(
            {"user_id": user_id},
            {"$set": {
                "name": user_data["name"],
                "picture": user_data.get("picture"),
            }},
        )
    else:
        user_id = f"user_{uuid.uuid4().hex[:12]}"
        new_user = {
            "user_id": user_id,
            "email": user_data["email"],
            "name": user_data["name"],
            "picture": user_data.get("picture"),
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        await db.users.insert_one(new_user)

    # Create session
    session_token = user_data.get("session_token", f"st_{uuid.uuid4().hex}")
    expires_at = datetime.now(timezone.utc) + timedelta(days=7)

    session_doc = {
        "user_id": user_id,
        "session_token": session_token,
        "expires_at": expires_at.isoformat(),
        "created_at": datetime.now(timezone.utc).isoformat(),
    }

    await db.user_sessions.delete_many({"user_id": user_id})
    await db.user_sessions.insert_one(session_doc)

    response.set_cookie(
        key="session_token",
        value=session_token,
        httponly=True,
        secure=True,
        samesite="none",
        path="/",
        max_age=7 * 24 * 60 * 60,
    )

    user_doc = await db.users.find_one({"user_id": user_id}, {"_id": 0})
    return {"user": user_doc, "session_token": session_token}


@router.get("/me")
async def get_me(user: User = Depends(get_current_user)):
    """Get current authenticated user."""
    return user.model_dump()


@router.post("/logout")
async def logout(request: Request, response: Response):
    """Logout user."""
    session_token = request.cookies.get("session_token")

    if not session_token:
        auth_header = request.headers.get("Authorization")
        if auth_header and auth_header.startswith("Bearer "):
            session_token = auth_header.split(" ")[1]

    if session_token:
        await db.user_sessions.delete_many({"session_token": session_token})

    response.delete_cookie(key="session_token", path="/")
    return {"message": "Logged out successfully"}


@router.put("/profile")
async def update_profile(
    update: UpdateUserProfileRequest,
    user: User = Depends(get_current_user),
):
    """Update user notification settings."""
    update_data = {k: v for k, v in update.model_dump().items() if v is not None}

    if update_data:
        await db.users.update_one(
            {"user_id": user.user_id},
            {"$set": update_data},
        )

    updated_user = await db.users.find_one(
        {"user_id": user.user_id},
        {"_id": 0},
    )

    return updated_user