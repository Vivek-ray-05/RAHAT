from app.core.enums import RiskLevel
from app.engines.risk.risk_agent import RiskEngine


def test_zero_readings_give_low_risk():
    engine = RiskEngine()
    result = engine.score_zone("Z01", "Test Zone", rainfall_mm=0.0, water_level_m=0.0, elevation_tier="high")
    assert result["score"] < 4.0
    assert result["risk_level"] == RiskLevel.LOW


def test_heavy_rain_and_water_push_risk_up():
    engine = RiskEngine()
    result = engine.score_zone("Z01", "Test Zone", rainfall_mm=80.0, water_level_m=2.0, elevation_tier="low")
    assert result["score"] >= 9.0
    assert result["risk_level"] == RiskLevel.CRITICAL


def test_elevation_tier_changes_score_for_identical_readings():
    high = RiskEngine().score_zone("Z01", "Z", rainfall_mm=20.0, water_level_m=0.5, elevation_tier="high")
    low = RiskEngine().score_zone("Z02", "Z", rainfall_mm=20.0, water_level_m=0.5, elevation_tier="low")
    assert low["score"] > high["score"]


def test_score_is_deterministic_for_same_inputs():
    a = RiskEngine().score_zone("Z01", "Z", rainfall_mm=15.0, water_level_m=0.3, elevation_tier="mid")
    b = RiskEngine().score_zone("Z01", "Z", rainfall_mm=15.0, water_level_m=0.3, elevation_tier="mid")
    assert a["score"] == b["score"]


def test_score_never_exceeds_bounds_even_at_extreme_severity():
    engine = RiskEngine()
    result = engine.score_zone(
        "Z01", "Z", rainfall_mm=500.0, water_level_m=10.0, elevation_tier="low", severity=10.0,
    )
    assert 0.0 <= result["score"] <= 10.0


def test_soil_saturation_persists_across_ticks_on_same_engine():
    """Repeated rain on the same zone should saturate the soil and push
    risk up tick over tick, even with identical per-tick readings --
    this statefulness is the reason RiskEngine is one-per-run, not
    reconstructed every tick."""
    engine = RiskEngine()
    first = engine.score_zone("Z01", "Z", rainfall_mm=10.0, water_level_m=0.2, elevation_tier="mid")
    second = engine.score_zone("Z01", "Z", rainfall_mm=10.0, water_level_m=0.2, elevation_tier="mid")
    assert second["score"] >= first["score"]


def test_time_to_critical_is_unknown_with_insufficient_history():
    engine = RiskEngine()
    result = engine.score_zone("Z01", "Z", rainfall_mm=5.0, water_level_m=0.1, elevation_tier="mid")
    assert result["time_to_critical"] == 99
