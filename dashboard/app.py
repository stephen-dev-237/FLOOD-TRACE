import sys
from pathlib import Path
import json

# ============================================================
# FLOODTRACE DASHBOARD
# ============================================================

PROJECT_ROOT = Path(__file__).resolve().parent.parent

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import pandas as pd
import plotly.graph_objects as go
import streamlit as st


# ============================================================
# PAGE CONFIG
# ============================================================

st.set_page_config(
    page_title="FloodTrace",
    page_icon="🌊",
    layout="wide",
    initial_sidebar_state="expanded",
)


# ============================================================
# CUSTOM CSS
# ============================================================

st.html(
    """
    <style>

    .ft-hero {
        padding: 28px 32px;
        border-radius: 18px;
        border: 1px solid rgba(128,128,128,0.25);
        margin-bottom: 28px;
    }

    .ft-title {
        font-size: 34px;
        font-weight: 800;
        line-height: 1.1;
        margin-bottom: 8px;
    }

    .ft-subtitle {
        font-size: 15px;
        opacity: 0.65;
    }

    .ft-card {
        padding: 20px;
        border-radius: 14px;
        border: 1px solid rgba(128,128,128,0.25);
        min-height: 115px;
        box-sizing: border-box;
    }

    .ft-label {
        font-size: 12px;
        font-weight: 600;
        opacity: 0.60;
        text-transform: uppercase;
        letter-spacing: 0.06em;
    }

    .ft-value {
        font-size: 25px;
        font-weight: 750;
        margin-top: 12px;
        word-break: break-word;
    }

    .ft-section {
        font-size: 21px;
        font-weight: 750;
        margin-top: 28px;
        margin-bottom: 12px;
    }

    .ft-boundary {
        padding: 20px;
        border-radius: 14px;
        border: 1px solid rgba(128,128,128,0.25);
        line-height: 1.8;
    }

    </style>
    """
)


# ============================================================
# HEADER
# ============================================================

st.html(
    """
    <div class="ft-hero">

        <div class="ft-title">
            🌊 FLOODTRACE
        </div>

        <div class="ft-subtitle">
            Post-Flood Exposure Intelligence & Inspection Prioritization
        </div>

    </div>
    """
)


# ============================================================
# LOAD FLEET QUEUE
# ============================================================

QUEUE_FILE = (
    PROJECT_ROOT
    / "fleet"
    / "floodtrace_inspection_queue.csv"
)


if not QUEUE_FILE.exists():

    st.error(
        "Fleet inspection queue not found."
    )

    st.info(
        "Run: python fleet/fleet_engine.py"
    )

    st.stop()


fleet = pd.read_csv(
    QUEUE_FILE
)


# ============================================================
# CLEAN NUMERIC DATA
# ============================================================

numeric_columns = [
    "priority_score",
    "evidence_quality_score",
    "maximum_water_level_m",
    "exposure_duration_minutes",
    "maximum_conductivity_ms_cm",
    "maximum_humidity_pct",
]

for column in numeric_columns:

    if column in fleet.columns:

        fleet[column] = pd.to_numeric(
            fleet[column],
            errors="coerce"
        )


# ============================================================
# SIDEBAR
# ============================================================

st.sidebar.title(
    "FloodTrace"
)

st.sidebar.caption(
    "Exposure Intelligence Console"
)

st.sidebar.divider()

page = st.sidebar.radio(
    "Navigation",
    [
        "Fleet Overview",
        "Inspection Queue",
        "Asset Passport",
    ]
)

st.sidebar.divider()

st.sidebar.caption(
    f"{len(fleet)} simulated assets loaded"
)


# ============================================================
# METRICS
# ============================================================

total_assets = len(fleet)

critical_count = (
    fleet["inspection_priority"]
    .eq("CRITICAL")
    .sum()
)

high_count = (
    fleet["inspection_priority"]
    .eq("HIGH")
    .sum()
)

medium_count = (
    fleet["inspection_priority"]
    .eq("MEDIUM")
    .sum()
)

