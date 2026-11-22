import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import pandas as pd
import numpy as np


# ============================================================
# FLOODTRACE — EVIDENCE QUALITY ENGINE v2
# ============================================================
#
# This score represents confidence in the QUALITY and
# COMPLETENESS of the recorded exposure evidence.
#
# It does NOT represent:
# - equipment damage probability
# - equipment safety
# - re-energization safety
#
# ============================================================


WEIGHTS = {
    "data_completeness": 0.30,
    "sensor_integrity": 0.20,
    "temporal_continuity": 0.15,
    "cross_sensor_consistency": 0.20,
    "reconstruction_stability": 0.15,
}


SENSOR_COLUMNS = [
    "water_level_m",
    "humidity_pct",
    "conductivity_ms_cm",
    "temperature_c",
    "power_state",
    "network_state",
]


# ============================================================
# 1. DATA COMPLETENESS
# ============================================================

def calculate_data_completeness(data):

    available = [
        c for c in SENSOR_COLUMNS
        if c in data.columns
    ]

    if not available:
        return 0.0

    total = len(data) * len(available)

    valid = data[available].notna().sum().sum()

    return float(valid / total)


# ============================================================
# 2. SENSOR INTEGRITY
# ============================================================

def calculate_sensor_integrity(data):

    if "sensor_integrity" not in data.columns:
        return 0.0

    integrity = pd.to_numeric(
        data["sensor_integrity"],
        errors="coerce"
    ).clip(0, 1)

    if integrity.dropna().empty:
        return 0.0

    return float(integrity.mean())


# ============================================================
# 3. TEMPORAL CONTINUITY
# ============================================================

def calculate_temporal_continuity(data):

    timestamps = pd.to_datetime(
        data["timestamp"],
        errors="coerce"
    ).dropna().sort_values()

    if len(timestamps) < 2:
        return 0.0

    intervals = (
        timestamps.diff()
        .dt.total_seconds()
        .div(60)
        .dropna()
    )

    if intervals.empty:
        return 0.0

    expected = intervals.mode().iloc[0]

    if expected <= 0:
        return 0.0

    tolerance = expected * 0.20

    valid_intervals = (
        (intervals >= expected - tolerance)
        &
        (intervals <= expected + tolerance)
    )

    return float(valid_intervals.mean())


# ============================================================
# 4. SENSOR COVERAGE PENALTY
# ============================================================
#
# Correlation alone can be misleading.
#
# Example:
#
# 100 measurements available
# 95 measurements missing
#
# The remaining 5 measurements could still correlate
# perfectly.
#
# Therefore cross-sensor consistency is multiplied by
# the availability of BOTH sensors.
# ============================================================

def pair_consistency(
    data,
    column_a,
    column_b
):

    if (
        column_a not in data.columns
        or
        column_b not in data.columns
    ):
        return None

    pair = data[
        [column_a, column_b]
    ].dropna()

    total = len(data)

    if total == 0:
        return 0.0

    coverage = len(pair) / total

    if len(pair) < 3:
        return 0.0

    correlation = pair[
        column_a
    ].corr(
        pair[column_b]
    )

    if pd.isna(correlation):
        return 0.0

    correlation_score = np.clip(
        correlation,
        0,
        1
    )

    # Coverage directly influences confidence.
    return float(
        correlation_score * coverage
    )


def calculate_cross_sensor_consistency(data):

    pairs = [
        (
            "water_level_m",
            "humidity_pct"
        ),
        (
            "water_level_m",
            "conductivity_ms_cm"
        ),
    ]

    scores = []

    for a, b in pairs:

        score = pair_consistency(
            data,
            a,
            b
        )

        if score is not None:
            scores.append(score)

    if not scores:
        return 0.0

    return float(np.mean(scores))


# ============================================================
# 5. RECONSTRUCTION STABILITY
# ============================================================

def calculate_reconstruction_stability(data):

    if "exposure_state" not in data.columns:
        return 0.0

    states = (
        data["exposure_state"]
        .dropna()
        .tolist()
    )

    if len(states) < 3:
        return 0.0

    isolated_changes = 0

    for i in range(1, len(states) - 1):

        if (
            states[i - 1] == states[i + 1]
            and
            states[i] != states[i - 1]
        ):
            isolated_changes += 1

    transitions = sum(
        states[i] != states[i - 1]
        for i in range(1, len(states))
    )

    if transitions == 0:
        return 1.0

    instability = (
        isolated_changes / transitions
    )

    return float(
        np.clip(
            1 - instability,
            0,
            1
        )
    )


# ============================================================
# 6. MISSING DATA SEVERITY
# ============================================================

def calculate_missing_data_severity(data):

    completeness = (
        calculate_data_completeness(data)
    )

    # 0 = no missingness
    # 1 = severe missingness

    return 1 - completeness


