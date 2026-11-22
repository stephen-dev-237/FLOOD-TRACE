import sys
from pathlib import Path
import json

# ============================================================
# PROJECT PATH
# ============================================================

PROJECT_ROOT = Path(__file__).resolve().parent.parent

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


import pandas as pd

from reconstruction.exposure_engine import (
    reconstruct_exposure
)

from evidence.confidence import (
    generate_evidence_report
)

from prioritization.priority_engine import (
    generate_priority_report
)


# ============================================================
# FLOODTRACE — ASSET EXPOSURE PASSPORT
# ============================================================
#
# PURPOSE
# -------
# Combine all reconstructed evidence for one asset into a
# single structured record.
#
# Pipeline:
#
# RAW DATA
#    ↓
# EXPOSURE RECONSTRUCTION
#    ↓
# EVIDENCE QUALITY
#    ↓
# INSPECTION PRIORITY
#    ↓
# ASSET EXPOSURE PASSPORT
#
# IMPORTANT:
# The passport records exposure evidence.
#
# It does NOT:
# - diagnose equipment damage
# - certify equipment safety
# - authorize re-energization
#
# ============================================================


# ============================================================
# PASSPORT VERSION
# ============================================================

PASSPORT_VERSION = "1.0"


# ============================================================
# HELPER
# ============================================================

def clean_value(value):

    """
    Convert values into JSON-safe Python types.
    """

    if value is None:
        return None

    if pd.isna(value):
        return None

    if hasattr(value, "item"):

        try:
            return value.item()

        except Exception:
            pass

    if hasattr(value, "isoformat"):

        try:
            return value.isoformat()

        except Exception:
            pass

    return value


# ============================================================
# BUILD EXPOSURE TIMELINE
# ============================================================

def build_exposure_timeline(
    reconstructed_data
):

    timeline = []

    for _, row in (
        reconstructed_data.iterrows()
    ):

        timeline.append({

            "timestamp":
                clean_value(
                    row["timestamp"]
                ),

            "water_level_m":
                clean_value(
                    row[
                        "water_level_m"
                    ]
                ),

            "water_level_smoothed_m":
                clean_value(
                    row[
                        "water_level_smoothed_m"
                    ]
                ),

            "water_trend":
                clean_value(
                    row[
                        "water_trend"
                    ]
                ),

            "exposure_state":
                clean_value(
                    row[
                        "exposure_state"
                    ]
                ),

            "power_state":
                clean_value(
                    row[
                        "power_state"
                    ]
                ),

            "network_state":
                clean_value(
                    row[
                        "network_state"
                    ]
                ),

            "sensor_integrity":
                clean_value(
                    row[
                        "sensor_integrity"
                    ]
                ),
        })

    return timeline


# ============================================================
# BUILD EPISODES
# ============================================================

def build_exposure_episodes(
    summary
):

    episodes = []

    for episode in summary.get(
        "episodes",
        []
    ):

        episodes.append({

            "state":
                clean_value(
                    episode["state"]
                ),

            "start":
                clean_value(
                    episode["start"]
                ),

            "end":
                clean_value(
                    episode["end"]
                ),

            "duration_minutes":
                clean_value(
                    episode[
                        "duration_minutes"
                    ]
                ),
        })

    return episodes


# ============================================================
# GENERATE PASSPORT
# ============================================================

