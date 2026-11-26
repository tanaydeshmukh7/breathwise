"""Authentication and user schemas."""

from datetime import datetime
from typing import List, Literal, Optional

from pydantic import BaseModel, EmailStr, Field


class UserRegisterRequest(BaseModel):
    name: str = Field(..., min_length=2, max_length=80)
    email: EmailStr
    password: str = Field(..., min_length=8, max_length=128)
    city: str = Field(default="Pune", max_length=80)
    latitude: float = Field(default=18.5204, ge=-90, le=90)
    longitude: float = Field(default=73.8567, ge=-180, le=180)


class UserLoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=1, max_length=128)


class UserPublic(BaseModel):
    id: str
    name: str
    email: EmailStr
    city: str = "Pune"
    latitude: float = 18.5204
    longitude: float = 73.8567
    age_group: Optional[str] = "adult"
    occupation: Optional[str] = "working_professional"
    transport_preference: Optional[str] = "mixed"
    exercise_habit: Optional[str] = "morning_outdoor"
    household_size: int = 3
    has_air_purifier: bool = False
    preferred_aqi_standard: Literal["indian_naqi", "us_aqi"] = "indian_naqi"
    created_at: Optional[datetime] = None


class AuthTokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserPublic


class FamilyMemberInput(BaseModel):
    name: str = Field(..., min_length=1, max_length=60)
    member_type: Literal["adult", "child", "elderly"]
    sensitivity_notes: str = Field(default="", max_length=250)
    daily_outdoor_minutes: int = Field(default=60, ge=0, le=720)


class FamilyMemberRecord(FamilyMemberInput):
    id: str
    user_id: str
    created_at: datetime


class PreferredLocation(BaseModel):
    label: str = Field(..., min_length=2, max_length=120)
    latitude: float = Field(..., ge=-90, le=90)
    longitude: float = Field(..., ge=-180, le=180)


class UserProfileUpdateRequest(BaseModel):
    name: Optional[str] = Field(default=None, min_length=2, max_length=80)
    city: Optional[str] = Field(default=None, max_length=80)
    latitude: Optional[float] = Field(default=None, ge=-90, le=90)
    longitude: Optional[float] = Field(default=None, ge=-180, le=180)
    age_group: Optional[Literal["child", "young_adult", "adult", "senior"]] = None
    occupation: Optional[str] = Field(default=None, max_length=80)
    transport_preference: Optional[str] = Field(default=None, max_length=80)
    exercise_habit: Optional[str] = Field(default=None, max_length=80)
    household_size: Optional[int] = Field(default=None, ge=1, le=20)
    has_air_purifier: Optional[bool] = None
    preferred_aqi_standard: Optional[Literal["indian_naqi", "us_aqi"]] = None
    notifications_enabled: Optional[bool] = None
    alert_threshold_naqi: Optional[int] = Field(default=None, ge=50, le=450)
    preferred_locations: Optional[List[PreferredLocation]] = None
    personal_preferences: Optional[str] = Field(default=None, max_length=400)
