"""Centralized prompt management system for BreatheWise AI Engine.

Contains 6 specialized prompt templates:
1. Air Quality Analysis
2. Daily Routine Generation
3. Indoor Air Recommendations
4. Sustainable Alternatives
5. Conversational Air Advisor
6. Environmental Impact Explanation
"""

from __future__ import annotations

import json
from typing import Any, Dict, Optional

STRICT_GROUNDING_RULES = """
CRITICAL GROUNDING & SAFETY RULES:
1. You are BreatheWise AI, an urban air quality decision assistant.
2. NEVER invent, guess, or alter AQI numbers, pollutant concentrations, weather readings, forecasts, health facts, or exact emissions reductions.
3. ONLY cite numbers explicitly present in the VERIFIED_ENVIRONMENTAL_DATA JSON block below. If a field is null or missing, explicitly state it is unavailable.
4. Distinguish clearly between CPCB Indian National AQI (NAQI) and US EPA AQI when mentioning index values.
5. Never claim to measure indoor air quality unless a physical indoor sensor reading is supplied (none is supplied here).
6. Provide general precautionary health guidance only — NEVER provide a medical diagnosis or prescribe treatment.
7. Output ONLY valid JSON matching the exact requested schema. Do not wrap in markdown or add commentary outside the JSON object.
""".strip()


def _format_context_block(
    env_snapshot: Dict[str, Any],
    user_context: Dict[str, Any],
    forecast_summary: Optional[Dict[str, Any]] = None,
) -> str:
    payload: Dict[str, Any] = {
        "VERIFIED_ENVIRONMENTAL_DATA": env_snapshot,
        "USER_AND_HOUSEHOLD_CONTEXT": user_context,
    }
    if forecast_summary is not None:
        payload["VERIFIED_HOURLY_FORECAST_SUMMARY"] = forecast_summary
    return json.dumps(payload, indent=2, default=str)


def build_air_analysis_messages(
    env_snapshot: Dict[str, Any], user_context: Dict[str, Any]
) -> list[dict[str, str]]:
    system = f"""{STRICT_GROUNDING_RULES}

TASK: Air Quality Analysis
Analyze the supplied current air quality and weather readings for the user's location and household context.
Return ONLY JSON matching:
{{
  "summary": "2-sentence plain-English explanation citing verified AQI/pollutant & weather drivers",
  "risk_level": "low | moderate | high | very_high | severe",
  "best_outdoor_window": "short recommendation based on current/forecast conditions or null",
  "precautionary_note": "brief non-medical precautionary statement",
  "recommendations": [
    {{
      "title": "concise action title",
      "reason": "why based on supplied pollutant/weather values",
      "action": "practical step for today",
      "priority": "high | medium | low"
    }}
  ]
}}
Provide exactly 3 high-signal recommendations."""
    user = _format_context_block(env_snapshot, user_context)
    return [{"role": "system", "content": system}, {"role": "user", "content": user}]


def build_advisor_chat_messages(
    question: str,
    env_snapshot: Dict[str, Any],
    user_context: Dict[str, Any],
    forecast_summary: Optional[Dict[str, Any]],
    history: list[dict[str, str]],
) -> list[dict[str, str]]:
    system = f"""{STRICT_GROUNDING_RULES}

TASK: Conversational Air Advisor
Answer the user's specific air quality, outdoor activity, ventilation, or family protection question using ONLY the verified environmental data and household context.
Return ONLY JSON matching:
{{
  "summary": "direct, practical answer addressing the user's question (max 4 sentences)",
  "risk_level": "low | moderate | high | very_high | severe",
  "best_outdoor_window": "specific time window from verified forecast if relevant, else null",
  "precautionary_note": "general precautionary reminder (not medical advice)",
  "recommendations": [
    {{
      "title": "actionable recommendation title",
      "reason": "grounded reason citing verified readings",
      "action": "concrete action the household can take",
      "priority": "high | medium | low"
    }}
  ]
}}
Provide 2 to 4 recommendations."""
    context_msg = _format_context_block(env_snapshot, user_context, forecast_summary)
    messages: list[dict[str, str]] = [
        {"role": "system", "content": system},
        {"role": "system", "content": f"CURRENT VERIFIED CONTEXT:\n{context_msg}"},
    ]
    for turn in history[-6:]:
        if turn.get("role") in ("user", "assistant") and turn.get("content"):
            messages.append({"role": turn["role"], "content": turn["content"][:800]})
    messages.append({"role": "user", "content": question})
    return messages