def generate_passport(
    reconstructed_data,
    summary
):

    # --------------------------------------------------------
    # Evidence quality
    # --------------------------------------------------------

    evidence_report = (
        generate_evidence_report(
            reconstructed_data
        )
    )

    # --------------------------------------------------------
    # Inspection priority
    # --------------------------------------------------------

    priority_report = (
        generate_priority_report(

            reconstructed_data,

            summary
        )
    )

    # --------------------------------------------------------
    # Build passport
    # --------------------------------------------------------

    passport = {

        # ====================================================
        # METADATA
        # ====================================================

        "passport_metadata": {

            "passport_version":
                PASSPORT_VERSION,

            "system":
                "FloodTrace",

            "record_type":
                "Asset Exposure Passport",

            "generated_at":
                pd.Timestamp.now(
                    tz="UTC"
                ).isoformat(),

            "purpose":
                (
                    "Post-event environmental "
                    "exposure reconstruction "
                    "and inspection prioritization."
                ),
        },

        # ====================================================
        # ASSET
        # ====================================================

        "asset": {

            "asset_id":
                clean_value(
                    summary[
                        "asset_id"
                    ]
                ),
        },

        # ====================================================
        # EVENT
        # ====================================================

        "event": {

            "scenario":
                clean_value(
                    summary[
                        "scenario"
                    ]
                ),

            "exposure_start":
                clean_value(
                    summary[
                        "exposure_start"
                    ]
                ),

            "exposure_end":
                clean_value(
                    summary[
                        "exposure_end"
                    ]
                ),

            "total_exposure_duration_minutes":
                clean_value(
                    summary[
                        "total_exposure_duration_minutes"
                    ]
                ),
        },

        # ====================================================
        # EXPOSURE SUMMARY
        # ====================================================

        "exposure_summary": {

            "maximum_exposure_state":
                clean_value(
                    summary[
                        "maximum_exposure_state"
                    ]
                ),

            "maximum_water_level_m":
                clean_value(
                    summary[
                        "maximum_water_level_m"
                    ]
                ),

            "maximum_conductivity_ms_cm":
                clean_value(
                    summary[
                        "maximum_conductivity_ms_cm"
                    ]
                ),

            "maximum_humidity_pct":
                clean_value(
                    summary[
                        "maximum_humidity_pct"
                    ]
                ),
        },

        # ====================================================
        # POWER / NETWORK HISTORY
        # ====================================================

        "disturbance_history": {

            "power_interruptions":
                clean_value(
                    summary[
                        "power_interruptions"
                    ]
                ),

            "power_off_duration_minutes":
                clean_value(
                    summary[
                        "power_off_duration_minutes"
                    ]
                ),

            "network_outages":
                clean_value(
                    summary[
                        "network_outages"
                    ]
                ),

            "network_offline_duration_minutes":
                clean_value(
                    summary[
                        "network_offline_duration_minutes"
                    ]
                ),
        },

        # ====================================================
        # EXPOSURE EPISODES
        # ====================================================

        "exposure_episodes":
            build_exposure_episodes(
                summary
            ),

        # ====================================================
        # EVIDENCE QUALITY
        # ====================================================

        "evidence_quality": {

            "score":
                clean_value(
                    evidence_report[
                        "confidence_score"
                    ]
                ),

            "band":
                clean_value(
                    evidence_report[
                        "confidence_band"
                    ]
                ),

            "components":
                {
                    key:
                    clean_value(value)

                    for key, value
                    in evidence_report[
                        "components"
                    ].items()
                },

            "coverage_factor":
                clean_value(
                    evidence_report[
                        "coverage_factor"
                    ]
                ),

            "strengths":
                evidence_report[
                    "strengths"
                ],

            "weaknesses":
                evidence_report[
                    "weaknesses"
                ],
        },

        # ====================================================
        # INSPECTION PRIORITY
        # ====================================================

        "inspection_priority": {

            "priority_score":
                clean_value(
                    priority_report[
                        "priority_score"
                    ]
                ),

            "priority_class":
                clean_value(
                    priority_report[
                        "inspection_priority"
                    ]
                ),

            "components": {

                "exposure_severity":
                    clean_value(
                        priority_report[
                            "exposure_severity_score"
                        ]
                    ),

                "exposure_duration":
                    clean_value(
                        priority_report[
                            "exposure_duration_score"
                        ]
                    ),

                "environmental_severity":
                    clean_value(
                        priority_report[
                            "environmental_severity_score"
                        ]
                    ),

                "power_disturbance":
                    clean_value(
                        priority_report[
                            "power_disturbance_score"
                        ]
                    ),

                "evidence_quality":
                    clean_value(
                        priority_report[
                            "evidence_quality_score"
                        ]
                    ),
            },

            "recommendation":
                clean_value(
                    priority_report[
                        "recommendation"
                    ]
                ),
        },

        # ====================================================
        # RAW RECONSTRUCTED TIMELINE
        # ====================================================

        "reconstructed_timeline":
            build_exposure_timeline(
                reconstructed_data
            ),

        # ====================================================
        # SAFETY BOUNDARY
        # ====================================================

        "system_boundary": {

            "damage_diagnosis":
                False,

            "equipment_safety_certification":
                False,

            "reenergization_authorization":
                False,

            "qualified_inspection_required":
                True,

            "statement":
                (
                    "This passport records reconstructed "
                    "environmental exposure evidence and "
                    "supports inspection prioritization. "
                    "It does not diagnose equipment damage "
                    "or certify equipment safety."
                ),
        },
    }

    return passport


