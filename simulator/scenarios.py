from dataclasses import dataclass
from enum import Enum


class ScenarioType(str, Enum):
    RAIN = "rain"
    PARTIAL_SUBMERSION = "partial_submersion"
    DEEP_SUBMERSION = "deep_submersion"
    POWER_FAILURE = "power_failure"


@dataclass
class ScenarioConfig:
    scenario: ScenarioType
    duration_minutes: int
    peak_water_level_m: float
    peak_conductivity_ms_cm: float
    peak_humidity_pct: float
    power_failure: bool = False
    network_failure: bool = False


SCENARIOS = {
    ScenarioType.RAIN: ScenarioConfig(
        scenario=ScenarioType.RAIN,
        duration_minutes=120,
        peak_water_level_m=0.08,
        peak_conductivity_ms_cm=0.4,
        peak_humidity_pct=88,
    ),

    ScenarioType.PARTIAL_SUBMERSION: ScenarioConfig(
        scenario=ScenarioType.PARTIAL_SUBMERSION,
        duration_minutes=240,
        peak_water_level_m=0.70,
        peak_conductivity_ms_cm=1.8,
        peak_humidity_pct=96,
        power_failure=True,
        network_failure=True,
    ),

    ScenarioType.DEEP_SUBMERSION: ScenarioConfig(
        scenario=ScenarioType.DEEP_SUBMERSION,
        duration_minutes=360,
        peak_water_level_m=1.30,
        peak_conductivity_ms_cm=2.5,
        peak_humidity_pct=98,
        power_failure=True,
        network_failure=True,
    ),

    ScenarioType.POWER_FAILURE: ScenarioConfig(
        scenario=ScenarioType.POWER_FAILURE,
        duration_minutes=180,
        peak_water_level_m=0.0,
        peak_conductivity_ms_cm=0.1,
        peak_humidity_pct=75,
        power_failure=True,
        network_failure=True,
    ),
}