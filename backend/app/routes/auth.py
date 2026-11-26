"""Authentication routes: register, login, current user."""

from fastapi import APIRouter, Depends, HTTPException, status

from app.config import Settings, get_settings
from app.database import DatabaseHandle, get_db, utcnow
from app.middleware.rate_limit import auth_rate_limiter
from app.schemas.auth import (
    AuthTokenResponse,
    UserLoginRequest,
    UserPublic,
    UserRegisterRequest,
)
from app.services.auth_service import (
    create_access_token,
    get_current_user,
    hash_password,
    verify_password,
)
from app.utils.security import sanitize_text, serialize_doc

router = APIRouter(prefix="/api/auth", tags=["Authentication"])


@router.post(
    "/register",
    response_model=AuthTokenResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(auth_rate_limiter)],
)
async def register_user(
    body: UserRegisterRequest,
    db: DatabaseHandle = Depends(get_db),
    settings: Settings = Depends(get_settings),
):
    email = body.email.lower().strip()
    existing = await db.users.find_one({"email": email})
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An account with this email already exists.",
        )

    now = utcnow()
    user_doc = {
        "name": sanitize_text(body.name, 80),
        "email": email,
        "password_hash": hash_password(body.password),
        "city": sanitize_text(body.city, 80) or settings.DEFAULT_CITY,
        "latitude": body.latitude,
        "longitude": body.longitude,
        "age_group": "adult",
        "occupation": "working_professional",
        "transport_preference": "mixed",
        "exercise_habit": "morning_outdoor",
        "household_size": 3,
        "has_air_purifier": False,
        "preferred_aqi_standard": "indian_naqi",
        "created_at": now,
        "updated_at": now,
    }
    result = await db.users.insert_one(user_doc)
    user_id_str = str(result.inserted_id)

    # Create default preferences document
    await db.user_preferences.update_one(
        {"user_id": user_id_str},
        {
            "$set": {
                "user_id": user_id_str,
                "notifications_enabled": True,
                "alert_threshold_naqi": 150,
                "preferred_locations": [
                    {
                        "label": user_doc["city"],
                        "latitude": body.latitude,
                        "longitude": body.longitude,
                    }
                ],
                "personal_preferences": "",
                "updated_at": now,
            }
        },
        upsert=True,
    )

    user_doc["_id"] = result.inserted_id
    user_doc.pop("password_hash", None)
    serialized = serialize_doc(user_doc) or {}
    token = create_access_token(user_id_str, email, settings)
    return AuthTokenResponse(access_token=token, user=UserPublic(**serialized))


@router.post(
    "/login",
    response_model=AuthTokenResponse,
    dependencies=[Depends(auth_rate_limiter)],
)
async def login_user(
    body: UserLoginRequest,
    db: DatabaseHandle = Depends(get_db),
    settings: Settings = Depends(get_settings),
):
    email = body.email.lower().strip()
    user = await db.users.find_one({"email": email})
    if not user or not verify_password(body.password, user.get("password_hash", "")):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password.",
        )

    user_id_str = str(user["_id"])
    user.pop("password_hash", None)
    serialized = serialize_doc(user) or {}
    token = create_access_token(user_id_str, email, settings)
    return AuthTokenResponse(access_token=token, user=UserPublic(**serialized))


@router.get("/me", response_model=UserPublic)
async def get_me(current_user: dict = Depends(get_current_user)):
    return UserPublic(**current_user)