low_count = (
    fleet["inspection_priority"]
    .eq("LOW")
    .sum()
)


# ============================================================
# METRIC CARD
# ============================================================

def metric_card(
    label,
    value
):

    st.html(
        f"""
        <div class="ft-card">

            <div class="ft-label">
                {label}
            </div>

            <div class="ft-value">
                {value}
            </div>

        </div>
        """
    )


# ============================================================
# SECTION TITLE
# ============================================================

def section_title(
    title
):

    st.html(
        f"""
        <div class="ft-section">
            {title}
        </div>
        """
    )


# ============================================================
# PAGE 1 — FLEET OVERVIEW
# ============================================================

if page == "Fleet Overview":

    section_title(
        "Fleet Overview"
    )

    # --------------------------------------------------------
    # Summary cards
    # --------------------------------------------------------

    col1, col2, col3, col4, col5 = st.columns(5)

    with col1:
        metric_card(
            "Assets Analyzed",
            total_assets
        )

    with col2:
        metric_card(
            "Critical",
            critical_count
        )

    with col3:
        metric_card(
            "High",
            high_count
        )

    with col4:
        metric_card(
            "Medium",
            medium_count
        )

    with col5:
        metric_card(
            "Low",
            low_count
        )

    # --------------------------------------------------------
    # Priority distribution
    # --------------------------------------------------------

    section_title(
        "Inspection Priority Distribution"
    )

    priority_counts = (
        fleet[
            "inspection_priority"
        ]
        .value_counts()
        .reindex(
            [
                "CRITICAL",
                "HIGH",
                "MEDIUM",
                "LOW"
            ],
            fill_value=0
        )
    )

    fig = go.Figure()

    fig.add_trace(
        go.Bar(
            x=priority_counts.index,
            y=priority_counts.values,
            text=priority_counts.values,
            textposition="auto",
        )
    )

    fig.update_layout(
        height=380,
        margin=dict(
            l=20,
            r=20,
            t=20,
            b=20
        ),
        xaxis_title="Inspection Priority",
        yaxis_title="Number of Assets",
    )

    st.plotly_chart(
        fig,
        use_container_width=True
    )

    # --------------------------------------------------------
    # Scenario distribution
    # --------------------------------------------------------

    section_title(
        "Event Scenario Distribution"
    )

    scenario_counts = (
        fleet[
            "scenario"
        ]
        .value_counts()
    )

    fig2 = go.Figure()

    fig2.add_trace(
        go.Bar(
            x=scenario_counts.index,
            y=scenario_counts.values,
            text=scenario_counts.values,
            textposition="auto",
        )
    )

    fig2.update_layout(
        height=380,
        margin=dict(
            l=20,
            r=20,
            t=20,
            b=20
        ),
        xaxis_title="Scenario",
        yaxis_title="Assets",
    )

    st.plotly_chart(
        fig2,
        use_container_width=True
    )

    # --------------------------------------------------------
    # Priority score distribution
    # --------------------------------------------------------

    section_title(
        "Priority Score Distribution"
    )

    fig3 = go.Figure()

    fig3.add_trace(
        go.Histogram(
            x=fleet[
                "priority_score"
            ],
            nbinsx=20,
        )
    )

    fig3.update_layout(
        height=350,
        margin=dict(
            l=20,
            r=20,
            t=20,
            b=20
        ),
        xaxis_title="Priority Score",
        yaxis_title="Assets",
    )

    st.plotly_chart(
        fig3,
        use_container_width=True
    )


# ============================================================
# PAGE 2 — INSPECTION QUEUE
# ============================================================

