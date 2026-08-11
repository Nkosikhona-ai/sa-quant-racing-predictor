"""
app.py — SA Horse Racing Predictor
====================================
Streamlit single-page app.

Workflow:
  1. Upload PhotoForm PDF  (or load demo race)
  2. Click "Process Race"
  3. Enter odds (optional)
  4. View extracted horses, ranked predictions, EV table, bar chart
"""

import os
import io
import logging
import streamlit as st
import pandas as pd
import numpy as np


from extractor import extract_from_pdf, get_demo_horses, Horse, ExtractionResult
from predictor import predict, Prediction, run_race_v311_turffontein, compute_probability_v311_turffontein

# ─── Logging ──────────────────────────────────────────────────────────────────
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ─── Page Config ──────────────────────────────────────────────────────────────
st.set_page_config(
    page_title  = "SA Quant Racing Predictor",
    page_icon   = "🏇",
    layout      = "wide",
    initial_sidebar_state = "expanded",
)

# ─── Custom CSS ───────────────────────────────────────────────────────────────
st.markdown("""
<style>
/* ---- fonts & colors ---- */
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&family=Rajdhani:wght@600;700&family=JetBrains+Mono:wght@400;500;600&family=Outfit:wght@400;600;700;900&display=swap');

:root {
    --gold: #d4a92a;
    --gold-bright: #ffdf7a;
    --gold-dim: rgba(212,169,42,0.1);
    --green-win: #22c55e;
    --red-loss: #ef4444;
    --amber-warn: #f59e0b;
    --background: #090b10;
    --sidebar: #0f1118;
    --card: #151824;
    --border: #222636;
    --muted-foreground: #8892b0;
    --foreground: #f0f2ff;
}

html, body, [class*="css"] {
    font-family: 'Inter', sans-serif;
}

.stApp {
    background: var(--background);
    color: var(--foreground);
}

/* Hide Streamlit default branding elements */
#MainMenu, footer {visibility: hidden;}

/* Custom Table Styles */
.data-table-v313 {
    width: 100%;
    border-collapse: collapse;
    font-size: 0.88rem;
    color: var(--foreground);
    border: 1px solid var(--border);
    border-radius: 8px;
    overflow: hidden;
    margin-top: 0.5rem;
}
.data-table-v313 th {
    background: var(--sidebar);
    color: var(--muted-foreground);
    font-size: 10px;
    text-transform: uppercase;
    letter-spacing: 0.07em;
    font-weight: 600;
    padding: 10px 12px;
    text-align: left;
    border-bottom: 1px solid var(--border);
}
.data-table-v313 tr {
    transition: background 0.15s ease;
}
.data-table-v313 tr:hover {
    background: rgba(255,255,255,0.02);
}
.data-table-v313 td {
    padding: 10px 12px;
    border-bottom: 1px solid var(--border);
    vertical-align: middle;
}
.row-rank-1 { background: rgba(212,169,42,0.05); border-left: 3px solid var(--gold); }
.row-rank-2 { border-left: 3px solid rgba(192,192,192,0.4); }
.row-rank-3 { border-left: 3px solid rgba(205,127,50,0.4); }

/* Circular Gauge */
.circular-chart {
  display: block;
  margin: 10px auto;
  max-width: 80px;
  max-height: 80px;
}
.circle-bg {
  fill: none;
  stroke: rgba(255,255,255,0.06);
  stroke-width: 2.8;
}
.circle {
  fill: none;
  stroke-width: 2.8;
  stroke-linecap: round;
  animation: progress 1s ease-out forwards;
}
.percentage {
  fill: #fff;
  font-family: 'JetBrains Mono', monospace;
  font-size: 8.5px;
  text-anchor: middle;
  font-weight: 600;
}

/* Metric / Stat Pill */
.meta-chip {
    padding: 4px 10px;
    border-radius: 4px;
    background: rgba(255,255,255,0.03);
    border: 1px solid var(--border);
    font-size: 0.78rem;
    color: var(--muted-foreground);
    display: inline-block;
}

/* Premium Layout Cards */
.card-best-bet {
    background: linear-gradient(135deg, rgba(212,169,42,0.15), rgba(21,24,36,0.95));
    border: 1px solid rgba(212,169,42,0.35);
    border-radius: 12px;
    padding: 1.5rem;
    position: relative;
    overflow: hidden;
}
.card-best-bet::before {
    content: "";
    position: absolute;
    top: 0; left: 0; right: 0; height: 3px;
    background: linear-gradient(90deg, var(--gold), var(--gold-bright));
}

.card-ev {
    background: var(--card);
    border: 1px solid var(--border);
    border-radius: 12px;
    padding: 1.5rem;
    display: flex;
    flex-direction: column;
    justify-content: space-between;
}

.form-box {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    width: 20px;
    height: 20px;
    font-size: 11px;
    font-weight: bold;
    border-radius: 3px;
    color: #fff;
    margin-right: 2px;
    text-shadow: 0 1px 1px rgba(0,0,0,0.5);
}

.signal-tag {
    font-size: 9px;
    font-weight: 800;
    text-transform: uppercase;
    padding: 2px 6px;
    border-radius: 3px;
    letter-spacing: 0.05em;
    display: inline-block;
}

/* Sidebar overriding */
[data-testid="stSidebar"] {
    background: var(--sidebar) !important;
    border-right: 1px solid var(--border);
}

/* Streamlit button overriding to look like premium dark sidebar buttons */
.stButton > button {
    background: transparent !important;
    color: var(--muted-foreground) !important;
    font-weight: 500 !important;
    border-radius: 6px !important;
    border: 1px solid transparent !important;
    transition: all 0.2s !important;
    text-align: left !important;
    padding: 8px 12px !important;
    white-space: pre-wrap !important;
    line-height: 1.3 !important;
}
.stButton > button:hover {
    background: rgba(255,255,255,0.03) !important;
    color: var(--foreground) !important;
    border-color: var(--border) !important;
}
.stButton > button:focus, .stButton > button:active {
    background: var(--gold-dim) !important;
    color: var(--gold) !important;
    border-color: rgba(212,169,42,0.3) !important;
}
</style>

""", unsafe_allow_html=True)


