import sys
from pathlib import Path

# ============================================================
# PROJECT PATH
# ============================================================

PROJECT_ROOT = Path(__file__).resolve().parent.parent

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


import pandas as pd
import numpy as np

from reconstruction.exposure_engine import (
    reconstruct_exposure
)

from evidence.confidence import (
    generate_evidence_report
)


# ============================================================
# FLOODTRACE — INSPECTION PRIORITIZATION ENGINE
# ============================================================
#
# PURPOSE
# -------
# Rank assets for qualified post-event inspection using
# reconstructed environmental exposure evidence.
#
# IMPORTANT SAFETY BOUNDARY
# ------------------------
# This system:
#
#   DOES:
#       - reconstruct exposure
#       - quantify environmental evidence
#       - rank inspection priority
#
#   DOES NOT:
#       - diagnose equipment damage
#       - determine electrical safety
#       - authorize re-energization
#       - certify equipment as safe
#
# ============================================================


# ============================================================
# PRIORITY MODEL
# ============================================================
#
# Final score:
#
#   45% → Exposure severity
#   20% → Exposure duration
#   10% → Environmental severity
#   10% → Power disturbance
#   15% → Evidence quality
#
# Total = 100%
#
# Network availability is NOT directly treated as damage.
# It is handled by the evidence-quality layer.
#
# ============================================================

PRIORITY_WEIGHTS = {

    "exposure_severity": 0.45,

    "exposure_duration": 0.20,

    "environmental_severity": 0.10,

    "power_disturbance": 0.10,

    "evidence_quality": 0.15,
}


# ============================================================
# MODEL NORMALIZATION RANGES
# ============================================================
#
# These are simulation/model reference ranges.
#
# They are NOT electrical safety thresholds.
#
# They simply allow different measurements to be combined
# into normalized 0–1 scores.
#
# ============================================================

MAX_EXPECTED_WATER_M = 1.50

MAX_EXPECTED_DURATION_MIN = 360.0

MAX_EXPECTED_CONDUCTIVITY = 2.50

MAX_EXPECTED_HUMIDITY = 100.0


# ============================================================
# NORMALIZATION
# ============================================================

def normalize(
    value,
    minimum,
    maximum
):

    if value is None:
        return 0.0

    if pd.isna(value):
        return 0.0

    if maximum <= minimum:
        return 0.0

    score = (
        value - minimum
    ) / (
        maximum - minimum
    )

    return float(
        np.clip(
            score,
            0.0,
            1.0
        )
    )


# ============================================================
# EXPOSURE STATE SEVERITY
# ============================================================

def get_exposure_state_score(
    exposure_state
):

    state_scores = {

        "DRY":
            0.00,

        "WETTING":
            0.20,

        "PARTIAL_SUBMERSION":
            0.65,

        "DEEP_EXPOSURE":
            1.00,

        "UNKNOWN":
            0.00,
    }

    return state_scores.get(
        exposure_state,
        0.00
    )


# ============================================================
# EXPOSURE SEVERITY
# ============================================================

def calculate_exposure_severity(
    summary
):

    maximum_water = (
        summary[
            "maximum_water_level_m"
        ]
    )

    maximum_state = (
        summary[
            "maximum_exposure_state"
        ]
    )

    # --------------------------------------------------------
    # Water depth component
    # --------------------------------------------------------

    water_score = normalize(
        maximum_water,
        0,
        MAX_EXPECTED_WATER_M
    )

    # --------------------------------------------------------
    # Exposure-state component
    # --------------------------------------------------------

    state_score = (
        get_exposure_state_score(
            maximum_state
        )
    )

    # --------------------------------------------------------
    # Combine
    #
    # State is slightly more important because it represents
    # the reconstructed exposure category.
    # --------------------------------------------------------

    severity = (

        0.60 * state_score

        +

        0.40 * water_score
    )

    return float(
        np.clip(
            severity,
            0,
            1
        )
    )


# ============================================================
# EXPOSURE DURATION
# ============================================================

def calculate_duration_score(
    summary
):

    duration = (
        summary[
            "total_exposure_duration_minutes"
        ]
    )

    return normalize(
        duration,
        0,
        MAX_EXPECTED_DURATION_MIN
    )


# ============================================================
# ENVIRONMENTAL SEVERITY
# ============================================================