# ============================================================
# SAVE PASSPORT
# ============================================================

def save_passport(
    passport,
    output_file
):

    output_path = (
        PROJECT_ROOT
        / output_file
    )

    output_path.parent.mkdir(
        parents=True,
        exist_ok=True
    )

    with open(
        output_path,
        "w",
        encoding="utf-8"
    ) as file:

        json.dump(
            passport,
            file,
            indent=4,
            ensure_ascii=False
        )

    return output_path


# ============================================================
# PRINT PASSPORT SUMMARY
# ============================================================

def print_passport(
    passport
):

    asset = passport[
        "asset"
    ]

    event = passport[
        "event"
    ]

    exposure = passport[
        "exposure_summary"
    ]

    evidence = passport[
        "evidence_quality"
    ]

    priority = passport[
        "inspection_priority"
    ]

    print("\n")

    print("=" * 75)

    print(
        "FLOODTRACE — ASSET EXPOSURE PASSPORT"
    )

    print("=" * 75)

    print(
        f"\nAsset ID: "
        f"{asset['asset_id']}"
    )

    print(
        f"Scenario: "
        f"{event['scenario']}"
    )

    print("\n")
    print("-" * 75)

    print("EXPOSURE")

    print("-" * 75)

    print(
        f"Maximum State: "
        f"{exposure['maximum_exposure_state']}"
    )

    print(
        f"Peak Water Level: "
        f"{exposure['maximum_water_level_m']} m"
    )

    print(
        f"Peak Conductivity: "
        f"{exposure['maximum_conductivity_ms_cm']} mS/cm"
    )

    print(
        f"Maximum Humidity: "
        f"{exposure['maximum_humidity_pct']}%"
    )

    print(
        f"Exposure Duration: "
        f"{event['total_exposure_duration_minutes']} min"
    )

    print("\n")
    print("-" * 75)

    print("EVIDENCE QUALITY")

    print("-" * 75)

    print(
        f"Evidence Score: "
        f"{evidence['score']}%"
    )

    print(
        f"Evidence Band: "
        f"{evidence['band']}"
    )

    print(
        f"Coverage Factor: "
        f"{evidence['coverage_factor']}"
    )

    print("\n")
    print("-" * 75)

    print("INSPECTION PRIORITY")

    print("-" * 75)

    print(
        f"Priority Score: "
        f"{priority['priority_score']}/100"
    )

    print(
        f"Priority Class: "
        f"{priority['priority_class']}"
    )

    print(
        f"Recommendation: "
        f"{priority['recommendation']}"
    )

    print("\n")
    print("-" * 75)

    print("SYSTEM BOUNDARY")

    print("-" * 75)

    print(
        "Damage diagnosis: NO"
    )

    print(
        "Safety certification: NO"
    )

    print(
        "Re-energization authorization: NO"
    )

    print(
        "Qualified inspection: REQUIRED"
    )

    print("\n")

    print("=" * 75)


# ============================================================
# MAIN TEST
# ============================================================

if __name__ == "__main__":

    # --------------------------------------------------------
    # Test with the highest-priority asset from the fleet
    # --------------------------------------------------------

    file = (
        "fleet/TX-1061.csv"
    )

    # --------------------------------------------------------
    # Stage 2
    # --------------------------------------------------------

    reconstructed_data, summary = (
        reconstruct_exposure(
            str(
                PROJECT_ROOT
                / file
            )
        )
    )

    # --------------------------------------------------------
    # Stage 6
    # --------------------------------------------------------

    passport = generate_passport(

        reconstructed_data,

        summary
    )

    # --------------------------------------------------------
    # Save
    # --------------------------------------------------------

    output_path = save_passport(

        passport,

        "passport/TX-1061_passport.json"
    )

    # --------------------------------------------------------
    # Display
    # --------------------------------------------------------

    print_passport(
        passport
    )

    print(
        f"\nPassport saved to:"
    )

    print(
        output_path
    )