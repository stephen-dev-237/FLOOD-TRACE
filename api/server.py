import sys
import json
import uuid
from pathlib import Path
from typing import Any

import pandas as pd
import numpy as np

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel


# ============================================================
# FLOODTRACE API
# ============================================================

PROJECT_ROOT = Path(__file__).resolve().parent.parent

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


# ============================================================
# FLOODTRACE ENGINES
# ============================================================

from reconstruction.exposure_engine import (
    reconstruct_exposure
)

from evidence.confidence import (
    generate_evidence_report
)

from prioritization.priority_engine import (
    generate_priority_report
)

from passport.passport_generator import (
    generate_passport,
    save_passport
)

from simulator.sensor_simulator import (
    generate_flood_event,
    ScenarioType
)


# ============================================================
# APP
# ============================================================

app = FastAPI(
    title="FloodTrace API",
    description=(
        "Local API bridge for the FloodTrace "
        "post-flood exposure intelligence platform."
    ),
    version="1.0.0"
)

from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://127.0.0.1:5500",
        "http://localhost:5500",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
# ============================================================
# CORS
# ============================================================

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============================================================
# PATHS
# ============================================================

FLEET_DIR = (
    PROJECT_ROOT / "fleet"
)

PASSPORT_DIR = (
    PROJECT_ROOT / "passport"
)

QUEUE_FILE = (
    FLEET_DIR /
    "floodtrace_inspection_queue.csv"
)


# ============================================================
# SIMULATION STATE
# ============================================================

simulation_state = {

    "running": False,

    "simulation_id": None,

    "asset_id": None,

    "scenario": None,

    "current_index": 0,

    "total_points": 0,

    "data": None,

    "reconstructed": None,

    "summary": None,

    "evidence": None,

    "priority": None,
}


# ============================================================
# JSON SERIALIZATION
# ============================================================

def json_safe(value: Any):

    if value is None:
        return None

    if isinstance(
        value,
        (np.integer,)
    ):
        return int(value)

    if isinstance(
        value,
        (np.floating,)
    ):
        return float(value)

    if isinstance(
        value,
        (np.bool_,)
    ):
        return bool(value)

    if isinstance(
        value,
        pd.Timestamp
    ):
        return value.isoformat()

    if isinstance(
        value,
        np.ndarray
    ):
        return [
            json_safe(x)
            for x in value.tolist()
        ]

    if isinstance(
        value,
        dict
    ):
        return {
            str(k): json_safe(v)
            for k, v in value.items()
        }

    if isinstance(
        value,
        (list, tuple)
    ):
        return [
            json_safe(x)
            for x in value
        ]

    if pd.isna(value):
        return None

    return value


# ============================================================
# DATAFRAME → JSON
# ============================================================

def dataframe_to_records(
    dataframe
):

    if dataframe is None:
        return []

    records = dataframe.to_dict(
        orient="records"
    )

    return json_safe(
        records
    )


# ============================================================
# HEALTH
# ============================================================

@app.get("/")
def root():

    return {

        "system": "FloodTrace",

        "status": "online",

        "version": "1.0.0",

        "mode": "simulation",

        "message":
            "FloodTrace API is running."
    }


@app.get("/api/health")
def health():

    return {

        "status": "online",

        "engines": {

            "simulator": True,

            "reconstruction": True,

            "evidence": True,

            "prioritization": True,

            "passport": True,
        }
    }


# ============================================================
# FLEET
# ============================================================

@app.get("/api/fleet")
def get_fleet():

    if not QUEUE_FILE.exists():

        raise HTTPException(
            status_code=404,
            detail=(
                "Fleet queue not found. "
                "Run fleet/fleet_engine.py first."
            )
        )

    fleet = pd.read_csv(
        QUEUE_FILE
    )

    fleet = fleet.replace(
        {
            np.nan: None
        }
    )

    return {

        "total_assets":
            len(fleet),

        "assets":
            dataframe_to_records(
                fleet
            )
    }


# ============================================================
# FLEET SUMMARY
# ============================================================