# ============================================================
# 7. FINAL SCORE
# ============================================================

def calculate_confidence(data):

    components = {

        "data_completeness":
            calculate_data_completeness(data),

        "sensor_integrity":
            calculate_sensor_integrity(data),

        "temporal_continuity":
            calculate_temporal_continuity(data),

        "cross_sensor_consistency":
            calculate_cross_sensor_consistency(data),

        "reconstruction_stability":
            calculate_reconstruction_stability(data),
    }

    weighted_score = sum(
        components[name] * WEIGHTS[name]
        for name in components
    )

    # --------------------------------------------------------
    # Additional penalty for significant missingness
    # --------------------------------------------------------
    #
    # This prevents a dataset with poor coverage from being
    # rescued by excellent correlation in the remaining data.
    # --------------------------------------------------------

    completeness = components[
        "data_completeness"
    ]

    if completeness >= 0.95:
        coverage_factor = 1.00

    elif completeness >= 0.85:
        coverage_factor = 0.95

    elif completeness >= 0.70:
        coverage_factor = 0.85

    elif completeness >= 0.50:
        coverage_factor = 0.70

    else:
        coverage_factor = 0.50

    final_score = (
        weighted_score
        * coverage_factor
    )

    return {
        "components": components,
        "weighted_score": weighted_score,
        "coverage_factor": coverage_factor,
        "confidence_score": final_score
    }


# ============================================================
# 8. CONFIDENCE BAND
# ============================================================

def confidence_band(score):

    if score >= 90:
        return "VERY HIGH"

    elif score >= 75:
        return "HIGH"

    elif score >= 60:
        return "MODERATE"

    elif score >= 40:
        return "LOW"

    return "VERY LOW"


# ============================================================
# 9. EXPLANATION
# ============================================================

def generate_confidence_explanation(
    components,
    score
):

    strengths = []
    weaknesses = []

    for name, value in components.items():

        percentage = value * 100

        readable = (
            name
            .replace("_", " ")
            .title()
        )

        if percentage >= 90:

            strengths.append(
                f"{readable}: "
                f"{percentage:.1f}%"
            )

        elif percentage < 75:

            weaknesses.append(
                f"{readable}: "
                f"{percentage:.1f}%"
            )

    return {
        "strengths": strengths,
        "weaknesses": weaknesses,
        "confidence_band":
            confidence_band(score)
    }


# ============================================================
# 10. COMPLETE REPORT
# ============================================================

def generate_evidence_report(data):

    result = calculate_confidence(data)

    score = (
        result["confidence_score"] * 100
    )

    explanation = (
        generate_confidence_explanation(
            result["components"],
            score
        )
    )

    return {

        "confidence_score":
            round(score, 2),

        "confidence_band":
            explanation[
                "confidence_band"
            ],

        "components":
            {
                key: round(
                    value * 100,
                    2
                )
                for key, value
                in result[
                    "components"
                ].items()
            },

        "coverage_factor":
            result["coverage_factor"],

        "strengths":
            explanation[
                "strengths"
            ],

        "weaknesses":
            explanation[
                "weaknesses"
            ]
    }


# ============================================================
# 11. TEST MULTIPLE DATASETS
# ============================================================

if __name__ == "__main__":

    from reconstruction.exposure_engine import (
        reconstruct_exposure
    )

    files = [
        "flood_event_partial_submersion.csv",
        "flood_event_sensor_failure.csv",
        "flood_event_deep_submersion.csv",
    ]

    print("\n")
    print("=" * 75)
    print("FLOODTRACE — EVIDENCE QUALITY VALIDATION")
    print("=" * 75)

    for file in files:

        try:

            reconstructed, summary = (
                reconstruct_exposure(file)
            )

            report = generate_evidence_report(
                reconstructed
            )

            print("\n")
            print("-" * 75)
            print(f"DATASET: {file}")
            print("-" * 75)

            print(
                f"Evidence Confidence : "
                f"{report['confidence_score']:.2f}%"
            )

            print(
                f"Confidence Band     : "
                f"{report['confidence_band']}"
            )

            print(
                f"Coverage Factor     : "
                f"{report['coverage_factor']:.2f}"
            )

            print("\nComponents:")

            for name, value in report[
                "components"
            ].items():

                print(
                    f"  {name.replace('_', ' ').title():35}"
                    f"{value:.2f}%"
                )

            if report["weaknesses"]:

                print("\nEvidence weaknesses:")

                for weakness in report[
                    "weaknesses"
                ]:

                    print(
                        f"  - {weakness}"
                    )

        except Exception as error:

            print(
                f"\nERROR processing {file}:"
            )

            print(error)

    print("\n")
    print("=" * 75)
    print(
        "The score represents evidence quality, "
        "not equipment safety or damage probability."
    )
    print("=" * 75)