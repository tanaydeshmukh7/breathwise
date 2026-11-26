"""Documented emissions & sustainability estimate calculator.

Explicitly separates factor-based CO2e avoidance estimates from measured
ambient pollution exposure, and leaves non-quantifiable actions as None
rather than fabricating numbers.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Optional


@dataclass(frozen=True)
class EmissionFactorSpec:
    action_type: str
    category: str
    default_label: str
    unit: str
    kg_co2e_per_unit: Optional[float]
    basis: str


# Documented reference factors (explicitly marked as estimates with assumptions):
# - Passenger car displaced by walking/cycling: ~0.171 kg CO2e/km (UK DESNZ/DEFRA average petrol/diesel car baseline)
# - Passenger car displaced by urban bus/metro: net ~0.10 kg CO2e/km saved (0.171 car - ~0.071 public transit)
# - Two-wheeler displaced by walking/cycling: ~0.083 kg CO2e/km (DEFRA average motorbike baseline)
# - Electricity saved in India grid: ~0.716 kg CO2/kWh (Central Electricity Authority of India, CO2 Baseline Database)
ACTION_FACTOR_CATALOG: Dict[str, EmissionFactorSpec] = {
    "public_transport_km": EmissionFactorSpec(
        action_type="public_transport_km",
        category="transportation",
        default_label="Commuted via metro or bus instead of private car",
        unit="km",
        kg_co2e_per_unit=0.10,
        basis="Estimate: ~0.10 kg CO2e/km net difference (0.171 car minus ~0.071 bus/rail baseline, DEFRA/DESNZ assumption).",
    ),
    "walk_cycle_km": EmissionFactorSpec(
        action_type="walk_cycle_km",
        category="transportation",
        default_label="Walked or cycled instead of driving a car",
        unit="km",
        kg_co2e_per_unit=0.171,
        basis="Estimate: ~0.171 kg CO2e/km displaced average passenger car (UK DESNZ/DEFRA passenger vehicle factor).",
    ),
    "two_wheeler_replaced_km": EmissionFactorSpec(
        action_type="two_wheeler_replaced_km",
        category="transportation",
        default_label="Walked or cycled instead of riding a petrol two-wheeler",
        unit="km",
        kg_co2e_per_unit=0.083,
        basis="Estimate: ~0.083 kg CO2e/km displaced petrol motorcycle/scooter baseline (DEFRA factor).",
    ),
    "electricity_saved_kwh": EmissionFactorSpec(
        action_type="electricity_saved_kwh",
        category="energy",
        default_label="Reduced household electricity usage (AC/appliances)",
        unit="kWh",
        kg_co2e_per_unit=0.716,
        basis="Estimate: ~0.716 kg CO2/kWh weighted average Indian grid emission factor (CEA India CO2 Baseline).",
    ),
    "no_open_burning": EmissionFactorSpec(
        action_type="no_open_burning",
        category="waste",
        default_label="Composted or segregated garden/household waste instead of burning",
        unit="event",
        kg_co2e_per_unit=None,
        basis="Qualitative local PM2.5 & black-carbon avoidance; exact mass-specific CO2e varies by waste composition and is not fabricated.",
    ),
    "clean_indoor_practice": EmissionFactorSpec(
        action_type="clean_indoor_practice",
        category="household",
        default_label="Used kitchen exhaust, wet mopping, and avoided indoor smoke/incense",
        unit="day",
        kg_co2e_per_unit=None,
        basis="Qualitative indoor particulate exposure reduction; does not represent measured indoor PM2.5.",
    ),
    "low_waste_shopping": EmissionFactorSpec(
        action_type="low_waste_shopping",
        category="shopping",
        default_label="Chose reusable bags, local produce, or refill packs",
        unit="trip",
        kg_co2e_per_unit=None,
        basis="Qualitative packaging & freight reduction; exact lifecycle savings depend on product supply chain.",
    ),
    "community_action": EmissionFactorSpec(
        action_type="community_action",
        category="community",
        default_label="Participated in local clean-air / tree-care / carpool awareness",
        unit="activity",
        kg_co2e_per_unit=None,
        basis="Community awareness & shared-mobility impact; not converted into fabricated numerical CO2e.",
    ),
}


def calculate_action_estimate(
    action_type: str, quantity: float
) -> tuple[Optional[float], str, str]:
    """Return (estimated_co2e_avoided_kg, unit, calculation_basis)."""
    spec = ACTION_FACTOR_CATALOG.get(action_type)
    if spec is None:
        return (
            None,
            "action",
            "Custom action logged; no standardized emission factor applied.",
        )
    if spec.kg_co2e_per_unit is None:
        return (None, spec.unit, spec.basis)
    estimated = round(spec.kg_co2e_per_unit * max(0.0, quantity), 3)
    return (estimated, spec.unit, spec.basis)
