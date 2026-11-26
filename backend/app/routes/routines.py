"""Saved daily routines CRUD routes with user ownership checks & pagination."""

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pymongo import DESCENDING

from app.database import DatabaseHandle, get_db, utcnow
from app.schemas.tracker import RoutineCreateRequest, RoutineUpdateRequest
from app.services.auth_service import get_current_user
from app.utils.security import parse_object_id, sanitize_text, serialize_doc

router = APIRouter(prefix="/api/routines", tags=["Routines"])


@router.get("")
async def list_routines(
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=10, ge=1, le=50),
    current_user: dict = Depends(get_current_user),
    db: DatabaseHandle = Depends(get_db),
):
    skip = (page - 1) * limit
    flt = {"user_id": current_user["id"]}
    docs = (
        await db.routines.find(flt)
        .sort("created_at", DESCENDING)
        .skip(skip)
        .limit(limit)
        .to_list(length=limit)
    )
    total = await db.routines.count_documents(flt)
    return {
        "page": page,
        "limit": limit,
        "total": total,
        "routines": [serialize_doc(d) for d in docs],
    }


@router.post("", status_code=status.HTTP_201_CREATED)
async def create_routine(
    body: RoutineCreateRequest,
    current_user: dict = Depends(get_current_user),
    db: DatabaseHandle = Depends(get_db),
):
    now = utcnow()
    doc = {
        "user_id": current_user["id"],
        "title": sanitize_text(body.title, 120),
        "location_name": sanitize_text(body.location_name, 100),
        "summary": sanitize_text(body.summary, 500),
        "optimal_outdoor_window": sanitize_text(body.optimal_outdoor_window, 120),
        "items": [slot.model_dump() for slot in body.items],
        "is_active": True,
        "created_at": now,
        "updated_at": now,
    }
    res = await db.routines.insert_one(doc)
    doc["_id"] = res.inserted_id
    return {"routine": serialize_doc(doc)}


@router.put("/{routine_id}")
async def update_routine(
    routine_id: str,
    body: RoutineUpdateRequest,
    current_user: dict = Depends(get_current_user),
    db: DatabaseHandle = Depends(get_db),
):
    oid = parse_object_id(routine_id)
    updates: dict = {"updated_at": utcnow()}
    if body.title is not None:
        updates["title"] = sanitize_text(body.title, 120)
    if body.summary is not None:
        updates["summary"] = sanitize_text(body.summary, 500)
    if body.items is not None:
        updates["items"] = [slot.model_dump() for slot in body.items]
    if body.is_active is not None:
        updates["is_active"] = body.is_active

    res = await db.routines.update_one(
        {"_id": oid, "user_id": current_user["id"]},
        {"$set": updates},
    )
    if res.matched_count == 0:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Routine not found.",
        )
    updated = await db.routines.find_one({"_id": oid, "user_id": current_user["id"]})
    return {"routine": serialize_doc(updated)}


@router.delete("/{routine_id}")
async def delete_routine(
    routine_id: str,
    current_user: dict = Depends(get_current_user),
    db: DatabaseHandle = Depends(get_db),
):
    oid = parse_object_id(routine_id)
    res = await db.routines.delete_one({"_id": oid, "user_id": current_user["id"]})
    if res.deleted_count == 0:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Routine not found.",
        )
    return {"deleted": True, "id": routine_id}