def build_daily_routine_messages(
    env_snapshot: Dict[str, Any],
    user_context: Dict[str, Any],
    forecast_summary: Dict[str, Any],
) -> list[dict[str, str]]:
    system = f"""{STRICT_GROUNDING_RULES}

TASK: Daily Routine Generation
Using the verified hourly air quality & weather forecast, generate a practical day schedule covering morning, travel, outdoor, work_study, and evening phases.
Return ONLY JSON matching:
{{
  "summary": "overview of today's pollution curve and why slots are timed this way",
  "optimal_outdoor_window": "best time range from the verified hourly forecast",
  "slots": [
    {{
      "time": "HH:MM",
      "phase": "morning | travel | outdoor | work_study | evening",
      "title": "short schedule item",
      "guidance": "practical instruction tailored to user lifestyle/household",
      "aqi_context": "referenced forecast NAQI / PM2.5 / weather condition for this hour",
      "priority": "high | medium | low"
    }}
  ]
}}
Include 5 to 6 chronological slots."""
    user = _format_context_block(env_snapshot, user_context, forecast_summary)
    return [{"role": "system", "content": system}, {"role": "user", "content": user}]


def build_indoor_advice_messages(
    env_snapshot: Dict[str, Any],
    user_context: Dict[str, Any],
    indoor_context: Dict[str, Any],
) -> list[dict[str, str]]:
    system = f"""{STRICT_GROUNDING_RULES}

TASK: Indoor Air Recommendations
Generate practical indoor air quality protection and ventilation guidance based on outdoor Open-Meteo conditions and household setup. Remember: we have NO indoor sensor; never claim to measure indoor PM2.5.
Return ONLY JSON matching:
{{
  "ventilation_verdict": "open_windows | brief_cross_ventilation | keep_closed_filter",
  "summary": "clear explanation of whether outdoor air currently helps or hurts indoor air",
  "key_steps": ["3 to 5 concise actionable steps"],
  "room_guidance": [
    {{
      "room": "Living Room | Kitchen | Bedroom",
      "ventilation_action": "specific window/exhaust guidance",
      "filtration_and_dust": "HEPA / wet mopping / source reduction guidance",
      "priority": "high | medium | low"
    }}
  ],
  "sensor_disclaimer": "Explicitly note indoor air is not directly measured without a physical sensor."
}}"""
    merged_user = {**user_context, "indoor_setup": indoor_context}
    user = _format_context_block(env_snapshot, merged_user)
    return [{"role": "system", "content": system}, {"role": "user", "content": user}]


def build_sustainable_alternatives_messages(
    env_snapshot: Dict[str, Any],
    user_context: Dict[str, Any],
    focus_category: Optional[str] = None,
) -> list[dict[str, str]]:
    system = f"""{STRICT_GROUNDING_RULES}

TASK: Sustainable Alternatives
Recommend realistic urban lifestyle alternatives across transportation, energy, household, shopping, waste, and community that reduce local emissions and personal exposure. Do NOT fabricate exact numerical CO2 savings; describe qualitative/documented benefits honestly.
Return ONLY JSON matching:
{{
  "summary": "concise framing connecting local air conditions to high-leverage daily choices",
  "alternatives": [
    {{
      "category": "transportation | energy | household | shopping | waste | community",
      "current_behavior": "common urban habit",
      "suggested_alternative": "practical lower-emission alternative",
      "why_it_matters": "link to PM2.5/NO2/ozone or community air quality",
      "potential_benefit": "qualitative environmental & exposure benefit (no fabricated numbers)",
      "practical_difficulty": "easy | moderate | challenging"
    }}
  ]
}}
Provide 6 alternatives covering diverse categories."""
    ctx = {**user_context, "focus_category": focus_category or "all"}
    user = _format_context_block(env_snapshot, ctx)
    return [{"role": "system", "content": system}, {"role": "user", "content": user}]


def build_impact_explanation_messages(
    impact_summary: Dict[str, Any],
    user_context: Dict[str, Any],
) -> list[dict[str, str]]:
    system = f"""{STRICT_GROUNDING_RULES}

TASK: Environmental Impact Explanation
Summarize the user's logged sustainable actions and explicitly distinguish estimated emissions avoided (calculated from documented emission factors) from measured ambient air exposure.
Return ONLY JSON matching:
{{
  "summary": "encouraging, factual summary referencing only the supplied logged totals",
  "risk_level": "low",
  "precautionary_note": "Clarifies that logged CO2e figures are factor-based estimates, distinct from personal pollution exposure.",
  "recommendations": [
    {{
      "title": "next high-impact habit",
      "reason": "based on user's current category mix",
      "action": "practical next action to log this week",
      "priority": "medium"
    }}
  ]
}}"""
    user = json.dumps(
        {"IMPACT_SUMMARY": impact_summary, "USER_CONTEXT": user_context},
        indent=2,
        default=str,
    )
    return [{"role": "system", "content": system}, {"role": "user", "content": user}]
