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

from simulator.sensor_simulator import (
    generate_flood_event,
    ScenarioType
)

from reconstruction.exposure_engine import (
    reconstruct_exposure
)

from prioritization.priority_engine import (
    generate_priority_report
)


# ============================================================
# FLOODTRACE — FLEET SIMULATION ENGINE
# ============================================================
#
# Generates multiple simulated assets, runs each asset through
# the complete FloodTrace processing pipeline, and creates a
# ranked inspection queue.
#
# Pipeline:
#
#   Scenario
#       ↓
#   Sensor Simulation
#       ↓
#   Exposure Reconstruction
#       ↓
#   Evidence Quality
#       ↓
#   Inspection Priority
#       ↓
#   Fleet Ranking
#
# ============================================================


# ============================================================
# CONFIGURATION
# ============================================================

NUMBER_OF_ASSETS = 100

RANDOM_SEED = 42

OUTPUT_FILE = (
    "fleet/floodtrace_inspection_queue.csv"
)


# ============================================================
# SCENARIO DISTRIBUTION
# ============================================================
#
# We deliberately create a mixture of event conditions.
#
# This gives us a realistic fleet for testing the ranking
# system instead of generating 100 identical assets.
#
# ============================================================

SCENARIOS = [

    ScenarioType.RAIN,

    ScenarioType.PARTIAL_SUBMERSION,

    ScenarioType.DEEP_SUBMERSION,

    ScenarioType.POWER_NETWORK_FAILURE,

    ScenarioType.SENSOR_FAILURE,
]


SCENARIO_WEIGHTS = [

    0.20,  # Rain

    0.35,  # Partial submersion

    0.20,  # Deep submersion

    0.15,  # Power/network failure

    0.10,  # Sensor failure
]


# ============================================================
# GENERATE ASSET
# ============================================================

def generate_asset(
    asset_number,
    scenario,
    seed
):

    asset_id = (
        f"TX-{1000 + asset_number:04d}"
    )

    data = generate_flood_event(

        asset_id=asset_id,

        scenario=scenario,

        duration_minutes=300,

        interval_minutes=5,

        seed=seed
    )

    return asset_id, data


# ============================================================
# PROCESS ONE ASSET
# ============================================================

def process_asset(
    asset_id,
    data
):

    # --------------------------------------------------------
    # Save temporary dataset
    # --------------------------------------------------------

    temporary_file = (
        PROJECT_ROOT
        / "fleet"
        / f"{asset_id}.csv"
    )

    data.to_csv(
        temporary_file,
        index=False
    )

    # --------------------------------------------------------
    # Stage 2
    # Exposure reconstruction
    # --------------------------------------------------------

    reconstructed_data, summary = (
        reconstruct_exposure(
            str(temporary_file)
        )
    )

    # --------------------------------------------------------
    # Stage 4
    # Inspection priority
    # --------------------------------------------------------

    report = generate_priority_report(

        reconstructed_data,

        summary
    )

    return report


# ============================================================
# GENERATE FLEET
# ============================================================

