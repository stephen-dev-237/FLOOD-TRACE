import pandas as pd
import numpy as np
from enum import Enum


# ============================================================
# FLOODTRACE EXPOSURE RECONSTRUCTION ENGINE
# ============================================================

class ExposureState(Enum):
    DRY = "DRY"
    WETTING = "WETTING"
    PARTIAL_SUBMERSION = "PARTIAL_SUBMERSION"
    DEEP_EXPOSURE = "DEEP_EXPOSURE"
    UNKNOWN = "UNKNOWN"


class WaterTrend(Enum):
    RISING = "RISING"
    STABLE = "STABLE"
    FALLING = "FALLING"
    UNKNOWN = "UNKNOWN"


# ------------------------------------------------------------
# CONFIGURATION
# ------------------------------------------------------------

# These are simulation/model thresholds.
# They are NOT electrical safety standards.

DRY_THRESHOLD = 0.03
WETTING_THRESHOLD = 0.15
DEEP_THRESHOLD = 0.70

# Hysteresis prevents rapid state flipping caused by noise.
DEEP_ENTER_THRESHOLD = 0.72
DEEP_EXIT_THRESHOLD = 0.68

WETTING_ENTER_THRESHOLD = 0.04
WETTING_EXIT_THRESHOLD = 0.02

MIN_VALID_WATER_LEVEL = 0.0

TREND_WINDOW = 3


# ============================================================
# DATA VALIDATION
# ============================================================

def validate_data(data):

    required_columns = [
        "timestamp",
        "water_level_m",
        "humidity_pct",
        "conductivity_ms_cm",
        "temperature_c",
        "power_state",
        "network_state",
        "sensor_integrity"
    ]

    missing_columns = [
        column
        for column in required_columns
        if column not in data.columns
    ]

    if missing_columns:
        raise ValueError(
            f"Missing required columns: {missing_columns}"
        )

    data = data.copy()

    data["timestamp"] = pd.to_datetime(
        data["timestamp"],
        errors="coerce"
    )

    data = data.sort_values(
        "timestamp"
    ).reset_index(drop=True)

    # Remove impossible negative water values
    data.loc[
        data["water_level_m"] < MIN_VALID_WATER_LEVEL,
        "water_level_m"
    ] = np.nan

    return data


# ============================================================
# WATER LEVEL SMOOTHING
# ============================================================

def smooth_water_level(data):

    data = data.copy()

    # Median filter is robust against isolated spikes.
    data["water_level_smoothed_m"] = (
        data["water_level_m"]
        .rolling(
            window=3,
            center=True,
            min_periods=1
        )
        .median()
    )

    return data


# ============================================================
# WATER TREND
# ============================================================

def calculate_water_trend(data):

    data = data.copy()

    water = data["water_level_smoothed_m"]

    change = (
        water.diff(TREND_WINDOW)
    )

    trend = []

    for value in change:

        if pd.isna(value):

            trend.append(
                WaterTrend.UNKNOWN.value
            )

        elif value > 0.01:

            trend.append(
                WaterTrend.RISING.value
            )

        elif value < -0.01:

            trend.append(
                WaterTrend.FALLING.value
            )

        else:

            trend.append(
                WaterTrend.STABLE.value
            )

    data["water_trend"] = trend

    return data


# ============================================================
# STATE CLASSIFICATION WITH HYSTERESIS
# ============================================================