elif page == "Inspection Queue":

    section_title(
        "Inspection Queue"
    )

    st.caption(
        "Assets ranked by reconstructed exposure evidence and inspection priority."
    )

    # --------------------------------------------------------
    # Filters
    # --------------------------------------------------------

    col1, col2 = st.columns(2)

    with col1:

        priority_filter = st.multiselect(
            "Priority",
            [
                "CRITICAL",
                "HIGH",
                "MEDIUM",
                "LOW"
            ],
            default=[
                "CRITICAL",
                "HIGH",
                "MEDIUM",
                "LOW"
            ]
        )

    with col2:

        scenario_options = sorted(
            fleet[
                "scenario"
            ]
            .dropna()
            .unique()
            .tolist()
        )

        scenario_filter = st.multiselect(
            "Scenario",
            scenario_options,
            default=scenario_options
        )

    filtered = fleet[
        fleet[
            "inspection_priority"
        ].isin(
            priority_filter
        )
        &
        fleet[
            "scenario"
        ].isin(
            scenario_filter
        )
    ].copy()

    # --------------------------------------------------------
    # Table
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

    st.dataframe(
        filtered[
            display_columns
        ],
        use_container_width=True,
        hide_index=True,
    )

    # --------------------------------------------------------
    # Download
    # --------------------------------------------------------

    csv_data = filtered.to_csv(
        index=False
    )

    st.download_button(
        label="Download Inspection Queue",
        data=csv_data,
        file_name="floodtrace_inspection_queue.csv",
        mime="text/csv",
    )


# ============================================================
# PAGE 3 — ASSET PASSPORT
# ============================================================