def generate_fleet():

    rng = np.random.default_rng(
        RANDOM_SEED
    )

    fleet_reports = []

    print("\n")
    print("=" * 75)
    print("FLOODTRACE — FLEET SIMULATION")
    print("=" * 75)

    print(
        f"\nGenerating "
        f"{NUMBER_OF_ASSETS} simulated assets..."
    )

    for asset_number in range(
        1,
        NUMBER_OF_ASSETS + 1
    ):

        # ----------------------------------------------------
        # Select scenario
        # ----------------------------------------------------

        scenario = rng.choice(

            SCENARIOS,

            p=SCENARIO_WEIGHTS
        )

        # ----------------------------------------------------
        # Unique seed per asset
        # ----------------------------------------------------

        seed = (
            RANDOM_SEED
            + asset_number
        )

        # ----------------------------------------------------
        # Generate sensor dataset
        # ----------------------------------------------------

        asset_id, data = (
            generate_asset(

                asset_number,

                scenario,

                seed
            )
        )

        # ----------------------------------------------------
        # Process complete pipeline
        # ----------------------------------------------------

        try:

            report = process_asset(

                asset_id,

                data
            )

            fleet_reports.append(
                report
            )

        except Exception as error:

            print(
                f"\nERROR processing "
                f"{asset_id}: {error}"
            )


    # ========================================================
    # BUILD FLEET DATAFRAME
    # ========================================================

    fleet = pd.DataFrame(
        fleet_reports
    )

    if fleet.empty:

        raise RuntimeError(
            "No assets were successfully processed."
        )

    # --------------------------------------------------------
    # Rank assets
    # --------------------------------------------------------

    fleet = fleet.sort_values(

        by=[
            "priority_score",
            "evidence_quality_score"
        ],

        ascending=[
            False,
            False
        ]
    ).reset_index(
        drop=True
    )

    fleet.insert(

        0,

        "rank",

        range(
            1,
            len(fleet) + 1
        )
    )

    # ========================================================
    # SAVE FINAL QUEUE
    # ========================================================

    fleet.to_csv(

        PROJECT_ROOT
        / OUTPUT_FILE,

        index=False
    )

    return fleet


# ============================================================
# FLEET SUMMARY
# ============================================================

def print_fleet_summary(
    fleet
):

    print("\n")
    print("=" * 75)
    print("FLOODTRACE — INSPECTION QUEUE")
    print("=" * 75)

    # --------------------------------------------------------
    # Top 20
    # --------------------------------------------------------

    display_columns = [

        "rank",

        "asset_id",

        "scenario",

        "maximum_exposure",

        "maximum_water_level_m",

        "exposure_duration_minutes",

        "evidence_quality_score",

        "priority_score",

        "inspection_priority",
    ]

    print("\nTOP PRIORITY ASSETS")
    print("-" * 75)

    print(

        fleet[
            display_columns
        ]
        .head(20)
        .to_string(
            index=False
        )
    )

    # ========================================================
    # PRIORITY DISTRIBUTION
    # ========================================================

    print("\n")
    print("=" * 75)
    print("PRIORITY DISTRIBUTION")
    print("=" * 75)

    priority_counts = (

        fleet[
            "inspection_priority"
        ]
        .value_counts()
    )

    priority_order = [

        "CRITICAL",

        "HIGH",

        "MEDIUM",

        "LOW",
    ]

    for priority in priority_order:

        count = priority_counts.get(
            priority,
            0
        )

        percentage = (
            count
            / len(fleet)
            * 100
        )

        print(

            f"{priority:10}"
            f"{count:4} assets   "
            f"{percentage:6.2f}%"
        )

    # ========================================================
    # SCENARIO DISTRIBUTION
    # ========================================================

    print("\n")
    print("=" * 75)
    print("SCENARIO DISTRIBUTION")
    print("=" * 75)

    scenario_counts = (
        fleet[
            "scenario"
        ]
        .value_counts()
    )

    for scenario, count in (
        scenario_counts.items()
    ):

        print(
            f"{scenario:30}"
            f"{count:4}"
        )

    # ========================================================
    # STATISTICS
    # ========================================================

    print("\n")
    print("=" * 75)
    print("FLEET STATISTICS")
    print("=" * 75)

    print(

        f"\nTotal assets: "
        f"{len(fleet)}"
    )

    print(

        f"Average priority score: "
        f"{fleet['priority_score'].mean():.2f}"
    )

    print(

        f"Maximum priority score: "
        f"{fleet['priority_score'].max():.2f}"
    )

    print(

        f"Minimum priority score: "
        f"{fleet['priority_score'].min():.2f}"
    )

    print(

        f"Average evidence quality: "
        f"{fleet['evidence_quality_score'].mean():.2f}%"
    )

    # ========================================================
    # OUTPUT
    # ========================================================

    print("\n")
    print("=" * 75)

    print(
        "Inspection queue saved to:"
    )

    print(
        OUTPUT_FILE
    )

    print("=" * 75)


# ============================================================
# MAIN
# ============================================================

if __name__ == "__main__":

    fleet = generate_fleet()

    print_fleet_summary(
        fleet
    )