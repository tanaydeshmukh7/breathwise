"""BreatheWise AI Engine powered by Google Gemini (google-genai SDK) with optional
Hugging Face Inference Providers (Qwen) support retained for provider switching.
"""

from __future__ import annotations

import asyncio
import json
import logging
import re
from typing import Any, Dict, List, Optional, Tuple, Type, TypeVar

from google import genai
from google.genai import errors as genai_errors
from google.genai import types as genai_types
from openai import APIConnectionError, APIStatusError, APITimeoutError, AsyncOpenAI, RateLimitError
from pydantic import BaseModel, ValidationError

from app.config import Settings
from app.prompts.templates import (
    build_advisor_chat_messages,
    build_air_analysis_messages,
    build_daily_routine_messages,
    build_impact_explanation_messages,
    build_indoor_advice_messages,
    build_sustainable_alternatives_messages,
)
from app.schemas.ai import (
    AIStatus,
    DailyRoutineSlot,
    IndoorRoomAdvice,
    RecommendationItem,
    StructuredAdvisorOutput,
    StructuredDailyRoutineOutput,
    StructuredIndoorOutput,
    StructuredSustainableOutput,
    SustainableAlternativeItem,
)

logger = logging.getLogger(__name__)
TModel = TypeVar("TModel", bound=BaseModel)


def _extract_json_object(raw_text: str) -> Dict[str, Any]:
    """Extract and parse a JSON object from raw model output safely."""
    cleaned = raw_text.strip()
    # Strip <think>...</think> blocks emitted by reasoning Qwen3 variants if present
    cleaned = re.sub(r"<think>.*?</think>", "", cleaned, flags=re.DOTALL).strip()
    if cleaned.startswith("```"):
        cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned)
        cleaned = re.sub(r"\s*```$", "", cleaned).strip()

    try:
        parsed = json.loads(cleaned)
        if isinstance(parsed, dict):
            return parsed
    except json.JSONDecodeError:
        pass

    start = cleaned.find("{")
    end = cleaned.rfind("}")
    if start != -1 and end != -1 and end > start:
        snippet = cleaned[start : end + 1]
        parsed = json.loads(snippet)
        if isinstance(parsed, dict):
            return parsed

    raise ValueError("Model response did not contain a valid JSON object.")


def _risk_from_naqi(naqi: Optional[int]) -> str:
    if naqi is None:
        return "moderate"
    if naqi <= 50:
        return "low"
    if naqi <= 100:
        return "moderate"
    if naqi <= 200:
        return "high"
    if naqi <= 300:
        return "very_high"
    return "severe"