@app.get("/api/fleet/summary")
def get_fleet_summary():

    if not QUEUE_FILE.exists():

        raise HTTPException(
            status_code=404,
            detail="Fleet queue not found."
        )

    fleet = pd.read_csv(
        QUEUE_FILE
    )

    priority_counts = (
        fleet[
            "inspection_priority"
        ]
        .value_counts()
        .to_dict()
    )

    scenario_counts = (
        fleet[
            "scenario"
        ]
        .value_counts()
        .to_dict()
    )

    return {

        "total_assets":
            int(len(fleet)),

        "priority_distribution":
            json_safe(
                priority_counts
            ),

        "scenario_distribution":
            json_safe(
                scenario_counts
            ),

        "average_priority_score":
            float(
                fleet[
                    "priority_score"
                ].mean()
            ),

        "maximum_priority_score":
            float(
                fleet[
                    "priority_score"
                ].max()
            ),

        "minimum_priority_score":
            float(
                fleet[
                    "priority_score"
                ].min()
            ),

        "average_evidence_quality":
            float(
                fleet[
                    "evidence_quality_score"
                ].mean()
            ),
    }


# ============================================================
# ASSET PASSPORT
# ============================================================

@app.get("/api/assets/{asset_id}")
def get_asset(
    asset_id: str
):

    passport_file = (
        PASSPORT_DIR /
        f"{asset_id}_passport.json"
    )

    if not passport_file.exists():

        raise HTTPException(
            status_code=404,
            detail=(
                f"Passport for "
                f"{asset_id} not found."
            )
        )

    with open(
        passport_file,
        "r",
        encoding="utf-8"
    ) as file:

        passport = json.load(
            file
        )

    return json_safe(
        passport
    )


# ============================================================
# ASSET TIMELINE
# ============================================================

@app.get(
    "/api/assets/{asset_id}/timeline"
)
def get_asset_timeline(
    asset_id: str
):

    passport_file = (
        PASSPORT_DIR /
        f"{asset_id}_passport.json"
    )

    if not passport_file.exists():

        raise HTTPException(
            status_code=404,
            detail="Asset passport not found."
        )

    with open(
        passport_file,
        "r",
        encoding="utf-8"
    ) as file:

        passport = json.load(
            file
        )

    return {

        "asset_id":
            asset_id,

        "timeline":
            passport[
                "reconstructed_timeline"
            ]
    }


# ============================================================
# ASSET EXPOSURE
# ============================================================

@app.get(
    "/api/assets/{asset_id}/exposure"
)
def get_asset_exposure(
    asset_id: str
):

    passport_file = (
        PASSPORT_DIR /
        f"{asset_id}_passport.json"
    )

    if not passport_file.exists():

        raise HTTPException(
            status_code=404,
            detail="Asset passport not found."
        )

    with open(
        passport_file,
        "r",
        encoding="utf-8"
    ) as file:

        passport = json.load(
            file
        )

    return {

        "asset_id":
            asset_id,

        "event":
            passport[
                "event"
            ],

        "exposure_summary":
            passport[
                "exposure_summary"
            ],

        "exposure_episodes":
            passport[
                "exposure_episodes"
            ],

        "disturbance_history":
            passport[
                "disturbance_history"
            ],
    }


# ============================================================
# ASSET EVIDENCE
# ============================================================

@app.get(
    "/api/assets/{asset_id}/evidence"
)
def get_asset_evidence(
    asset_id: str
):

    passport_file = (
        PASSPORT_DIR /
        f"{asset_id}_passport.json"
    )

    if not passport_file.exists():

        raise HTTPException(
            status_code=404,
            detail="Asset passport not found."
        )

    with open(
        passport_file,
        "r",
        encoding="utf-8"
    ) as file:

        passport = json.load(
            file
        )

    return {

        "asset_id":
            asset_id,

        "evidence_quality":
            passport[
                "evidence_quality"
            ]
    }


# ============================================================
# ASSET PRIORITY
# ============================================================

@app.get(
    "/api/assets/{asset_id}/priority"
)
def get_asset_priority(
    asset_id: str
):

    passport_file = (
        PASSPORT_DIR /
        f"{asset_id}_passport.json"
    )

    if not passport_file.exists():

        raise HTTPException(
            status_code=404,
            detail="Asset passport not found."
        )

    with open(
        passport_file,
        "r",
        encoding="utf-8"
    ) as file:

        passport = json.load(
            file
        )

    return {

        "asset_id":
            asset_id,

        "inspection_priority":
            passport[
                "inspection_priority"
            ]
    }