def calculate_environmental_severity(
    summary
):

    conductivity = (
        summary[
            "maximum_conductivity_ms_cm"
        ]
    )

    humidity = (
        summary[
            "maximum_humidity_pct"
        ]
    )

    conductivity_score = normalize(
        conductivity,
        0,
        MAX_EXPECTED_CONDUCTIVITY
    )

    humidity_score = normalize(
        humidity,
        40,
        MAX_EXPECTED_HUMIDITY
    )

    # Conductivity is given greater weight because it provides
    # additional environmental context for floodwater exposure.

    environmental_score = (

        0.70 * conductivity_score

        +

        0.30 * humidity_score
    )

    return float(
        np.clip(
            environmental_score,
            0,
            1
        )
    )


# ============================================================
# POWER DISTURBANCE
# ============================================================

def calculate_power_disturbance(
    summary
):

    interruptions = (
        summary[
            "power_interruptions"
        ]
    )

    duration = (
        summary[
            "power_off_duration_minutes"
        ]
    )

    interruption_score = normalize(
        interruptions,
        0,
        3
    )

    duration_score = normalize(
        duration,
        0,
        180
    )

    disturbance_score = (

        0.50 * interruption_score

        +

        0.50 * duration_score
    )

    return float(
        np.clip(
            disturbance_score,
            0,
            1
        )
    )


# ============================================================
# EVIDENCE QUALITY
# ============================================================

def calculate_evidence_quality(
    reconstructed_data
):

    report = (
        generate_evidence_report(
            reconstructed_data
        )
    )

    score = (
        report[
            "confidence_score"
        ]
        / 100
    )

    return float(
        np.clip(
            score,
            0,
            1
        )
    )


# ============================================================
# FINAL PRIORITY SCORE
# ============================================================

def calculate_priority(
    reconstructed_data,
    summary
):

    # --------------------------------------------------------
    # Calculate individual components
    # --------------------------------------------------------

    exposure_score = (
        calculate_exposure_severity(
            summary
        )
    )

    duration_score = (
        calculate_duration_score(
            summary
        )
    )

    environmental_score = (
        calculate_environmental_severity(
            summary
        )
    )

    power_score = (
        calculate_power_disturbance(
            summary
        )
    )

    evidence_score = (
        calculate_evidence_quality(
            reconstructed_data
        )
    )

    # --------------------------------------------------------
    # Weighted final score
    # --------------------------------------------------------

    final_score = (

        PRIORITY_WEIGHTS[
            "exposure_severity"
        ]
        * exposure_score

        +

        PRIORITY_WEIGHTS[
            "exposure_duration"
        ]
        * duration_score

        +

        PRIORITY_WEIGHTS[
            "environmental_severity"
        ]
        * environmental_score

        +

        PRIORITY_WEIGHTS[
            "power_disturbance"
        ]
        * power_score

        +

        PRIORITY_WEIGHTS[
            "evidence_quality"
        ]
        * evidence_score
    )

    final_score = float(
        np.clip(
            final_score,
            0,
            1
        )
    )

    return {

        "exposure_severity_score":
            round(
                exposure_score * 100,
                2
            ),

        "exposure_duration_score":
            round(
                duration_score * 100,
                2
            ),

        "environmental_severity_score":
            round(
                environmental_score * 100,
                2
            ),

        "power_disturbance_score":
            round(
                power_score * 100,
                2
            ),

        "evidence_quality_score":
            round(
                evidence_score * 100,
                2
            ),

        "priority_score":
            round(
                final_score * 100,
                2
            ),
    }


# ============================================================
# PRIORITY CLASSIFICATION
# ============================================================

def classify_priority(
    priority_score
):

    if priority_score >= 80:

        return "CRITICAL"

    elif priority_score >= 60:

        return "HIGH"

    elif priority_score >= 35:

        return "MEDIUM"

    else:

        return "LOW"


# ============================================================
# INSPECTION RECOMMENDATION
# ============================================================

def generate_recommendation(
    priority
):

    recommendations = {

        "CRITICAL":
            (
                "Prioritize qualified inspection "
                "as early as operationally feasible."
            ),

        "HIGH":
            (
                "Prioritize for qualified "
                "post-event inspection."
            ),

        "MEDIUM":
            (
                "Include in the qualified inspection "
                "queue after higher-priority assets."
            ),

        "LOW":
            (
                "Lower inspection priority based on "
                "reconstructed exposure evidence."
            ),
    }

    return recommendations[
        priority
    ]


# ============================================================
# COMPLETE ASSET REPORT
# ============================================================