# ─── Session State Init ───────────────────────────────────────────────────────
def _init_state():
    defaults = {
        "horses":           [],
        "all_races":        {},   # {race_num: [Horse, ...]}
        "current_race":     1,
        "extraction":       None,
        "predictions":      [],
        "all_results":      {},
        "odds_map":         {},
        "processed":        False,
        "demo_mode":        False,
        "race_name":        "Greyville R1 – 1200m (Demo)",
        "venue_selector":   "Greyville",
        "surface_selector": "Polytrack",
        "distance_selector": 1200,
        "race_class_selector": "Stakes",
        "model_mode_selector": "Greyville Poly v3.13 ★",
        "_last_file_id":    None,   # Bug 7: track uploaded file identity
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v

_init_state()


def reset_race_state():
    """Wipe ALL extracted data, predictions, and status flags.

    This is the ONLY place state should be wiped.  Every key that holds
    race-specific data must be reset here to prevent stale data leaking
    across uploads/mode switches.
    """
    st.session_state.horses = []
    st.session_state.all_races = {}
    st.session_state.current_race = 1
    st.session_state.extraction = None
    st.session_state.predictions = []
    st.session_state.all_results = {}   # Bug 2: authoritative prediction store
    st.session_state.odds_map = {}
    st.session_state.processed = False
    st.session_state._last_file_id = None   # Bug 7: clear file identity





# ─── Helpers ──────────────────────────────────────────────────────────────────

def _model_mode_html() -> str:
    mode = st.session_state.get("model_mode_selector", "Greyville Poly v3.13 ★")
    model_path = os.path.join(os.path.dirname(__file__), "calibration_model_v42.pkl")
    if "v3.13" in mode:
        return '<span class="mode-tag" style="background:rgba(212,169,42,0.15); color:#d4a92a; border:1px solid rgba(212,169,42,0.35); font-weight:700; padding:4px 10px; border-radius:20px;">🏆 Greyville Poly v3.13 Active</span>'
    elif "v3.11" in mode:
        return '<span class="mode-tag mode-ml" style="background:rgba(245,200,66,0.15); color:#f5c842; border:1px solid rgba(245,200,66,0.35); font-weight:700; padding:4px 10px; border-radius:20px;">⚡ Turffontein v3.11 Active</span>'
    elif "ML Calibrated" in mode:
        if os.path.exists(model_path):
            return '<span class="mode-tag mode-ml" style="font-weight:700; padding:4px 10px; border-radius:20px;">🤖 ML Calibrated (v4.2) Active</span>'
        return '<span class="mode-tag mode-rule" style="background:rgba(255,92,122,0.12); color:#ff5c7a; border:1px solid rgba(255,92,122,0.25); font-weight:700; padding:4px 10px; border-radius:20px;">⚠️ ML Calibrated (v4.2) - PKL Missing!</span>'
    elif "Legacy Rule" in mode:
        return '<span class="mode-tag mode-rule" style="background:rgba(167,139,250,0.12); color:#a78bfa; border:1px solid rgba(167,139,250,0.25); font-weight:700; padding:4px 10px; border-radius:20px;">📐 Legacy Rule (v3.8) Active</span>'
    return '<span class="mode-tag mode-ml" style="background:rgba(0,224,150,0.12); color:#00e096; border:1px solid rgba(0,224,150,0.25); font-weight:700; padding:4px 10px; border-radius:20px;">🏇 7-Track Adaptive (v3.9) Active</span>'


def _confidence_badge(conf: str) -> str:
    cls = {"High": "badge-high", "Medium": "badge-medium", "Low": "badge-low"}.get(conf, "badge-low")
    return f'<span class="badge {cls}">{conf}</span>'


def _value_bet_icon(is_value: bool) -> str:
    return "✅ Value" if is_value else "—"


def _rank_str(rank: int) -> str:
    medals = {1: "🥇", 2: "🥈", 3: "🥉"}
    return f"{medals.get(rank, '')} {rank}"


def _ev_color(ev: float) -> str:
    if ev > 0.10:  return "🟢"
    if ev > 0.00:  return "🟡"
    return "🔴"


def _show_metric_row(horses, predictions):
    n_horses = len(horses)
    n_value  = sum(1 for p in predictions if p.value_bet)
    top_prob = f"{predictions[0].probability * 100:.1f}%" if predictions else "—"
    top_ev   = f"{predictions[0].ev:+.3f}" if predictions else "—"

    st.markdown(f"""
    <div class="metric-row">
      <div class="metric-card">
        <div class="metric-val">{n_horses}</div>
        <div class="metric-label">Runners</div>
      </div>
      <div class="metric-card">
        <div class="metric-val">{n_value}</div>
        <div class="metric-label">Value Bets</div>
      </div>
      <div class="metric-card">
        <div class="metric-val">{top_prob}</div>
        <div class="metric-label">Top Probability</div>
      </div>
      <div class="metric-card">
        <div class="metric-val">{top_ev}</div>
        <div class="metric-label">Top EV</div>
      </div>
    </div>
    """, unsafe_allow_html=True)


# ─── Sidebar ──────────────────────────────────────────────────────────────────

def render_sidebar():
    with st.sidebar:
        # 1. Top Brand Header
        st.markdown("""
        <div style="padding: 0.5rem 0; border-bottom: 1px solid var(--border); margin-bottom: 0.75rem;">
          <div style="font-family: 'Rajdhani', sans-serif; font-weight: 700; font-size: 1.2rem; color: var(--gold); letter-spacing: 0.1em; line-height: 1;">
            SA QUANT RACING
          </div>
          <div style="font-size: 0.65rem; color: var(--muted-foreground); letter-spacing: 0.1em; margin-top: 0.15rem; text-transform: uppercase;">
            BETTING INTELLIGENCE
          </div>
        </div>
        """, unsafe_allow_html=True)

        # 2. Model Stats Block
        active_r = st.session_state.get("current_race", 1)
        st.markdown(f"""
        <div style="padding: 0.25rem 0.25rem 0.65rem; border-bottom: 1px solid var(--border); margin-bottom: 0.75rem;">
          <div style="display: flex; justify-content: space-between; margin-bottom: 0.35rem;">
            <span style="font-size: 9px; color: var(--muted-foreground); letter-spacing: 0.07em; text-transform: uppercase;">MODEL VERSION</span>
            <span style="font-size: 11px; color: var(--gold); font-family: 'JetBrains Mono', monospace; font-weight: 600;">v3.13</span>
          </div>
          <div style="display: flex; justify-content: space-between; margin-bottom: 0.35rem;">
            <span style="font-size: 9px; color: var(--muted-foreground); letter-spacing: 0.07em; text-transform: uppercase;">TODAY'S TRACK</span>
            <span style="font-size: 11px; color: var(--foreground); font-weight: 600;">{st.session_state.get("venue_selector", "Greyville")} Poly</span>
          </div>
          <div style="display: flex; justify-content: space-between; margin-bottom: 0.35rem;">
            <span style="font-size: 9px; color: var(--muted-foreground); letter-spacing: 0.07em; text-transform: uppercase;">RACE CARD</span>
            <span style="font-size: 11px; color: var(--foreground); font-family: 'JetBrains Mono', monospace; font-weight: 600;">{active_r} of {len(st.session_state.get("all_races", {}))}</span>
          </div>
          <div style="display: flex; justify-content: space-between; margin-bottom: 0.35rem;">
            <span style="font-size: 9px; color: var(--muted-foreground); letter-spacing: 0.07em; text-transform: uppercase;">PREDICTIONS</span>
            <span style="font-size: 11px; color: var(--foreground); font-weight: 600;">{len(st.session_state.get("all_races", {}))} races</span>
          </div>
          <div style="display: flex; justify-content: space-between;">
            <span style="font-size: 9px; color: var(--muted-foreground); letter-spacing: 0.07em; text-transform: uppercase;">WIN RATE</span>
            <span style="font-size: 11px; color: var(--green-win); font-family: 'JetBrains Mono', monospace; font-weight: 600;">25–30%</span>
          </div>
        </div>
        """, unsafe_allow_html=True)

        # 3. Model mode indicator badge
        st.markdown(_model_mode_html(), unsafe_allow_html=True)
        st.markdown("<div style='height:0.5rem'></div>", unsafe_allow_html=True)

        # 4. File upload & Demo Toggle
        st.markdown("#### 📄 Upload PhotoForm PDF")
        uploaded = st.file_uploader(
            label       = "Drag & drop or browse",
            type        = ["pdf"],
            label_visibility = "collapsed",
            key         = "pdf_upload",
            on_change   = reset_race_state,  # Wipe old state immediately when a new file is chosen
        )

        demo_mode = st.checkbox("🎮 Use Demo Race (no PDF needed)", value=st.session_state.demo_mode)
        if demo_mode != st.session_state.demo_mode:
            reset_race_state()               # Wipe previous race data first
            st.session_state.demo_mode = demo_mode
            if demo_mode:
                st.session_state.race_name = "Fairview R1 – 1200m (Demo)"
                st.session_state.venue_selector = "Fairview"
                st.session_state.distance_selector = 1200
                st.session_state.race_class_selector = "Stakes"
                st.session_state.surface_selector = "Turf"
                st.session_state.races_meta = {
                    1: {"venue": "Fairview", "surface": "Turf", "distance": "1200m", "race_time": "12:15", "stake": "R80,000", "race_number": 1, "betting_leg": "Bipot Leg 1"},
                    2: {"venue": "Fairview", "surface": "Turf", "distance": "1200m", "race_time": "12:50", "stake": "R90,000", "race_number": 2, "betting_leg": "Bipot Leg 2"},
                    3: {"venue": "Fairview", "surface": "Turf", "distance": "1400m", "race_time": "13:25", "stake": "R100,000", "race_number": 3, "betting_leg": "Place Accumulator Leg 1"},
                }

        # 5. Prediction Engine Config & Track Parameters (in a clean collapsed expander to save sidebar space)
        with st.expander("⚙️ Engine & Track Config"):
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
                "Model Mode",
                options=model_mode_options,
                index=default_index,
                key="model_mode_selector"
            )

            venue_options = ["Turffontein", "Greyville", "Kenilworth", "Durbanville", "Fairview", "Scottsville", "Vaal"]
            v_idx = 0
            if st.session_state.venue_selector in venue_options:
                v_idx = venue_options.index(st.session_state.venue_selector)
            venue = st.selectbox(
                "Track / Venue",
                options=venue_options,
                index=v_idx,
                key="venue_selector"
            )

            if venue == "Greyville":
                surface_options = ["Polytrack", "Turf"]
                s_idx = 0
                if st.session_state.surface_selector in surface_options:
                    s_idx = surface_options.index(st.session_state.surface_selector)
                surface = st.selectbox(
                    "Surface",
                    options=surface_options,
                    index=s_idx,
                    key="surface_selector"
                )
            else:
                st.text_input("Surface", value="Turf", disabled=True, key="surface_disabled")
                surface = "Turf"
                st.session_state.surface_selector = "Turf"

            distance = st.number_input(
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
            race_class = st.selectbox(
                "Race Class",
                options=rc_options,
                index=rc_idx,
                key="race_class_selector"
            )

            race_name = st.text_input("Race Name / Description", value=st.session_state.race_name, key="race_name")

        # 6. Race List Selector (Buttons)
        all_races = st.session_state.get("all_races", {})
        all_results = st.session_state.get("all_results", {})
        if all_races:
            st.markdown('<div style="font-size: 9px; color: var(--muted-foreground); letter-spacing: 0.08em; margin: 0.75rem 0 0.4rem; text-transform: uppercase;">Races</div>', unsafe_allow_html=True)
            races_meta = st.session_state.get("races_meta", {})
            for r in sorted(all_races.keys()):
                r_horses = all_races[r]
                r_meta = races_meta.get(r, {})
                time_str = r_meta.get("race_time", "")
                dist_val = r_meta.get("distance", "")

                time_part = f"{time_str}" if time_str else ""
                dist_part = f"({dist_val})" if dist_val else ""
                header_line = f"R{r}"
                if time_part or dist_part:
                    header_line += f" · {time_part} {dist_part}".strip()

                top_pred = all_results.get(r, [None])[0] if all_results else None
                if top_pred:
                    prob = int(top_pred.probability * 100)
                    h_name = top_pred.horse.split(" ")[0]
                    btn_label = f"{header_line}\n🏆 {h_name} ({prob}%)"
                else:
                    btn_label = f"{header_line}\n{len(r_horses)} runners"
                    
                isSelected = (r == st.session_state.current_race)
                label_prefix = "👉 " if isSelected else ""
                
                if st.button(f"{label_prefix}{btn_label}", key=f"sidebar_race_btn_{r}", use_container_width=True):
                    st.session_state.current_race = r
                    st.session_state.horses       = list(all_races[r])  # Bug 4: copy to break shared reference
                    # Only mark as processed (and restore predictions) if results exist for this race;
                    # otherwise reset so the user can generate predictions fresh.
                    if all_results and r in all_results:
                        st.session_state.predictions = all_results[r]
                        st.session_state.processed   = True
                    else:
                        st.session_state.predictions = []
                        st.session_state.processed   = False
                    st.rerun()

        # 7. Action Buttons
        st.markdown("<div style='height:0.5rem'></div>", unsafe_allow_html=True)
        process_clicked = st.button("⚡ Process Race", use_container_width=True)

        with st.expander("ℹ️ PDF Extraction Help"):
            st.markdown("""
            - Draw / barrier number
            - Horse name
            - Jockey & trainer
            - Form string, runs
            - Weight carried
            - Rating / handicap mark
            """)

        st.markdown("""
        <div style="font-size: 9px; color: var(--muted-foreground); letter-spacing: 0.08em; margin: 0.75rem 0 0.4rem; text-transform: uppercase;">
          v3.13 Engine Audit Checklist
        </div>
        <div style="display:flex; flex-direction:column; gap:6px; background:rgba(255,255,255,0.02); border:1px solid var(--border); border-radius:6px; padding:10px; font-size:0.75rem; color:#8892b0;">
          <div style="display:flex; align-items:center; gap:6px;"><span style="color:#00e096;">✔</span> Longshot Score Boost Disabled</div>
          <div style="display:flex; align-items:center; gap:6px;"><span style="color:#00e096;">✔</span> Odds-on favorite 35% Floor Active</div>
          <div style="display:flex; align-items:center; gap:6px;"><span style="color:#00e096;">✔</span> Apprentice Jockey Multiplier Active</div>
          <div style="display:flex; align-items:center; gap:6px;"><span style="color:#00e096;">✔</span> Greyville Poly Draw Bias Applied</div>
        </div>
        """, unsafe_allow_html=True)
        st.markdown("<div style='height:0.5rem'></div>", unsafe_allow_html=True)

        with st.expander("📐 EV Formula"):
            st.latex(r"EV = p \times (odds - 1) - (1 - p)")
            st.markdown("""
            - **p** = model probability  
            - **odds** = decimal odds  
            - EV > 0 = positive expectation  
            - EV > 0.05 + Medium+ confidence = **Value Bet ✅**
            """)

        return uploaded, process_clicked


# ─── v3.11 Preprocessing & Output Helpers ────────────────────────────────────

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


# ─── Race Grouping Helper ───────────────────────────────────────────────────────

def group_horses_by_race(horses: list) -> dict:
    """
    Bucket Horse objects by their .race attribute.
    Returns {race_num: [Horse, ...]} sorted by draw within each race.
    """
    all_races: dict = {}
    
    # First, try to get race numbers from .race attribute
    for h in horses:
        # Try multiple attribute names for race number
        rnum = None
        for attr in ['race', 'race_num', 'race_number', 'raceNo']:
            if hasattr(h, attr):
                val = getattr(h, attr)
                if val is not None:
                    rnum = int(val)
                    break
        
        # If no race number found, default to race 1
        if rnum is None:
            rnum = 1
            
        all_races.setdefault(rnum, []).append(h)
    
    # Sort each bucket by draw number
    for rnum in all_races:
        all_races[rnum].sort(key=lambda h: getattr(h, 'draw', 0))
    
    return all_races


# ─── Extraction Section ───────────────────────────────────────────────────────

def run_extraction(uploaded_file, demo_mode: bool) -> bool:
    """Extract horses from PDF or demo data. Returns True on success."""
    if demo_mode:
        horses = get_demo_horses()
        # Demo: horses are distributed into multiple races (R1, R2, R3)
        for i, h in enumerate(horses):
            if i < 8:
                h.race = 1
            elif i < 16:
                h.race = 2
            else:
                h.race = 3
                
        all_races = group_horses_by_race(horses)

        result = ExtractionResult(
            horses     = horses,
            confidence = 1.0,
            warnings   = [],
            raw_text   = "Demo mode — synthetic data",
            pages_read = 0,
        )
        demo_odds = {
            "African Gold":  1.90, "Protea Pride": 2.80, "Silver Storm": 4.50,
            "Highveld King": 5.00, "Vaal Champion": 6.00, "Dragon Heart": 8.50,
            "Cape Legend":  14.00, "Ubuntu Prince": 7.50,
        }
        for h in horses:
            name_key = getattr(h, "horse", "Unknown")
            try:
                h.forecast_odds = demo_odds.get(name_key, 0.0)
            except AttributeError:
                pass

        st.session_state.all_races    = all_races
        st.session_state.current_race = min(all_races.keys())
        st.session_state.horses       = list(all_races[st.session_state.current_race])  # Bug 4: copy
        st.session_state.extraction   = result
        st.session_state.processed    = False
        st.session_state.predictions  = []   # Clear stale predictions from previous runs
        st.session_state.all_results  = {}
        st.session_state.odds_map     = {
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
        st.warning("⚠️ Please upload a PDF or enable Demo Mode.")
        return False

    # Validate file size (< 20 MB)
    file_bytes = uploaded_file.read()
    if len(file_bytes) > 20 * 1024 * 1024:
        st.error("❌ File too large (> 20 MB). Please upload a smaller PDF.")
        return False

    st.info("⏳ Processing PDF... this usually takes 2–5 seconds.")
    progress_bar = st.progress(0)
    status_text = st.empty()
    status_text.text("📄 Starting extraction...")
    
    with st.spinner("📄 Extracting race data from PDF..."):
        try:
            progress_bar.progress(25)
            status_text.text("📄 Parsing PDF structure...")
            # Save PDF to disk so the diagnostic script can inspect it
            _debug_pdf_path = "debug_uploaded.pdf"
            try:
                with open(_debug_pdf_path, "wb") as _f:
                    _f.write(file_bytes)
                logger.info("Saved uploaded PDF to %s for diagnostic", _debug_pdf_path)
            except Exception as _e:
                logger.warning("Could not save debug PDF: %s", _e)

            result = extract_from_pdf(file_bytes)
            progress_bar.progress(100)
            status_text.text("✅ Extraction complete!")

            # ─── App-side safety net ────────────────────────────────────────
            # Runs even if the extractor's own post-processing was skipped due
            # to a cached .pyc or any other reason.
            if result and result.horses:
                def _is_bad_horse(h) -> bool:
                    n = getattr(h, "horse", "").strip()
                    return not n or len(n) < 3

                result.horses = [h for h in result.horses if not _is_bad_horse(h)]

                # Bug 1: Bump race 0 → 1 (ONLY for horses actually in race 0)
                # Previously this incremented ALL horses, shifting races 0-7 to 1-8
                # but also shifting races that were already correct, creating phantoms.
                has_race_0 = any(h.race == 0 for h in result.horses)
                if has_race_0:
                    for h in result.horses:
                        if h.race == 0:
                            h.race = 1

                result.horses.sort(key=lambda h: (h.race, h.draw))
                logger.info(
                    "App-side fix applied: %d horses across races %s",
                    len(result.horses),
                    sorted({h.race for h in result.horses}),
                )
            # ────────────────────────────────────────────────────────────────
        except Exception as e:
            progress_bar.empty()
            status_text.empty()
            st.error(f"❌ Extraction failed: {e}")
            logger.exception("PDF extraction error")
            return False

    # Validate
    if not result.is_valid:
        st.markdown(f"""
        <div class="warn-banner">
          ❌ <strong>Extraction failed</strong> — could not find at least 2 valid horses in the PDF.<br>
          Check that this is a standard SA PhotoForm/Computaform race card PDF.
        </div>
        """, unsafe_allow_html=True)
        if result.warnings:
            with st.expander("🔍 Extraction warnings"):
                for w in result.warnings:
                    st.write(f"• {w}")
        return False

    # Filter malformed objects
    valid_horses = [h for h in result.horses if hasattr(h, "horse")]

    # Ensure each horse has a race number assigned (fallback if extractor missed it)
    for h in valid_horses:
        if not hasattr(h, 'race') or getattr(h, 'race', None) is None:
            h.race = 1

    # Preprocess: assign default MRs and initialise list fields
    race_class = st.session_state.get("race_class_selector", "Grade 1")
    preprocess_horse_data(valid_horses, race_class)

    # Group by race number (populated by extractor boundary detection)
    all_races = group_horses_by_race(valid_horses)

    # If ALL horses ended up in race 1 and the field is suspiciously large,
    # try the saddle-reset heuristic from extractor before giving up.
    if len(all_races) == 1 and len(valid_horses) > 12:
        st.warning(
            f"⚠️ All {len(valid_horses)} horses were assigned to Race 1. "
            "Attempting saddle-reset redistribution…"
        )
        from extractor import _assign_by_saddle_reset
        valid_horses_sorted = sorted(valid_horses, key=lambda h: (getattr(h, 'saddle', 0), getattr(h, 'draw', 0)))
        valid_horses_sorted = _assign_by_saddle_reset(valid_horses_sorted, n_races=len(valid_horses) // 8)
        all_races = group_horses_by_race(valid_horses_sorted)
        logger.info(f"Saddle-reset heuristic reassigned horses to races: {sorted(all_races.keys())}")

    # Only split into fixed groups of 8 as a last resort (warn user)
    if len(all_races) == 1 and len(valid_horses) > 8:
        st.warning(
            "⚠️ Could not detect race boundaries automatically. "
            "Horses are being split into groups of up to 8. "
            "Please verify the race assignments below."
        )
        all_races = {}
        for i in range(0, len(valid_horses), 8):
            race_num = (i // 8) + 1
            group = valid_horses[i:i+8]
            for h in group:
                h.race = race_num
            all_races[race_num] = group
        logger.info(f"Last-resort split: {len(valid_horses)} horses into {len(all_races)} groups of ~8")

    if not all_races:
        st.error("❌ No races detected in the extracted data.")
        return False

    first_race = min(all_races.keys())
    n_races    = len(all_races)
    total_h    = len(valid_horses)

    st.session_state.races_meta = getattr(result, "races_meta", {})

    st.session_state.all_races    = all_races
    st.session_state.current_race = first_race
    st.session_state.horses       = list(all_races[first_race])  # Bug 4: copy
    st.session_state.extraction   = result
    st.session_state.processed    = False
    st.session_state.predictions  = []   # Clear stale predictions from previous runs
    st.session_state.all_results  = {}
    st.session_state.odds_map     = {
        getattr(h, "horse", "Unknown"): getattr(h, "market_odds", getattr(h, "forecast_odds", 0.0))
        for h in valid_horses
    }
    st.success(
        f"✅ {total_h} horse{'s' if total_h != 1 else ''} loaded across "
        f"{n_races} race{'s' if n_races != 1 else ''} — showing Race {first_race}."
    )
    return True


# ─── Dynamic Race Header Component ────────────────────────────────────────────

def render_race_header(current_race: int):
    """Render dynamic ComputaForm race header badges strictly tied to current_race."""
    races_meta = st.session_state.get("races_meta", {})
    meta = races_meta.get(current_race, {})

    venue       = meta.get("venue")
    surface     = meta.get("surface")
    distance    = meta.get("distance")
    race_time   = meta.get("race_time")
    stake       = meta.get("stake")
    betting_leg = meta.get("betting_leg")

    badges = []
    if venue:
        badges.append(f'<span class="meta-chip">📍 <strong>{venue}</strong></span>')
    if surface:
        badges.append(f'<span class="meta-chip">🌱 {surface}</span>')
    if distance:
        badges.append(f'<span class="meta-chip">📏 {distance}</span>')
    if race_time:
        badges.append(f'<span class="meta-chip">🕛 {race_time}</span>')
    if stake:
        badges.append(f'<span class="meta-chip">💰 {stake}</span>')

    # Race Number badge - strictly dynamic based on actual current_race
    badges.append(f'<span class="meta-chip">🏁 Race {current_race}</span>')

    if betting_leg:
        badges.append(f'<span class="meta-chip">🎫 {betting_leg}</span>')

    if badges:
        html = f"""
        <div style="display:flex; flex-wrap:wrap; gap:8px; margin-bottom:1rem;">
          {"".join(badges)}
        </div>
        """
        st.markdown(html, unsafe_allow_html=True)


# ─── Race Preview Section ─────────────────────────────────────────────────────

def render_race_preview(horses: list[Horse], extraction: ExtractionResult):
    """Display extracted horses table with confidence indicator."""

    conf = extraction.confidence
    conf_label = extraction.confidence_label

    conf_color = {"High": "#00e096", "Medium": "#f5c842", "Low": "#ff5c7a"}[conf_label]
    conf_bar   = int(conf * 100)

    st.markdown('<div class="section-title">📋 Race Preview — Extracted Horses</div>', unsafe_allow_html=True)

    col_conf, col_pages, col_runners = st.columns(3)
    col_conf.markdown(f"""
    <div class="metric-card">
      <div class="metric-val" style="color:{conf_color};">{conf_bar}%</div>
      <div class="metric-label">Extraction Confidence ({conf_label})</div>
    </div>""", unsafe_allow_html=True)
    col_pages.markdown(f"""
    <div class="metric-card">
      <div class="metric-val">{extraction.pages_read}</div>
      <div class="metric-label">PDF Pages Read</div>
    </div>""", unsafe_allow_html=True)
    col_runners.markdown(f"""
    <div class="metric-card">
      <div class="metric-val">{len(horses)}</div>
      <div class="metric-label">Horses Found</div>
    </div>""", unsafe_allow_html=True)

    if extraction.warnings:
        with st.expander(f"⚠️ {len(extraction.warnings)} extraction warning(s)"):
            for w in extraction.warnings:
                st.write(f"• {w}")

    # Horse table
    df_preview = pd.DataFrame([{
        "Draw":    h.draw,
        "Horse":   h.horse,
        "Jockey":  h.jockey,
        "Trainer": h.trainer,
        "Form":    h.form_string or "—",
        "Runs":    h.runs,
        "Wt (kg)": h.weight if h.weight > 0 else "—",
        "Rating":  h.merit_rating if h.merit_rating is not None else "—",
    } for h in sorted(horses, key=lambda x: x.draw)])

    st.dataframe(
        df_preview,
        use_container_width = True,
        hide_index          = True,
        column_config={
            "Draw":    st.column_config.NumberColumn("Draw", width="small"),
            "Horse":   st.column_config.TextColumn("Horse", width="medium"),
            "Form":    st.column_config.TextColumn("Form",  width="medium"),
            "Runs":    st.column_config.NumberColumn("Runs", width="small"),
            "Wt (kg)": st.column_config.TextColumn("Wt (kg)", width="small"),
            "Rating":  st.column_config.TextColumn("Rating",  width="small"),
        },
    )

    # Debug Panel
    with st.expander("🔬 Raw Extracted JSON Debug Panel"):
        import dataclasses
        import json

        # Race assignment summary
        all_races_local = st.session_state.get("all_races", {})
        if all_races_local:
            st.markdown("**Race Assignment Summary:**")
            for rnum in sorted(all_races_local.keys()):
                names = [getattr(h, "horse", "?") for h in all_races_local[rnum]]
                st.write(f"Race {rnum}: {len(names)} horses → {', '.join(names[:5])}{'...' if len(names) > 5 else ''}")

        # Raw text preview (first 1000 chars)
        if extraction.raw_text:
            st.markdown("**Raw PDF Text (first 1000 chars):**")
            st.code(extraction.raw_text[:1000], language="text")

        st.markdown("**Full Horse JSON:**")
        raw_list = [dataclasses.asdict(h) for h in horses]
        st.json(raw_list)


# ─── Odds Input ───────────────────────────────────────────────────────────────

def render_odds_input(horses: list[Horse]) -> dict:
    """Let user enter/override decimal odds for each horse. Returns odds_map."""

    st.markdown('<div class="section-title">💰 Market Odds (decimal format)</div>', unsafe_allow_html=True)
    st.caption(
        "Pre-populated from the ComputaForm F/B forecast. "
        "Edit any value to use live market odds (e.g. from Hollywood Bets). "
        "Leave 0 to let the model estimate fair odds from probability."
    )

    existing = st.session_state.odds_map
    odds_map = {}

    # Safety: only process horses with a valid .horse attribute
    valid_horses = [
        h for h in horses
        if hasattr(h, "horse") and isinstance(h.horse, str) and len(h.horse) > 2
    ]

    # Render in 2-column grid
    cols_per_row = 4
    horse_list   = sorted(valid_horses, key=lambda h: h.draw)
    rows         = [horse_list[idx:idx+cols_per_row] for idx in range(0, len(horse_list), cols_per_row)]

    # Include the file ID in the key namespace so Streamlit resets all
    # number_input widgets when a new PDF is uploaded (avoids stale cached values).
    file_slot = str(st.session_state.get("_last_file_id", "demo")).replace(" ", "_")

    i = 0
    for row in rows:
        cols = st.columns(cols_per_row)
        for col, horse in zip(cols, row):
            with col:
                # Prefer user's previously-entered value, then market_odds (pre-populated
                # from the PDF), then forecast_odds, then 0.
                default_val = float(
                    existing.get(
                        horse.horse,
                        getattr(horse, "market_odds", getattr(horse, "forecast_odds", 0.0))
                    ) or 0.0
                )
                val = st.number_input(
                    label     = f"#{horse.draw} {horse.horse}",
                    min_value = 0.0,
                    max_value = 999.0,
                    value     = default_val,
                    step      = 0.10,
                    format    = "%.2f",
                    key       = f"odds_{file_slot}_{i}_{horse.draw}_{horse.horse.replace(' ','_')}",
                )
                odds_map[horse.horse] = val
                # Show the original ComputaForm F/B forecast as a reference hint
                fb_str = getattr(horse, "fb_odds_str", "")
                if fb_str:
                    st.caption(f"📋 CF Forecast: {fb_str}")
                i += 1

    st.session_state.odds_map.update(odds_map)  # Bug 6: merge, don't overwrite (preserves other races' odds)
    return odds_map


# ─── Predictions Section ──────────────────────────────────────────────────────

def render_predictions(predictions: list[Prediction], race_name: str):
    """Display full ranked predictions table + EV summary."""

    st.markdown(f'<div class="section-title">🏆 Predictions — {race_name}</div>', unsafe_allow_html=True)

    _show_metric_row(st.session_state.horses, predictions)

    # ── Value bets callout
    value_bets = [p for p in predictions if p.value_bet]
    if value_bets:
        vb_str = "  |  ".join(f"#{p.draw} **{p.horse}** ({p.ev:+.3f} EV @ {p.odds})" for p in value_bets)
        st.markdown(f"""
        <div class="success-banner">
          ✅ <strong>{len(value_bets)} Value Bet(s) Found:</strong>&nbsp;&nbsp;{vb_str}
        </div>
        """, unsafe_allow_html=True)
    else:
        st.markdown("""
        <div class="info-banner">
          ℹ️ No value bets detected at current odds. Consider reviewing the odds or waiting for line movement.
        </div>
        """, unsafe_allow_html=True)

    # ── Longshot bets callout
    longshots = [p for p in predictions if getattr(p, "longshot", False)]
    if longshots:
        ls_str = "  |  ".join(f"#{p.draw} **{p.horse}** ({p.ev:+.3f} EV @ {p.odds})" for p in longshots)
        st.markdown(f"""
        <div class="success-banner" style="background: rgba(255,92,122,0.08); border: 1px solid rgba(255,92,122,0.25); color: #ff5c7a;">
          🔥 <strong>{len(longshots)} Longshot Alert(s):</strong>&nbsp;&nbsp;{ls_str}
        </div>
        """, unsafe_allow_html=True)

    # ── Build display dataframe
    rows = []
    for p in predictions:
        rows.append({
            "Rank":        _rank_str(p.rank),
            "Draw":        p.draw,
            "Horse":       p.horse,
            "Jockey":      p.jockey,
            "Odds":        f"{p.odds:.2f}",
            "Probability": p.probability,
            "EV":          p.ev,
            "Rule Score":  p.rule_score,
            "Confidence":  p.confidence,
            "Value Bet":   "✅ Value" if p.value_bet else "—",
            "Longshot":    "🔥 Longshot" if getattr(p, "longshot", False) else "—",
        })

    df = pd.DataFrame(rows)

    # Colour EV column
    def style_table(df_in):
        styles = pd.DataFrame("", index=df_in.index, columns=df_in.columns)
        for i, row in df_in.iterrows():
            if row.get("Value Bet") == "✅ Value":
                styles.loc[i, :] = "background-color: rgba(0,224,150,0.08);"
        return styles

    st.dataframe(
        df,
        use_container_width = True,
        hide_index          = True,
        column_config={
            "Probability": st.column_config.ProgressColumn(
                "Probability",
                min_value = 0.0,
                max_value = 1.0,
                format    = "%.1f%%",
            ),
            "EV": st.column_config.NumberColumn(
                "EV",
                format = "%+.3f",
            ),
            "Rule Score": st.column_config.ProgressColumn(
                "Rule Score",
                min_value = 0.0,
                max_value = 1.0,
                format    = "%.3f",
            ),
            "Rank":  st.column_config.TextColumn("Rank",  width="small"),
            "Draw":  st.column_config.NumberColumn("Draw", width="small"),
            "Odds":  st.column_config.TextColumn("Odds",  width="small"),
        },
    )

    # ── Detailed EV breakdown (expander)
    with st.expander("📊 Detailed EV Breakdown"):
        ev_rows = []
        for p in predictions:
            ev_rows.append({
                "Horse":          p.horse,
                "Model Prob":     f"{p.probability*100:.2f}%",
                "Implied Prob":   f"{p.implied_prob*100:.2f}%" if p.odds > 1 else "—",
                "Edge":           f"{(p.probability - p.implied_prob)*100:+.2f}%" if p.odds > 1 else "—",
                "Decimal Odds":   p.odds,
                "EV":             f"{p.ev:+.4f}",
                "EV Indicator":   _ev_color(p.ev),
                "Confidence":     p.confidence,
                "Longshot":       "🔥 Yes" if getattr(p, "longshot", False) else "—",
            })
        st.dataframe(pd.DataFrame(ev_rows), use_container_width=True, hide_index=True)


# ─── Exotics Intelligence Section ─────────────────────────────────────────────

def render_exotics_intelligence(results: list, all_results: dict = None, current_race: int = 1):
    """
    Exotics Intelligence Panel
    Provides quantitative probability-derived exotic betting predictions (Exacta, Trifecta,
    Quartet, Swinger) and multi-race meeting permutations.
    """
    if not results:
        return

    st.markdown('<div class="section-title">🧬 Exotics Intelligence Panel</div>', unsafe_allow_html=True)
    st.caption("Quantitative probability-derived exotic betting calculations, optimal combinations, and multi-race permutations.")

    tab_single, tab_multi = st.tabs([
        f"🎯 Race {current_race} Single-Race Exotics",
        "🏆 Meeting Multi-Race Permutations"
    ])

    def _g(p, attr, default=None):
        if hasattr(p, attr):
            return getattr(p, attr)
        if isinstance(p, dict):
            return p.get(attr, default)
        return default

    sorted_p = sorted(results, key=lambda x: _g(x, "rank", 99))

    def name(p): return _g(p, "horse", "Unknown")
    def draw(p): return _g(p, "draw", 0)
    def prob(p): return float(_g(p, "probability", 0.0))
    def odds(p): return float(_g(p, "odds", 10.0))

    tot_p = sum(prob(p) for p in sorted_p)
    norm_p = [prob(p) / tot_p if tot_p > 0 else 1.0 / len(sorted_p) for p in sorted_p]

    with tab_single:
        if len(sorted_p) >= 2:
            p1, p2 = norm_p[0], norm_p[1]
            h1, h2 = sorted_p[0], sorted_p[1]

            denom1 = max(1.0 - p1, 1e-5)
            exacta_prob = p1 * (p2 / denom1)
            exacta_fair_odds = 1.0 / exacta_prob if exacta_prob > 0 else 999.0

            col_ex, col_sw = st.columns(2)
            with col_ex:
                st.markdown(f"""
                <div style="background:var(--card); border:1px solid var(--border); border-radius:10px; padding:1.2rem; height:100%;">
                  <div style="font-size:0.75rem; font-weight:800; color:var(--gold); text-transform:uppercase; letter-spacing:0.07em; margin-bottom:0.5rem;">
                    🎯 EXACTA INTELLIGENCE (1st &amp; 2nd)
                  </div>
                  <div style="background:rgba(212,169,42,0.08); border:1px solid rgba(212,169,42,0.25); border-radius:8px; padding:0.8rem; margin-bottom:0.8rem;">
                    <div style="font-size:0.75rem; color:var(--muted-foreground);">Top Model Straight Exacta</div>
                    <div style="font-size:1.1rem; font-weight:800; color:#fff; font-family:'Outfit',sans-serif; margin:4px 0;">
                      #{draw(h1)} {name(h1)} <span style="color:var(--gold);">➔</span> #{draw(h2)} {name(h2)}
                    </div>
                    <div style="display:flex; justify-content:space-between; font-size:0.8rem; margin-top:6px;">
                      <span>Model Probability: <strong style="color:var(--green-win);">{exacta_prob*100:.2f}%</strong></span>
                      <span>Fair Odds: <strong style="color:var(--gold);">{exacta_fair_odds:.1f}/1</strong></span>
                    </div>
                  </div>
                  <div style="font-size:0.8rem; color:var(--foreground);">
                    <strong>Exacta Box (Top 3):</strong> #{draw(sorted_p[0])}, #{draw(sorted_p[1])}, #{draw(sorted_p[2]) if len(sorted_p)>2 else ''}<br>
                    <span style="font-size:0.75rem; color:var(--muted-foreground);">6 Combinations · Cost: R6 @ R1/unit</span>
                  </div>
                </div>
                """, unsafe_allow_html=True)

            with col_sw:
                sw1 = f"#{draw(h1)} {name(h1)} + #{draw(h2)} {name(h2)}"
                h3 = sorted_p[2] if len(sorted_p) > 2 else h2
                sw2 = f"#{draw(h1)} {name(h1)} + #{draw(h3)} {name(h3)}"
                sw3 = f"#{draw(h2)} {name(h2)} + #{draw(h3)} {name(h3)}"

                st.markdown(f"""
                <div style="background:var(--card); border:1px solid var(--border); border-radius:10px; padding:1.2rem; height:100%;">
                  <div style="font-size:0.75rem; font-weight:800; color:#5c9fff; text-transform:uppercase; letter-spacing:0.07em; margin-bottom:0.5rem;">
                    🔄 SWINGER INTELLIGENCE (Any 2 in Top 3)
                  </div>
                  <div style="display:flex; flex-direction:column; gap:6px;">
                    <div style="background:rgba(92,159,255,0.06); border:1px solid rgba(92,159,255,0.2); border-radius:6px; padding:6px 10px; font-size:0.82rem; font-weight:700; color:#fff;">
                      ⭐ Primary Swinger: {sw1}
                    </div>
                    <div style="background:rgba(255,255,255,0.03); border:1px solid var(--border); border-radius:6px; padding:6px 10px; font-size:0.82rem; color:var(--muted-foreground);">
                      🔹 Secondary Swinger: {sw2}
                    </div>
                    <div style="background:rgba(255,255,255,0.03); border:1px solid var(--border); border-radius:6px; padding:6px 10px; font-size:0.82rem; color:var(--muted-foreground);">
                      🔹 Coverage Swinger: {sw3}
                    </div>
                  </div>
                </div>
                """, unsafe_allow_html=True)

        st.markdown("<div style='height:0.8rem;'></div>", unsafe_allow_html=True)

        if len(sorted_p) >= 3:
            p1, p2, p3 = norm_p[0], norm_p[1], norm_p[2]
            h1, h2, h3 = sorted_p[0], sorted_p[1], sorted_p[2]

            denom1 = max(1.0 - p1, 1e-5)
            denom2 = max(1.0 - p1 - p2, 1e-5)
            trifecta_prob = p1 * (p2 / denom1) * (p3 / denom2)
            trifecta_fair_odds = 1.0 / trifecta_prob if trifecta_prob > 0 else 999.0

            col_tri, col_qrt = st.columns(2)
            with col_tri:
                st.markdown(f"""
                <div style="background:var(--card); border:1px solid var(--border); border-radius:10px; padding:1.2rem; height:100%;">
                  <div style="font-size:0.75rem; font-weight:800; color:var(--green-win); text-transform:uppercase; letter-spacing:0.07em; margin-bottom:0.5rem;">
                    🏆 TRIFECTA INTELLIGENCE (1st, 2nd, 3rd)
                  </div>
                  <div style="background:rgba(34,197,94,0.08); border:1px solid rgba(34,197,94,0.25); border-radius:8px; padding:0.8rem; margin-bottom:0.8rem;">
                    <div style="font-size:0.75rem; color:var(--muted-foreground);">Top Straight Trifecta</div>
                    <div style="font-size:1rem; font-weight:800; color:#fff; font-family:'Outfit',sans-serif; margin:4px 0;">
                      #{draw(h1)} {name(h1)} <span style="color:var(--green-win);">➔</span> #{draw(h2)} {name(h2)} <span style="color:var(--green-win);">➔</span> #{draw(h3)} {name(h3)}
                    </div>
                    <div style="display:flex; justify-content:space-between; font-size:0.8rem; margin-top:6px;">
                      <span>Model Prob: <strong style="color:var(--green-win);">{trifecta_prob*100:.2f}%</strong></span>
                      <span>Fair Odds: <strong style="color:var(--gold);">{trifecta_fair_odds:.1f}/1</strong></span>
                    </div>
                  </div>
                  <div style="font-size:0.8rem; color:var(--foreground); line-height:1.4;">
                    <strong>Banker Trifecta:</strong> Standout #{draw(h1)} with #{draw(h2)}, #{draw(h3)}, #{draw(sorted_p[3]) if len(sorted_p)>3 else ''} (6 combos)<br>
                    <strong>Trifecta Box (Top 4):</strong> 24 Combinations · Cost: R24 @ R1/unit
                  </div>
                </div>
                """, unsafe_allow_html=True)

            with col_qrt:
                h4 = sorted_p[3] if len(sorted_p) > 3 else h3
                quartet_str = f"#{draw(h1)} {name(h1)} ➔ #{draw(h2)} {name(h2)} ➔ #{draw(h3)} {name(h3)} ➔ #{draw(h4)} {name(h4)}"
                st.markdown(f"""
                <div style="background:var(--card); border:1px solid var(--border); border-radius:10px; padding:1.2rem; height:100%;">
                  <div style="font-size:0.75rem; font-weight:800; color:#a78bfa; text-transform:uppercase; letter-spacing:0.07em; margin-bottom:0.5rem;">
                    👑 QUARTET INTELLIGENCE (1st, 2nd, 3rd, 4th)
                  </div>
                  <div style="background:rgba(167,139,250,0.08); border:1px solid rgba(167,139,250,0.25); border-radius:8px; padding:0.8rem; margin-bottom:0.8rem;">
                    <div style="font-size:0.75rem; color:var(--muted-foreground);">Top Straight Quartet</div>
                    <div style="font-size:0.92rem; font-weight:800; color:#fff; font-family:'Outfit',sans-serif; margin:4px 0;">
                      {quartet_str}
                    </div>
                  </div>
                  <div style="font-size:0.8rem; color:var(--foreground); line-height:1.4;">
                    <strong>Banker Quartet:</strong> Banker #{draw(h1)} 1st, Box rest (24 combos)<br>
                    <strong>Quartet Box (Top 4):</strong> 24 Combinations · Cost: R24 @ R1/unit
                  </div>
                </div>
                """, unsafe_allow_html=True)

    with tab_multi:
        all_r = all_results if all_results else {}
        perms_text = generate_perms_block(all_r)

        st.markdown("""
        <div style="font-size:0.88rem; color:var(--muted-foreground); margin-bottom:0.75rem;">
          Multi-race permutations automatically structure optimal selections based on quantitative win probabilities across all meeting races.
        </div>
        """, unsafe_allow_html=True)

        if perms_text and "(Not enough races" not in perms_text:
            st.code(perms_text, language="text")
        else:
            st.info("ℹ️ Generate predictions across all races in the meeting to view Pick 6, BiPot, and Jackpot permutations.")


# ─── Feature Debug Expander ───────────────────────────────────────────────────

def render_model_debug(predictions: list[Prediction]):
    with st.expander("🔬 Model Feature Breakdown (Advanced)"):
        feature_names = [
            "Draw Bias", "Form Score", "Jockey WR", "Trainer WR",
            "Weight Penalty", "Rating Norm", "Experience",
            "Field Size Norm", "Has Form", "Win Rate (Form)",
            "Top-3 Rate (Form)", "Composite v3.8",
        ]
        rows = []
        for p in predictions:
            row = {"Horse": p.horse, "Rank": p.rank}
            for name, val in zip(feature_names, p.features):
                row[name] = round(val, 3)
            rows.append(row)
        st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)


# ─── Main App ─────────────────────────────────────────────────────────────────

def main():
    # Hero header
    st.markdown("""
    <div class="hero-header">
      <div class="hero-icon">🏇</div>
      <div>
        <div class="hero-title">SA Quant Racing Predictor</div>
        <div class="hero-sub">
          Upload a PhotoForm PDF · Extract horses · Generate ranked predictions with EV &amp; value bets
        </div>
      </div>
    </div>
    """, unsafe_allow_html=True)

    # Sidebar
    uploaded_file, process_clicked = render_sidebar()

    # ── Bug 7: File identity tracking — detect new/changed uploads
    if uploaded_file is not None:
        file_id = f"{uploaded_file.name}_{uploaded_file.size}"
        if file_id != st.session_state.get("_last_file_id"):
            reset_race_state()
            st.session_state._last_file_id = file_id

    # ── Process trigger
    if process_clicked:
        success = run_extraction(uploaded_file, st.session_state.demo_mode)
        if success:
            st.session_state.processed = False   # reset so odds can be entered
            # Force a full rerun so the sidebar immediately reflects the new races
            # and the main view shows only the new data with no stale state.
            st.rerun()

    # ── If we have horses, show preview + odds input
    horses     = [
        h for h in st.session_state.horses
        if hasattr(h, "horse") and isinstance(h.horse, str) and len(h.horse) > 2
    ]
    extraction = st.session_state.extraction

    if not horses:
        # Landing state
        col_l, col_r = st.columns(2)
        with col_l:
            st.markdown("""
            <div class="info-banner">
              👋 <strong>Welcome!</strong> Upload a PhotoForm PDF in the sidebar and click
              <strong>Process Race</strong> to get started.<br><br>
              Or enable <strong>Demo Mode</strong> to explore with a sample race.
            </div>
            """, unsafe_allow_html=True)
        with col_r:
            st.markdown("""
            <div style="background:rgba(255,255,255,0.03); border:1px solid rgba(255,255,255,0.06);
                        border-radius:12px; padding:1.25rem;">
              <div style="font-size:0.8rem; color:#8892b0; margin-bottom:0.75rem;">FEATURES</div>
              <div style="display:flex; flex-direction:column; gap:0.5rem; font-size:0.88rem; color:#c9d1e0;">
                <div>📄 PDF extraction from SA PhotoForm race cards</div>
                <div>🤖 ML calibration model (GBM + isotonic)</div>
                <div>📐 Rule-based scoring v3.8 (draw, form, jockey, trainer, weight)</div>
                <div>💹 EV = prob × (odds − 1) − (1 − prob)</div>
                <div>✅ Automatic value bet detection</div>
                <div>📊 Interactive probability & EV charts</div>
              </div>
            </div>
            """, unsafe_allow_html=True)
        return

    # ── Resolve current race's horses from all_races
    all_races     = st.session_state.get("all_races", {})
    current_race  = st.session_state.get("current_race", 1)

    # Bug 3: all_races is the SINGLE SOURCE OF TRUTH.
    # Never re-derive it from the flat 'horses' list — that caused single-race
    # re-grouping that erased all other races.
    if not all_races:
        st.warning("⚠️ No race data loaded. Please upload a PDF and click Process Race.")
        return

    race_horses = all_races.get(current_race, [])
    race_horses = [h for h in race_horses if hasattr(h, "horse") and isinstance(h.horse, str) and len(h.horse) > 2]

    if not race_horses:
        st.warning(f"⚠️ No horses found for Race {current_race}. Please use the sidebar to select a race.")
        return

    # ── Race Header & Preview
    render_race_header(current_race)
    render_race_preview(race_horses, extraction)

    st.markdown("---")

    # ── Odds input
    odds_map = render_odds_input(race_horses)

    st.markdown("<div style='height:0.5rem'></div>", unsafe_allow_html=True)

    col_gen, _ = st.columns([1, 3])
    with col_gen:
        gen_clicked = st.button("🚀 Generate Predictions", use_container_width=True)

    if gen_clicked or (st.session_state.processed and st.session_state.get("predictions")):
        with st.spinner("🤖 Running predictions meeting-wide..."):
            venue      = st.session_state.get("venue_selector",       "Greyville")
            surface    = st.session_state.get("surface_selector",     "Polytrack")
            distance   = int(st.session_state.get("distance_selector", 1200))
            race_class = st.session_state.get("race_class_selector",  "Stakes")
            model_mode = st.session_state.get("model_mode_selector",  "Greyville Poly v3.13 ★")

            # Bug 2: ALWAYS reset results dict before generating predictions.
            # Previously this guard never fired (key always exists from _init_state),
            # so stale races from previous uploads persisted in all_results.
            st.session_state.all_results = {}

            # Run predictions for ALL races in the meeting
            for r_num, r_horses in all_races.items():
                # Ensure every horse in r_horses has valid forecast_odds
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

                # Determine correct distance
                h_dist = r_horses[0].get("distance", distance) if hasattr(r_horses[0], "get") else getattr(r_horses[0], "distance", distance)
                try:
                    h_dist = int(h_dist)
                except (ValueError, TypeError):
                    h_dist = distance

                # Map current odds overrides (only for current race)
                r_odds_map = odds_map if r_num == current_race else {}

                # Run predicting engine
                if "v3.11" in model_mode:
                    race_context = {
                        "distance":   h_dist,
                        "surface":    "Turf",
                        "race_type":  f"Race {r_num}",
                        "venue":      "Turffontein",
                        "odds_map":   r_odds_map,
                    }
                    r_results, r_field_size = run_race_v311_turffontein(r_horses, race_context)
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
            st.session_state.field_size  = len(race_horses)
            st.session_state.processed   = True

        # ─── MAIN COLUMN GRID (Left Main Panel, Right Statistics Panel) ─────────
        results = st.session_state.get("predictions", [])
        all_results = st.session_state.get("all_results", {})
        
        col_main, col_right = st.columns([3, 1])

        with col_main:
            # 1. Dynamic Race Header Badges
            render_race_header(current_race)

            # 2. Best Bet & EV Side-by-Side Cards
            top_horse = results[0] if results else None
            top_prob_val = (top_horse.probability if hasattr(top_horse, 'probability') else top_horse.get('probability', 0)) * 100 if top_horse else 0
            top_odds_val = (top_horse.odds if hasattr(top_horse, 'odds') else top_horse.get('odds', 0)) if top_horse else 0
            top_ev_val   = (top_horse.ev if hasattr(top_horse, 'ev') else top_horse.get('ev', 0)) if top_horse else 0

            # Find matching Horse object for trainer/runs info
            top_matching = next((h for h in race_horses if (h.get("horse", "") if hasattr(h, "get") else getattr(h, "horse", "")) == (top_horse.horse if top_horse else "")), None)
            top_runs = top_matching.get("runs", 0) if hasattr(top_matching, "get") else getattr(top_matching, "runs", 0) if top_matching else 0
            top_trainer = top_horse.trainer if top_horse else "Unknown"

            col_bb, col_ev = st.columns(2)
            with col_bb:
                st.markdown(f"""
<div class="card-best-bet">
  <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:0.75rem;">
    <span style="font-size:11px; font-weight:800; text-transform:uppercase; color:var(--gold); letter-spacing:0.07em;">⭐ TOP PREDICTION</span>
    <span style="background:rgba(212,169,42,0.15); color:var(--gold); font-size:10px; font-weight:700; padding:2px 6px; border-radius:12px;">{top_prob_val:.1f}% Win Prob</span>
  </div>
  <div style="font-size:1.6rem; font-weight:900; color:#fff; font-family:'Outfit',sans-serif; margin-bottom:0.25rem;">
    #{top_horse.draw if top_horse else 0} {top_horse.horse if top_horse else "N/A"}
  </div>
  <div style="color:var(--muted-foreground); font-size:0.8rem; margin-bottom:1rem;">
     Trainer: {top_trainer} · Runs: {top_runs}
  </div>
  <div style="display:flex; gap:1.5rem; border-top:1px dashed rgba(255,255,255,0.06); padding-top:0.75rem;">
    <div>
      <div style="font-size:12px; color:var(--muted-foreground);">Odds</div>
      <div style="font-size:1.1rem; font-weight:700; color:var(--gold);">{top_odds_val:.2f}</div>
    </div>
    <div>
      <div style="font-size:12px; color:var(--muted-foreground);">Exp. Value (EV)</div>
      <div style="font-size:1.1rem; font-weight:700; color:{'var(--green-win)' if top_ev_val > 0 else 'var(--red-loss)'};">{top_ev_val:+.3f}</div>
    </div>
  </div>
</div>
""", unsafe_allow_html=True)

            with col_ev:
                # EV summary table/grid of all races
                grid_html = ""
                for r in sorted(all_races.keys()):
                    r_results = all_results.get(r, [])
                    if r_results:
                        r_top = r_results[0]
                        r_top_ev = r_top.ev if hasattr(r_top, "ev") else r_top.get("ev", 0.0)
                        bg = "rgba(34,197,94,0.15)" if r_top_ev > 0.05 else "rgba(255,255,255,0.03)"
                        border_c = "var(--green-win)" if r_top_ev > 0.05 else "var(--border)"
                        text_c = "var(--green-win)" if r_top_ev > 0.05 else "var(--muted-foreground)"
                        grid_html += f"""<div style="display:flex; flex-direction:column; align-items:center; justify-content:center; width:36px; height:36px; background:{bg}; border:1px solid {border_c}; border-radius:6px; font-size:0.7rem; font-weight:700; color:{text_c}; cursor:pointer;" title="Race {r} Top Pick EV: {r_top_ev:+.2f}">
  R{r}
  <span style="font-size:8px; font-weight:500;">{r_top_ev:+.1f}</span>
</div>"""
                    else:
                        grid_html += f"""<div style="display:flex; flex-direction:column; align-items:center; justify-content:center; width:36px; height:36px; background:rgba(255,255,255,0.01); border:1px solid var(--border); border-radius:6px; font-size:0.7rem; font-weight:700; color:rgba(255,255,255,0.15);">
  R{r}
</div>"""

                st.markdown(f"""
<div class="card-ev" style="height:100%;">
  <div>
    <div style="font-size:11px; font-weight:800; text-transform:uppercase; color:var(--muted-foreground); letter-spacing:0.07em; margin-bottom:0.5rem;">
      ⚖️ EXPECTED VALUE (EV) MEETING MATRIX
    </div>
    <div style="display:flex; flex-wrap:wrap; gap:8px;">
      {grid_html}
    </div>
  </div>
  <div style="background:rgba(245,158,11,0.07); border:1px solid rgba(245,158,11,0.2); border-radius:6px; padding:6px 10px; font-size:0.75rem; color:#f59e0b; margin-top:0.75rem;">
    ⚠ Positive EV indicates an overlay (value bet) against market forecast price.
  </div>
</div>
""", unsafe_allow_html=True)

            # 3. Custom HTML Rankings Table
            st.markdown('<div style="font-size:1.1rem; font-weight:700; color:#fff; margin:1.5rem 0 0.5rem;">🏆 Race Rankings Table</div>', unsafe_allow_html=True)

            table_rows = ""
            for p in results:
                # Rank Medal
                rank_lbl = str(p.rank)
                row_cls = ""
                if p.rank == 1:
                    rank_lbl = "🏆 1"
                    row_cls = "row-rank-1"
                elif p.rank == 2:
                    rank_lbl = "🥈 2"
                    row_cls = "row-rank-2"
                elif p.rank == 3:
                    rank_lbl = "🥉 3"
                    row_cls = "row-rank-3"

                # Form figures styling
                matching = next((h for h in race_horses if (h.get("horse", "") if hasattr(h, "get") else getattr(h, "horse", "")) == p.horse), None)
                form_figs = matching.form_figures if hasattr(matching, "form_figures") else []
                form_html = ""
                for fig in form_figs[-5:]:
                    fig_str = str(fig) if fig != 99 else "0"
                    bg_c = "var(--gold)" if fig_str == "1" else "var(--green-win)" if fig_str in ("2", "3") else "rgba(255,255,255,0.05)"
                    form_html += f'<span class="form-box" style="background:{bg_c};">{fig_str}</span>'

                if not form_html:
                    form_html = '<span style="color:var(--muted-foreground); font-size:0.75rem;">N/A</span>'

                # Win / Place Value Signal tags
                signal_tags = ""
                if p.value_bet:
                    signal_tags += '<span class="signal-tag" style="background:rgba(34,197,94,0.15); color:var(--green-win); border:1px solid rgba(34,197,94,0.3);">VALUE WIN</span> '
                if p.odds >= 10.0 and p.ev > 0.0:
                    signal_tags += '<span class="signal-tag" style="background:rgba(245,158,11,0.15); color:#f59e0b; border:1px solid rgba(245,158,11,0.3);">LONGSHOT</span> '

                weight_carried = matching.get("weight", 56.0) if hasattr(matching, "get") else getattr(matching, "weight", 56.0) if matching else 56.0

                table_rows += f"""<tr class="{row_cls}">
  <td style="font-weight:700;">{rank_lbl}</td>
  <td>#{p.draw}</td>
  <td>
    <div style="font-weight:700; color:#fff; font-size:0.92rem;">{p.horse}</div>
    <div style="font-size:0.75rem; color:var(--muted-foreground);">{p.trainer}</div>
  </td>
  <td>{p.jockey}</td>
  <td>{weight_carried:.1f} kg</td>
  <td>{form_html}</td>
  <td style="font-family:'JetBrains Mono',monospace; font-weight:700; color:var(--gold);">{p.odds:.2f}</td>
  <td style="font-family:'JetBrains Mono',monospace; font-weight:700;">{p.probability * 100:.1f}%</td>
  <td style="font-family:'JetBrains Mono',monospace; font-weight:700; color:{'var(--green-win)' if p.ev > 0 else 'var(--red-loss)'};">{p.ev:+.3f}</td>
  <td>{signal_tags}</td>
</tr>"""

            st.markdown(f"""
<table class="data-table-v313">
  <thead>
    <tr>
      <th style="width:60px;">RNK</th>
      <th style="width:50px;">DR</th>
      <th>HORSE / TRAINER</th>
      <th>JOCKEY</th>
      <th style="width:70px;">WGT</th>
      <th>FORM (RECENT)</th>
      <th style="width:65px;">ODDS</th>
      <th style="width:75px;">PROB</th>
      <th style="width:75px;">EV</th>
      <th>SIGNALS</th>
    </tr>
  </thead>
  <tbody>
    {table_rows}
  </tbody>
</table>
""", unsafe_allow_html=True)

            # Monospace string tables for copy/paste
            races_meta_dict = st.session_state.get("races_meta", {})
            curr_meta_data  = races_meta_dict.get(current_race, {})
            curr_race_time  = curr_meta_data.get("race_time", "")
            raw_dist        = curr_meta_data.get("distance", "")
            curr_race_dist  = str(raw_dist).replace("m", "").strip() if raw_dist else str(st.session_state.get("distance_selector", 1200))
            curr_race_class = st.session_state.get("race_class_selector", "Stakes")

            with st.expander("📋 Copyable Plain-Text Tables"):
                table_str = generate_v311_table_string(
                    results=results,
                    race_num=current_race,
                    race_time=curr_race_time if curr_race_time else "12:00",
                    distance=curr_race_dist,
                    field_size=st.session_state.get("field_size", len(results)),
                    race_type=curr_race_class,
                    race_horses=race_horses,
                )
                st.code(table_str, language="text")

                st.markdown("### ⭐ Value Bets & Longshot Summary")
                st.code(generate_value_bets_block(all_results), language="text")
                st.code(generate_longshots_block(all_results), language="text")

            # Exotics Intelligence Section
            try:
                render_exotics_intelligence(results, all_results, current_race)
                from predictor import Prediction as _Pred
                pred_objs = [p for p in results if isinstance(p, _Pred)]
                if pred_objs:
                    render_model_debug(pred_objs)
            except Exception as e:
                logger.exception("Error rendering exotics intelligence: %s", e)

        with col_right:
            # 1. Circular SVG Confidence Gauges
            # Calculate average EV / confidence
            avg_ev = sum(p.ev for p in results) / len(results) if results else 0
            all_r_evs = [p_item.ev for r_k, r_list in all_results.items() for p_item in r_list]
            meeting_avg_ev = sum(all_r_evs) / len(all_r_evs) if all_r_evs else 0

            # SVG Circle strokes (dashoffset = 220 - (220 * pct / 100))
            this_race_pct = min(max(int((top_prob_val / 50.0) * 100), 0), 100) # Norm relative to a 50% max win prob
            meet_avg_pct  = min(max(int((meeting_avg_ev + 0.15) / 0.3 * 100), 0), 100) # Norm EV -0.15 to +0.15 as 0 to 100%

            offset_race = 220 - (220 * this_race_pct / 100)
            offset_meet = 220 - (220 * meet_avg_pct / 100)

            st.markdown(f"""
            <div style="background:var(--card); border:1px solid var(--border); border-radius:12px; padding:1rem; margin-bottom:1rem; text-align:center;">
              <div style="font-size:10px; font-weight:800; color:var(--muted-foreground); letter-spacing:0.07em; text-transform:uppercase; margin-bottom:0.75rem;">
                🎯 CONFIDENCE INDEX
              </div>
              <div style="display:flex; justify-content:space-around; align-items:center;">
                <div>
                  <svg viewBox="0 0 36 36" class="circular-chart" style="stroke:var(--gold);">
                    <path class="circle-bg" d="M18 2.0845 a 15.9155 15.9155 0 0 1 0 31.831 a 15.9155 15.9155 0 0 1 0 -31.831" />
                    <path class="circle" stroke-dasharray="{this_race_pct}, 100" d="M18 2.0845 a 15.9155 15.9155 0 0 1 0 31.831 a 15.9155 15.9155 0 0 1 0 -31.831" />
                    <text x="18" y="20.3" class="percentage">{top_prob_val:.0f}%</text>
                  </svg>
                  <div style="font-size:9px; font-weight:700; color:var(--muted-foreground); text-transform:uppercase;">This Race</div>
                </div>
                <div>
                  <svg viewBox="0 0 36 36" class="circular-chart" style="stroke:var(--green-win);">
                    <path class="circle-bg" d="M18 2.0845 a 15.9155 15.9155 0 0 1 0 31.831 a 15.9155 15.9155 0 0 1 0 -31.831" />
                    <path class="circle" stroke-dasharray="{meet_avg_pct}, 100" d="M18 2.0845 a 15.9155 15.9155 0 0 1 0 31.831 a 15.9155 15.9155 0 0 1 0 -31.831" />
                    <text x="18" y="20.3" class="percentage">{meeting_avg_ev:+.2f}</text>
                  </svg>
                  <div style="font-size:9px; font-weight:700; color:var(--muted-foreground); text-transform:uppercase;">Meeting EV</div>
                </div>
              </div>
            </div>
            """, unsafe_allow_html=True)

            # 2. Value Bets List Panel
            v_bets_all = []
            for r_k in sorted(all_results.keys()):
                for pred_item in all_results[r_k]:
                    if pred_item.value_bet:
                        v_bets_all.append((r_k, pred_item))

            vb_items = []
            for r_k, vb in v_bets_all:
                vb_items.append(
                    f'<div style="display:flex; justify-content:space-between; align-items:center; background:rgba(34,197,94,0.04); border:1px solid rgba(34,197,94,0.15); border-radius:6px; padding:8px 10px; font-size:0.8rem; color:var(--foreground);">'
                    f'<div><span style="font-weight:900; color:var(--green-win); margin-right:4px;">R{r_k}</span><span style="font-weight:700;">#{vb.draw} {vb.horse}</span></div>'
                    f'<div style="text-align:right;"><div style="font-weight:700; color:var(--gold);">{vb.odds:.2f}</div><div style="font-size:9px; color:var(--green-win); font-family:\'JetBrains Mono\',monospace;">{vb.ev:+.2f} EV</div></div>'
                    f'</div>'
                )

            if not vb_items:
                vb_content = '<div style="color:var(--muted-foreground); font-size:0.8rem; text-align:center; padding:1rem;">No value bets detected yet. Generate predictions to find value opportunities.</div>'
            else:
                vb_content = "".join(vb_items)

            vb_panel_html = (
                f'<div style="background:var(--card); border:1px solid var(--border); border-radius:12px; padding:1.25rem; margin-bottom:1rem;">'
                f'<div style="font-size:10px; font-weight:800; color:var(--muted-foreground); letter-spacing:0.07em; text-transform:uppercase; margin-bottom:0.75rem;">⭐ DETECTED VALUE BETS</div>'
                f'<div style="display:flex; flex-direction:column; gap:8px;">{vb_content}</div>'
                f'</div>'
            )
            st.markdown(vb_panel_html, unsafe_allow_html=True)

            # 3. Permutations / Meeting Stats Summary Card
            total_races_run = len(all_results)
            tot_value_bets = len(v_bets_all)
            ev_color_class = "var(--green-win)" if meeting_avg_ev > 0 else "var(--red-loss)"
            summary_panel_html = (
                f'<div style="background:var(--card); border:1px solid var(--border); border-radius:12px; padding:1.25rem;">'
                f'<div style="font-size:10px; font-weight:800; color:var(--muted-foreground); letter-spacing:0.07em; text-transform:uppercase; margin-bottom:0.75rem;">📊 MEETING STATS SUMMARY</div>'
                f'<div style="display:flex; flex-direction:column; gap:8px; font-size:0.82rem;">'
                f'<div style="display:flex; justify-content:space-between;"><span style="color:var(--muted-foreground);">Total Races Analyzed</span><span style="font-weight:700; color:#fff;">{total_races_run} of 8</span></div>'
                f'<div style="display:flex; justify-content:space-between;"><span style="color:var(--muted-foreground);">Total Value Bets Detected</span><span style="font-weight:700; color:var(--green-win);">{tot_value_bets}</span></div>'
                f'<div style="display:flex; justify-content:space-between;"><span style="color:var(--muted-foreground);">Meeting Avg Expected Value</span><span style="font-weight:700; color:{ev_color_class};">{meeting_avg_ev:+.3f}</span></div>'
                f'</div>'
                f'</div>'
            )
            st.markdown(summary_panel_html, unsafe_allow_html=True)


if __name__ == "__main__":
    main()
