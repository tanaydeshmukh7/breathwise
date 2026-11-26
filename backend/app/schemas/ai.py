"""Structured Pydantic schemas for AI inputs and validated Qwen outputs."""

from typing import List, Literal, Optional

from pydantic import BaseModel, Field


class RecommendationItem(BaseModel):
    title: str = Field(..., min_length=2, max_length=120)
    reason: str = Field(..., min_length=2, max_length=400)
    action: str = Field(..., min_length=2, max_length=400)
    priority: Literal["high", "medium", "low"] = "medium"


class StructuredAdvisorOutput(BaseModel):
    summary: str = Field(..., min_length=5, max_length=600)
    risk_level: Literal["low", "moderate", "high", "very_high", "severe"]
    recommendations: List[RecommendationItem] = Field(..., min_length=1, max_length=6)
    best_outdoor_window: Optional[str] = Field(default=None, max_length=160)
    precautionary_note: str = Field(
        default="General environmental precaution only — not medical advice.",
        max_length=300,
    )


class DailyRoutineSlot(BaseModel):
    time: str = Field(..., max_length=20)
    phase: Literal["morning", "travel", "outdoor", "work_study", "evening"]
    title: str = Field(..., max_length=120)
    guidance: str = Field(..., max_length=350)
    aqi_context: str = Field(..., max_length=180)
    priority: Literal["high", "medium", "low"] = "medium"


class StructuredDailyRoutineOutput(BaseModel):
    summary: str = Field(..., max_length=500)
    optimal_outdoor_window: str = Field(..., max_length=120)
    slots: List[DailyRoutineSlot] = Field(..., min_length=3, max_length=8)


class IndoorRoomAdvice(BaseModel):
    room: str = Field(..., max_length=60)
    ventilation_action: str = Field(..., max_length=240)
    filtration_and_dust: str = Field(..., max_length=240)
    priority: Literal["high", "medium", "low"] = "medium"


class StructuredIndoorOutput(BaseModel):
    ventilation_verdict: Literal["open_windows", "brief_cross_ventilation", "keep_closed_filter"]
    summary: str = Field(..., max_length=500)
    key_steps: List[str] = Field(default_factory=list, max_length=6)
    room_guidance: List[IndoorRoomAdvice] = Field(default_factory=list, max_length=5)
    sensor_disclaimer: str = Field(
        default=(
            "Indoor air quality is not directly measured without a physical indoor sensor; "
            "recommendations combine outdoor Open-Meteo conditions with household context."
        ),
        max_length=300,
    )


class SustainableAlternativeItem(BaseModel):
    category: Literal[
        "transportation",
        "energy",
        "household",
        "shopping",
        "waste",
        "community",
    ]
    current_behavior: str = Field(..., max_length=160)
    suggested_alternative: str = Field(..., max_length=200)
    why_it_matters: str = Field(..., max_length=280)
    potential_benefit: str = Field(..., max_length=240)
    practical_difficulty: Literal["easy", "moderate", "challenging"]


class StructuredSustainableOutput(BaseModel):
    summary: str = Field(..., max_length=500)
    alternatives: List[SustainableAlternativeItem] = Field(..., min_length=3, max_length=8)


class UserContextInput(BaseModel):
    location_name: str = Field(default="Pune", max_length=100)
    latitude: float = Field(default=18.5204, ge=-90, le=90)
    longitude: float = Field(default=73.8567, ge=-180, le=180)
    household_context: Literal["general", "family_with_children", "elderly_care", "outdoor_athlete", "commuter"] = "general"
    lifestyle_notes: str = Field(default="", max_length=400)
    has_air_purifier: bool = False
    model_id: Optional[str] = Field(default=None, max_length=120)


class AdvisorChatRequest(UserContextInput):
    message: str = Field(..., min_length=2, max_length=1200)
    conversation_id: Optional[str] = None


class AnalyzeAirRequest(UserContextInput):
    pass


class DailyRoutineRequest(UserContextInput):
    pass


class IndoorAdviceRequest(UserContextInput):
    cooking_fuel: Literal["lpg_induction", "mixed", "solid_biomass"] = "lpg_induction"
    uses_incense_or_dhoop: bool = False


class SustainableAlternativesRequest(UserContextInput):
    focus_category: Optional[str] = None


AIStatus = Literal["live_gemini", "live_qwen", "rule_based_fallback"]


class AIResponseEnvelope(BaseModel):
    ai_status: AIStatus
    model_used: str
    provider: str
    fallback_reason: Optional[str] = None
    data_source: str
    reading_timestamp: Optional[str] = None
    conversation_id: Optional[str] = None
    environmental_snapshot: dict
    result: dict