def generate_priority_report(
    reconstructed_data,
    summary
):

    scores = calculate_priority(
        reconstructed_data,
        summary
    )

    priority = classify_priority(
        scores[
            "priority_score"
        ]
    )

    recommendation = (
        generate_recommendation(
            priority
        )
    )

    return {

        # ----------------------------------------------------
        # Asset information
        # ----------------------------------------------------

        "asset_id":
            summary[
                "asset_id"
            ],

        "scenario":
            summary[
                "scenario"
            ],

        # ----------------------------------------------------
        # Exposure information
        # ----------------------------------------------------

        "maximum_exposure":
            summary[
                "maximum_exposure_state"
            ],

        "maximum_water_level_m":
            summary[
                "maximum_water_level_m"
            ],

        "exposure_duration_minutes":
            summary[
                "total_exposure_duration_minutes"
            ],

        "maximum_conductivity_ms_cm":
            summary[
                "maximum_conductivity_ms_cm"
            ],

        "maximum_humidity_pct":
            summary[
                "maximum_humidity_pct"
            ],

        # ----------------------------------------------------
        # Disturbance information
        # ----------------------------------------------------

        "power_interruptions":
            summary[
                "power_interruptions"
            ],

        "power_off_duration_minutes":
            summary[
                "power_off_duration_minutes"
            ],

        "network_outages":
            summary[
                "network_outages"
            ],

        "network_offline_duration_minutes":
            summary[
                "network_offline_duration_minutes"
            ],

        # ----------------------------------------------------
        # Scores
        # ----------------------------------------------------

        "exposure_severity_score":
            scores[
                "exposure_severity_score"
            ],

        "exposure_duration_score":
            scores[
                "exposure_duration_score"
            ],

        "environmental_severity_score":
            scores[
                "environmental_severity_score"
            ],

        "power_disturbance_score":
            scores[
                "power_disturbance_score"
            ],

        "evidence_quality_score":
            scores[
                "evidence_quality_score"
            ],

        # ----------------------------------------------------
        # Final decision-support output
        # ----------------------------------------------------

        "priority_score":
            scores[
                "priority_score"
            ],

        "inspection_priority":
            priority,

        "recommendation":
            recommendation,
    }


# ============================================================
# DISPLAY REPORT
# ============================================================

def print_report(
    report
):

    print("\n")

    print("=" * 75)

    print(
        "FLOODTRACE — INSPECTION PRIORITIZATION"
    )

    print("=" * 75)

    print(
        f"\nAsset: "
        f"{report['asset_id']}"
    )

    print(
        f"Scenario: "
        f"{report['scenario']}"
    )

    print(
        f"Maximum Exposure: "
        f"{report['maximum_exposure']}"
    )

    print(
        f"Maximum Water Level: "
        f"{report['maximum_water_level_m']} m"
    )

    print(
        f"Exposure Duration: "
        f"{report['exposure_duration_minutes']} min"
    )

    print(
        f"Maximum Conductivity: "
        f"{report['maximum_conductivity_ms_cm']} "
        f"mS/cm"
    )

    print("\n")

    print("=" * 75)

    print(
        "PRIORITY COMPONENTS"
    )

    print("=" * 75)

    print(
        f"Exposure Severity:       "
        f"{report['exposure_severity_score']:.2f}"
    )

    print(
        f"Exposure Duration:       "
        f"{report['exposure_duration_score']:.2f}"
    )

    print(
        f"Environmental Severity:  "
        f"{report['environmental_severity_score']:.2f}"
    )

    print(
        f"Power Disturbance:       "
        f"{report['power_disturbance_score']:.2f}"
    )

    print(
        f"Evidence Quality:        "
        f"{report['evidence_quality_score']:.2f}"
    )

    print("\n")

    print("=" * 75)

    print(
        "FINAL DECISION"
    )

    print("=" * 75)

    print(
        f"\nPriority Score: "
        f"{report['priority_score']:.2f}/100"
    )

    print(
        f"Inspection Priority: "
        f"{report['inspection_priority']}"
    )

    print(
        "\nRecommendation:"
    )

    print(
        report[
            "recommendation"
        ]
    )

    print("\n")

    print("=" * 75)

    print(
        "This ranking prioritizes inspection attention."
    )

    print(
        "It does not diagnose damage, determine "
        "equipment safety, or authorize re-energization."
    )

    print("=" * 75)


# ============================================================
# TEST
# ============================================================

if __name__ == "__main__":

    # --------------------------------------------------------
    # Dataset used for this test
    # --------------------------------------------------------

    file = (
        "flood_event_partial_submersion.csv"
    )

    # --------------------------------------------------------
    # Reconstruct exposure
    # --------------------------------------------------------

    reconstructed_data, summary = (
        reconstruct_exposure(
            file
        )
    )

    # --------------------------------------------------------
    # Generate priority report
    # --------------------------------------------------------

    report = (
        generate_priority_report(
            reconstructed_data,
            summary
        )
    )

    # --------------------------------------------------------
    # Display
    # --------------------------------------------------------

    print_report(
        report
    )