def classify_state(
    water_level,
    previous_state
):

    if pd.isna(water_level):

        return ExposureState.UNKNOWN.value

    # --------------------------------------------------------
    # DRY
    # --------------------------------------------------------

    if previous_state == ExposureState.DRY.value:

        if water_level >= WETTING_ENTER_THRESHOLD:
            return ExposureState.WETTING.value

        return ExposureState.DRY.value

    # --------------------------------------------------------
    # WETTING
    # --------------------------------------------------------

    if previous_state == ExposureState.WETTING.value:

        if water_level < WETTING_EXIT_THRESHOLD:
            return ExposureState.DRY.value

        if water_level >= DEEP_ENTER_THRESHOLD:
            return ExposureState.DEEP_EXPOSURE.value

        if water_level > WETTING_THRESHOLD:
            return ExposureState.PARTIAL_SUBMERSION.value

        return ExposureState.WETTING.value

    # --------------------------------------------------------
    # PARTIAL SUBMERSION
    # --------------------------------------------------------

    if previous_state == ExposureState.PARTIAL_SUBMERSION.value:

        if water_level < WETTING_EXIT_THRESHOLD:
            return ExposureState.DRY.value

        if water_level <= WETTING_THRESHOLD:
            return ExposureState.WETTING.value

        if water_level >= DEEP_ENTER_THRESHOLD:
            return ExposureState.DEEP_EXPOSURE.value

        return ExposureState.PARTIAL_SUBMERSION.value

    # --------------------------------------------------------
    # DEEP EXPOSURE
    # --------------------------------------------------------

    if previous_state == ExposureState.DEEP_EXPOSURE.value:

        # Notice the lower exit threshold.
        # This prevents 0.70 / 0.71 / 0.69 bouncing.

        if water_level < DEEP_EXIT_THRESHOLD:

            if water_level <= WETTING_THRESHOLD:
                return ExposureState.WETTING.value

            return ExposureState.PARTIAL_SUBMERSION.value

        return ExposureState.DEEP_EXPOSURE.value

    # --------------------------------------------------------
    # UNKNOWN / INITIAL STATE
    # --------------------------------------------------------

    if water_level < DRY_THRESHOLD:
        return ExposureState.DRY.value

    elif water_level <= WETTING_THRESHOLD:
        return ExposureState.WETTING.value

    elif water_level < DEEP_ENTER_THRESHOLD:
        return ExposureState.PARTIAL_SUBMERSION.value

    else:
        return ExposureState.DEEP_EXPOSURE.value


# ============================================================
# RECONSTRUCT EXPOSURE STATES
# ============================================================

def reconstruct_states(data):

    data = data.copy()

    states = []

    previous_state = ExposureState.DRY.value

    for water_level in data[
        "water_level_smoothed_m"
    ]:

        current_state = classify_state(
            water_level,
            previous_state
        )

        states.append(current_state)

        # Unknown measurements do not destroy
        # the previous exposure state.
        if current_state != ExposureState.UNKNOWN.value:
            previous_state = current_state

    data["exposure_state"] = states

    return data


# ============================================================
# REMOVE ONE-SAMPLE STATE GLITCHES
# ============================================================

def remove_state_glitches(data):

    data = data.copy()

    states = data[
        "exposure_state"
    ].tolist()

    for i in range(1, len(states) - 1):

        previous_state = states[i - 1]
        current_state = states[i]
        next_state = states[i + 1]

        # If a state appears for only one observation
        # between two identical states, treat it as noise.

        if (
            previous_state == next_state
            and current_state != previous_state
        ):

            states[i] = previous_state

    data[
        "exposure_state"
    ] = states

    return data


# ============================================================
# EXPOSURE EPISODES
# ============================================================

def build_episodes(data):

    episodes = []

    current_state = None
    start_time = None

    for _, row in data.iterrows():

        state = row["exposure_state"]
        timestamp = row["timestamp"]

        if state != current_state:

            # Close previous episode
            if current_state is not None:

                episodes.append({
                    "state": current_state,
                    "start": start_time,
                    "end": timestamp
                })

            current_state = state
            start_time = timestamp

    # Close final episode
    if current_state is not None:

        episodes.append({
            "state": current_state,
            "start": start_time,
            "end": data[
                "timestamp"
            ].iloc[-1]
        })

    # Add duration
    for episode in episodes:

        duration = (
            episode["end"]
            - episode["start"]
        ).total_seconds() / 60

        episode["duration_minutes"] = round(
            duration,
            2
        )

    return episodes


# ============================================================
# POWER / NETWORK EVENTS
# ============================================================

def count_state_transitions(
    data,
    column,
    target_value
):

    values = data[column].tolist()

    transitions = 0

    previous = None

    for value in values:

        if (
            value == target_value
            and previous != target_value
        ):

            transitions += 1

        previous = value

    return transitions


def calculate_state_duration(
    data,
    column,
    target_value
):

    mask = data[column] == target_value

    if not mask.any():
        return 0

    # Assume each observation represents
    # the interval until the next observation.

    timestamps = data["timestamp"]

    if len(timestamps) < 2:
        return 0

    interval_minutes = (
        timestamps.diff()
        .dt.total_seconds()
        .median()
        / 60
    )

    return round(
        mask.sum() * interval_minutes,
        2
    )


# ============================================================
# EXPOSURE SUMMARY
# ============================================================

