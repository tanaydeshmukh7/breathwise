"""Personal Impact Tracker routes: summary, logged actions, factor catalog."""

from collections import defaultdict
from datetime import timedelta

from fastapi import APIRouter, Depends, Query, status
from pymongo import DESCENDING

from app.database import DatabaseHandle, get_db, utcnow
from app.schemas.tracker import SustainableActionCreateRequest
from app.services.auth_service import get_current_user
from app.services.impact_calculator import (
    ACTION_FACTOR_CATALOG,
    calculate_action_estimate,
)
from app.utils.security import sanitize_text, serialize_doc

router = APIRouter(prefix="/api/impact", tags=["Personal Impact Tracker"])


@router.get("/catalog")
async def get_action_catalog():
    return {
        "methodology_note": (
            "Quantitative CO2e estimates are computed only for actions with established "
            "emission factors (UK DESNZ/DEFRA transport baselines, CEA India electricity grid baseline). "
            "Qualitative exposure/waste actions do not fabricate CO2e numbers."
        ),
        "actions": [
            {
                "action_type": spec.action_type,
                "category": spec.category,
                "default_label": spec.default_label,
                "unit": spec.unit,
                "kg_co2e_per_unit": spec.kg_co2e_per_unit,
                "basis": spec.basis,
            }
            for spec in ACTION_FACTOR_CATALOG.values()
        ],
    }


@router.get("/summary")
async def get_impact_summary(
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=20, ge=1, le=100),
    current_user: dict = Depends(get_current_user),
    db: DatabaseHandle = Depends(get_db),
):
    flt = {"user_id": current_user["id"]}
    all_actions = (
        await db.sustainable_actions.find(flt)
        .sort("completed_at", DESCENDING)
        .to_list(length=500)
    )

    total_co2e = 0.0
    public_transport_km = 0.0
    walk_cycle_km = 0.0
    energy_saved_kwh = 0.0
    by_category: dict[str, int] = defaultdict(int)
    weekly_buckets: dict[str, dict] = {}

    now = utcnow()
    for i in range(6, -1, -1):
        day_str = (now - timedelta(days=i)).strftime("%Y-%m-%d")
        weekly_buckets[day_str] = {"date": day_str, "actions": 0, "estimated_co2e_kg": 0.0}

    for act in all_actions:
        cat = act.get("category", "household")
        by_category[cat] += 1
        co2 = act.get("estimated_co2e_avoided_kg")
        if isinstance(co2, (int, float)):
            total_co2e += float(co2)
        atype = act.get("action_type", "")
        qty = float(act.get("quantity") or 0.0)
        if atype == "public_transport_km":
            public_transport_km += qty
        elif atype in ("walk_cycle_km", "two_wheeler_replaced_km"):
            walk_cycle_km += qty
        elif atype == "electricity_saved_kwh":
            energy_saved_kwh += qty

        comp = act.get("completed_at")
        if comp is not None:
            day_key = comp.strftime("%Y-%m-%d") if hasattr(comp, "strftime") else str(comp)[:10]
            if day_key in weekly_buckets:
                weekly_buckets[day_key]["actions"] += 1
                if isinstance(co2, (int, float)):
                    weekly_buckets[day_key]["estimated_co2e_kg"] = round(
                        weekly_buckets[day_key]["estimated_co2e_kg"] + float(co2), 3
                    )

    skip = (page - 1) * limit
    paged = all_actions[skip : skip + limit]
    return {
        "total_actions": len(all_actions),
        "total_estimated_co2e_avoided_kg": round(total_co2e, 2),
        "public_transport_km": round(public_transport_km, 1),
        "walk_cycle_km": round(walk_cycle_km, 1),
        "energy_saved_kwh": round(energy_saved_kwh, 1),
        "by_category": dict(by_category),
        "weekly_progress": list(weekly_buckets.values()),
        "actions": [serialize_doc(a) for a in paged],
        "disclaimer": (
            "Estimated emissions avoided are calculated from documented reference factors "
            "and represent environmental footprint reduction, not measured personal pollution exposure."
        ),
    }


@router.post("/actions", status_code=status.HTTP_201_CREATED)
async def log_sustainable_action(
    body: SustainableActionCreateRequest,
    current_user: dict = Depends(get_current_user),
    db: DatabaseHandle = Depends(get_db),
):
    co2_est, unit, basis = calculate_action_estimate(body.action_type, body.quantity)
    now = utcnow()
    doc = {
        "user_id": current_user["id"],
        "category": body.category,
        "action_type": sanitize_text(body.action_type, 80),
        "action_name": sanitize_text(body.action_name, 140),
        "quantity": body.quantity,
        "unit": unit,
        "estimated_co2e_avoided_kg": co2_est,
        "calculation_basis": basis,
        "is_estimate": True,
        "notes": sanitize_text(body.notes, 300),
        "completed_at": now,
    }
    res = await db.sustainable_actions.insert_one(doc)
    doc["_id"] = res.inserted_id
    return {"action": serialize_doc(doc)}