# ============================================================
# SIMULATION REQUEST
# ============================================================

class SimulationRequest(
    BaseModel
):

    asset_id: str = "SIM-0001"

    scenario: str = "partial_submersion"

    duration_minutes: int = 300

    interval_minutes: int = 5

    seed: int = 42


# ============================================================
# SCENARIO CONVERSION
# ============================================================

def get_scenario(
    scenario_name: str
):

    normalized = (
        scenario_name
        .strip()
        .lower()
        .replace(
            " ",
            "_"
        )
        .replace(
            "-",
            "_"
        )
    )

    mapping = {

        "rain":
            ScenarioType.RAIN,

        "partial_submersion":
            ScenarioType.PARTIAL_SUBMERSION,

        "deep_submersion":
            ScenarioType.DEEP_SUBMERSION,

        "power_network_failure":
            ScenarioType.POWER_NETWORK_FAILURE,

        "sensor_failure":
            ScenarioType.SENSOR_FAILURE,
    }

    if normalized not in mapping:

        raise HTTPException(
            status_code=400,
            detail={
                "error":
                    "Unknown scenario.",

                "available_scenarios":
                    list(
                        mapping.keys()
                    )
            }
        )

    return mapping[
        normalized
    ]


# ============================================================
# RUN SIMULATION
# ============================================================

@app.post(
    "/api/simulation/run"
)
def run_simulation(
    request: SimulationRequest
):

    scenario = get_scenario(
        request.scenario
    )

    asset_id = (
        request.asset_id
        .strip()
    )

    if not asset_id:

        raise HTTPException(
            status_code=400,
            detail="Asset ID cannot be empty."
        )

    # --------------------------------------------------------
    # Generate sensor data
    # --------------------------------------------------------

    data = generate_flood_event(

        asset_id=asset_id,

        scenario=scenario,

        duration_minutes=
            request.duration_minutes,

        interval_minutes=
            request.interval_minutes,

        seed=request.seed
    )

    # --------------------------------------------------------
    # Save simulated sensor data
    # --------------------------------------------------------

    simulation_file = (
        FLEET_DIR /
        f"{asset_id}_live_simulation.csv"
    )

    data.to_csv(
        simulation_file,
        index=False
    )

    # --------------------------------------------------------
    # Exposure reconstruction
    # --------------------------------------------------------

    reconstructed_data, summary = (
        reconstruct_exposure(
            str(simulation_file)
        )
    )

    # --------------------------------------------------------
    # Evidence quality
    # --------------------------------------------------------

    evidence = (
        generate_evidence_report(
            reconstructed_data
        )
    )

    # --------------------------------------------------------
    # Inspection priority
    # --------------------------------------------------------

    priority = (
        generate_priority_report(

            reconstructed_data,

            summary
        )
    )

    # --------------------------------------------------------
    # Passport
    # --------------------------------------------------------

    passport = generate_passport(

        reconstructed_data,

        summary
    )

    passport_path = save_passport(

        passport,

        f"passport/"
        f"{asset_id}_passport.json"
    )

    # --------------------------------------------------------
    # Store live state
    # --------------------------------------------------------

    simulation_state[
        "running"
    ] = True

    simulation_state[
        "simulation_id"
    ] = str(
        uuid.uuid4()
    )

    simulation_state[
        "asset_id"
    ] = asset_id

    simulation_state[
        "scenario"
    ] = request.scenario

    simulation_state[
        "current_index"
    ] = 0

    simulation_state[
        "total_points"
    ] = len(data)

    simulation_state[
        "data"
    ] = data

    simulation_state[
        "reconstructed"
    ] = reconstructed_data

    simulation_state[
        "summary"
    ] = summary

    simulation_state[
        "evidence"
    ] = evidence

    simulation_state[
        "priority"
    ] = priority

    return {

        "status":
            "simulation_ready",

        "simulation_id":
            simulation_state[
                "simulation_id"
            ],

        "asset_id":
            asset_id,

        "scenario":
            request.scenario,

        "total_points":
            len(data),

        "passport":
            f"/api/assets/{asset_id}",

        "message":
            (
                "Simulation generated and "
                "FloodTrace engines executed."
            )
    }