def calculate_summary(
    data,
    episodes
):

    valid_water = data[
        "water_level_smoothed_m"
    ].dropna()

    exposed_states = [
        ExposureState.WETTING.value,
        ExposureState.PARTIAL_SUBMERSION.value,
        ExposureState.DEEP_EXPOSURE.value
    ]

    exposure_data = data[
        data["exposure_state"].isin(
            exposed_states
        )
    ]

    if not exposure_data.empty:

        exposure_start = (
            exposure_data["timestamp"].min()
        )

        exposure_end = (
            exposure_data["timestamp"].max()
        )

        exposure_duration = (
            exposure_end
            - exposure_start
        ).total_seconds() / 60

    else:

        exposure_start = None
        exposure_end = None
        exposure_duration = 0

    # Maximum continuous depth
    maximum_water = (
        valid_water.max()
        if not valid_water.empty
        else None
    )

    # Maximum environmental values
    maximum_conductivity = (
        data["conductivity_ms_cm"]
        .max()
    )

    maximum_humidity = (
        data["humidity_pct"]
        .max()
    )

    # Power/network
    power_off_duration = calculate_state_duration(
        data,
        "power_state",
        "OFF"
    )

    network_offline_duration = calculate_state_duration(
        data,
        "network_state",
        "OFFLINE"
    )

    power_interruptions = count_state_transitions(
        data,
        "power_state",
        "OFF"
    )

    network_outages = count_state_transitions(
        data,
        "network_state",
        "OFFLINE"
    )

    # Maximum observed exposure state
    state_priority = {
        ExposureState.DRY.value: 0,
        ExposureState.WETTING.value: 1,
        ExposureState.PARTIAL_SUBMERSION.value: 2,
        ExposureState.DEEP_EXPOSURE.value: 3,
        ExposureState.UNKNOWN.value: -1
    }

    observed_states = data[
        "exposure_state"
    ].unique()

    dominant_state = max(
        observed_states,
        key=lambda state:
        state_priority.get(state, -1)
    )

    return {

        "asset_id":
            data["asset_id"].iloc[0]
            if "asset_id" in data.columns
            else "UNKNOWN",

        "scenario":
            data["scenario"].iloc[0]
            if "scenario" in data.columns
            else "UNKNOWN",

        "maximum_water_level_m":
            round(maximum_water, 3)
            if maximum_water is not None
            else None,

        "maximum_conductivity_ms_cm":
            round(maximum_conductivity, 3),

        "maximum_humidity_pct":
            round(maximum_humidity, 2),

        "exposure_start":
            exposure_start,

        "exposure_end":
            exposure_end,

        "total_exposure_duration_minutes":
            round(exposure_duration, 2),

        "maximum_exposure_state":
            dominant_state,

        "power_interruptions":
            power_interruptions,

        "power_off_duration_minutes":
            power_off_duration,

        "network_outages":
            network_outages,

        "network_offline_duration_minutes":
            network_offline_duration,

        "episodes":
            episodes
    }


# ============================================================
# MAIN PIPELINE
# ============================================================

def reconstruct_exposure(csv_file):

    data = pd.read_csv(csv_file)

    # 1. Validate
    data = validate_data(data)

    # 2. Smooth measurement noise
    data = smooth_water_level(data)

    # 3. Determine rising/falling/stable
    data = calculate_water_trend(data)

    # 4. Reconstruct exposure states
    data = reconstruct_states(data)

    # 5. Remove isolated classification glitches
    data = remove_state_glitches(data)

    # 6. Build exposure episodes
    episodes = build_episodes(data)

    # 7. Generate summary
    summary = calculate_summary(
        data,
        episodes
    )

    return data, summary


# ============================================================
# DISPLAY
# ============================================================

if __name__ == "__main__":

    file = "flood_event_partial_submersion.csv"

    reconstructed_data, summary = (
        reconstruct_exposure(file)
    )

    print("\n")
    print("=" * 70)
    print("FLOODTRACE EXPOSURE RECONSTRUCTION")
    print("=" * 70)

    print("\nEXPOSURE TIMELINE")
    print("-" * 70)

    print(
        reconstructed_data[
            [
                "timestamp",
                "water_level_m",
                "water_level_smoothed_m",
                "water_trend",
                "exposure_state"
            ]
        ].to_string(index=False)
    )

    print("\n")
    print("=" * 70)
    print("RECONSTRUCTED EXPOSURE EPISODES")
    print("=" * 70)

    for episode in summary["episodes"]:

        print(
            f"{episode['state']:25}"
            f"{episode['start']} → "
            f"{episode['end']}   "
            f"{episode['duration_minutes']} min"
        )

    print("\n")
    print("=" * 70)
    print("EXPOSURE SUMMARY")
    print("=" * 70)

    for key, value in summary.items():

        if key != "episodes":

            print(
                f"{key}: {value}"
            )