"""Routine and Impact Tracker schemas."""

from datetime import datetime
from typing import List, Literal, Optional

from pydantic import BaseModel, Field

from app.schemas.ai import DailyRoutineSlot


class RoutineCreateRequest(BaseModel):
    title: str = Field(..., min_length=2, max_length=120)
    location_name: str = Field(default="Pune", max_length=100)
    summary: str = Field(default="", max_length=500)
    optimal_outdoor_window: str = Field(default="", max_length=120)
    items: List[DailyRoutineSlot] = Field(..., min_length=1, max_length=10)


class RoutineUpdateRequest(BaseModel):
    title: Optional[str] = Field(default=None, min_length=2, max_length=120)
    summary: Optional[str] = Field(default=None, max_length=500)
    items: Optional[List[DailyRoutineSlot]] = None
    is_active: Optional[bool] = None


class SustainableActionCreateRequest(BaseModel):
    category: Literal[
        "transportation",
        "energy",
        "household",
        "shopping",
        "waste",
        "community",
    ]
    action_type: str = Field(..., min_length=2, max_length=80)
    action_name: str = Field(..., min_length=2, max_length=140)
    quantity: float = Field(default=1.0, gt=0, le=500)
    notes: str = Field(default="", max_length=300)


class ImpactActionRecord(BaseModel):
    id: str
    category: str
    action_type: str
    action_name: str
    quantity: float
    unit: str
    estimated_co2e_avoided_kg: Optional[float]
    calculation_basis: str
    is_estimate: bool = True
    completed_at: datetime
