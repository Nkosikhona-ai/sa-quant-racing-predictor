"""
app.py — SA Quant Racing Predictor & Intelligence Terminal
=============================================================
A professional quantitative horse racing intelligence platform for
South African racing — built for serious bettors and quant analysts.

Frontend Architecture: Refined Financial/Racing Analytics Terminal
Approved Palette:
  - Background: Deep Black (#090B10)
  - Sidebar: Dark Charcoal (#10121A)
  - Card Background: Dark Navy (#161A26)
  - Primary Accent: Champagne / Gold (#E5AD24)
  - Positive Indicator: Emerald Green (#16C784)
  - Negative Indicator: Red (#F04452)
  - Primary Text: Off-White (#F4F5F7)
  - Secondary Text: Muted Grey (#9299A8)
  - Border Subtle: Subtle Dark Grey (#292E3B)
"""

import os
import io
import json
import logging
import dataclasses
import pandas as pd
import numpy as np
import streamlit as st

from extractor import extract_from_pdf, get_demo_horses, Horse, ExtractionResult
from predictor import predict, Prediction, run_race_v311_turffontein, compute_probability_v311_turffontein

# ─── Logging ──────────────────────────────────────────────────────────────────
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ─── Page Configuration ───────────────────────────────────────────────────────
st.set_page_config(
    page_title="SA Quant Racing | Quantitative Intelligence Terminal",
    page_icon="🏇",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ─── Design System & Custom CSS ───────────────────────────────────────────────
st.markdown("""
<style>
/* ─── Typography & Fonts ───────────────────────────────────────────── */
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&family=JetBrains+Mono:wght@400;500;600;700&family=Outfit:wght@400;500;600;700;800;900&family=Rajdhani:wght@600;700&display=swap');

:root {
    --bg-primary: #090B10;
    --bg-sidebar: #10121A;
    --bg-card: #161A26;
    --bg-card-subtle: #1C2232;
    --bg-input: #121520;
    --accent-gold: #E5AD24;
    --accent-gold-bright: #FBD364;
    --accent-gold-dim: rgba(229, 173, 36, 0.12);
    --indicator-green: #16C784;
    --indicator-green-dim: rgba(22, 199, 132, 0.12);
    --indicator-red: #F04452;
    --indicator-red-dim: rgba(240, 68, 82, 0.12);
    --accent-blue: #4D88FF;
    --accent-blue-dim: rgba(77, 136, 255, 0.12);
    --accent-purple: #A78BFA;
    --accent-purple-dim: rgba(167, 139, 250, 0.12);
    --text-primary: #F4F5F7;
    --text-secondary: #9299A8;
    --text-muted: #646E82;
    --border-subtle: #292E3B;
    --border-hover: #3A4256;
}

/* ─── Global App Layout ────────────────────────────────────────────── */
html, body, [class*="css"], .stApp {
    font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
    background-color: var(--bg-primary) !important;
    color: var(--text-primary) !important;
}

#MainMenu, footer, header {
    visibility: hidden;
}

.block-container {
    padding-top: 1.5rem !important;
    padding-bottom: 3rem !important;
    max-width: 1480px !important;
}

/* ─── Sidebar Styling ──────────────────────────────────────────────── */
[data-testid="stSidebar"] {
    background-color: var(--bg-sidebar) !important;
    border-right: 1px solid var(--border-subtle) !important;
}

[data-testid="stSidebar"] .block-container {
    padding: 1.25rem 1rem !important;
}

/* ─── Tabs Styling ─────────────────────────────────────────────────── */
.stTabs [data-baseweb="tab-list"] {
    gap: 8px;
    background-color: rgba(16, 18, 26, 0.7);
    padding: 6px;
    border-radius: 10px;
    border: 1px solid var(--border-subtle);
    margin-bottom: 1.25rem;
}

.stTabs [data-baseweb="tab"] {
    height: 42px;
    border-radius: 8px;
    color: var(--text-secondary);
    font-size: 0.88rem;
    font-weight: 600;
    padding: 0 16px;
    border: 1px solid transparent;
    transition: all 0.2s ease;
}

.stTabs [aria-selected="true"] {
    background-color: var(--bg-card) !important;
    color: var(--accent-gold) !important;
    border: 1px solid rgba(229, 173, 36, 0.35) !important;
    box-shadow: 0 2px 8px rgba(0, 0, 0, 0.3) !important;
}

/* ─── Standard Terminal Card ───────────────────────────────────────── */
.terminal-card {
    background-color: var(--bg-card);
    border: 1px solid var(--border-subtle);
    border-radius: 12px;
    padding: 1.25rem 1.5rem;
    margin-bottom: 1rem;
    transition: border-color 0.2s ease;
}

.terminal-card:hover {
    border-color: var(--border-hover);
}

/* ─── Featured Top Prediction Card ─────────────────────────────────── */
.card-featured-top {
    background: linear-gradient(135deg, rgba(229, 173, 36, 0.12) 0%, rgba(22, 26, 38, 0.98) 100%);
    border: 1px solid rgba(229, 173, 36, 0.35);
    border-radius: 14px;
    padding: 1.5rem 1.75rem;
    position: relative;
    overflow: hidden;
    margin-bottom: 1.25rem;
    box-shadow: 0 8px 24px rgba(0, 0, 0, 0.4);
}

.card-featured-top::before {
    content: "";
    position: absolute;
    top: 0;
    left: 0;
    right: 0;
    height: 3px;
    background: linear-gradient(90deg, var(--accent-gold), var(--accent-gold-bright));
}

/* ─── Race Overview Bar ────────────────────────────────────────────── */
.race-overview-bar {
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    gap: 10px;
    background-color: var(--bg-card);
    border: 1px solid var(--border-subtle);
    border-radius: 10px;
    padding: 0.75rem 1.25rem;
    margin-bottom: 1.25rem;
}

.meta-chip {
    display: inline-flex;
    align-items: center;
    gap: 6px;
    padding: 4px 10px;
    border-radius: 6px;
    background-color: rgba(255, 255, 255, 0.03);
    border: 1px solid var(--border-subtle);
    font-size: 0.8rem;
    color: var(--text-secondary);
}

.meta-chip strong {
    color: var(--text-primary);
    font-weight: 600;
}

.meta-chip-gold {
    background-color: var(--accent-gold-dim);
    border-color: rgba(229, 173, 36, 0.3);
    color: var(--accent-gold);
}

/* ─── Modern Metric Stat Box ───────────────────────────────────────── */
.stat-box {
    background-color: var(--bg-card-subtle);
    border: 1px solid var(--border-subtle);
    border-radius: 8px;
    padding: 0.75rem 1rem;
    text-align: center;
}

.stat-box-label {
    font-size: 0.72rem;
    text-transform: uppercase;
    letter-spacing: 0.08em;
    color: var(--text-muted);
    margin-bottom: 4px;
    font-weight: 600;
}

.stat-box-val {
    font-family: 'JetBrains Mono', monospace;
    font-size: 1.25rem;
    font-weight: 700;
    color: var(--text-primary);
}

/* ─── Responsive Clean Table ───────────────────────────────────────── */
.table-responsive-container {
    width: 100%;
    overflow-x: auto;
    border-radius: 10px;
    border: 1px solid var(--border-subtle);
    margin-bottom: 1.25rem;
    background-color: var(--bg-card);
}

.terminal-data-table {
    width: 100%;
    border-collapse: collapse;
    font-size: 0.85rem;
    color: var(--text-primary);
    text-align: left;
}

.terminal-data-table th {
    background-color: var(--bg-sidebar);
    color: var(--text-secondary);
    font-size: 0.72rem;
    text-transform: uppercase;
    letter-spacing: 0.08em;
    font-weight: 700;
    padding: 12px 14px;
    border-bottom: 1px solid var(--border-subtle);
    white-space: nowrap;
}

.terminal-data-table td {
    padding: 12px 14px;
    border-bottom: 1px solid var(--border-subtle);
    vertical-align: middle;
}

.terminal-data-table tr {
    transition: background-color 0.15s ease;
}

.terminal-data-table tr:hover {
    background-color: rgba(255, 255, 255, 0.02);
}

.terminal-data-table tr.top-pick-row {
    background-color: rgba(229, 173, 36, 0.06);
    border-left: 3px solid var(--accent-gold);
}

.terminal-data-table tr.rank-2-row {
    border-left: 3px solid rgba(192, 192, 192, 0.4);
}

.terminal-data-table tr.rank-3-row {
    border-left: 3px solid rgba(205, 127, 50, 0.4);
}

/* ─── Form Boxes ───────────────────────────────────────────────────── */
.form-box {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    width: 22px;
    height: 22px;
    font-size: 10.5px;
    font-weight: 700;
    border-radius: 4px;
    color: #FFFFFF;
    margin-right: 3px;
    font-family: 'JetBrains Mono', monospace;
}

/* ─── Badges & Signal Tags ─────────────────────────────────────────── */
.signal-tag {
    font-size: 9px;
    font-weight: 800;
    text-transform: uppercase;
    padding: 3px 7px;
    border-radius: 4px;
    letter-spacing: 0.05em;
    display: inline-block;
}

.signal-value {
    background-color: var(--indicator-green-dim);
    color: var(--indicator-green);
    border: 1px solid rgba(22, 199, 132, 0.35);
}

.signal-longshot {
    background-color: rgba(245, 158, 11, 0.15);
    color: #F59E0B;
    border: 1px solid rgba(245, 158, 11, 0.35);
}

/* ─── Exotics Cards ────────────────────────────────────────────────── */
.exotics-card {
    background-color: var(--bg-card);
    border: 1px solid var(--border-subtle);
    border-radius: 12px;
    padding: 1.25rem;
    height: 100%;
    display: flex;
    flex-direction: column;
    justify-content: space-between;
}

.exotics-card-header {
    font-size: 0.75rem;
    font-weight: 800;
    letter-spacing: 0.08em;
    text-transform: uppercase;
    margin-bottom: 0.75rem;
    display: flex;
    justify-content: space-between;
    align-items: center;
}

.combo-box {
    background-color: var(--bg-card-subtle);
    border: 1px solid var(--border-subtle);
    border-radius: 8px;
    padding: 0.9rem;
    margin-bottom: 0.75rem;
}

/* ─── Circular Charts ──────────────────────────────────────────────── */
.circular-chart {
    display: block;
    margin: 8px auto;
    max-width: 76px;
    max-height: 76px;
}

.circle-bg {
    fill: none;
    stroke: rgba(255, 255, 255, 0.06);
    stroke-width: 2.8;
}

.circle {
    fill: none;
    stroke-width: 2.8;
    stroke-linecap: round;
}

.percentage {
    fill: #FFFFFF;
    font-family: 'JetBrains Mono', monospace;
    font-size: 8.5px;
    text-anchor: middle;
    font-weight: 700;
}

/* ─── Custom Dark Buttons ──────────────────────────────────────────── */
.stButton > button {
    border-radius: 8px !important;
    font-size: 0.85rem !important;
    font-weight: 600 !important;
    transition: all 0.2s ease !important;
}

/* Primary Button Override */
button[kind="primary"] {
    background: linear-gradient(135deg, var(--accent-gold), #c9961d) !important;
    color: #090B10 !important;
    border: none !important;
    font-weight: 700 !important;
}

/* Streamlit Expander & Widget Overrides */
[data-testid="stExpander"] {
    background-color: var(--bg-card) !important;
    border: 1px solid var(--border-subtle) !important;
    border-radius: 10px !important;
    margin-bottom: 0.75rem !important;
}

/* Responsive Grid Helper */
@media (max-width: 992px) {
    .race-overview-bar {
        flex-direction: column;
        align-items: flex-start;
    }
}
</style>
""", unsafe_allow_html=True)


# ─── Session State Initialisation ─────────────────────────────────────────────
def _init_state():
    """Initialise default session state variables if not already present."""
    defaults = {
        "horses":               [],
        "all_races":            {},   # {race_num: [Horse, ...]}
        "current_race":         1,
        "extraction":           None,
        "predictions":          [],
        "all_results":          {},   # Authoritative predictions across all races
        "odds_map":             {},
        "processed":            False,
        "demo_mode":            False,
        "race_name":            "Fairview R1 – 1200m (Demo)",
        "venue_selector":       "Fairview",
        "surface_selector":     "Turf",
        "distance_selector":    1200,
        "race_class_selector":  "Stakes",
        "model_mode_selector":  "Greyville Poly v3.13 ★",
        "_last_file_id":        None,
        "races_meta":           {},
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v

_init_state()


def reset_race_state():
    """Wipe race-specific data to prevent stale leakage across uploads/mode switches."""
    st.session_state.horses = []
    st.session_state.all_races = {}
    st.session_state.current_race = 1
    st.session_state.extraction = None
    st.session_state.predictions = []
    st.session_state.all_results = {}
    st.session_state.odds_map = {}
    st.session_state.processed = False
    st.session_state._last_file_id = None
    st.session_state.races_meta = {}


# ─── Model & Status Helpers ───────────────────────────────────────────────────
def _model_mode_badge() -> str:
    """Return styled HTML badge for currently selected model mode."""
    mode = st.session_state.get("model_mode_selector", "Greyville Poly v3.13 ★")
    model_path = os.path.join(os.path.dirname(__file__), "calibration_model_v42.pkl")

    if "v3.13" in mode:
        return '<span style="background:var(--accent-gold-dim); color:var(--accent-gold); border:1px solid rgba(229,173,36,0.35); font-weight:700; font-size:11px; padding:4px 10px; border-radius:20px; display:inline-block;">⚡ Greyville Poly v3.13 Active</span>'
    elif "v3.11" in mode:
        return '<span style="background:rgba(245,200,66,0.15); color:#f5c842; border:1px solid rgba(245,200,66,0.35); font-weight:700; font-size:11px; padding:4px 10px; border-radius:20px; display:inline-block;">⚡ Turffontein v3.11 Active</span>'
    elif "ML Calibrated" in mode:
        if os.path.exists(model_path):
            return '<span style="background:var(--indicator-green-dim); color:var(--indicator-green); border:1px solid rgba(22,199,132,0.35); font-weight:700; font-size:11px; padding:4px 10px; border-radius:20px; display:inline-block;">🤖 ML Calibrated (v4.2) Active</span>'
        return '<span style="background:var(--indicator-red-dim); color:var(--indicator-red); border:1px solid rgba(240,68,82,0.35); font-weight:700; font-size:11px; padding:4px 10px; border-radius:20px; display:inline-block;">⚠️ ML Calibrated (v4.2) - PKL Missing</span>'
    elif "Legacy Rule" in mode:
        return '<span style="background:var(--accent-purple-dim); color:var(--accent-purple); border:1px solid rgba(167,139,250,0.35); font-weight:700; font-size:11px; padding:4px 10px; border-radius:20px; display:inline-block;">📐 Legacy Rule (v3.8) Active</span>'
    return '<span style="background:var(--indicator-green-dim); color:var(--indicator-green); border:1px solid rgba(22,199,132,0.35); font-weight:700; font-size:11px; padding:4px 10px; border-radius:20px; display:inline-block;">🏇 7-Track Adaptive (v3.9) Active</span>'


def get_default_mr(race_class: str, runs: int, first_timer: bool) -> int:
    """Return a sensible default Merit Rating when none is available."""
    class_map = {
        "Grade 1": 108, "Grade 2": 100, "Grade 3": 92, "Listed": 85,
        "Merit Rated (MR)": 80, "Maiden Plate": 72, "Pinnacle Stakes": 95,
        "Other Handicap": 75, "F": 55, "G": 55, "A": 80, "B": 75, "C": 70,
    }
    base = class_map.get(race_class, 70)
    if first_timer:
        base = max(base - 5, 50)
    elif runs == 0:
        base = max(base - 3, 50)
    return base


def preprocess_horse_data(race_horses: list, race_class: str) -> list:
    """Assign default merit ratings and ensure all list fields are initialised."""
    for h in race_horses:
        if isinstance(h, dict):
            runs = h.get("runs", 0)
            first_timer = h.get("first_timer", False)
            if h.get("merit_rating") is None:
                h["merit_rating"] = get_default_mr(race_class, runs, first_timer)
            if "comment_history" not in h:
                h["comment_history"] = []
            if "gear_history" not in h:
                h["gear_history"] = []
        else:
            runs = getattr(h, "runs", 0)
            first_timer = getattr(h, "first_timer", False)
            if getattr(h, "merit_rating", None) is None:
                try:
                    h.merit_rating = get_default_mr(race_class, runs, first_timer)
                except AttributeError:
                    pass
    return race_horses


def _is_filly(horse_name: str, race_type: str = "") -> bool:
    """Deduce if a horse is a filly/mare from the race description."""
    female_keywords = ("fillies", "f & m", "fm", "mare", "filly")
    combined = (horse_name + " " + race_type).lower()
    return any(kw in combined for kw in female_keywords)


def generate_v311_table_string(
    results: list,
    race_num: int,
    race_time: str,
    distance: int,
    field_size: int,
    race_type: str,
    race_horses: list,
) -> str:
    """Generate the professional monospace race results table."""
    lines = []
    sep = "=" * 110
    dash = "-" * 110
    header = f"{'Rnk':<4} {'Horse':<32} {'Dr':<3} {'Wgt':>5} {'Odds':>6} {'Prob':>8} {'EV':>9} | {'Form':<8} {'Jockey':<20}"

    lines.append(sep)
    lines.append(f"RACE {race_num} | {race_time} | {distance}m | {field_size} runners [{race_type}]")
    lines.append(sep)
    lines.append(header)
    lines.append(dash)

    medals = {1: "🏆", 2: "🥈", 3: "🥉"}

    for r in results:
        if hasattr(r, "horse"):
            horse_name = r.horse
            rank = r.rank
            draw = r.draw
            odds = r.odds
            prob = r.probability
            ev = r.ev
            jockey = r.jockey
        else:
            horse_name = r.get("horse", "")
            rank = r.get("rank", 1)
            draw = r.get("draw", 0)
            odds = r.get("odds", 10.0)
            prob = r.get("probability", 0.0)
            ev = r.get("ev", 0.0)
            jockey = r.get("jockey", "")

        matching = next(
            (h for h in race_horses
             if (h.get("horse", "") if hasattr(h, "get") else getattr(h, "horse", "")) == horse_name),
            None,
        )
        weight = 0.0
        form = "N/A"
        if matching:
            weight = matching.get("weight", 0.0) if hasattr(matching, "get") else getattr(matching, "weight", 0.0)
            form = matching.get("form_string", "") if hasattr(matching, "get") else getattr(matching, "form_string", "")
            if not form:
                form = "N/A"

        medal = medals.get(rank, "  ")
        prefix = f"{medal} {rank}" if rank <= 3 else f"   {rank}"
        # Filly indicator
        filly_tag = " [F]" if _is_filly(horse_name, race_type) else ""
        display_name = f"{horse_name}{filly_tag}"

        line = (
            f"{prefix:<4} {display_name:<32} {draw:<3} {weight:>5.1f} {odds:>6.1f} "
            f"{prob*100:>7.1f}% {ev:>+9.3f} | {form:<8} {jockey:<20}"
        )
        lines.append(line)

    lines.append(sep)
    return "\n".join(lines)


def generate_value_bets_block(all_results: dict) -> str:
    """Generate the VALUE BETS SUMMARY block across all races."""
    lines = [
        "=" * 110,
        "⭐ VALUE BETS SUMMARY (WIN BETS - EV > 30%, Rank ≤ 3, Odds ≥ 4/1)",
        "=" * 110,
    ]
    found = False
    for race_num in sorted(all_results.keys()):
        predictions = all_results[race_num]
        for p in predictions:
            vb = p.value_bet if hasattr(p, "value_bet") else p.get("value_bet", False)
            if vb:
                found = True
                horse = p.horse if hasattr(p, "horse") else p.get("horse", "")
                draw = p.draw if hasattr(p, "draw") else p.get("draw", 0)
                odds = p.odds if hasattr(p, "odds") else p.get("odds", 0.0)
                ev = p.ev if hasattr(p, "ev") else p.get("ev", 0.0)
                ev_pct = ev * 100
                conf = "HIGH" if ev_pct >= 40 else "MEDIUM" if ev_pct >= 30 else "MODERATE"
                lines.append(f"   R{race_num}: #{draw} {horse} at {odds:.1f}/1 - EV: {ev_pct:+.1f}% [{conf}] - BET: WIN")
    if not found:
        lines.append("   No value bets meeting criteria (EV > 30%, Rank ≤ 3, Odds ≥ 4/1).")
    return "\n".join(lines)


def generate_longshots_block(all_results: dict) -> str:
    """Generate the LONGSHOT ALERTS block across all races."""
    lines = [
        "=" * 110,
        "🔥 v3.11 LONGSHOT ALERTS (10/1+ with EV > 25%, Rank ≤ 8)",
        "=" * 110,
    ]
    found = False
    for race_num in sorted(all_results.keys()):
        predictions = all_results[race_num]
        for p in predictions:
            ls = p.longshot if hasattr(p, "longshot") else p.get("longshot", False)
            if ls:
                found = True
                horse = p.horse if hasattr(p, "horse") else p.get("horse", "")
                draw = p.draw if hasattr(p, "draw") else p.get("draw", 0)
                odds = p.odds if hasattr(p, "odds") else p.get("odds", 0.0)
                ev = p.ev if hasattr(p, "ev") else p.get("ev", 0.0)
                rank = p.rank if hasattr(p, "rank") else p.get("rank", 0)
                ev_pct = ev * 100
                if odds >= 15.0:
                    icon = "🔥 15/1+ LONGSHOT"
                else:
                    icon = "⚡ LONGSHOT"
                lines.append(f"   ⚡ R{race_num}: {icon}: {horse} at {odds:.1f}/1 (EV: {ev_pct:+.1f}%, Rank: {rank})")
    if not found:
        lines.append("   No longshot alerts meeting criteria.")
    return "\n".join(lines)


def _get_perm_selections(predictions: list, n: int = 3) -> list:
    """Return the top N selections from a race as (draw, horse_name) tuples."""
    sel = []
    for p in predictions[:n]:
        draw = p.draw if hasattr(p, "draw") else p.get("draw", 0)
        horse = p.horse if hasattr(p, "horse") else p.get("horse", "")
        sel.append((draw, horse))
    return sel


def _build_perm_leg_str(selections: list) -> str:
    return ", ".join(f"#{d} {n}" for d, n in selections)


def generate_perms_block(all_results: dict) -> str:
    """Generate BiPot, Pick 6, Jackpot 1, Jackpot 2 perm selections."""
    race_nums = sorted(all_results.keys())
    if not race_nums:
        return ""

    lines = []
    sep = "=" * 90

    def _perm_section(label, legs_race_nums, n_top, n_banker=2):
        sec_lines = [
            sep,
            f"🏆 {label} PERM (v3.11)",
            sep,
        ]
        total_combos = 1
        for leg_idx, rn in enumerate(legs_race_nums, 1):
            if rn not in all_results or not all_results[rn]:
                sec_lines.append(f"  Leg {leg_idx}: (Race {rn} — no predictions)")
                total_combos *= n_top
                continue
            preds = all_results[rn]
            # Use 2 selections for first leg as banker, 3 for rest
            n_sel = n_banker if leg_idx == 1 else n_top
            n_sel = min(n_sel, len(preds))
            sels = _get_perm_selections(preds, n_sel)
            sec_lines.append(f"  Leg {leg_idx}: {_build_perm_leg_str(sels)}")
            total_combos *= n_sel
        sec_lines.append("")
        sec_lines.append(f"  💰 Total combinations: {total_combos}")
        sec_lines.append(f"  💰 Cost (R1/line): R{total_combos}")
        return sec_lines

    # BiPot: Races 2-7
    bipot_races = [r for r in race_nums if 2 <= r <= 7]
    if len(bipot_races) >= 2:
        lines += _perm_section("BIPOT (Races 2-7)", bipot_races[:6], n_top=3, n_banker=2)
        lines.append("")

    # Pick 6: Races 3-8
    p6_races = [r for r in race_nums if 3 <= r <= 8]
    if len(p6_races) >= 2:
        lines += _perm_section("PICK 6 (Races 3-8)", p6_races[:6], n_top=3, n_banker=2)
        lines.append("")

    # Jackpot 1: Races 4-7
    j1_races = [r for r in race_nums if 4 <= r <= 7]
    if len(j1_races) >= 2:
        lines += _perm_section("JACKPOT 1 (Races 4-7)", j1_races[:4], n_top=2, n_banker=1)
        lines.append("")

    # Jackpot 2: Races 5-8
    j2_races = [r for r in race_nums if 5 <= r <= 8]
    if len(j2_races) >= 2:
        lines += _perm_section("JACKPOT 2 (Races 5-8)", j2_races[:4], n_top=2, n_banker=1)

    if not lines:
        return "(Not enough races for perm generation)"
    return "\n".join(lines)


def group_horses_by_race(horses: list) -> dict:
    """Bucket Horse objects by race number, sorted by draw."""
    all_races: dict = {}
    for h in horses:
        rnum = None
        for attr in ['race', 'race_num', 'race_number', 'raceNo']:
            if hasattr(h, attr):
                val = getattr(h, attr)
                if val is not None:
                    rnum = int(val)
                    break
        if rnum is None:
            rnum = 1
        all_races.setdefault(rnum, []).append(h)

    for rnum in all_races:
        all_races[rnum].sort(key=lambda h: getattr(h, 'draw', 0))
    return all_races


def _build_demo_meeting() -> list[Horse]:
    """Generate realistic South African thoroughbred fields across Races 1, 2, and 3."""
    demo_cards = [
        # Race 1
        ("African Gold", 1, 1.90, "1-1-1-2-1", "W. Marwing", "S. Tarry", 105, 1),
        ("Protea Pride", 2, 2.80, "2-1-3-1", "R. Fourie", "J. Snaith", 98, 1),
        ("Silver Storm", 3, 4.50, "3-2-2-4", "M. Yeni", "M. de Kock", 92, 1),
        ("Highveld King", 4, 5.00, "4-1-2-3", "G. Lerena", "C. Dawson", 90, 1),
        ("Vaal Champion", 5, 6.00, "1-4-5-2", "P. Strydom", "A. Fortune", 88, 1),
        ("Dragon Heart", 6, 8.50, "5-3-1-6", "K. Matsunyane", "B. Crawford", 85, 1),
        ("Ubuntu Prince", 7, 7.50, "2-5-4-3", "C. Zackey", "D. Nieuwenhuizen", 84, 1),
        ("Cape Legend", 8, 14.00, "6-7-8-5", "S. Khumalo", "P. Peter", 80, 1),
        # Race 2
        ("Durban Thunder", 1, 2.20, "1-2-1-1", "S. Moodley", "G. van Zyl", 102, 2),
        ("Coastal Express", 2, 3.50, "2-3-1-2", "A. Mgudlwa", "D. Kannemeyer", 96, 2),
        ("Table Mountain", 3, 4.20, "1-1-4-3", "R. Fourie", "J. Snaith", 94, 2),
        ("Karoo Sun", 4, 6.50, "3-4-2-1", "K. de Melo", "M. de Kock", 89, 2),
        ("Golden Willow", 5, 9.00, "5-2-3-5", "M. Yeni", "D. Bosch", 86, 2),
        ("Kalahari King", 6, 12.00, "4-5-1-4", "C. Habib", "W. Whitehead", 84, 2),
        ("Drakensberg", 7, 16.00, "6-6-3-2", "T. Godden", "M. Miller", 81, 2),
        ("Zulu Dawn", 8, 20.00, "7-8-5-4", "S. Hlengwa", "A. Wright", 78, 2),
        # Race 3
        ("Sandton Star", 1, 2.00, "1-1-2-1", "G. Lerena", "J. Janse v Vuuren", 104, 3),
        ("Highveld Storm", 2, 3.20, "2-1-3-2", "P. Strydom", "S. Tarry", 97, 3),
        ("Royal Leopard", 3, 5.50, "1-3-4-1", "R. Danielson", "S. Pettigrew", 93, 3),
        ("Cheetah Strike", 4, 7.00, "4-2-1-3", "M. van Rensburg", "M. Azzie", 89, 3),
        ("Blue Crane", 5, 8.50, "3-5-2-4", "K. Matsunyane", "B. Webber", 86, 3),
        ("Pretoria Lass", 6, 11.00, "5-4-3-2", "C. Maujean", "F. Bronkhorst", 83, 3),
        ("Sun City", 7, 14.00, "6-7-4-5", "J. Penny", "R. Magner", 80, 3),
        ("Gold Reef", 8, 25.00, "8-8-7-6", "D. Schwarz", "C. Spies", 76, 3),
    ]

    horses = []
    for name, dr, odds, form, jock, train, mr, r_num in demo_cards:
        h = Horse(
            horse=name,
            draw=dr,
            saddle=dr,
            weight=58.0,
            jockey=jock,
            trainer=train,
            forecast_odds=odds,
            form_string=form,
            runs=7,
            wins=3,
            third_places=1,
            f3_pct=57,
            merit_rating=mr,
            course_runs=3,
            horse_gear="",
            first_timer=False,
            running_comment="Proven form runner in solid condition.",
            comment_history=[],
            race=r_num
        )
        horses.append(h)
    return horses


def run_extraction(uploaded_file, demo_mode: bool) -> bool:
    """Extract horses from PDF or load demo meeting data."""
    if demo_mode:
        horses = _build_demo_meeting()
        all_races = group_horses_by_race(horses)

        result = ExtractionResult(
            horses=horses,
            confidence=1.0,
            warnings=[],
            raw_text="Demo mode — synthetic South African thoroughbred race meeting data",
            pages_read=3,
        )

        st.session_state.all_races = all_races
        st.session_state.current_race = min(all_races.keys())
        st.session_state.horses = list(all_races[st.session_state.current_race])
        st.session_state.extraction = result
        st.session_state.processed = False
        st.session_state.predictions = []
        st.session_state.all_results = {}
        st.session_state.odds_map = {
            getattr(h, "horse", "Unknown"): getattr(h, "market_odds", getattr(h, "forecast_odds", 0.0))
            for h in horses
        }
        st.session_state.races_meta = {
            1: {"venue": "Fairview", "surface": "Turf", "distance": "1200m", "race_time": "12:15", "stake": "R80,000", "race_number": 1, "betting_leg": "Bipot Leg 1"},
            2: {"venue": "Fairview", "surface": "Turf", "distance": "1200m", "race_time": "12:50", "stake": "R90,000", "race_number": 2, "betting_leg": "Bipot Leg 2"},
            3: {"venue": "Fairview", "surface": "Turf", "distance": "1400m", "race_time": "13:25", "stake": "R100,000", "race_number": 3, "betting_leg": "Place Accumulator Leg 1"},
        }
        return True

    if uploaded_file is None:
        st.warning("⚠️ Please select a Computaform PDF or enable Demo Mode in the sidebar.")
        return False

    file_bytes = uploaded_file.read()
    if len(file_bytes) > 20 * 1024 * 1024:
        st.error("❌ File exceeds maximum permitted size (20 MB).")
        return False

    with st.spinner("📄 Extracting Computaform race data..."):
        try:
            result = extract_from_pdf(file_bytes)
            if result and result.horses:
                def _is_bad_horse(h) -> bool:
                    n = getattr(h, "horse", "").strip()
                    return not n or len(n) < 3

                result.horses = [h for h in result.horses if not _is_bad_horse(h)]

                has_race_0 = any(h.race == 0 for h in result.horses)
                if has_race_0:
                    for h in result.horses:
                        if h.race == 0:
                            h.race = 1

                result.horses.sort(key=lambda h: (h.race, h.draw))
        except Exception as e:
            st.error(f"❌ Extraction error: {e}")
            logger.exception("PDF extraction failed")
            return False

    if not result.is_valid:
        st.error("❌ Extraction incomplete — unable to identify at least 2 valid runners in the uploaded file.")
        return False

    valid_horses = [h for h in result.horses if hasattr(h, "horse")]
    for h in valid_horses:
        if not hasattr(h, 'race') or getattr(h, 'race', None) is None:
            h.race = 1

    race_class = st.session_state.get("race_class_selector", "Grade 1")
    preprocess_horse_data(valid_horses, race_class)
    all_races = group_horses_by_race(valid_horses)

    if len(all_races) == 1 and len(valid_horses) > 12:
        from extractor import _assign_by_saddle_reset
        valid_horses_sorted = sorted(valid_horses, key=lambda h: (getattr(h, 'saddle', 0), getattr(h, 'draw', 0)))
        valid_horses_sorted = _assign_by_saddle_reset(valid_horses_sorted, n_races=len(valid_horses) // 8)
        all_races = group_horses_by_race(valid_horses_sorted)

    if not all_races:
        st.error("❌ No races could be segmented from the extracted data.")
        return False

    first_race = min(all_races.keys())
    st.session_state.races_meta = getattr(result, "races_meta", {})
    st.session_state.all_races = all_races
    st.session_state.current_race = first_race
    st.session_state.horses = list(all_races[first_race])
    st.session_state.extraction = result
    st.session_state.processed = False
    st.session_state.predictions = []
    st.session_state.all_results = {}
    st.session_state.odds_map = {
        getattr(h, "horse", "Unknown"): getattr(h, "market_odds", getattr(h, "forecast_odds", 0.0))
        for h in valid_horses
    }
    st.success(f"✅ Loaded {len(valid_horses)} runners across {len(all_races)} races. Currently displaying Race {first_race}.")
    return True


# ─── Sidebar Component ────────────────────────────────────────────────────────
def render_sidebar():
    """Renders the fixed left sidebar with branding, engine info, uploads, and navigation."""
    with st.sidebar:
        # 1. Branding Header
        st.markdown("""
        <div style="padding: 0.25rem 0 0.85rem; border-bottom: 1px solid var(--border-subtle); margin-bottom: 1rem;">
          <div style="font-family: 'Rajdhani', sans-serif; font-weight: 700; font-size: 1.35rem; color: var(--accent-gold); letter-spacing: 0.08em; line-height: 1;">
            SA QUANT RACING
          </div>
          <div style="font-size: 0.68rem; font-weight: 600; color: var(--text-secondary); letter-spacing: 0.12em; margin-top: 0.35rem; text-transform: uppercase;">
            BETTING INTELLIGENCE TERMINAL
          </div>
        </div>
        """, unsafe_allow_html=True)

        # 2. System Status & Model Card
        active_r = st.session_state.get("current_race", 1)
        total_races = len(st.session_state.get("all_races", {}))
        card_str = f"{active_r} of {total_races}" if total_races > 0 else "None loaded"
        track_display = f"{st.session_state.get('venue_selector', 'Fairview')} ({st.session_state.get('surface_selector', 'Turf')})"

        st.markdown(f"""
        <div style="background-color: var(--bg-card); border: 1px solid var(--border-subtle); border-radius: 10px; padding: 0.85rem 1rem; margin-bottom: 1rem;">
          <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom: 0.5rem;">
            <span style="font-size:0.7rem; color:var(--text-muted); font-weight:700; text-transform:uppercase; letter-spacing:0.06em;">ENGINE</span>
            <span style="font-size:0.8rem; font-family:'JetBrains Mono', monospace; font-weight:700; color:var(--accent-gold);">v3.13 QUANT</span>
          </div>
          <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom: 0.5rem;">
            <span style="font-size:0.7rem; color:var(--text-muted); font-weight:700; text-transform:uppercase; letter-spacing:0.06em;">VENUE</span>
            <span style="font-size:0.8rem; font-weight:600; color:var(--text-primary);">{track_display}</span>
          </div>
          <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom: 0.5rem;">
            <span style="font-size:0.7rem; color:var(--text-muted); font-weight:700; text-transform:uppercase; letter-spacing:0.06em;">MEETING</span>
            <span style="font-size:0.8rem; font-family:'JetBrains Mono', monospace; font-weight:600; color:var(--text-primary);">{card_str}</span>
          </div>
          <div style="display:flex; justify-content:space-between; align-items:center;" title="Historical research backtest benchmark (Phases 1–3); not a guarantee of forward live returns.">
            <span style="font-size:0.7rem; color:var(--text-muted); font-weight:700; text-transform:uppercase; letter-spacing:0.06em;">HISTORICAL BENCHMARK</span>
            <span style="font-size:0.8rem; font-family:'JetBrains Mono', monospace; font-weight:700; color:var(--indicator-green);">25–30%</span>
          </div>
          <div style="font-size:0.65rem; color:var(--text-muted); margin-top:2px; font-style:italic; line-height:1.2;">
            *Research baseline (not live returns)
          </div>
        </div>
        """, unsafe_allow_html=True)

        st.markdown(_model_mode_badge(), unsafe_allow_html=True)
        st.markdown("<div style='height: 0.75rem;'></div>", unsafe_allow_html=True)

        # 3. Race Card Upload & File Status
        st.markdown("<div style='font-size:0.75rem; font-weight:700; color:var(--text-secondary); text-transform:uppercase; letter-spacing:0.08em; margin-bottom:0.4rem;'>📄 Race Card Document</div>", unsafe_allow_html=True)
        uploaded = st.file_uploader(
            label="Upload Computaform PDF",
            type=["pdf"],
            label_visibility="collapsed",
            key="pdf_upload",
            on_change=reset_race_state,
        )

        if uploaded is not None:
            file_mb = len(uploaded.getvalue()) / (1024 * 1024)
            st.markdown(f"""
            <div style="background:rgba(22,199,132,0.06); border:1px solid rgba(22,199,132,0.25); border-radius:6px; padding:6px 10px; font-size:0.75rem; color:var(--indicator-green); margin-bottom:0.5rem; display:flex; justify-content:space-between;">
              <span style="overflow:hidden; text-overflow:ellipsis; white-space:nowrap; max-width:140px;">📎 {uploaded.name}</span>
              <span>{file_mb:.1f} MB</span>
            </div>
            """, unsafe_allow_html=True)

        demo_mode = st.checkbox("🎮 Use Demo Race Card", value=st.session_state.demo_mode)
        if demo_mode != st.session_state.demo_mode:
            reset_race_state()
            st.session_state.demo_mode = demo_mode
            if demo_mode:
                st.session_state.race_name = "Fairview R1 – 1200m (Demo)"
                st.session_state.venue_selector = "Fairview"
                st.session_state.distance_selector = 1200
                st.session_state.race_class_selector = "Stakes"
                st.session_state.surface_selector = "Turf"
                run_extraction(None, demo_mode=True)
                st.rerun()

        # 4. Action Button: Process Race
        st.markdown("<div style='height:0.25rem'></div>", unsafe_allow_html=True)
        process_clicked = st.button("⚡ Process Race Card", type="primary", use_container_width=True)

        # 5. Expandable Configuration Groups
        with st.expander("⚙️ Engine & Model Configuration"):
            model_mode_options = [
                "Greyville Poly v3.13 ★",
                "Turffontein v3.11 ★",
                "7-Track Adaptive (v3.9)",
                "ML Calibrated (v4.2)",
                "Legacy Rule (v3.8)",
            ]
            default_index = 0
            if st.session_state.model_mode_selector in model_mode_options:
                default_index = model_mode_options.index(st.session_state.model_mode_selector)

            model_mode = st.selectbox(
                "Prediction Engine",
                options=model_mode_options,
                index=default_index,
                key="model_mode_selector"
            )

        with st.expander("📍 Track & Meeting Parameters"):
            venue_options = ["Turffontein", "Greyville", "Kenilworth", "Durbanville", "Fairview", "Scottsville", "Vaal"]
            v_idx = 0
            if st.session_state.venue_selector in venue_options:
                v_idx = venue_options.index(st.session_state.venue_selector)
            venue = st.selectbox("Track / Venue", options=venue_options, index=v_idx, key="venue_selector")

            if venue == "Greyville":
                surface_options = ["Polytrack", "Turf"]
                s_idx = 0
                if st.session_state.surface_selector in surface_options:
                    s_idx = surface_options.index(st.session_state.surface_selector)
                st.selectbox("Surface", options=surface_options, index=s_idx, key="surface_selector")
            else:
                st.selectbox("Surface", options=["Turf"], index=0, key="surface_selector", disabled=True)

            st.number_input(
                "Distance (m)",
                min_value=800,
                max_value=3200,
                value=int(st.session_state.distance_selector),
                step=100,
                key="distance_selector"
            )

            rc_options = ["Grade 1", "Grade 2", "Grade 3", "Listed", "Merit Rated (MR)", "Maiden Plate", "Pinnacle Stakes", "Other Handicap"]
            rc_idx = 0
            if st.session_state.race_class_selector in rc_options:
                rc_idx = rc_options.index(st.session_state.race_class_selector)
            st.selectbox("Race Class", options=rc_options, index=rc_idx, key="race_class_selector")
            st.text_input("Race Title", value=st.session_state.race_name, key="race_name")

        # 6. Race Navigation
        all_races = st.session_state.get("all_races", {})
        all_results = st.session_state.get("all_results", {})
        races_meta = st.session_state.get("races_meta", {})

        if all_races:
            st.markdown("""
            <div style="font-size:0.75rem; font-weight:700; color:var(--text-secondary); text-transform:uppercase; letter-spacing:0.08em; margin: 1rem 0 0.5rem;">
              🏁 Race Navigation
            </div>
            """, unsafe_allow_html=True)

            for r in sorted(all_races.keys()):
                r_horses = all_races[r]
                r_meta = races_meta.get(r, {})
                time_str = r_meta.get("race_time", "")
                dist_val = r_meta.get("distance", "")

                time_dist_label = f"{time_str} · {dist_val}" if (time_str and dist_val) else (time_str or dist_val or f"{len(r_horses)} runners")
                is_selected = (r == st.session_state.current_race)

                top_pred = all_results.get(r, [None])[0] if all_results else None
                top_str = ""
                if top_pred:
                    prob_pct = int(top_pred.probability * 100)
                    h_short = top_pred.horse.split()[0]
                    top_str = f" · 🏆 {h_short} ({prob_pct}%)"

                btn_label = f"Race {r} [{time_dist_label}]{top_str}"
                if is_selected:
                    btn_label = f"👉 {btn_label}"

                if st.button(btn_label, key=f"nav_race_{r}", use_container_width=True):
                    st.session_state.current_race = r
                    st.session_state.horses = list(all_races[r])
                    if all_results and r in all_results:
                        st.session_state.predictions = all_results[r]
                        st.session_state.processed = True
                    else:
                        st.session_state.predictions = []
                        st.session_state.processed = False
                    st.rerun()

        # 7. Audit & Formula Reference
        with st.expander("ℹ️ Quant Audit & EV Reference"):
            st.latex(r"EV = p \times (odds - 1) - (1 - p)")
            st.markdown("""
            - **EV > 0.05 + Medium/High Confidence** = Value Overlay ✅
            - **Odds >= 10.0 + Positive EV** = Longshot Alert 🔥
            - Models calibrated via Harville sequential probabilities.
            """)

        return uploaded, process_clicked


# ─── Dashboard Components ─────────────────────────────────────────────────────

def render_race_overview_bar(current_race: int):
    """Render a compact horizontal information bar with key race conditions."""
    races_meta = st.session_state.get("races_meta", {})
    meta = races_meta.get(current_race, {})

    venue = meta.get("venue") or st.session_state.get("venue_selector", "Fairview")
    surface = meta.get("surface") or st.session_state.get("surface_selector", "Turf")
    distance = meta.get("distance") or f"{st.session_state.get('distance_selector', 1200)}m"
    race_time = meta.get("race_time") or "12:15"
    stake = meta.get("stake") or "R80,000"
    betting_leg = meta.get("betting_leg") or "Exotics Available"

    st.markdown(f"""
    <div class="race-overview-bar">
      <div class="meta-chip meta-chip-gold">
        <span>🏁</span> <strong>Race {current_race}</strong>
      </div>
      <div class="meta-chip">
        <span>📍</span> <span>Course:</span> <strong>{venue} ({surface})</strong>
      </div>
      <div class="meta-chip">
        <span>📏</span> <span>Distance:</span> <strong>{distance}</strong>
      </div>
      <div class="meta-chip">
        <span>🕛</span> <span>Post Time:</span> <strong>{race_time}</strong>
      </div>
      <div class="meta-chip">
        <span>💰</span> <span>Stake:</span> <strong>{stake}</strong>
      </div>
      <div class="meta-chip">
        <span>🎫</span> <span>Leg:</span> <strong>{betting_leg}</strong>
      </div>
    </div>
    """, unsafe_allow_html=True)


def render_featured_prediction(results: list, race_horses: list):
    """Renders the prominent Top Prediction card without crowding the screen."""
    if not results:
        return

    top_horse = results[0]
    top_name = top_horse.horse
    top_draw = top_horse.draw
    top_prob = top_horse.probability * 100
    top_odds = top_horse.odds
    top_ev = top_horse.ev
    top_conf = getattr(top_horse, "confidence", "High")

    matching = next((h for h in race_horses if (h.get("horse", "") if hasattr(h, "get") else getattr(h, "horse", "")) == top_name), None)
    trainer = top_horse.trainer if top_horse.trainer else (getattr(matching, "trainer", "N/A") if matching else "N/A")
    jockey = top_horse.jockey if top_horse.jockey else (getattr(matching, "jockey", "N/A") if matching else "N/A")

    ev_color = "var(--indicator-green)" if top_ev > 0 else "var(--indicator-red)"
    ev_sign = "+" if top_ev > 0 else ""

    col_hero, col_metrics = st.columns([1.4, 1])

    with col_hero:
        st.markdown(f"""
        <div class="card-featured-top">
          <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:0.75rem;">
            <div style="display:flex; align-items:center; gap:8px;">
              <span style="font-size:0.72rem; font-weight:800; text-transform:uppercase; color:var(--accent-gold); letter-spacing:0.08em;">
                🏆 TOP QUANT SELECTION · RANK 1
              </span>
              <span style="background:var(--accent-gold-dim); color:var(--accent-gold); font-size:10px; font-weight:700; padding:2px 8px; border-radius:12px; border:1px solid rgba(229,173,36,0.3);">
                {top_conf} Confidence
              </span>
            </div>
            <span style="font-family:'JetBrains Mono',monospace; font-size:0.85rem; color:var(--text-secondary);">
              Draw #{top_draw}
            </span>
          </div>

          <div style="font-family:'Outfit', sans-serif; font-size:1.85rem; font-weight:900; color:#FFFFFF; margin-bottom:0.35rem; line-height:1.15;">
            #{top_draw} {top_name}
          </div>

          <div style="font-size:0.85rem; color:var(--text-secondary); margin-bottom:1.25rem;">
            <span>Trainer: <strong style="color:var(--text-primary);">{trainer}</strong></span> ·
            <span>Jockey: <strong style="color:var(--text-primary);">{jockey}</strong></span>
          </div>

          <div style="display:grid; grid-template-columns: repeat(3, 1fr); gap:12px; border-top:1px dashed var(--border-subtle); padding-top:1rem;">
            <div>
              <div style="font-size:0.72rem; color:var(--text-muted); text-transform:uppercase; font-weight:700;">WIN PROBABILITY</div>
              <div style="font-family:'JetBrains Mono', monospace; font-size:1.35rem; font-weight:800; color:var(--accent-gold);">{top_prob:.1f}%</div>
            </div>
            <div>
              <div style="font-size:0.72rem; color:var(--text-muted); text-transform:uppercase; font-weight:700;">MARKET ODDS</div>
              <div style="font-family:'JetBrains Mono', monospace; font-size:1.35rem; font-weight:800; color:var(--text-primary);">{top_odds:.2f}</div>
            </div>
            <div>
              <div style="font-size:0.72rem; color:var(--text-muted); text-transform:uppercase; font-weight:700;">EXPECTED VALUE</div>
              <div style="font-family:'JetBrains Mono', monospace; font-size:1.35rem; font-weight:800; color:{ev_color};">{ev_sign}{top_ev:.3f}</div>
            </div>
          </div>
        </div>
        """, unsafe_allow_html=True)

    with col_metrics:
        # Confidence & Race Matrix preview
        all_results = st.session_state.get("all_results", {})
        grid_items = []
        for r_num in sorted(st.session_state.get("all_races", {}).keys()):
            r_preds = all_results.get(r_num, [])
            if r_preds:
                r_top = r_preds[0]
                ev_val = getattr(r_top, "ev", 0.0)
                bg = "rgba(22,199,132,0.12)" if ev_val > 0.05 else "rgba(255,255,255,0.03)"
                brd = "var(--indicator-green)" if ev_val > 0.05 else "var(--border-subtle)"
                txt = "var(--indicator-green)" if ev_val > 0.05 else "var(--text-secondary)"
                grid_items.append(
                    f'<div style="display:flex; flex-direction:column; align-items:center; justify-content:center; width:44px; height:44px; background:{bg}; border:1px solid {brd}; border-radius:8px; font-size:0.75rem; font-weight:700; color:{txt};" title="Race {r_num} EV: {ev_val:+.2f}">'
                    f'<span>R{r_num}</span><span style="font-size:9px; font-weight:500;">{ev_val:+.1f}</span></div>'
                )
            else:
                grid_items.append(
                    f'<div style="display:flex; flex-direction:column; align-items:center; justify-content:center; width:44px; height:44px; background:rgba(255,255,255,0.02); border:1px solid var(--border-subtle); border-radius:8px; font-size:0.75rem; font-weight:700; color:var(--text-muted);">'
                    f'<span>R{r_num}</span></div>'
                )

        grid_html = "".join(grid_items)

        st.markdown(f"""
        <div class="terminal-card" style="height:100%; display:flex; flex-direction:column; justify-content:space-between;">
          <div>
            <div style="font-size:0.75rem; font-weight:800; color:var(--text-secondary); text-transform:uppercase; letter-spacing:0.08em; margin-bottom:0.75rem;">
              ⚖️ Meeting Expected Value Matrix
            </div>
            <div style="display:flex; flex-wrap:wrap; gap:8px; margin-bottom:0.75rem;">
              {grid_html}
            </div>
          </div>
          <div style="background:rgba(229,173,36,0.06); border:1px solid rgba(229,173,36,0.2); border-radius:8px; padding:8px 12px; font-size:0.78rem; color:var(--accent-gold);">
            💡 Green indicates positive market expectation (overlay). Select races in the sidebar to review individual odds.
          </div>
        </div>
        """, unsafe_allow_html=True)


def render_rankings_table(results: list, race_horses: list):
    """Renders the comprehensive rankings table with clean typography and spacing."""
    if not results:
        return

    table_rows_list = []
    for p in results:
        rank_val = p.rank
        rank_display = f"#{rank_val}"
        row_cls = ""

        if rank_val == 1:
            rank_display = "🏆 1"
            row_cls = "top-pick-row"
        elif rank_val == 2:
            rank_display = "🥈 2"
            row_cls = "rank-2-row"
        elif rank_val == 3:
            rank_display = "🥉 3"
            row_cls = "rank-3-row"

        # Matching Horse object for metadata
        matching = next((h for h in race_horses if (h.get("horse", "") if hasattr(h, "get") else getattr(h, "horse", "")) == p.horse), None)
        weight_val = matching.get("weight", 56.0) if hasattr(matching, "get") else getattr(matching, "weight", 56.0) if matching else 56.0

        # Form pill representation
        form_figs = matching.form_figures if hasattr(matching, "form_figures") else []
        form_html = ""
        for fig in form_figs[-5:]:
            fig_str = str(fig) if fig != 99 else "0"
            bg_c = "var(--accent-gold)" if fig_str == "1" else "var(--indicator-green)" if fig_str in ("2", "3") else "rgba(255,255,255,0.06)"
            form_html += f'<span class="form-box" style="background:{bg_c};">{fig_str}</span>'

        if not form_html:
            form_str = matching.form_string if hasattr(matching, "form_string") else ""
            form_html = f'<span style="font-family:monospace; color:var(--text-secondary);">{form_str or "N/A"}</span>'

        # Signal tags
        signal_tags = []
        if getattr(p, "value_bet", False):
            signal_tags.append('<span class="signal-tag signal-value">VALUE WIN</span>')
        if getattr(p, "longshot", False) or (p.odds >= 10.0 and p.ev > 0.0):
            signal_tags.append('<span class="signal-tag signal-longshot">LONGSHOT</span>')
        signals_display = " ".join(signal_tags) if signal_tags else '<span style="color:var(--text-muted);">—</span>'

        ev_color = "var(--indicator-green)" if p.ev > 0 else "var(--indicator-red)"
        ev_sign = "+" if p.ev > 0 else ""
        trainer_display = p.trainer or "Trainer N/A"
        jockey_display = p.jockey or "Jockey N/A"

        row_str = f"""<tr class="{row_cls}">
<td style="font-weight:700; font-family:'Outfit',sans-serif;">{rank_display}</td>
<td style="font-family:'JetBrains Mono',monospace; color:var(--text-secondary);">#{p.draw}</td>
<td>
  <div style="font-weight:700; color:var(--text-primary); font-size:0.92rem;">{p.horse}</div>
  <div style="font-size:0.75rem; color:var(--text-muted);">{trainer_display}</div>
</td>
<td style="color:var(--text-secondary); font-size:0.85rem;">{jockey_display}</td>
<td style="font-family:'JetBrains Mono',monospace; font-size:0.85rem;">{weight_val:.1f} kg</td>
<td>{form_html}</td>
<td style="font-family:'JetBrains Mono',monospace; font-weight:700; color:var(--accent-gold);">{p.odds:.2f}</td>
<td style="font-family:'JetBrains Mono',monospace; font-weight:700; color:var(--text-primary);">{p.probability * 100:.1f}%</td>
<td style="font-family:'JetBrains Mono',monospace; font-weight:700; color:{ev_color};">{ev_sign}{p.ev:.3f}</td>
<td>{signals_display}</td>
</tr>"""
        table_rows_list.append(row_str)

    table_rows_str = "\n".join(table_rows_list)
    table_html = f"""<div class="table-responsive-container">
<table class="terminal-data-table">
<thead>
<tr>
  <th style="width:65px;">RNK</th>
  <th style="width:55px;">DR</th>
  <th>HORSE &amp; TRAINER</th>
  <th>JOCKEY</th>
  <th style="width:80px;">WEIGHT</th>
  <th>RECENT FORM</th>
  <th style="width:75px;">ODDS</th>
  <th style="width:85px;">WIN PROB</th>
  <th style="width:85px;">EXP. VALUE</th>
  <th>SIGNALS</th>
</tr>
</thead>
<tbody>
{table_rows_str}
</tbody>
</table>
</div>"""
    st.markdown(table_html, unsafe_allow_html=True)


def render_value_bets_panel(results: list):
    """Renders detected value bets and overlays for the current race."""
    value_bets = [p for p in results if getattr(p, "value_bet", False)]
    longshots = [p for p in results if getattr(p, "longshot", False) or (p.odds >= 10.0 and p.ev > 0.0)]

    if value_bets:
        cards_html_list = []
        for vb in value_bets:
            card_str = f"""<div style="background:rgba(22,199,132,0.06); border:1px solid rgba(22,199,132,0.25); border-radius:8px; padding:12px 14px; margin-bottom:8px; display:flex; justify-content:space-between; align-items:center;">
<div>
  <span style="font-weight:800; font-size:0.95rem; color:var(--text-primary);">#{vb.draw} {vb.horse}</span>
  <span class="signal-tag signal-value" style="margin-left:8px;">VALUE OVERLAY</span>
  <div style="font-size:0.78rem; color:var(--text-muted); margin-top:2px;">Model: {vb.probability*100:.1f}% vs Market Implied: {vb.implied_prob*100:.1f}%</div>
</div>
<div style="text-align:right;">
  <div style="font-family:'JetBrains Mono',monospace; font-weight:700; color:var(--accent-gold); font-size:1.05rem;">{vb.odds:.2f}</div>
  <div style="font-family:'JetBrains Mono',monospace; font-weight:700; color:var(--indicator-green); font-size:0.85rem;">{vb.ev:+.3f} EV</div>
</div>
</div>"""
            cards_html_list.append(card_str)
        cards_html_str = "\n".join(cards_html_list)
        vb_html = f"""<div class="terminal-card">
<div style="font-size:0.75rem; font-weight:800; color:var(--indicator-green); text-transform:uppercase; letter-spacing:0.08em; margin-bottom:0.75rem;">
  ✅ Value Bets Detected in this Race
</div>
{cards_html_str}
</div>"""
        st.markdown(vb_html, unsafe_allow_html=True)
    else:
        empty_html = """<div style="background-color: var(--bg-card); border: 1px solid var(--border-subtle); border-radius: 8px; padding: 12px 16px; margin-bottom: 1rem; font-size: 0.85rem; color: var(--text-secondary); display:flex; align-items:center; gap:8px;">
<span>ℹ️</span> <span>No mathematical overlays (EV &gt; 5%) detected at current prices. Line movements or live pool odds may unlock value.</span>
</div>"""
        st.markdown(empty_html, unsafe_allow_html=True)


def render_odds_editor(race_horses: list) -> dict:
    """Render compact, collapsible odds editor."""
    with st.expander("✏️ Review & Adjust Live Market Odds"):
        st.caption("Adjust decimal odds to reflect live price fluctuations before regenerating predictions.")
        existing = st.session_state.odds_map
        odds_map = {}
        cols_per_row = 4
        rows = [race_horses[idx:idx+cols_per_row] for idx in range(0, len(race_horses), cols_per_row)]
        file_slot = str(st.session_state.get("_last_file_id", "demo")).replace(" ", "_")

        for r_idx, row in enumerate(rows):
            cols = st.columns(cols_per_row)
            for c_idx, horse in enumerate(row):
                with cols[c_idx]:
                    h_name = getattr(horse, "horse", "Runner")
                    h_draw = getattr(horse, "draw", 0)
                    default_val = float(
                        existing.get(h_name, getattr(horse, "market_odds", getattr(horse, "forecast_odds", 0.0))) or 0.0
                    )
                    val = st.number_input(
                        label=f"#{h_draw} {h_name}",
                        min_value=0.0,
                        max_value=999.0,
                        value=default_val,
                        step=0.10,
                        format="%.2f",
                        key=f"odds_{file_slot}_{r_idx}_{c_idx}_{h_draw}",
                    )
                    odds_map[h_name] = val

        st.session_state.odds_map.update(odds_map)
        return odds_map


def render_exotics_intelligence(results: list, all_results: dict = None, current_race: int = 1):
    """Renders Exacta, Swinger, Trifecta, Quartet, and multi-race perm panels in spacious cards."""
    if not results:
        st.info("No race prediction results available. Please run predictions first.")
        return

    subtab_single, subtab_multi = st.tabs([
        f"🎯 Race {current_race} Single-Race Exotics",
        "🏆 Meeting Multi-Race Permutations (Pick 6, BiPot, Jackpot)"
    ])

    def _g(p, attr, default=None):
        return getattr(p, attr, default) if hasattr(p, attr) else p.get(attr, default) if isinstance(p, dict) else default

    sorted_p = sorted(results, key=lambda x: _g(x, "rank", 99))
    def name(p): return _g(p, "horse", "Unknown")
    def draw(p): return _g(p, "draw", 0)
    def prob(p): return float(_g(p, "probability", 0.0))

    tot_p = sum(prob(p) for p in sorted_p)
    norm_p = [prob(p) / tot_p if tot_p > 0 else 1.0 / len(sorted_p) for p in sorted_p]

    with subtab_single:
        col_exacta, col_swinger = st.columns(2)

        with col_exacta:
            if len(sorted_p) >= 2:
                p1, p2 = norm_p[0], norm_p[1]
                denom1 = max(1.0 - p1, 1e-5)
                exacta_prob = p1 * (p2 / denom1)
                exacta_fair_odds = 1.0 / exacta_prob if exacta_prob > 0 else 999.0
                h1, h2 = sorted_p[0], sorted_p[1]

                st.markdown(f"""
                <div class="exotics-card">
                  <div>
                    <div class="exotics-card-header" style="color:var(--accent-gold);">
                      <span>🎯 EXACTA INTELLIGENCE (1st &amp; 2nd)</span>
                      <span style="font-size:0.7rem; color:var(--text-muted);">HARVILLE MODEL</span>
                    </div>
                    <div class="combo-box">
                      <div style="font-size:0.75rem; color:var(--text-muted); margin-bottom:4px;">Top Model Straight Exacta</div>
                      <div style="font-size:1.15rem; font-weight:800; color:#FFFFFF; font-family:'Outfit',sans-serif; margin-bottom:8px;">
                        #{draw(h1)} {name(h1)} <span style="color:var(--accent-gold);">➔</span> #{draw(h2)} {name(h2)}
                      </div>
                      <div style="display:flex; justify-content:space-between; font-size:0.8rem; border-top:1px dashed var(--border-subtle); padding-top:6px;">
                        <span>Model Probability: <strong style="color:var(--indicator-green); font-family:'JetBrains Mono',monospace;">{exacta_prob*100:.2f}%</strong></span>
                        <span>Fair Odds: <strong style="color:var(--accent-gold); font-family:'JetBrains Mono',monospace;">{exacta_fair_odds:.1f}/1</strong></span>
                      </div>
                    </div>
                  </div>
                  <div style="font-size:0.8rem; color:var(--text-secondary); line-height:1.45; border-top:1px solid var(--border-subtle); padding-top:8px;">
                    <div><strong>Exacta Box (Top 3):</strong> #{draw(sorted_p[0])}, #{draw(sorted_p[1])}, #{draw(sorted_p[2]) if len(sorted_p)>2 else ''}</div>
                    <div style="color:var(--text-muted); font-size:0.75rem;">6 Combinations · Cost: R6 @ R1 unit</div>
                  </div>
                </div>
                """, unsafe_allow_html=True)

        with col_swinger:
            if len(sorted_p) >= 2:
                h1, h2 = sorted_p[0], sorted_p[1]
                h3 = sorted_p[2] if len(sorted_p) > 2 else h2
                sw1 = f"#{draw(h1)} {name(h1)} + #{draw(h2)} {name(h2)}"
                sw2 = f"#{draw(h1)} {name(h1)} + #{draw(h3)} {name(h3)}"
                sw3 = f"#{draw(h2)} {name(h2)} + #{draw(h3)} {name(h3)}"

                st.markdown(f"""
                <div class="exotics-card">
                  <div>
                    <div class="exotics-card-header" style="color:var(--accent-blue);">
                      <span>🔄 SWINGER INTELLIGENCE (Any 2 in Top 3)</span>
                      <span style="font-size:0.7rem; color:var(--text-muted);">TOP COMBOS</span>
                    </div>
                    <div style="display:flex; flex-direction:column; gap:6px; margin-bottom:0.75rem;">
                      <div style="background:var(--accent-blue-dim); border:1px solid rgba(77,136,255,0.25); border-radius:6px; padding:7px 10px; font-size:0.82rem; font-weight:700; color:#FFFFFF;">
                        ⭐ Primary Swinger: {sw1}
                      </div>
                      <div style="background:var(--bg-card-subtle); border:1px solid var(--border-subtle); border-radius:6px; padding:7px 10px; font-size:0.82rem; color:var(--text-secondary);">
                        🔹 Secondary Swinger: {sw2}
                      </div>
                      <div style="background:var(--bg-card-subtle); border:1px solid var(--border-subtle); border-radius:6px; padding:7px 10px; font-size:0.82rem; color:var(--text-secondary);">
                        🔹 Coverage Swinger: {sw3}
                      </div>
                    </div>
                  </div>
                  <div style="font-size:0.8rem; color:var(--text-secondary); border-top:1px solid var(--border-subtle); padding-top:8px;">
                    <div><strong>Swinger Box (Top 3):</strong> 3 Combinations · Cost: R3 @ R1 unit</div>
                  </div>
                </div>
                """, unsafe_allow_html=True)

        st.markdown("<div style='height:0.5rem;'></div>", unsafe_allow_html=True)

        col_trifecta, col_quartet = st.columns(2)

        with col_trifecta:
            if len(sorted_p) >= 3:
                p1, p2, p3 = norm_p[0], norm_p[1], norm_p[2]
                denom1 = max(1.0 - p1, 1e-5)
                denom2 = max(1.0 - p1 - p2, 1e-5)
                trifecta_prob = p1 * (p2 / denom1) * (p3 / denom2)
                trifecta_fair_odds = 1.0 / trifecta_prob if trifecta_prob > 0 else 999.0
                h1, h2, h3 = sorted_p[0], sorted_p[1], sorted_p[2]

                st.markdown(f"""
                <div class="exotics-card">
                  <div>
                    <div class="exotics-card-header" style="color:var(--indicator-green);">
                      <span>🏆 TRIFECTA INTELLIGENCE (1st, 2nd, 3rd)</span>
                      <span style="font-size:0.7rem; color:var(--text-muted);">SEQUENTIAL</span>
                    </div>
                    <div class="combo-box">
                      <div style="font-size:0.75rem; color:var(--text-muted); margin-bottom:4px;">Top Straight Trifecta</div>
                      <div style="font-size:1.05rem; font-weight:800; color:#FFFFFF; font-family:'Outfit',sans-serif; margin-bottom:8px;">
                        #{draw(h1)} {name(h1)} <span style="color:var(--indicator-green);">➔</span> #{draw(h2)} {name(h2)} <span style="color:var(--indicator-green);">➔</span> #{draw(h3)} {name(h3)}
                      </div>
                      <div style="display:flex; justify-content:space-between; font-size:0.8rem; border-top:1px dashed var(--border-subtle); padding-top:6px;">
                        <span>Model Prob: <strong style="color:var(--indicator-green); font-family:'JetBrains Mono',monospace;">{trifecta_prob*100:.2f}%</strong></span>
                        <span>Fair Odds: <strong style="color:var(--accent-gold); font-family:'JetBrains Mono',monospace;">{trifecta_fair_odds:.1f}/1</strong></span>
                      </div>
                    </div>
                  </div>
                  <div style="font-size:0.8rem; color:var(--text-secondary); line-height:1.45; border-top:1px solid var(--border-subtle); padding-top:8px;">
                    <div><strong>Banker Trifecta:</strong> #{draw(h1)} with #{draw(h2)}, #{draw(h3)}, #{draw(sorted_p[3]) if len(sorted_p)>3 else ''} (6 combos)</div>
                    <div style="color:var(--text-muted); font-size:0.75rem;">Trifecta Box (Top 4): 24 Combos · Cost: R24 @ R1 unit</div>
                  </div>
                </div>
                """, unsafe_allow_html=True)

        with col_quartet:
            if len(sorted_p) >= 3:
                h1, h2, h3 = sorted_p[0], sorted_p[1], sorted_p[2]
                h4 = sorted_p[3] if len(sorted_p) > 3 else h3
                quartet_str = f"#{draw(h1)} {name(h1)} ➔ #{draw(h2)} {name(h2)} ➔ #{draw(h3)} {name(h3)} ➔ #{draw(h4)} {name(h4)}"

                st.markdown(f"""
                <div class="exotics-card">
                  <div>
                    <div class="exotics-card-header" style="color:var(--accent-purple);">
                      <span>👑 QUARTET INTELLIGENCE (1st–4th)</span>
                      <span style="font-size:0.7rem; color:var(--text-muted);">TOP COMBOS</span>
                    </div>
                    <div class="combo-box">
                      <div style="font-size:0.75rem; color:var(--text-muted); margin-bottom:4px;">Top Straight Quartet</div>
                      <div style="font-size:0.95rem; font-weight:800; color:#FFFFFF; font-family:'Outfit',sans-serif; margin-bottom:8px;">
                        {quartet_str}
                      </div>
                    </div>
                  </div>
                  <div style="font-size:0.8rem; color:var(--text-secondary); line-height:1.45; border-top:1px solid var(--border-subtle); padding-top:8px;">
                    <div><strong>Banker Quartet:</strong> Banker #{draw(h1)} 1st, Box {draw(h2)}, {draw(h3)}, {draw(h4)} (6 combos)</div>
                    <div style="color:var(--text-muted); font-size:0.75rem;">Quartet Box (Top 4): 24 Combos · Cost: R24 @ R1 unit</div>
                  </div>
                </div>
                """, unsafe_allow_html=True)

        with st.expander("📐 Harville Formula & Exotics Mathematical Derivation"):
            st.latex(r"P(i \text{ 1st}, j \text{ 2nd}) = P(i) \times \frac{P(j)}{1 - P(i)}")
            st.latex(r"P(i \text{ 1st}, j \text{ 2nd}, k \text{ 3rd}) = P(i) \times \frac{P(j)}{1 - P(i)} \times \frac{P(k)}{1 - P(i) - P(j)}")
            st.caption("Fair market odds equal the mathematical reciprocal of sequential conditional probabilities.")

    with subtab_multi:
        all_r = all_results if all_results else {}
        perms_text = generate_perms_block(all_r)

        if perms_text and "(Not enough races" not in perms_text:
            st.markdown("""
            <div style="font-size:0.85rem; color:var(--text-secondary); margin-bottom:0.75rem;">
              Multi-race permutations structure optimal Banker and Contender selections derived from model probabilities across all meeting legs.
            </div>
            """, unsafe_allow_html=True)
            st.code(perms_text, language="text")
        else:
            st.info("ℹ️ Multi-race permutations require meeting predictions across at least 4 races. Generate meeting predictions to unlock Pick 6, BiPot, and Jackpot perm cards.")


def render_quantitative_analytics(results: list, all_results: dict):
    """Renders gauges, meeting analytics, and model feature breakdowns."""
    if not results:
        st.info("Run predictions to display quantitative analytics.")
        return

    col_g1, col_g2, col_stats = st.columns([1, 1, 1.5])

    top_prob_val = results[0].probability * 100 if results else 0
    all_evs = [p.ev for r_k, r_list in all_results.items() for p in r_list] if all_results else [p.ev for p in results]
    meeting_avg_ev = sum(all_evs) / len(all_evs) if all_evs else 0.0

    this_race_pct = min(max(int((top_prob_val / 50.0) * 100), 0), 100)
    meet_avg_pct = min(max(int((meeting_avg_ev + 0.15) / 0.3 * 100), 0), 100)

    with col_g1:
        st.markdown(f"""
        <div class="terminal-card" style="text-align:center; height:100%;">
          <div style="font-size:0.72rem; font-weight:800; color:var(--text-muted); text-transform:uppercase; letter-spacing:0.08em; margin-bottom:0.5rem;">
            TOP PICK CONFIDENCE
          </div>
          <svg viewBox="0 0 36 36" class="circular-chart" style="stroke:var(--accent-gold);">
            <path class="circle-bg" d="M18 2.0845 a 15.9155 15.9155 0 0 1 0 31.831 a 15.9155 15.9155 0 0 1 0 -31.831" />
            <path class="circle" stroke-dasharray="{this_race_pct}, 100" d="M18 2.0845 a 15.9155 15.9155 0 0 1 0 31.831 a 15.9155 15.9155 0 0 1 0 -31.831" />
            <text x="18" y="20.3" class="percentage">{top_prob_val:.0f}%</text>
          </svg>
          <div style="font-size:0.78rem; font-weight:600; color:var(--text-primary); margin-top:4px;">This Race Win Prob</div>
        </div>
        """, unsafe_allow_html=True)

    with col_g2:
        st.markdown(f"""
        <div class="terminal-card" style="text-align:center; height:100%;">
          <div style="font-size:0.72rem; font-weight:800; color:var(--text-muted); text-transform:uppercase; letter-spacing:0.08em; margin-bottom:0.5rem;">
            MEETING EV METRIC
          </div>
          <svg viewBox="0 0 36 36" class="circular-chart" style="stroke:var(--indicator-green);">
            <path class="circle-bg" d="M18 2.0845 a 15.9155 15.9155 0 0 1 0 31.831 a 15.9155 15.9155 0 0 1 0 -31.831" />
            <path class="circle" stroke-dasharray="{meet_avg_pct}, 100" d="M18 2.0845 a 15.9155 15.9155 0 0 1 0 31.831 a 15.9155 15.9155 0 0 1 0 -31.831" />
            <text x="18" y="20.3" class="percentage">{meeting_avg_ev:+.2f}</text>
          </svg>
          <div style="font-size:0.78rem; font-weight:600; color:var(--text-primary); margin-top:4px;">Average Expected Value</div>
        </div>
        """, unsafe_allow_html=True)

    with col_stats:
        total_races_analyzed = len(all_results)
        total_val_bets = sum(1 for r_k, r_list in all_results.items() for p in r_list if getattr(p, "value_bet", False))
        ev_class = "var(--indicator-green)" if meeting_avg_ev > 0 else "var(--indicator-red)"

        st.markdown(f"""
        <div class="terminal-card" style="height:100%;">
          <div style="font-size:0.72rem; font-weight:800; color:var(--text-muted); text-transform:uppercase; letter-spacing:0.08em; margin-bottom:0.75rem;">
            MEETING LEVEL QUANT SUMMARY
          </div>
          <div style="display:flex; flex-direction:column; gap:8px; font-size:0.85rem;">
            <div style="display:flex; justify-content:space-between;">
              <span style="color:var(--text-secondary);">Races Evaluated</span>
              <span style="font-weight:700; color:#FFFFFF;">{total_races_analyzed}</span>
            </div>
            <div style="display:flex; justify-content:space-between;">
              <span style="color:var(--text-secondary);">Detected Value Bets</span>
              <span style="font-weight:700; color:var(--indicator-green);">{total_val_bets}</span>
            </div>
            <div style="display:flex; justify-content:space-between;">
              <span style="color:var(--text-secondary);">Meeting Average EV</span>
              <span style="font-weight:700; color:{ev_class};">{meeting_avg_ev:+.3f}</span>
            </div>
            <div style="display:flex; justify-content:space-between;">
              <span style="color:var(--text-secondary);">Model Status</span>
              <span style="font-weight:700; color:var(--accent-gold);">Calibrated</span>
            </div>
          </div>
        </div>
        """, unsafe_allow_html=True)

    # Progressive disclosure: Model Feature Breakdown
    with st.expander("🔬 Model Feature Breakdown (Advanced Quantitative Attributes)"):
        feature_names = [
            "Draw Bias", "Form Score", "Jockey WR", "Trainer WR",
            "Weight Penalty", "Rating Norm", "Experience",
            "Field Size Norm", "Has Form", "Win Rate (Form)",
            "Top-3 Rate (Form)", "Composite v3.8",
        ]
        feat_rows = []
        for p in results:
            if hasattr(p, "features") and p.features:
                row = {"Horse": p.horse, "Rank": p.rank}
                for name_f, val_f in zip(feature_names, p.features):
                    row[name_f] = round(val_f, 3)
                feat_rows.append(row)
        if feat_rows:
            st.dataframe(pd.DataFrame(feat_rows), use_container_width=True, hide_index=True)
        else:
            st.caption("Feature vectors generated in standard mode.")


def render_terminal_export_and_diagnostics(results: list, all_results: dict, current_race: int, race_horses: list, extraction: ExtractionResult):
    """Renders copyable monospace terminal tables, summaries, and raw extraction debug panel."""
    st.markdown("""
    <div style="font-size:0.75rem; font-weight:800; color:var(--text-secondary); text-transform:uppercase; letter-spacing:0.08em; margin-bottom:0.75rem;">
      📋 Terminal Text Output &amp; Diagnostics
    </div>
    """, unsafe_allow_html=True)

    races_meta_dict = st.session_state.get("races_meta", {})
    curr_meta_data = races_meta_dict.get(current_race, {})
    curr_race_time = curr_meta_data.get("race_time", "12:15")
    raw_dist = curr_meta_data.get("distance", "")
    curr_race_dist = str(raw_dist).replace("m", "").strip() if raw_dist else str(st.session_state.get("distance_selector", 1200))
    curr_race_class = st.session_state.get("race_class_selector", "Stakes")

    with st.expander("📄 Monospace Race Results Table (Copyable)"):
        table_str = generate_v311_table_string(
            results=results,
            race_num=current_race,
            race_time=curr_race_time,
            distance=int(curr_race_dist) if curr_race_dist.isdigit() else 1200,
            field_size=len(results),
            race_type=curr_race_class,
            race_horses=race_horses,
        )
        st.code(table_str, language="text")

    with st.expander("⭐ Value Bets & Longshot Summary (Meeting-Wide)"):
        st.code(generate_value_bets_block(all_results), language="text")
        st.code(generate_longshots_block(all_results), language="text")

    with st.expander("🔬 Raw Extracted JSON Debug Panel"):
        if extraction:
            st.markdown(f"**Confidence:** `{extraction.confidence_label} ({int(extraction.confidence * 100)}%)` | **Pages Read:** `{extraction.pages_read}`")
            if extraction.warnings:
                st.markdown("**Warnings:**")
                for w in extraction.warnings:
                    st.write(f"• {w}")
            st.markdown("**Extracted Horses JSON:**")
            raw_list = [dataclasses.asdict(h) for h in race_horses if hasattr(h, "__dataclass_fields__")]
            st.json(raw_list if raw_list else [str(h) for h in race_horses])


# ─── Main Application Workflow ────────────────────────────────────────────────
def main():
    uploaded_file, process_clicked = render_sidebar()

    # Track uploaded file identity
    if uploaded_file is not None:
        file_id = f"{uploaded_file.name}_{uploaded_file.size}"
        if file_id != st.session_state.get("_last_file_id"):
            reset_race_state()
            st.session_state._last_file_id = file_id

    # Extraction Trigger
    if process_clicked:
        success = run_extraction(uploaded_file, st.session_state.demo_mode)
        if success:
            st.session_state.processed = False
            st.rerun()

    # Verify horses loaded
    all_races = st.session_state.get("all_races", {})
    current_race = st.session_state.get("current_race", 1)
    extraction = st.session_state.get("extraction")

    if not all_races:
        # Empty / Welcome State
        st.markdown("""
        <div style="background-color:var(--bg-card); border:1px solid var(--border-subtle); border-radius:14px; padding:2.5rem; text-align:center; max-width:800px; margin:2rem auto;">
          <div style="font-size:3rem; margin-bottom:1rem;">🏇</div>
          <div style="font-family:'Outfit',sans-serif; font-size:1.85rem; font-weight:800; color:#FFFFFF; margin-bottom:0.5rem;">
            SA Quant Racing Intelligence Terminal
          </div>
          <div style="color:var(--text-secondary); font-size:0.95rem; line-height:1.6; margin-bottom:1.75rem;">
            Upload an official SA Computaform / PhotoForm PDF in the sidebar or toggle <strong>Demo Race Card</strong> to inspect probability forecasts, Expected Value calculations, and full exotic intelligence.
          </div>
          <div style="display:inline-flex; gap:12px; font-size:0.8rem; color:var(--text-muted);">
            <span>✔ Harville Exotics</span> ·
            <span>✔ Model Calibration</span> ·
            <span>✔ Value Overlay Detection</span> ·
            <span>✔ Multi-Race Permutations</span>
          </div>
        </div>
        """, unsafe_allow_html=True)
        return

    race_horses = all_races.get(current_race, [])
    race_horses = [h for h in race_horses if hasattr(h, "horse") and isinstance(h.horse, str) and len(h.horse) > 2]

    if not race_horses:
        st.warning(f"⚠️ No horse data found for Race {current_race}. Select an alternative race in the sidebar.")
        return

    # Top Compact Race Overview Bar
    render_race_overview_bar(current_race)

    # Review & Adjust Odds (Collapsible)
    odds_map = render_odds_editor(race_horses)

    # Prediction Execution Trigger
    col_run, col_status = st.columns([1, 2])
    with col_run:
        gen_clicked = st.button("🚀 Generate Predictions", type="primary", use_container_width=True)

    auto_run = st.session_state.demo_mode and not st.session_state.processed
    if gen_clicked or auto_run or (st.session_state.processed and st.session_state.get("predictions")):
        with st.spinner("🤖 Executing quantitative models across meeting races..."):
            venue = st.session_state.get("venue_selector", "Fairview")
            surface = st.session_state.get("surface_selector", "Turf")
            distance = int(st.session_state.get("distance_selector", 1200))
            race_class = st.session_state.get("race_class_selector", "Stakes")
            model_mode = st.session_state.get("model_mode_selector", "Greyville Poly v3.13 ★")

            st.session_state.all_results = {}

            for r_num, r_horses in all_races.items():
                for h in r_horses:
                    if hasattr(h, "forecast_odds"):
                        try:
                            if float(h.forecast_odds or 0) <= 1.0:
                                h.forecast_odds = 10.0
                        except (ValueError, TypeError):
                            h.forecast_odds = 10.0
                    elif isinstance(h, dict):
                        try:
                            if float(h.get("forecast_odds", 0) or 0) <= 1.0:
                                h["forecast_odds"] = 10.0
                        except (ValueError, TypeError):
                            h["forecast_odds"] = 10.0

                h_dist = r_horses[0].get("distance", distance) if hasattr(r_horses[0], "get") else getattr(r_horses[0], "distance", distance)
                try:
                    h_dist = int(h_dist)
                except (ValueError, TypeError):
                    h_dist = distance

                r_odds_map = odds_map if r_num == current_race else {}

                if "v3.11" in model_mode:
                    race_context = {
                        "distance": h_dist,
                        "surface": "Turf",
                        "race_type": f"Race {r_num}",
                        "venue": "Turffontein",
                        "odds_map": r_odds_map,
                    }
                    r_results, _ = run_race_v311_turffontein(r_horses, race_context)
                else:
                    r_results = predict(
                        horses=r_horses,
                        odds_map=r_odds_map,
                        venue=venue,
                        surface=surface,
                        distance=h_dist,
                        race_class=race_class,
                        model_mode=model_mode
                    )

                st.session_state.all_results[r_num] = r_results

            st.session_state.predictions = st.session_state.all_results.get(current_race, [])
            st.session_state.field_size = len(race_horses)
            st.session_state.processed = True

    results = st.session_state.get("predictions", [])
    all_results = st.session_state.get("all_results", {})

    if results:
        # Featured Selection Hero Card
        render_featured_prediction(results, race_horses)

        # Tabbed Workspace: Clean, spacious, progressive disclosure
        tab_rankings, tab_exotics, tab_analytics, tab_export = st.tabs([
            "🏆 Race Rankings & Overlays",
            "🧬 Exotics Intelligence",
            "📊 Quantitative Analytics",
            "📋 Terminal Export & Diagnostics"
        ])

        with tab_rankings:
            render_rankings_table(results, race_horses)
            render_value_bets_panel(results)

        with tab_exotics:
            render_exotics_intelligence(results, all_results, current_race)

        with tab_analytics:
            render_quantitative_analytics(results, all_results)

        with tab_export:
            render_terminal_export_and_diagnostics(results, all_results, current_race, race_horses, extraction)
    else:
        st.info("💡 Click **'Generate Predictions'** above to compute win probabilities, Expected Value, and exotic betting intelligence.")


if __name__ == "__main__":
    main()