elif page == "Asset Passport":

    section_title(
        "Asset Exposure Passport"
    )

    # --------------------------------------------------------
    # Asset selection
    # --------------------------------------------------------

    asset_ids = (
        fleet[
            "asset_id"
        ]
        .astype(str)
        .tolist()
    )

    selected_asset = st.selectbox(
        "Select Asset",
        asset_ids
    )

    selected_row = fleet[
        fleet[
            "asset_id"
        ].astype(str)
        == selected_asset
    ]

    if selected_row.empty:

        st.warning(
            "Asset not found."
        )

        st.stop()

    # --------------------------------------------------------
    # Passport file
    # --------------------------------------------------------

    passport_file = (
        PROJECT_ROOT
        / "passport"
        / f"{selected_asset}_passport.json"
    )

    if not passport_file.exists():

        st.warning(
            f"Passport not found for {selected_asset}."
        )

        st.info(
            "Run: python passport/generate_all_passports.py"
        )

        st.stop()

    with open(
        passport_file,
        "r",
        encoding="utf-8"
    ) as file:

        passport = json.load(
            file
        )

    # ========================================================
    # TOP SUMMARY
    # ========================================================

    col1, col2, col3, col4 = st.columns(4)

    with col1:

        metric_card(
            "Asset",
            selected_asset
        )

    with col2:

        metric_card(
            "Exposure",
            passport[
                "exposure_summary"
            ][
                "maximum_exposure_state"
            ]
        )

    with col3:

        metric_card(
            "Evidence",
            f"{passport['evidence_quality']['score']}%"
        )

    with col4:

        metric_card(
            "Priority",
            passport[
                "inspection_priority"
            ][
                "priority_class"
            ]
        )

    # ========================================================
    # EXPOSURE
    # ========================================================

    section_title(
        "Exposure Reconstruction"
    )

    exposure = passport[
        "exposure_summary"
    ]

    event = passport[
        "event"
    ]

    col1, col2, col3, col4 = st.columns(4)

    with col1:

        metric_card(
            "Peak Water",
            f"{exposure['maximum_water_level_m']} m"
        )

    with col2:

        metric_card(
            "Duration",
            f"{event['total_exposure_duration_minutes']} min"
        )

    with col3:

        metric_card(
            "Conductivity",
            f"{exposure['maximum_conductivity_ms_cm']} mS/cm"
        )

    with col4:

        metric_card(
            "Humidity",
            f"{exposure['maximum_humidity_pct']}%"
        )

    # ========================================================
    # EVIDENCE QUALITY
    # ========================================================

    section_title(
        "Evidence Quality"
    )

    evidence = passport[
        "evidence_quality"
    ]

    evidence_components = (
        evidence[
            "components"
        ]
    )

    evidence_df = pd.DataFrame(
        {
            "Component":
                [
                    key.replace(
                        "_",
                        " "
                    ).title()

                    for key
                    in evidence_components
                ],

            "Score":
                [
                    float(value)
                    for value
                    in evidence_components.values()
                ]
        }
    )

    fig4 = go.Figure()

    fig4.add_trace(
        go.Bar(
            x=evidence_df[
                "Score"
            ],
            y=evidence_df[
                "Component"
            ],
            orientation="h",
            text=[
                f"{x:.2f}%"
                for x in evidence_df[
                    "Score"
                ]
            ],
            textposition="auto",
        )
    )

    fig4.update_layout(
        height=350,
        margin=dict(
            l=20,
            r=20,
            t=20,
            b=20
        ),
        xaxis_title="Evidence Quality (%)",
        yaxis_title="",
        xaxis=dict(
            range=[
                0,
                100
            ]
        )
    )

    st.plotly_chart(
        fig4,
        use_container_width=True
    )

    # ========================================================
    # INSPECTION PRIORITY
    # ========================================================

    section_title(
        "Inspection Priority"
    )

    priority = passport[
        "inspection_priority"
    ]

    col1, col2 = st.columns(2)

    with col1:

        metric_card(
            "Priority Score",
            f"{priority['priority_score']}/100"
        )

    with col2:

        metric_card(
            "Classification",
            priority[
                "priority_class"
            ]
        )

    st.info(
        priority[
            "recommendation"
        ]
    )

    # ========================================================
    # EXPOSURE TIMELINE
    # ========================================================

    section_title(
        "Exposure Timeline"
    )

    timeline = pd.DataFrame(
        passport[
            "reconstructed_timeline"
        ]
    )

    if not timeline.empty:

        timeline[
            "timestamp"
        ] = pd.to_datetime(
            timeline[
                "timestamp"
            ]
        )

        fig5 = go.Figure()

        fig5.add_trace(
            go.Scatter(
                x=timeline[
                    "timestamp"
                ],
                y=timeline[
                    "water_level_m"
                ],
                mode="lines",
                name="Water Level",
                line=dict(
                    width=3
                )
            )
        )

        fig5.add_trace(
            go.Scatter(
                x=timeline[
                    "timestamp"
                ],
                y=timeline[
                    "water_level_smoothed_m"
                ],
                mode="lines",
                name="Smoothed Water Level",
                line=dict(
                    dash="dash"
                )
            )
        )

        fig5.update_layout(
            height=450,
            margin=dict(
                l=20,
                r=20,
                t=20,
                b=20
            ),
            xaxis_title="Time",
            yaxis_title="Water Level (m)",
            hovermode="x unified",
        )

        st.plotly_chart(
            fig5,
            use_container_width=True
        )

    # ========================================================
    # EXPOSURE EPISODES
    # ========================================================

    section_title(
        "Exposure Episodes"
    )

    episodes = passport[
        "exposure_episodes"
    ]

    if episodes:

        episodes_df = pd.DataFrame(
            episodes
        )

        st.dataframe(
            episodes_df,
            use_container_width=True,
            hide_index=True,
        )

    else:

        st.info(
            "No exposure episodes recorded."
        )

    # ========================================================
    # SYSTEM BOUNDARY
    # ========================================================

    section_title(
        "System Boundary"
    )

    boundary = passport[
        "system_boundary"
    ]

    st.html(
        f"""
        <div class="ft-boundary">

            <b>
                FloodTrace provides exposure evidence
                and inspection prioritization.
            </b>

            <br><br>

            Damage diagnosis:
            <b>NO</b>

            <br>

            Equipment safety certification:
            <b>NO</b>

            <br>

            Re-energization authorization:
            <b>NO</b>

            <br>

            Qualified inspection:
            <b>REQUIRED</b>

            <br><br>

            {boundary['statement']}

        </div>
        """
    )