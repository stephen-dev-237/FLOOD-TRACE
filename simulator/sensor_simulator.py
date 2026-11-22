import numpy as np
import pandas as pd
from enum import Enum


class ScenarioType(Enum):
    RAIN = "rain"
    PARTIAL_SUBMERSION = "partial_submersion"
    DEEP_SUBMERSION = "deep_submersion"
    POWER_NETWORK_FAILURE = "power_network_failure"
    SENSOR_FAILURE = "sensor_failure"


def generate_flood_event(
    asset_id="TX-1047",
    scenario=ScenarioType.PARTIAL_SUBMERSION,
    duration_minutes=300,
    interval_minutes=5,
    seed=42
):
    """
    Generate simulated FloodTrace sensor data.

    This represents what future physical sensors could record.
    """

    rng = np.random.default_rng(seed)

    # ---------------------------------------------------------
    # TIME
    # ---------------------------------------------------------

    number_of_samples = (duration_minutes // interval_minutes) + 1

    timestamps = pd.date_range(
        start="2026-08-26 10:00:00",
        periods=number_of_samples,
        freq=f"{interval_minutes}min"
    )

    n = len(timestamps)

    # ---------------------------------------------------------
    # FLOOD PROFILE
    # ---------------------------------------------------------

    x = np.linspace(0, 1, n)

    if scenario == ScenarioType.RAIN:

        peak_water = 0.08

        water_level = (
            peak_water
            * np.sin(np.pi * x) ** 2
        )

    elif scenario == ScenarioType.PARTIAL_SUBMERSION:

        peak_water = 0.70

        water_level = (
            peak_water
            * np.sin(np.pi * x) ** 1.3
        )

    elif scenario == ScenarioType.DEEP_SUBMERSION:

        peak_water = 1.30

        water_level = (
            peak_water
            * np.sin(np.pi * x) ** 1.1
        )

    elif scenario == ScenarioType.POWER_NETWORK_FAILURE:

        peak_water = 0.45

        water_level = (
            peak_water
            * np.sin(np.pi * x) ** 1.5
        )

    elif scenario == ScenarioType.SENSOR_FAILURE:

        peak_water = 0.70

        water_level = (
            peak_water
            * np.sin(np.pi * x) ** 1.3
        )

    # Add very small measurement noise
    water_level += rng.normal(0, 0.005, n)

    water_level = np.clip(
        water_level,
        0,
        None
    )

    # ---------------------------------------------------------
    # WATER CONTACT
    # ---------------------------------------------------------

    water_contact = water_level > 0.03

    # ---------------------------------------------------------
    # HUMIDITY
    # ---------------------------------------------------------

    base_humidity = 70

    if scenario == ScenarioType.RAIN:
        peak_humidity = 88

    elif scenario == ScenarioType.PARTIAL_SUBMERSION:
        peak_humidity = 96

    elif scenario == ScenarioType.DEEP_SUBMERSION:
        peak_humidity = 98

    else:
        peak_humidity = 94

    humidity = (
        base_humidity
        + (
            peak_humidity - base_humidity
        )
        * (
            water_level /
            max(peak_water, 0.01)
        )
    )

    humidity += rng.normal(0, 1.0, n)

    humidity = np.clip(
        humidity,
        40,
        100
    )

    # ---------------------------------------------------------
    # TEMPERATURE
    # ---------------------------------------------------------

    temperature = (
        30
        - 2
        * (
            water_level /
            max(peak_water, 0.01)
        )
    )

    temperature += rng.normal(0, 0.3, n)

    # ---------------------------------------------------------
    # WATER CONDUCTIVITY
    # ---------------------------------------------------------

    if scenario == ScenarioType.RAIN:
        peak_conductivity = 0.4

    elif scenario == ScenarioType.PARTIAL_SUBMERSION:
        peak_conductivity = 1.8

    elif scenario == ScenarioType.DEEP_SUBMERSION:
        peak_conductivity = 2.5

    else:
        peak_conductivity = 1.2

    conductivity = (
        0.1
        + (
            peak_conductivity - 0.1
        )
        * (
            water_level /
            max(peak_water, 0.01)
        )
    )

    conductivity += rng.normal(0, 0.03, n)

    conductivity = np.clip(
        conductivity,
        0,
        None
    )

    # ---------------------------------------------------------
    # POWER STATE
    # ---------------------------------------------------------

    power_state = np.array(
        ["ON"] * n,
        dtype=object
    )

    # ---------------------------------------------------------
    # NETWORK STATE
    # ---------------------------------------------------------

    network_state = np.array(
        ["ONLINE"] * n,
        dtype=object
    )

    if scenario in [
        ScenarioType.PARTIAL_SUBMERSION,
        ScenarioType.DEEP_SUBMERSION,
        ScenarioType.POWER_NETWORK_FAILURE
    ]:

        failure_start = int(n * 0.35)
        failure_end = int(n * 0.75)

        power_state[
            failure_start:failure_end
        ] = "OFF"

        network_state[
            failure_start:failure_end
        ] = "OFFLINE"

    # ---------------------------------------------------------
    # SENSOR INTEGRITY
    # ---------------------------------------------------------

    sensor_integrity = np.ones(n)

    if scenario == ScenarioType.SENSOR_FAILURE:

        failure_start = int(n * 0.45)
        failure_end = int(n * 0.60)

        # Simulate degraded sensor quality
        sensor_integrity[
            failure_start:failure_end
        ] = rng.uniform(
            0.20,
            0.60,
            failure_end - failure_start
        )

        # Some water-level readings become missing
        water_level[
            failure_start:failure_end
        ] = np.nan

        # Some conductivity readings become missing
        conductivity[
            failure_start:failure_end
        ] = np.nan

    # ---------------------------------------------------------
    # BUILD DATAFRAME
    # ---------------------------------------------------------

    data = pd.DataFrame({

        "asset_id": asset_id,

        "scenario": scenario.value,

        "timestamp": timestamps,

        "water_level_m": water_level,

        "water_contact": water_contact,

        "humidity_pct": humidity,

        "conductivity_ms_cm": conductivity,

        "temperature_c": temperature,

        "power_state": power_state,

        "network_state": network_state,

        "sensor_integrity": sensor_integrity
    })

    return data


# =============================================================
# RUN SIMULATIONS
# =============================================================

if __name__ == "__main__":

    scenarios = [

        ScenarioType.RAIN,

        ScenarioType.PARTIAL_SUBMERSION,

        ScenarioType.DEEP_SUBMERSION,

        ScenarioType.POWER_NETWORK_FAILURE,

        ScenarioType.SENSOR_FAILURE
    ]

    for scenario in scenarios:

        print("\n" + "=" * 60)

        print(
            f"Generating scenario: "
            f"{scenario.value.upper()}"
        )

        print("=" * 60)

        data = generate_flood_event(
            asset_id="TX-1047",
            scenario=scenario
        )

        filename = (
            f"flood_event_"
            f"{scenario.value}.csv"
        )

        data.to_csv(
            filename,
            index=False
        )

        print(data.head())

        print(
            f"\nSaved: {filename}"
        )

    print("\nAll simulations completed.")