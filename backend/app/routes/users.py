"""User profile, preferences, and family mode routes."""

from fastapi import APIRouter, Depends, HTTPException, status
from pymongo import DESCENDING

from app.database import DatabaseHandle, get_db, utcnow
from app.schemas.auth import (
    FamilyMemberInput,
    UserProfileUpdateRequest,
    UserPublic,
)
from app.services.auth_service import get_current_user
from app.utils.security import parse_object_id, sanitize_text, serialize_doc

router = APIRouter(prefix="/api/users", tags=["Users & Family"])


@router.get("/profile")
async def get_user_profile(
    current_user: dict = Depends(get_current_user),
    db: DatabaseHandle = Depends(get_db),
):
    prefs = await db.user_preferences.find_one({"user_id": current_user["id"]})
    family = (
        await db.family_profiles.find({"user_id": current_user["id"]})
        .sort("created_at", DESCENDING)
        .to_list(length=20)
    )
    return {
        "user": UserPublic(**current_user),
        "preferences": serialize_doc(prefs)
        or {
            "user_id": current_user["id"],
            "notifications_enabled": True,
            "alert_threshold_naqi": 150,
            "preferred_locations": [],
            "personal_preferences": "",
        },
        "family_profiles": [serialize_doc(m) for m in family],
    }


@router.put("/profile")
async def update_user_profile(
    body: UserProfileUpdateRequest,
    current_user: dict = Depends(get_current_user),
    db: DatabaseHandle = Depends(get_db),
):
    now = utcnow()
    user_updates: dict = {"updated_at": now}
    for field in (
        "name",
        "city",
        "latitude",
        "longitude",
        "age_group",
        "occupation",
        "transport_preference",
        "exercise_habit",
        "household_size",
        "has_air_purifier",
        "preferred_aqi_standard",
    ):
        val = getattr(body, field)
        if val is not None:
            user_updates[field] = sanitize_text(val, 100) if isinstance(val, str) else val

    oid = parse_object_id(current_user["id"])
    await db.users.update_one({"_id": oid}, {"$set": user_updates})

    pref_updates: dict = {"user_id": current_user["id"], "updated_at": now}
    if body.notifications_enabled is not None:
        pref_updates["notifications_enabled"] = body.notifications_enabled
    if body.alert_threshold_naqi is not None:
        pref_updates["alert_threshold_naqi"] = body.alert_threshold_naqi
    if body.preferred_locations is not None:
        pref_updates["preferred_locations"] = [
            loc.model_dump() for loc in body.preferred_locations
        ]
    if body.personal_preferences is not None:
        pref_updates["personal_preferences"] = sanitize_text(
            body.personal_preferences, 400
        )

    await db.user_preferences.update_one(
        {"user_id": current_user["id"]},
        {"$set": pref_updates},
        upsert=True,
    )

    updated_user = await db.users.find_one({"_id": oid})
    if updated_user:
        updated_user.pop("password_hash", None)
    prefs = await db.user_preferences.find_one({"user_id": current_user["id"]})
    return {
        "user": UserPublic(**(serialize_doc(updated_user) or current_user)),
        "preferences": serialize_doc(prefs),
    }


@router.get("/family")
async def list_family_members(
    current_user: dict = Depends(get_current_user),
    db: DatabaseHandle = Depends(get_db),
):
    docs = (
        await db.family_profiles.find({"user_id": current_user["id"]})
        .sort("created_at", DESCENDING)
        .to_list(length=25)
    )
    return {"family_profiles": [serialize_doc(d) for d in docs]}


@router.post("/family", status_code=status.HTTP_201_CREATED)
async def add_family_member(
    body: FamilyMemberInput,
    current_user: dict = Depends(get_current_user),
    db: DatabaseHandle = Depends(get_db),
):
    count = await db.family_profiles.count_documents({"user_id": current_user["id"]})
    if count >= 15:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Maximum of 15 family profiles reached.",
        )
    doc = {
        "user_id": current_user["id"],
        "name": sanitize_text(body.name, 60),
        "member_type": body.member_type,
        "sensitivity_notes": sanitize_text(body.sensitivity_notes, 250),
        "daily_outdoor_minutes": body.daily_outdoor_minutes,
        "created_at": utcnow(),
    }
    res = await db.family_profiles.insert_one(doc)
    doc["_id"] = res.inserted_id
    return {"family_member": serialize_doc(doc)}


@router.delete("/family/{member_id}")
async def delete_family_member(
    member_id: str,
    current_user: dict = Depends(get_current_user),
    db: DatabaseHandle = Depends(get_db),
):
    oid = parse_object_id(member_id)
    res = await db.family_profiles.delete_one(
        {"_id": oid, "user_id": current_user["id"]}
    )
    if res.deleted_count == 0:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Family profile not found.",
        )
    return {"deleted": True, "id": member_id}