# ============================================================
# CURRENT SIMULATION STATE
# ============================================================

@app.get(
    "/api/simulation/state"
)
def get_simulation_state():

    if (
        simulation_state[
            "data"
        ] is None
    ):

        return {

            "running": False,

            "message":
                "No simulation loaded."
        }

    data = (
        simulation_state[
            "data"
        ]
    )

    index = (
        simulation_state[
            "current_index"
        ]
    )

    # --------------------------------------------------------
    # Current observation
    # --------------------------------------------------------

    if len(data) > 0:

        current_index = min(
            index,
            len(data) - 1
        )

        current_row = (
            data.iloc[
                current_index
            ]
            .to_dict()
        )

    else:

        current_row = {}

    return {

        "running":
            simulation_state[
                "running"
            ],

        "simulation_id":
            simulation_state[
                "simulation_id"
            ],

        "asset_id":
            simulation_state[
                "asset_id"
            ],

        "scenario":
            simulation_state[
                "scenario"
            ],

        "current_index":
            current_index,

        "total_points":
            len(data),

        "progress_percent":
            (
                (
                    current_index
                    /
                    max(
                        len(data) - 1,
                        1
                    )
                )
                * 100
            ),

        "current_observation":
            json_safe(
                current_row
            ),

        "exposure_summary":
            json_safe(
                simulation_state[
                    "summary"
                ]
            ),

        "evidence":
            json_safe(
                simulation_state[
                    "evidence"
                ]
            ),

        "priority":
            json_safe(
                simulation_state[
                    "priority"
                ]
            ),
    }


# ============================================================
# ADVANCE SIMULATION
# ============================================================

@app.post(
    "/api/simulation/step"
)
def simulation_step():

    if (
        simulation_state[
            "data"
        ] is None
    ):

        raise HTTPException(
            status_code=400,
            detail="No simulation loaded."
        )

    data = (
        simulation_state[
            "data"
        ]
    )

    current_index = (
        simulation_state[
            "current_index"
        ]
    )

    if current_index >= (
        len(data) - 1
    ):

        simulation_state[
            "running"
        ] = False

        return {

            "status":
                "complete",

            "state":
                get_simulation_state()
        }

    simulation_state[
        "current_index"
    ] += 1

    return {

        "status":
            "advanced",

        "state":
            get_simulation_state()
    }


# ============================================================
# PAUSE
# ============================================================

@app.post(
    "/api/simulation/pause"
)
def pause_simulation():

    simulation_state[
        "running"
    ] = False

    return {

        "status":
            "paused"
    }


# ============================================================
# RESET
# ============================================================

@app.post(
    "/api/simulation/reset"
)
def reset_simulation():

    simulation_state[
        "running"
    ] = False

    simulation_state[
        "simulation_id"
    ] = None

    simulation_state[
        "asset_id"
    ] = None

    simulation_state[
        "scenario"
    ] = None

    simulation_state[
        "current_index"
    ] = 0

    simulation_state[
        "total_points"
    ] = 0

    simulation_state[
        "data"
    ] = None

    simulation_state[
        "reconstructed"
    ] = None

    simulation_state[
        "summary"
    ] = None

    simulation_state[
        "evidence"
    ] = None

    simulation_state[
        "priority"
    ] = None

    return {

        "status":
            "reset"
    }


# ============================================================
# LIVE TIMELINE
# ============================================================

@app.get(
    "/api/simulation/timeline"
)
def simulation_timeline():

    if (
        simulation_state[
            "reconstructed"
        ] is None
    ):

        raise HTTPException(
            status_code=404,
            detail="No simulation loaded."
        )

    reconstructed = (
        simulation_state[
            "reconstructed"
        ]
    )

    current_index = (
        simulation_state[
            "current_index"
        ]
    )

    visible = (
        reconstructed
        .iloc[
            :current_index + 1
        ]
    )

    return {

        "asset_id":
            simulation_state[
                "asset_id"
            ],

        "scenario":
            simulation_state[
                "scenario"
            ],

        "timeline":
            dataframe_to_records(
                visible
            )
    }


# ============================================================
# RUN SERVER
# ============================================================

if __name__ == "__main__":

    import uvicorn

    uvicorn.run(

        "api.server:app",

        host="127.0.0.1",

        port=8000,

        reload=True
    )