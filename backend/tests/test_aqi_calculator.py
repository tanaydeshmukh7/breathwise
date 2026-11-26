"""Tests for CPCB Indian NAQI & US EPA AQI calculator."""

from app.services.aqi_calculator import (
    classify_indian_naqi,
    classify_us_aqi,
    compute_indian_naqi,
)


def test_indian_naqi_requires_minimum_three_pollutants_and_pm():
    res = compute_indian_naqi(pm2_5=45.0, nitrogen_dioxide=30.0)
    assert res.value is None
    assert res.category == "Unavailable"

    res_no_pm = compute_indian_naqi(
        nitrogen_dioxide=40.0, ozone=60.0, sulphur_dioxide=20.0
    )
    assert res_no_pm.value is None


def test_indian_naqi_pune_sample_computation():
    # Sample Open-Meteo Pune reading: PM2.5=38, PM10=38.9, NO2=19.1, O3=79, CO=638 ug/m3 (0.638 mg/m3), SO2=13.2
    res = compute_indian_naqi(
        pm2_5=38.0,
        pm10=38.9,
        nitrogen_dioxide=19.1,
        ozone=79.0,
        carbon_monoxide_ug_m3=638.0,
        sulphur_dioxide=13.2,
    )
    assert res.value is not None
    # PM2.5=38 is in 30-60 -> 51-100 band (~64); O3=79 is in 50-100 -> 51-100 band (~79)
    assert res.category == "Satisfactory"
    assert res.dominant_pollutant == "O3"
    assert res.sub_indices["CO"] < 50  # 0.638 mg/m3 is well within Good (0-1.0 mg/m3)
    assert res.methodology == "CPCB Indian National AQI (NAQI)"


def test_standards_not_mixed():
    naqi_cat, _, _ = classify_indian_naqi(135)
    us_cat, _, _ = classify_us_aqi(135)
    assert naqi_cat == "Moderately Polluted"
    assert us_cat == "Unhealthy for Sensitive Groups"