class AIService:
    """Orchestrates Google Gemini (active) or HF Qwen inference with strict Pydantic validation & fallbacks."""

    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    @property
    def active_provider_key(self) -> str:
        return self.settings.active_ai_provider

    def _resolve_gemini_model(self, requested_model: Optional[str]) -> str:
        """Return the explicitly requested model or configured GEMINI_MODEL without silent substitution."""
        if requested_model is not None:
            cleaned = requested_model.strip()
            if cleaned:
                return cleaned
        return self.settings.GEMINI_MODEL.strip()

    @staticmethod
    def _is_valid_gemini_model_id(model_name: str) -> bool:
        return bool(re.fullmatch(r"(?:models/)?[A-Za-z0-9][A-Za-z0-9._-]{0,119}", model_name))

    def _create_gemini_client(self) -> Optional[genai.Client]:
        api_key = self.settings.GEMINI_API_KEY.strip()
        if not api_key:
            return None
        timeout_ms = max(1000, int(self.settings.GEMINI_TIMEOUT_SECONDS * 1000))
        return genai.Client(
            api_key=api_key,
            http_options=genai_types.HttpOptions(timeout=timeout_ms),
        )

    @staticmethod
    def _messages_to_gemini_payload(
        messages: list[dict[str, str]]
    ) -> Tuple[Optional[str], List[genai_types.Content]]:
        system_parts: List[str] = []
        contents: List[genai_types.Content] = []
        for msg in messages:
            role = msg.get("role", "user")
            text = (msg.get("content") or "").strip()
            if not text:
                continue
            if role == "system":
                system_parts.append(text)
            elif role == "assistant":
                contents.append(
                    genai_types.Content(
                        role="model",
                        parts=[genai_types.Part.from_text(text=text)],
                    )
                )
            else:
                contents.append(
                    genai_types.Content(
                        role="user",
                        parts=[genai_types.Part.from_text(text=text)],
                    )
                )
        system_instruction = "\n\n".join(system_parts) if system_parts else None
        return system_instruction, contents

    @staticmethod
    def _format_gemini_error(
        exc: genai_errors.APIError, model_name: str
    ) -> Tuple[Optional[int], str]:
        code = getattr(exc, "code", None)
        msg_raw = str(getattr(exc, "message", "") or str(exc))
        msg_upper = msg_raw.upper()

        if code in (401, 403) or "API_KEY_INVALID" in msg_upper or "API KEY NOT VALID" in msg_upper:
            return (
                code or 401,
                f"HTTP {code or 401} Invalid or unauthorized GEMINI_API_KEY for {model_name}.",
            )
        if code == 429 or "RESOURCE_EXHAUSTED" in msg_upper or "QUOTA" in msg_upper:
            return (
                429,
                f"HTTP 429 Gemini API rate limit or quota exhausted for {model_name}.",
            )
        if code == 404 or "NOT_FOUND" in msg_upper:
            return (
                404,
                f"HTTP 404 Gemini model '{model_name}' is unavailable or not found.",
            )
        if code == 503 or "UNAVAILABLE" in msg_upper:
            return (
                503,
                f"HTTP 503 Gemini model '{model_name}' is temporarily unavailable due to high demand.",
            )
        if code == 504 or "DEADLINE_EXCEEDED" in msg_upper:
            return (
                504,
                f"HTTP 504 Gemini request to '{model_name}' exceeded server deadline.",
            )
        return (
            code,
            f"HTTP {code} Gemini API error for {model_name}.",
        )

    async def verify_gemini_connection(
        self, requested_model: Optional[str] = None
    ) -> Dict[str, Any]:
        """Perform one minimal completion against the configured Gemini model without fallback substitution."""
        chosen_model = self._resolve_gemini_model(requested_model)
        provider_label = "google_gemini"
        if not self._is_valid_gemini_model_id(chosen_model):
            return {
                "ok": False,
                "http_status": 400,
                "model_id": chosen_model,
                "provider": provider_label,
                "response": None,
                "error": f"Invalid Gemini model identifier '{chosen_model}'.",
            }
        client = self._create_gemini_client()
        if client is None:
            return {
                "ok": False,
                "http_status": None,
                "model_id": chosen_model,
                "provider": provider_label,
                "response": None,
                "error": "GEMINI_API_KEY is not configured in backend environment.",
            }

        try:
            resp = await asyncio.wait_for(
                client.aio.models.generate_content(
                    model=chosen_model,
                    contents='Respond strictly with JSON: {"status": "ok", "service": "BreatheWise"}',
                    config=genai_types.GenerateContentConfig(
                        temperature=0.0,
                        max_output_tokens=256,
                        response_mime_type="application/json",
                    ),
                ),
                timeout=self.settings.GEMINI_TIMEOUT_SECONDS,
            )
            text = resp.text if hasattr(resp, "text") else None
            raw_ver = getattr(resp, "model_version", None)
            actual_model = (
                raw_ver.strip()
                if isinstance(raw_ver, str) and raw_ver.strip()
                else chosen_model
            )
            return {
                "ok": True,
                "http_status": 200,
                "model_id": actual_model,
                "provider": provider_label,
                "response": text,
                "error": None,
            }
        except genai_errors.APIError as exc:
            code, msg = self._format_gemini_error(exc, chosen_model)
            return {
                "ok": False,
                "http_status": code,
                "model_id": chosen_model,
                "provider": provider_label,
                "response": None,
                "error": msg,
            }
        except (asyncio.TimeoutError, TimeoutError):
            return {
                "ok": False,
                "http_status": 504,
                "model_id": chosen_model,
                "provider": provider_label,
                "response": None,
                "error": f"Gemini request to {chosen_model} timed out after {self.settings.GEMINI_TIMEOUT_SECONDS}s.",
            }
        except Exception as exc:
            if "timeout" in type(exc).__name__.lower():
                return {
                    "ok": False,
                    "http_status": 504,
                    "model_id": chosen_model,
                    "provider": provider_label,
                    "response": None,
                    "error": f"Gemini request to {chosen_model} timed out ({type(exc).__name__}).",
                }
            return {
                "ok": False,
                "http_status": None,
                "model_id": chosen_model,
                "provider": provider_label,
                "response": None,
                "error": f"Gemini connection error ({type(exc).__name__}).",
            }

    async def _invoke_gemini_structured(
        self,
        messages: list[dict[str, str]],
        schema_cls: Type[TModel],
        requested_model: Optional[str] = None,
        max_tokens: int = 1200,
    ) -> Tuple[Optional[TModel], str, Optional[str]]:
        """Call ONLY the configured/requested Gemini model and validate output with Pydantic."""
        chosen_model = self._resolve_gemini_model(requested_model)
        if not self._is_valid_gemini_model_id(chosen_model):
            return (
                None,
                chosen_model,
                f"Invalid Gemini model identifier '{chosen_model}'.",
            )
        client = self._create_gemini_client()
        if client is None:
            return (
                None,
                chosen_model,
                "GEMINI_API_KEY is not configured; returning deterministic advisory from verified Open-Meteo data.",
            )

        system_instruction, contents = self._messages_to_gemini_payload(messages)
        try:
            resp = await asyncio.wait_for(
                client.aio.models.generate_content(
                    model=chosen_model,
                    contents=contents,
                    config=genai_types.GenerateContentConfig(
                        system_instruction=system_instruction,
                        temperature=0.2,
                        max_output_tokens=max(4096, max_tokens),
                        response_mime_type="application/json",
                        response_schema=schema_cls,
                    ),
                ),
                timeout=self.settings.GEMINI_TIMEOUT_SECONDS,
            )
            content = resp.text if hasattr(resp, "text") else None
            if not content:
                return (None, chosen_model, f"Empty response from Gemini model {chosen_model}.")
            payload = _extract_json_object(content)
            validated = schema_cls.model_validate(payload)
            raw_ver = getattr(resp, "model_version", None)
            actual_model = (
                raw_ver.strip()
                if isinstance(raw_ver, str) and raw_ver.strip()
                else chosen_model
            )
            return (validated, actual_model, None)
        except genai_errors.APIError as exc:
            _, err_msg = self._format_gemini_error(exc, chosen_model)
            logger.warning(err_msg)
            return (None, chosen_model, err_msg)
        except (asyncio.TimeoutError, TimeoutError):
            err_msg = f"Gemini API timed out after {self.settings.GEMINI_TIMEOUT_SECONDS}s for {chosen_model}."
            logger.warning(err_msg)
            return (None, chosen_model, err_msg)
        except (ValueError, ValidationError, json.JSONDecodeError) as exc:
            err_msg = f"Malformed AI output from {chosen_model} failed schema validation ({type(exc).__name__})."
            logger.warning(err_msg)
            return (None, chosen_model, err_msg)
        except Exception as exc:
            if "timeout" in type(exc).__name__.lower():
                err_msg = f"Gemini API timed out ({type(exc).__name__}) for {chosen_model}."
            else:
                err_msg = f"Gemini API transport/unexpected error ({type(exc).__name__}) for {chosen_model}."
            logger.warning(err_msg)
            return (None, chosen_model, err_msg)

    async def verify_ai_connection(
        self, requested_model: Optional[str] = None
    ) -> Dict[str, Any]:
        if self.active_provider_key == "huggingface":
            return await self.verify_qwen_connection(requested_model=requested_model)
        return await self.verify_gemini_connection(requested_model=requested_model)

    async def _invoke_active_structured(
        self,
        messages: list[dict[str, str]],
        schema_cls: Type[TModel],
        requested_model: Optional[str] = None,
        max_tokens: int = 1200,
    ) -> Tuple[Optional[TModel], AIStatus, str, Optional[str]]:
        """Invoke the active AI provider and return (validated_or_None, live_status_tag, model_used, err)."""
        if self.active_provider_key == "huggingface":
            validated, model_used, err = await self._invoke_qwen_structured(
                messages, schema_cls, requested_model=requested_model, max_tokens=max_tokens
            )
            return (validated, "live_qwen", model_used, err)
        validated, model_used, err = await self._invoke_gemini_structured(
            messages, schema_cls, requested_model=requested_model, max_tokens=max_tokens
        )
        return (validated, "live_gemini", model_used, err)

    def _resolve_model(self, requested_model: Optional[str]) -> str:
        if requested_model is not None:
            cleaned = requested_model.strip()
            if cleaned:
                return cleaned
        return self.settings.HF_MODEL.strip()

    def _create_client(self) -> Optional[AsyncOpenAI]:
        token = self.settings.HF_TOKEN.strip()
        if not token:
            return None
        return AsyncOpenAI(
            base_url=self.settings.HF_BASE_URL,
            api_key=token,
            timeout=self.settings.HF_TIMEOUT_SECONDS,
        )

    @staticmethod
    def _format_api_error(exc: APIStatusError, model_name: str) -> tuple[Optional[int], str]:
        code = getattr(exc, "status_code", None)
        if code == 402:
            return (
                402,
                f"HTTP 402 Payment Required for {model_name}: Hugging Face Inference Providers credits required or exhausted.",
            )
        if code == 401:
            return (
                401,
                f"HTTP 401 Unauthorized for {model_name}: Hugging Face token is invalid or lacks Inference Providers permission.",
            )
        if code == 403:
            return (
                403,
                f"HTTP 403 Forbidden for {model_name}: Hugging Face token does not have access to this model/provider.",
            )
        if code == 429:
            return (
                429,
                f"HTTP 429 Rate Limit Exceeded for {model_name}: Hugging Face Inference Providers quota/rate limit hit.",
            )
        return (
            code,
            f"HTTP {code} error from Hugging Face router for {model_name}.",
        )

    async def verify_qwen_connection(
        self, requested_model: Optional[str] = None
    ) -> Dict[str, Any]:
        """Perform one minimal completion against the configured Qwen model without fallback substitution."""
        chosen_model = self._resolve_model(requested_model)
        provider_url = self.settings.HF_BASE_URL
        client = self._create_client()
        if client is None:
            return {
                "ok": False,
                "http_status": None,
                "model_id": chosen_model,
                "provider": provider_url,
                "response": None,
                "error": "HF_TOKEN is not configured in backend environment.",
            }

        try:
            raw_resp = await client.chat.completions.with_raw_response.create(
                model=chosen_model,
                messages=[
                    {
                        "role": "user",
                        "content": 'Respond strictly with JSON: {"status": "ok", "service": "BreatheWise"}',
                    }
                ],
                temperature=0.0,
                max_tokens=40,
            )
            http_status = raw_resp.status_code
            parsed = raw_resp.parse()
            content = parsed.choices[0].message.content if parsed.choices else None
            actual_model = getattr(parsed, "model", None) or chosen_model
            return {
                "ok": True,
                "http_status": http_status,
                "model_id": actual_model,
                "provider": provider_url,
                "response": content,
                "error": None,
            }
        except RateLimitError as exc:
            code, msg = self._format_api_error(exc, chosen_model)
            return {
                "ok": False,
                "http_status": code or 429,
                "model_id": chosen_model,
                "provider": provider_url,
                "response": None,
                "error": msg,
            }
        except APIStatusError as exc:
            code, msg = self._format_api_error(exc, chosen_model)
            return {
                "ok": False,
                "http_status": code,
                "model_id": chosen_model,
                "provider": provider_url,
                "response": None,
                "error": msg,
            }
        except APITimeoutError:
            return {
                "ok": False,
                "http_status": 504,
                "model_id": chosen_model,
                "provider": provider_url,
                "response": None,
                "error": f"Request to {chosen_model} timed out after {self.settings.HF_TIMEOUT_SECONDS}s.",
            }
        except APIConnectionError as exc:
            return {
                "ok": False,
                "http_status": None,
                "model_id": chosen_model,
                "provider": provider_url,
                "response": None,
                "error": f"Network error connecting to Hugging Face router ({type(exc).__name__}).",
            }
        except Exception as exc:
            return {
                "ok": False,
                "http_status": None,
                "model_id": chosen_model,
                "provider": provider_url,
                "response": None,
                "error": f"Unexpected verification error ({type(exc).__name__}).",
            }

    async def _invoke_qwen_structured(
        self,
        messages: list[dict[str, str]],
        schema_cls: Type[TModel],
        requested_model: Optional[str] = None,
        max_tokens: int = 900,
    ) -> Tuple[Optional[TModel], str, Optional[str]]:
        """Call ONLY the configured/requested Qwen model through HF router and validate with Pydantic.

        Never silently substitutes a different model.
        Returns (validated_model_or_None, model_used, error_reason_or_None).
        """
        chosen_model = self._resolve_model(requested_model)
        client = self._create_client()
        if client is None:
            return (
                None,
                chosen_model,
                "HF_TOKEN is not configured; returning deterministic advisory from verified Open-Meteo data.",
            )

        try:
            response = await client.chat.completions.create(
                model=chosen_model,
                messages=messages,  # type: ignore[arg-type]
                temperature=0.2,
                max_tokens=max_tokens,
            )
            content = response.choices[0].message.content if response.choices else None
            if not content:
                return (None, chosen_model, f"Empty response from {chosen_model}.")
            payload = _extract_json_object(content)
            validated = schema_cls.model_validate(payload)
            return (validated, chosen_model, None)
        except RateLimitError as exc:
            _, err_msg = self._format_api_error(exc, chosen_model)
            logger.warning(err_msg)
            return (None, chosen_model, err_msg)
        except APIStatusError as exc:
            _, err_msg = self._format_api_error(exc, chosen_model)
            logger.warning(err_msg)
            return (None, chosen_model, err_msg)
        except APITimeoutError:
            err_msg = f"Hugging Face router timed out after {self.settings.HF_TIMEOUT_SECONDS}s for {chosen_model}."
            logger.warning(err_msg)
            return (None, chosen_model, err_msg)
        except APIConnectionError as exc:
            err_msg = f"Hugging Face router connection error ({type(exc).__name__}) for {chosen_model}."
            logger.warning(err_msg)
            return (None, chosen_model, err_msg)
        except (ValueError, ValidationError, json.JSONDecodeError) as exc:
            err_msg = f"Malformed AI output from {chosen_model} failed schema validation ({type(exc).__name__})."
            logger.warning(err_msg)
            return (None, chosen_model, err_msg)
        except Exception as exc:
            err_msg = f"Unexpected AI service error ({type(exc).__name__}) for {chosen_model}."
            logger.exception("Unexpected error invoking %s", chosen_model)
            return (None, chosen_model, err_msg)

    async def analyze_air_quality(
        self,
        env_snapshot: Dict[str, Any],
        user_context: Dict[str, Any],
        requested_model: Optional[str] = None,
    ) -> Tuple[StructuredAdvisorOutput, AIStatus, str, Optional[str]]:
        messages = build_air_analysis_messages(env_snapshot, user_context)
        validated, live_tag, model_used, err = await self._invoke_active_structured(
            messages, StructuredAdvisorOutput, requested_model
        )
        if validated is not None:
            return (validated, live_tag, model_used, None)
        return (
            self._fallback_air_analysis(env_snapshot, user_context),
            "rule_based_fallback",
            model_used,
            err,
        )

    async def chat_advisor(
        self,
        question: str,
        env_snapshot: Dict[str, Any],
        user_context: Dict[str, Any],
        forecast_summary: Optional[Dict[str, Any]],
        history: list[dict[str, str]],
        requested_model: Optional[str] = None,
    ) -> Tuple[StructuredAdvisorOutput, AIStatus, str, Optional[str]]:
        messages = build_advisor_chat_messages(
            question, env_snapshot, user_context, forecast_summary, history
        )
        validated, live_tag, model_used, err = await self._invoke_active_structured(
            messages, StructuredAdvisorOutput, requested_model
        )
        if validated is not None:
            return (validated, live_tag, model_used, None)
        return (
            self._fallback_advisor_chat(question, env_snapshot, user_context, forecast_summary),
            "rule_based_fallback",
            model_used,
            err,
        )

    async def generate_daily_routine(
        self,
        env_snapshot: Dict[str, Any],
        user_context: Dict[str, Any],
        forecast_summary: Dict[str, Any],
        requested_model: Optional[str] = None,
    ) -> Tuple[StructuredDailyRoutineOutput, AIStatus, str, Optional[str]]:
        messages = build_daily_routine_messages(
            env_snapshot, user_context, forecast_summary
        )
        validated, live_tag, model_used, err = await self._invoke_active_structured(
            messages, StructuredDailyRoutineOutput, requested_model, max_tokens=1400
        )
        if validated is not None:
            return (validated, live_tag, model_used, None)
        return (
            self._fallback_daily_routine(env_snapshot, forecast_summary),
            "rule_based_fallback",
            model_used,
            err,
        )

    async def generate_indoor_advice(
        self,
        env_snapshot: Dict[str, Any],
        user_context: Dict[str, Any],
        indoor_context: Dict[str, Any],
        requested_model: Optional[str] = None,
    ) -> Tuple[StructuredIndoorOutput, AIStatus, str, Optional[str]]:
        messages = build_indoor_advice_messages(
            env_snapshot, user_context, indoor_context
        )
        validated, live_tag, model_used, err = await self._invoke_active_structured(
            messages, StructuredIndoorOutput, requested_model, max_tokens=1200
        )
        if validated is not None:
            return (validated, live_tag, model_used, None)
        return (
            self._fallback_indoor_advice(env_snapshot, user_context, indoor_context),
            "rule_based_fallback",
            model_used,
            err,
        )

    async def generate_sustainable_alternatives(
        self,
        env_snapshot: Dict[str, Any],
        user_context: Dict[str, Any],
        focus_category: Optional[str] = None,
        requested_model: Optional[str] = None,
    ) -> Tuple[StructuredSustainableOutput, AIStatus, str, Optional[str]]:
        messages = build_sustainable_alternatives_messages(
            env_snapshot, user_context, focus_category
        )
        validated, live_tag, model_used, err = await self._invoke_active_structured(
            messages, StructuredSustainableOutput, requested_model, max_tokens=1400
        )
        if validated is not None:
            return (validated, live_tag, model_used, None)
        return (
            self._fallback_sustainable_alternatives(env_snapshot, focus_category),
            "rule_based_fallback",
            model_used,
            err,
        )

    async def explain_impact(
        self,
        impact_summary: Dict[str, Any],
        user_context: Dict[str, Any],
        requested_model: Optional[str] = None,
    ) -> Tuple[StructuredAdvisorOutput, AIStatus, str, Optional[str]]:
        messages = build_impact_explanation_messages(impact_summary, user_context)
        validated, live_tag, model_used, err = await self._invoke_active_structured(
            messages, StructuredAdvisorOutput, requested_model
        )
        if validated is not None:
            return (validated, live_tag, model_used, None)
        total_co2 = impact_summary.get("total_estimated_co2e_avoided_kg", 0.0)
        total_actions = impact_summary.get("total_actions", 0)
        fallback = StructuredAdvisorOutput(
            summary=(
                f"You have logged {total_actions} sustainable actions with an estimated "
                f"{total_co2} kg CO2e avoided based on documented emission factors. "
                "These estimates reflect emission savings rather than direct indoor or personal exposure measurements."
            ),
            risk_level="low",
            precautionary_note=(
                "CO2e values are factor-based estimates using DEFRA/DESNZ and CEA India baselines, "
                "separate from ambient air quality readings."
            ),
            recommendations=[
                RecommendationItem(
                    title="Prioritize short-trip mode shifts",
                    reason="Replacing short urban car or two-wheeler trips reduces both tailpipe NO2 and particulate resuspension.",
                    action="Log walking, cycling, or metro trips when ambient NAQI is within safe limits.",
                    priority="medium",
                )
            ],
        )
        return (fallback, "rule_based_fallback", model_used, err)

    # ------------------------------------------------------------------
    # Deterministic, strictly data-grounded fallbacks (never fabricate data)
    # ------------------------------------------------------------------

    @staticmethod
    def _extract_metrics(env_snapshot: Dict[str, Any]) -> Dict[str, Any]:
        aq = env_snapshot.get("air_quality") or {}
        weather = env_snapshot.get("weather") or {}
        indices = aq.get("indices") or {}
        naqi = indices.get("indian_naqi") or {}
        us_aqi = indices.get("us_aqi") or {}
        pollutants = aq.get("pollutants") or {}
        return {
            "city": (aq.get("location") or {}).get("name", "your area"),
            "naqi": naqi.get("value"),
            "naqi_cat": naqi.get("category", "Unavailable"),
            "dominant": naqi.get("dominant_pollutant"),
            "us_aqi": us_aqi.get("value"),
            "pm2_5": (pollutants.get("pm2_5") or {}).get("value"),
            "pm10": (pollutants.get("pm10") or {}).get("value"),
            "no2": (pollutants.get("nitrogen_dioxide") or {}).get("value"),
            "o3": (pollutants.get("ozone") or {}).get("value"),
            "temp": (weather.get("temperature") or {}).get("value"),
            "humidity": (weather.get("humidity") or {}).get("value"),
            "wind_speed": (weather.get("wind") or {}).get("speed"),
            "condition": weather.get("condition", "Unavailable"),
        }

    def _fallback_air_analysis(
        self, env_snapshot: Dict[str, Any], user_context: Dict[str, Any]
    ) -> StructuredAdvisorOutput:
        m = self._extract_metrics(env_snapshot)
        naqi = m["naqi"]
        risk = _risk_from_naqi(naqi)
        sensitive = user_context.get("household_context") in (
            "family_with_children",
            "elderly_care",
        )
        summary = (
            f"In {m['city']}, CPCB Indian NAQI is {naqi if naqi is not None else 'unavailable'} "
            f"({m['naqi_cat']}) with PM2.5 at {m['pm2_5']} μg/m³ and PM10 at {m['pm10']} μg/m³. "
            f"Current weather is {m['condition']} at {m['temp']}°C with {m['wind_speed']} km/h winds."
        )
        recs: List[RecommendationItem] = []
        if naqi is not None and naqi > 100:
            recs.append(
                RecommendationItem(
                    title="Shift vigorous exercise indoors",
                    reason=f"Indian NAQI is {naqi} ({m['naqi_cat']}), led by {m['dominant'] or 'particulate matter'}.",
                    action="Avoid intense outdoor cardio during peak pollution; choose indoor stretching or strength training.",
                    priority="high",
                )
            )
            recs.append(
                RecommendationItem(
                    title="Limit outdoor window ventilation during peak haze",
                    reason=f"Outdoor PM2.5 is {m['pm2_5']} μg/m³ with wind at {m['wind_speed']} km/h.",
                    action=(
                        "Run your HEPA purifier if available and ventilate briefly only when afternoon winds disperse pollutants."
                        if user_context.get("has_air_purifier")
                        else "Keep roadside-facing windows closed during peak traffic and use kitchen exhaust when cooking."
                    ),
                    priority="high" if sensitive else "medium",
                )
            )
        else:
            recs.append(
                RecommendationItem(
                    title="Use current conditions for planned outdoor time",
                    reason=f"Indian NAQI is {naqi if naqi is not None else 'within lower range'} ({m['naqi_cat']}).",
                    action="Schedule walks away from heavy traffic corridors and monitor afternoon ozone changes.",
                    priority="medium",
                )
            )
            recs.append(
                RecommendationItem(
                    title="Cross-ventilate living spaces briefly",
                    reason=f"Outdoor PM2.5 ({m['pm2_5']} μg/m³) and {m['humidity']}% humidity support natural airing.",
                    action="Open opposite windows for 15–20 minutes while keeping indoor smoke sources (incense/frying) minimal.",
                    priority="low",
                )
            )

        recs.append(
            RecommendationItem(
                title="Reduce personal commute exposure & emissions",
                reason=f"Ambient NO2 is {m['no2']} μg/m³ near traffic corridors.",
                action="Choose metro/bus or less congested side streets, and wear a well-fitted N95 mask near busy roads if sensitive.",
                priority="medium",
            )
        )
        return StructuredAdvisorOutput(
            summary=summary,
            risk_level=risk,  # type: ignore[arg-type]
            best_outdoor_window=(
                "Mid-afternoon (13:00–16:00) typically offers stronger thermal mixing; check hourly chart."
                if naqi is not None and naqi > 100
                else "Current conditions allow moderate outdoor activity; check hourly trend before evening."
            ),
            precautionary_note=(
                "General environmental precaution only — not medical advice. "
                + ("Extra caution advised for children and elderly family members." if sensitive else "")
            ).strip(),
            recommendations=recs[:3],
        )

    def _fallback_advisor_chat(
        self,
        question: str,
        env_snapshot: Dict[str, Any],
        user_context: Dict[str, Any],
        forecast_summary: Optional[Dict[str, Any]],
    ) -> StructuredAdvisorOutput:
        base = self._fallback_air_analysis(env_snapshot, user_context)
        m = self._extract_metrics(env_snapshot)
        q_lower = question.lower()
        best_window = (forecast_summary or {}).get("best_window") or base.best_outdoor_window

        if "window" in q_lower or "ventilat" in q_lower:
            verdict = (
                "keep windows mostly closed during high particulate hours and use kitchen exhaust"
                if (m["naqi"] or 0) > 100
                else "briefly cross-ventilate away from traffic-facing roads"
            )
            summary = (
                f"Based on {m['city']}'s verified reading (Indian NAQI {m['naqi']} — {m['naqi_cat']}, "
                f"PM2.5 {m['pm2_5']} μg/m³, wind {m['wind_speed']} km/h), it is better to {verdict}. "
                "Note that indoor air quality is not directly measured without an indoor sensor."
            )
        elif "walk" in q_lower or "exercise" in q_lower or "outside" in q_lower or "run" in q_lower:
            summary = (
                f"In {m['city']}, current Indian NAQI is {m['naqi']} ({m['naqi_cat']}) with PM2.5 at {m['pm2_5']} μg/m³. "
                f"Best forecast window: {best_window}. "
                + (
                    "Prefer light indoor workouts until particulate levels ease."
                    if (m["naqi"] or 0) > 150
                    else "Prefer parks or low-traffic streets during the cleaner forecast window."
                )
            )
        else:
            summary = base.summary

        return StructuredAdvisorOutput(
            summary=summary,
            risk_level=base.risk_level,
            best_outdoor_window=best_window,
            precautionary_note=base.precautionary_note,
            recommendations=base.recommendations,
        )

    def _fallback_daily_routine(
        self, env_snapshot: Dict[str, Any], forecast_summary: Dict[str, Any]
    ) -> StructuredDailyRoutineOutput:
        m = self._extract_metrics(env_snapshot)
        best_win = forecast_summary.get("best_window") or "13:00–16:00 (verified forecast minimum)"
        hourly_points = forecast_summary.get("upcoming_hours") or []

        def _ctx_at(target_prefix: str) -> str:
            for pt in hourly_points:
                t = str(pt.get("time", ""))
                if target_prefix in t:
                    return f"Forecast NAQI {pt.get('indian_naqi')}, PM2.5 {pt.get('pm2_5')} μg/m³"
            return f"Current NAQI {m['naqi']} ({m['naqi_cat']}), {m['temp']}°C"

        naqi_high = (m["naqi"] or 0) > 120
        slots = [
            DailyRoutineSlot(
                time="07:00",
                phase="morning",
                title="Morning air check & indoor prep",
                guidance=(
                    "Keep bedrooms sealed against cool morning inversion haze; run air purifier or wet-mop hard floors."
                    if naqi_high
                    else "Check local NAQI before opening windows briefly away from busy roads."
                ),
                aqi_context=_ctx_at("T07:00"),
                priority="high" if naqi_high else "medium",
            ),
            DailyRoutineSlot(
                time="08:30",
                phase="travel",
                title="Low-exposure commute planning",
                guidance="Prefer enclosed metro/bus transit or less congested routes; avoid idling in peak intersection traffic.",
                aqi_context=_ctx_at("T08:00"),
                priority="high",
            ),
            DailyRoutineSlot(
                time="13:00",
                phase="work_study",
                title="Midday ventilation & hydration",
                guidance="Use warmer midday hours for brief cross-ventilation if outdoor PM2.5 dips below morning levels.",
                aqi_context=_ctx_at("T13:00"),
                priority="medium",
            ),
            DailyRoutineSlot(
                time="16:00",
                phase="outdoor",
                title="Timed outdoor activity window",
                guidance=(
                    "Keep outdoor walks short and low-intensity, choosing tree-lined parks away from traffic."
                    if naqi_high
                    else "Good window for brisk walking or children's outdoor play away from arterial roads."
                ),
                aqi_context=_ctx_at("T16:00"),
                priority="medium",
            ),
            DailyRoutineSlot(
                time="19:30",
                phase="evening",
                title="Evening cooking & indoor protection",
                guidance="Run kitchen exhaust hood while cooking, avoid incense or indoor smoke, and close outer windows before night inversion.",
                aqi_context=_ctx_at("T19:00"),
                priority="high",
            ),
        ]
        return StructuredDailyRoutineOutput(
            summary=(
                f"Generated from verified Open-Meteo hourly forecast for {m['city']} "
                f"(current Indian NAQI {m['naqi']}, {m['naqi_cat']})."
            ),
            optimal_outdoor_window=best_win,
            slots=slots,
        )

    def _fallback_indoor_advice(
        self,
        env_snapshot: Dict[str, Any],
        user_context: Dict[str, Any],
        indoor_context: Dict[str, Any],
    ) -> StructuredIndoorOutput:
        m = self._extract_metrics(env_snapshot)
        naqi = m["naqi"] or 0
        if naqi <= 60:
            verdict = "open_windows"
            summary = f"Outdoor Indian NAQI in {m['city']} is {naqi} ({m['naqi_cat']}), so natural cross-ventilation can help refresh indoor air."
        elif naqi <= 140:
            verdict = "brief_cross_ventilation"
            summary = f"Outdoor Indian NAQI is {naqi} ({m['naqi_cat']}). Use short midday cross-ventilation away from traffic and minimize indoor smoke."
        else:
            verdict = "keep_closed_filter"
            summary = f"Outdoor Indian NAQI is elevated at {naqi} ({m['naqi_cat']}, PM2.5 {m['pm2_5']} μg/m³). Keep outer windows closed and focus on filtration and source control."

        steps = [
            "Run kitchen exhaust or open a single kitchen window briefly only during active cooking to vent cooking aerosols.",
            "Replace dry sweeping with damp mopping or HEPA vacuuming so settled PM10 dust is not resuspended.",
            "Eliminate indoor combustion sources such as incense sticks, dhoop, candles, and tobacco smoke.",
        ]
        if user_context.get("has_air_purifier"):
            steps.append("Run a true HEPA air purifier continuously in the bedroom/living room with doors closed.")
        else:
            steps.append("Seal obvious window gaps near busy roads and place door draft stoppers on exterior doors.")
        if indoor_context.get("cooking_fuel") == "solid_biomass":
            steps.append("Prioritize transitioning from biomass/solid fuel to LPG or electric induction with active ventilation.")

        rooms = [
            IndoorRoomAdvice(
                room="Living Room",
                ventilation_action="Ventilate only during lower-PM midday hours; keep traffic-facing windows closed at peak rush hour.",
                filtration_and_dust="Wet-wipe hard surfaces daily; keep a HEPA unit away from corners if available.",
                priority="medium",
            ),
            IndoorRoomAdvice(
                room="Kitchen",
                ventilation_action="Turn on chimney/exhaust fan 5 minutes before cooking and leave on 10 minutes after.",
                filtration_and_dust="Use lids on pans during high-heat frying to reduce fine aerosol plumes.",
                priority="high",
            ),
            IndoorRoomAdvice(
                room="Bedroom",
                ventilation_action="Close windows before evening temperature drop traps winter smog outdoors.",
                filtration_and_dust="Wash bedding weekly in warm water and keep clutter minimal to cut dust buildup.",
                priority="high",
            ),
        ]
        return StructuredIndoorOutput(
            ventilation_verdict=verdict,  # type: ignore[arg-type]
            summary=summary,
            key_steps=steps,
            room_guidance=rooms,
        )

    def _fallback_sustainable_alternatives(
        self, env_snapshot: Dict[str, Any], focus_category: Optional[str]
    ) -> StructuredSustainableOutput:
        m = self._extract_metrics(env_snapshot)
        items = [
            SustainableAlternativeItem(
                category="transportation",
                current_behavior="Solo petrol car or two-wheeler trips under 5 km",
                suggested_alternative="Use metro/bus, carpool, or walk/cycle on low-pollution hours",
                why_it_matters=f"Reduces local tailpipe NO2 (currently {m['no2']} μg/m³) and brake/road PM2.5.",
                potential_benefit="Documented per-km emission reductions when replacing private motor trips (~0.10–0.17 kg CO2e/km car baseline estimate).",
                practical_difficulty="easy",
            ),
            SustainableAlternativeItem(
                category="energy",
                current_behavior="Running AC/geysers on default schedules during moderate weather",
                suggested_alternative="Set AC to 24–26°C, use ceiling fans, and switch off standby loads",
                why_it_matters="Lowers thermal power plant demand linked to regional SO2 and particulate emissions.",
                potential_benefit="Estimated ~0.716 kg CO2 avoided per kWh saved on the Indian electricity grid (CEA baseline).",
                practical_difficulty="easy",
            ),
            SustainableAlternativeItem(
                category="household",
                current_behavior="Daily incense burning and dry sweeping indoors",
                suggested_alternative="Switch to damp mopping and essential-oil diffusers or fresh ventilation",
                why_it_matters="Cuts indoor fine particulate spikes without adding chemical aerosols.",
                potential_benefit="Immediate reduction in avoidable indoor smoke exposure for children and elderly.",
                practical_difficulty="easy",
            ),
            SustainableAlternativeItem(
                category="shopping",
                current_behavior="Frequent single-item express deliveries and single-use plastic bags",
                suggested_alternative="Consolidate weekly orders and buy seasonal local produce with reusable totes",
                why_it_matters="Reduces urban last-mile diesel/two-wheeler delivery trips and packaging waste.",
                potential_benefit="Lower neighborhood traffic density and reduced upstream packaging footprint.",
                practical_difficulty="moderate",
            ),
            SustainableAlternativeItem(
                category="waste",
                current_behavior="Mixed household/garden waste sent to open dumps or burnt",
                suggested_alternative="Segregate wet waste for home/society composting and recycle dry waste",
                why_it_matters="Open waste burning is a major winter PM2.5 and black-carbon spike driver in Indian cities.",
                potential_benefit="Eliminates toxic localized smoke plumes and diverts organics from landfills.",
                practical_difficulty="moderate",
            ),
            SustainableAlternativeItem(
                category="community",
                current_behavior="Individual school drop-offs and uncoordinated housing society practices",
                suggested_alternative="Organize neighborhood school carpools and society zero-burning pledges",
                why_it_matters="Multiplies per-household reductions across an entire residential lane.",
                potential_benefit="Shared street-level traffic reduction and collective local air stewardship.",
                practical_difficulty="challenging",
            ),
        ]
        if focus_category and focus_category != "all":
            prioritized = [i for i in items if i.category == focus_category] + [
                i for i in items if i.category != focus_category
            ]
            items = prioritized
        return StructuredSustainableOutput(
            summary=(
                f"Targeted low-emission habits for {m['city']} prioritized for PM2.5 ({m['pm2_5']} μg/m³) "
                f"and NO2 ({m['no2']} μg/m³) conditions."
            ),
            alternatives=items,
        )
