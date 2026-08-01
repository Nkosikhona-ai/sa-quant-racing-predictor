"""
predictor.py — Quantitative Racing Prediction Engine v3.9
============================================================
Includes:
- v3.9 7-Track Adaptive Engine (modular track-specific logic)
- v4.2 ML Calibration (Gradient Boosting Model + Isotonic Calibration)
- v3.8 Legacy Rule-Based composite scoring

Pipeline:
  1. Parse track, surface, distance, race_class, and model_mode.
  2. Compute probability distribution based on the chosen mode.
  3. Apply market signal caps & floors (if odds are available).
  4. Calculate EV = prob * (odds - 1) - (1 - prob).
  5. Identify value bets, confidence, and longshot opportunities.
  6. Rank and return prediction objects.
"""

from __future__ import annotations

import os
import re
import logging
import numpy as np
from dataclasses import dataclass, field
from typing import Optional, List, Dict

logger = logging.getLogger(__name__)

MODEL_PATH = os.path.join(os.path.dirname(__file__), "calibration_model_v42.pkl")

# ─── Reference Constants ──────────────────────────────────────────────────────
BASE_WEIGHT = 56.0
WEIGHT_PENALTY = 0.004  # per 0.5 kg
MAX_RATING = 130.0

# ─── Draw Bias Table (v3.8 Reference) ─────────────────────────────────────────
DRAW_BIAS_V38 = {
    1:  1.06, 2:  1.04, 3:  1.02, 4:  1.00, 5:  1.00,
    6:  0.99, 7:  0.97, 8:  0.95, 9:  0.93, 10: 0.91,
    11: 0.90, 12: 0.88, 13: 0.87, 14: 0.85, 15: 0.84,
    16: 0.83,
}

# ─── Jockey Win-Rates (SA 2024/25 Season Baseline) ───────────────────────────
JOCKEY_WIN_RATE = {
    "W. Marwing":      0.282,
    "R. Fourie":       0.261,
    "K. de Melo":      0.244,
    "L. Hewitson":     0.238,
    "B. Fayd'herbe":   0.221,
    "G. Lerena":       0.218,
    "C. Murray":       0.198,
    "A. Fortune":      0.185,
    "F. Schoeman":     0.179,
    "A. Marcus":       0.168,
    "M. Yeni":         0.154,
    "C. Maujean":      0.148,
    "K. Nkosi":        0.143,
    "P. Strydom":      0.138,
    "W. Mapelo":       0.134,
    "T. Drier":        0.125,
}
JOCKEY_DEFAULT_RATE = 0.14

# ─── Trainer Win-Rates ────────────────────────────────────────────────────────
TRAINER_WIN_RATE = {
    "S. Tarry":         0.298,
    "M. de Kock":       0.271,
    "J. Snaith":        0.248,
    "D. Kannemeyer":    0.231,
    "G. Azzie":         0.218,
    "J. van Zyl":       0.208,
    "C. Laird":         0.195,
    "J. Ramsden":       0.182,
    "J. de Beer":       0.175,
    "P. Matchett":      0.168,
    "A. Laird":         0.162,
    "M. Roberts":       0.155,
    "G. Kotzen":        0.148,
    "A. Drier":         0.141,
    "P. Strydom":       0.135,
}
TRAINER_DEFAULT_RATE = 0.14

# ─── Jockey Track-Specific Boosts (v3.9) ──────────────────────────────────────
JOCKEY_TRACK_BOOSTS = {
    "R. Fourie": {
        "greyville": 0.05,
        "kenilworth": 0.04,
        "durbanville": 0.04,
        "fairview": 0.03,
        "scottsville": 0.03,
        "turffontein": 0.02,
        "vaal": 0.02,
    },
    "W. Marwing": {
        "turffontein": 0.05,
        "vaal": 0.04,
        "greyville": 0.02,
        "scottsville": 0.02,
    },
    "G. Lerena": {
        "turffontein": 0.05,
        "vaal": 0.05,
        "greyville": 0.02,
    },
    "K. de Melo": {
        "greyville": 0.05,
        "scottsville": 0.04,
        "kenilworth": 0.03,
        "durbanville": 0.03,
    },
    "A. Marcus": {
        "kenilworth": 0.05,
        "durbanville": 0.05,
    },
    "B. Fayd'herbe": {
        "kenilworth": 0.04,
        "durbanville": 0.04,
        "greyville": 0.02,
    },
    "M. Yeni": {
        "fairview": 0.05,
        "vaal": 0.04,
        "turffontein": 0.03,
        "greyville": 0.03,
    },
    "L. Hewitson": {
        "turffontein": 0.04,
        "vaal": 0.04,
        "greyville": 0.03,
        "kenilworth": 0.02,
    }
}

# ─── Trainer Track-Specific Boosts (v3.9) ─────────────────────────────────────
TRAINER_TRACK_BOOSTS = {
    "S. Tarry": {
        "turffontein": 0.05,
        "vaal": 0.05,
        "greyville": 0.03,
    },
    "M. de Kock": {
        "turffontein": 0.05,
        "vaal": 0.04,
        "greyville": 0.04,
    },
    "J. Snaith": {
        "kenilworth": 0.06,
        "durbanville": 0.06,
        "greyville": 0.02,
    },
    "D. Kannemeyer": {
        "kenilworth": 0.04,
        "greyville": 0.04,
        "durbanville": 0.03,
    },
    "C. Laird": {
        "turffontein": 0.04,
        "greyville": 0.03,
    },
    "J. van Zyl": {
        "turffontein": 0.04,
        "vaal": 0.03,
    },
    "G. Kotzen": {
        "kenilworth": 0.03,
        "durbanville": 0.03,
        "fairview": 0.04,
        "greyville": 0.03,
    },
    "A. Wright": {
        "greyville": 0.05,
        "scottsville": 0.04,
    }
}

# ─── Data Classes ─────────────────────────────────────────────────────────────

@dataclass
class Horse:
    horse: str
    draw: int
    saddle: int
    weight: float
    jockey: str
    trainer: str
    forecast_odds: float
    form_string: str
    runs: int
    wins: int
    third_places: int
    f3_pct: int
    merit_rating: Optional[int]
    course_runs: int
    horse_gear: str
    first_timer: bool
    running_comment: str
    comment_history: list[str] = field(default_factory=list)

    @property
    def form_figures(self) -> list[int]:
        """Return list of finish positions from form string, most recent last."""
        figures = []
        for ch in re.split(r"[-/\s]", self.form_string):
            ch = ch.strip()
            if ch.isdigit():
                figures.append(int(ch))
            elif ch.upper() in ("W", "1"):
                figures.append(1)
            elif ch.upper() in ("U", "F", "P", "R", "0"):
                figures.append(99)
        return figures[-6:]

    @property
    def recent_form_score(self) -> float:
        """Exponentially weighted recent form: lower finish = better score."""
        figs = self.form_figures
        if not figs:
            return 50.0
        weights = [0.4 ** (len(figs) - 1 - i) for i in range(len(figs))]
        total_w = sum(weights)
        weighted = sum((1 / max(f, 1)) * w for f, w in zip(figs, weights))
        raw = weighted / total_w * 100
        return min(max(raw, 0), 100)


@dataclass
class Prediction:
    rank:        int
    horse:       str
    draw:        int
    jockey:      str
    trainer:     str
    odds:        float
    probability: float          # 0–1
    ev:          float          # expected value
    rule_score:  float          # raw composite score
    confidence:  str            # "High" / "Medium" / "Low"
    value_bet:   bool
    longshot:    bool = False
    features:    list[float] = field(default_factory=list, repr=False)

    @property
    def prob_pct(self) -> str:
        return f"{self.probability * 100:.1f}%"

    @property
    def ev_str(self) -> str:
        sign = "+" if self.ev >= 0 else ""
        return f"{sign}{self.ev:.3f}"

    @property
    def implied_prob(self) -> float:
        if self.odds and self.odds > 1:
            return 1 / self.odds
        return 0.0

    @property
    def edge(self) -> float:
        return self.probability - self.implied_prob


# ─── Helper Functions ─────────────────────────────────────────────────────────

def clean_name_string(name: str) -> str:
    """Strip apprentice markers and parentheses from jockey/trainer names."""
    name = name.replace("*", "")
    name = re.sub(r"\(.*?\)", "", name)
    return name.strip()


# ─── Rule Score v3.8 ──────────────────────────────────────────────────────────

def rule_score_v38(
    draw_bias:    float,
    form_score:   float,
    jockey_wr:    float,
    trainer_wr:   float,
    weight_pen:   float,
    rating_norm:  float,
) -> float:
    WEIGHTS = {
        "form":    0.30,
        "rating":  0.22,
        "jockey":  0.18,
        "trainer": 0.12,
        "draw":    0.10,
        "weight":  0.08,
    }
    score = (
        WEIGHTS["form"]    * form_score
      + WEIGHTS["rating"]  * rating_norm
      + WEIGHTS["jockey"]  * (jockey_wr / 0.30)
      + WEIGHTS["trainer"] * (trainer_wr / 0.30)
      + WEIGHTS["draw"]    * draw_bias
      + WEIGHTS["weight"]  * weight_pen
    )
    return float(np.clip(score, 0.0, 1.0))


# ─── Feature Engineering (Legacy / ML Compatibility) ──────────────────────────

def build_features(horse, field_size: int) -> list[float]:
    """Build 12-feature vector for compatibility with v4.2 ML model."""
    draw    = max(1, min(horse.draw, 16))
    figs    = horse.form_figures
    runs    = max(horse.runs, 1)

    db = DRAW_BIAS_V38.get(draw, 0.83)
    form_score = horse.recent_form_score / 100.0
    jwr = JOCKEY_WIN_RATE.get(clean_name_string(horse.jockey), JOCKEY_DEFAULT_RATE)
    twr = TRAINER_WIN_RATE.get(clean_name_string(horse.trainer), TRAINER_DEFAULT_RATE)

    excess = max(0.0, horse.weight - BASE_WEIGHT) / 0.5
    wt_pen = 1.0 - (excess * WEIGHT_PENALTY)
    wt_pen = max(0.8, wt_pen)

    mr = horse.merit_rating
    rat_norm = min(mr, MAX_RATING) / MAX_RATING if mr is not None and mr > 0 else 0.5
    exp_norm = np.log1p(runs) / np.log1p(100)
    fs_norm = 1.0 / max(field_size, 1)
    has_form = 1.0 if figs else 0.0

    wins_in_form  = sum(1 for f in figs if f == 1)
    win_rate_form = wins_in_form / max(len(figs), 1)

    top3_in_form  = sum(1 for f in figs if 1 <= f <= 3)
    top3_rate     = top3_in_form / max(len(figs), 1)

    comp = rule_score_v38(db, form_score, jwr, twr, wt_pen, rat_norm)

    return [
        db, form_score, jwr, twr, wt_pen, rat_norm,
        exp_norm, fs_norm, has_form, win_rate_form, top3_rate, comp,
    ]


# ─── Model Loader (ML Calibration Support) ────────────────────────────────────

_CACHED_MODEL = None

def _load_model():
    global _CACHED_MODEL
    if _CACHED_MODEL is not None:
        return _CACHED_MODEL
    if os.path.exists(MODEL_PATH):
        try:
            import joblib
            _CACHED_MODEL = joblib.load(MODEL_PATH)
            logger.info("Loaded calibration model from %s", MODEL_PATH)
            return _CACHED_MODEL
        except Exception as e:
            logger.warning("Failed to load model: %s", e)
    return None


# ─── Softmax Normalisation ────────────────────────────────────────────────────

def _softmax(scores: list[float], temperature: float = 1.2) -> np.ndarray:
    arr = np.array(scores, dtype=float)
    arr = arr / temperature
    arr = arr - arr.max()
    exp = np.exp(arr)
    return exp / exp.sum()


# ─── EV Calculation ───────────────────────────────────────────────────────────

def calc_ev(probability: float, odds: float) -> float:
    if odds <= 1.0:
        return -1.0
    return probability * (odds - 1.0) - (1.0 - probability)


# ─── Confidence Label ─────────────────────────────────────────────────────────

def _confidence_label(prob: float, ev: float) -> str:
    if prob >= 0.30 and ev >= 0.10:
        return "High"
    elif prob >= 0.18 and ev >= 0.00:
        return "Medium"
    return "Low"


# ─── Track-Specific Draw Bias (v3.9 Distance-Aware) ──────────────────────────

def get_draw_bias(venue: str, surface: str, distance: float, draw: int) -> float:
    bias = 1.0
    v_lower = venue.lower()
    s_lower = surface.lower()
    
    if v_lower == "greyville":
        if s_lower == "polytrack":
            # Polytrack: strong low draw bias at short/middle distances
            if distance <= 1400:
                if draw <= 3: bias = 1.06
                elif draw >= 8: bias = 0.92
            elif distance <= 1800:
                if draw <= 3: bias = 1.04
                elif draw >= 9: bias = 0.94
        else:  # Turf
            if distance <= 1200:
                if draw <= 3: bias = 1.05
                elif draw >= 9: bias = 0.93
            elif distance >= 1600:
                bias = 1.00
    elif v_lower == "turffontein":
        if distance > 1200:
            if draw <= 4: bias = 1.05
            elif draw >= 10: bias = 0.91
    elif v_lower == "kenilworth":
        if distance <= 1200:
            if draw >= 10: bias = 1.04
            elif draw <= 3: bias = 0.97
        else:
            if draw <= 4: bias = 1.04
            elif draw >= 10: bias = 0.92
    elif v_lower == "durbanville":
        if draw <= 3: bias = 1.07
        elif draw >= 8: bias = 0.90
    elif v_lower == "fairview":
        if distance > 1200:
            if draw <= 4: bias = 1.04
            elif draw >= 9: bias = 0.92
    elif v_lower == "scottsville":
        if distance <= 1200:
            if draw >= 8: bias = 1.04
            elif draw <= 3: bias = 0.96
    elif v_lower == "vaal":
        if distance <= 1400:
            if draw >= 10: bias = 1.03
            elif draw <= 3: bias = 0.97
            
    return bias


# ─── v3.9 Adaptive Core Logic ─────────────────────────────────────────────────

def calculate_v39_score(horse, venue: str, surface: str, distance: float, race_class: str) -> float:
    is_first_timer = horse.first_timer
    
    # 2. Apprentice allowance detection
    jockey_name = horse.jockey or "Unknown"
    is_apprentice = False
    allowance = 0.0
    if "*" in jockey_name or "(a)" in jockey_name.lower() or "app" in jockey_name.lower():
        is_apprentice = True
        allowance = 2.5
    allowance_match = re.search(r"\((\d+(?:\.\d+)?)\)", jockey_name)
    if allowance_match:
        is_apprentice = True
        allowance = float(allowance_match.group(1))
        
    effective_weight = horse.weight - allowance
    excess = max(0.0, effective_weight - BASE_WEIGHT) / 0.5
    weight_pen = 1.0 - (excess * WEIGHT_PENALTY)
    weight_pen = max(0.8, weight_pen)
    
    # 3. Form and Rating baseline
    if is_first_timer:
        form_score = 0.50
        mr = horse.merit_rating
        rating_val = mr if mr is not None and mr > 0 else 72
    else:
        form_score = horse.recent_form_score / 100.0
        mr = horse.merit_rating
        rating_val = mr if mr is not None and mr > 0 else 70
        
    rating_norm = min(rating_val, MAX_RATING) / MAX_RATING
    
    # Win rates
    jwr = JOCKEY_WIN_RATE.get(clean_name_string(jockey_name), JOCKEY_DEFAULT_RATE)
    twr = TRAINER_WIN_RATE.get(clean_name_string(horse.trainer), TRAINER_DEFAULT_RATE)
    
    # Composite baseline
    score = (
        0.30 * form_score
      + 0.22 * rating_norm
      + 0.18 * (jwr / 0.30)
      + 0.12 * (twr / 0.30)
      + 0.08 * weight_pen
    )
    
    # 4. Draw Bias
    db = get_draw_bias(venue, surface, distance, horse.draw)
    score += 0.10 * db
    
    # 5. Jockey and Trainer track boosts
    j_tb = JOCKEY_TRACK_BOOSTS.get(clean_name_string(jockey_name), {}).get(venue.lower(), 0.0)
    t_tb = TRAINER_TRACK_BOOSTS.get(clean_name_string(horse.trainer), {}).get(venue.lower(), 0.0)
    score += j_tb + t_tb
    
    # 6. Greyville Polytrack specialist logic
    if venue.lower() == "greyville" and surface.lower() == "polytrack":
        name_lower = horse.horse.lower()
        if "poly" in name_lower or "durban" in name_lower or "zulu" in name_lower or "standard" in name_lower:
            score += 0.06
        if clean_name_string(horse.trainer) in ["A. Wright", "G. Kotzen", "S. Tarry"] or clean_name_string(jockey_name) in ["K. Nkosi", "T. Drier", "R. Fourie"]:
            score += 0.02
            
    # 7. Veteran bonus scaled by form
    if horse.runs >= 15:
        score += 0.05 * form_score
        
    # 8. Post-race distress penalty
    figs = horse.form_figures
    if figs:
        last_run = figs[-1]
        if last_run == 99 or last_run > 8:
            score -= 0.06
            
    # 9. Second-place adjustment
    if figs:
        second_places = sum(1 for f in figs if f == 2)
        if figs[-1] == 2:
            score += 0.02
        if second_places >= 2:
            score -= 0.03
            
    # 10. First-timer calibration adjustment
    if is_first_timer:
        score += 0.02
        
    return float(np.clip(score, 0.0, 1.0))


# ─── Main Predict Function ────────────────────────────────────────────────────

def predict(
    horses: list,
    odds_map: Optional[dict] = None,
    venue: str = "Turffontein",
    surface: str = "Turf",
    distance: int = 1400,
    race_class: str = "Grade 1",
    model_mode: str = "7-Track Adaptive (v3.9)"
) -> list[Prediction]:
    """
    Run prediction pipeline based on the selected mode.

    Args:
        horses:      List of Horse objects from extractor.
        odds_map:    Dict {horse_name: decimal_odds}.
        venue:       Name of the track/venue.
        surface:     Turf / Polytrack.
        distance:    Distance in meters.
        race_class:  Race category/handicap grade.
        model_mode:  "7-Track Adaptive (v3.9)" | "ML Calibrated (v4.2)" | "Legacy Rule (v3.8)".
    """
    if not horses:
        return []

    if "v3.13" in model_mode:
        predictions, _ = run_race_v313_greyville(horses, {
            "venue": venue,
            "surface": surface,
            "distance": distance,
            "race_class": race_class,
            "odds_map": odds_map
        })
        return predictions

    odds_map = odds_map or {}
    field_size = len(horses)
    model = _load_model()
    
    # ── 1. Calculate raw scores and feature matrix
    feature_matrix = []
    legacy_rule_scores = []
    v39_scores = []
    
    for h in horses:
        feats = build_features(h, field_size)
        feature_matrix.append(feats)
        legacy_rule_scores.append(feats[11])
        
        v39_s = calculate_v39_score(h, venue, surface, distance, race_class)
        v39_scores.append(v39_s)

    # ── 2. Probability estimation based on mode
    if model_mode == "ML Calibrated (v4.2)" and model is not None:
        try:
            X = np.array(feature_matrix, dtype=float)
            raw_probs = model.predict_proba(X)
            if raw_probs.ndim == 2 and raw_probs.shape[1] >= 2:
                win_probs = raw_probs[:, 1].tolist()
            else:
                win_probs = raw_probs[:, 0].tolist()
            total = sum(win_probs)
            probs = [p / total for p in win_probs] if total > 0 else _softmax(legacy_rule_scores).tolist()
            logger.info("Using v4.2 ML calibration model")
        except Exception as e:
            logger.warning("ML Calibration failed, falling back to v3.9: %s", e)
            probs = _softmax(v39_scores).tolist()
    elif model_mode == "Legacy Rule (v3.8)":
        probs = _softmax(legacy_rule_scores).tolist()
        logger.info("Using v3.8 legacy rule-based probabilities")
    else:
        # Default to v3.9
        probs = _softmax(v39_scores).tolist()
        logger.info("Using v3.9 7-Track Adaptive probabilities")

    # ── 3. Market signal caps & floors
    has_market_odds = False
    temp_probs = list(probs)
    resolved_odds = {}
    
    for i, h in enumerate(horses):
        if odds_map and h.horse in odds_map and odds_map[h.horse] > 1.0:
            odds = float(odds_map[h.horse])
        elif h.forecast_odds and h.forecast_odds > 1.0:
            odds = float(h.forecast_odds)
        else:
            odds = round(1.0 / max(probs[i], 0.01), 2)
        resolved_odds[h.horse] = odds
        
        # Apply market caps/floors for v3.9 only
        if model_mode == "7-Track Adaptive (v3.9)" and odds > 1.0:
            has_market_odds = True
            implied_prob = 1.0 / odds
            capped_prob = min(max(probs[i], implied_prob * 0.35), implied_prob * 2.2)
            temp_probs[i] = capped_prob
            
    if has_market_odds and model_mode == "7-Track Adaptive (v3.9)":
        total_p = sum(temp_probs)
        if total_p > 0:
            probs = [p / total_p for p in temp_probs]

    # ── 4. Build prediction objects
    predictions: list[Prediction] = []
    
    for i, h in enumerate(horses):
        prob = probs[i]
        odds = resolved_odds[h.horse]
        ev = calc_ev(prob, odds)
        conf = _confidence_label(prob, ev)
        val_bet = ev > 0.05 and conf in ("High", "Medium")
        
        rs_rep = v39_scores[i] if model_mode == "7-Track Adaptive (v3.9)" else legacy_rule_scores[i]
        
        feats_rep = feature_matrix[i]
        if model_mode == "7-Track Adaptive (v3.9)":
            feats_rep = list(feature_matrix[i])
            feats_rep[11] = v39_scores[i]

        predictions.append(Prediction(
            rank        = 0,
            horse       = h.horse,
            draw        = h.draw,
            jockey      = h.jockey,
            trainer     = h.trainer,
            odds        = odds,
            probability = round(prob, 4),
            ev          = round(ev, 4),
            rule_score  = round(rs_rep, 4),
            confidence  = conf,
            value_bet   = val_bet,
            features    = [round(f, 4) for f in feats_rep],
        ))

    # ── 5. Sort by probability descending
    predictions.sort(key=lambda p: p.probability, reverse=True)
    for rank, pred in enumerate(predictions, start=1):
        pred.rank = rank

    # ── 6. Longshot detection (requires rank to be resolved)
    for pred in predictions:
        if pred.odds >= 11.0 and pred.ev > 0.0 and pred.rank <= 4:
            pred.longshot = True

    return predictions


# ═══════════════════════════════════════════════════════════════════════════════
# ─── v3.11 Turffontein Engine ─────────────────────────────────────────────────
# ═══════════════════════════════════════════════════════════════════════════════

# ============================================================
# BASIC HELPERS
# ============================================================

def extract_positions(form_string):
    if not form_string:
        return []
    nums = re.findall(r'\d+', str(form_string))
    return [int(n) for n in nums]


def score_form(form_string):
    positions = extract_positions(form_string)
    if not positions:
        return 0.30

    recent = positions[-5:]

    def score(p):
        if p == 1:   return 1.0
        elif p == 2: return 0.85
        elif p == 3: return 0.70
        elif p <= 5: return 0.55
        elif p <= 8: return 0.35
        return 0.20

    return sum(score(p) for p in recent) / len(recent)


def compute_momentum(form_string):
    positions = extract_positions(form_string)
    if len(positions) < 3:
        return 0.0

    last3 = positions[-3:]
    return sum(1 for p in last3 if p <= 3) / 3


def draw_bias(draw):
    if draw in [7, 9]:
        return 1.15
    elif draw <= 3:
        return 1.05
    elif draw >= 10:
        return 0.90
    return 1.0


def parse_odds(o):
    try:
        return float(o)
    except Exception:
        return 10.0


# ============================================================
# FULL V3.11 TURFFONTEIN ENGINE
# ============================================================

# --- Elite boosts & helpers for v3.11 engine ---
TRAINER_ELITE_BOOST_TFV311 = {
    "M/M de Kock": 1.17,
    "S. Tarry": 1.15,
    "M. de Kock": 1.17,
    "J. Snaith": 1.12,
    "M. G. Azzie": 1.10,
    "G. Azzie": 1.10,
    "M G Azzie": 1.10,
}
JOCKEY_ELITE_BOOST_TFV311 = {
    "G. Lerena": 1.21,
    "R. Fourie": 1.25,
    "K. de Melo": 1.20,
    "L. Hewitson": 1.18,
    "C. Murray": 1.15,
    "G Lerena": 1.21,
    "R Fourie": 1.25,
    "K de Melo": 1.20,
    "L Hewitson": 1.18,
    "C Murray": 1.15,
}

def compute_draw_bias_turffontein_v311(draw, distance, field_size):
    # Turffontein draw bias: middle/inner draws are favored. Draw 7/9 gets 1.18.
    if draw in (7, 9):
        return 1.18
    elif draw <= 3:
        return 1.10
    elif draw <= 6:
        return 1.05
    elif draw >= 10:
        return 0.90
    return 1.0

def compute_apprentice_multiplier(jockey):
    if jockey and "*" in str(jockey):
        return 1.04
    return 1.0

def compute_maiden_juvenile_boost(race_type, first_timer):
    if "maiden juvenile" in str(race_type).lower() and first_timer:
        return 1.12
    return 1.0

def compute_mr_advantage(horse_mr, base_mr=70):
    if horse_mr is None:
        return 0.0
    return max(0.0, (float(horse_mr) - base_mr) * 0.01)

def compute_weight_advantage(avg_weight, weight):
    return max(0.0, (avg_weight - weight) * 0.02)


def compute_probability_v311_turffontein(horse, context):
    """
    Score a single horse (passed as a plain dict).
    """
    form_string = horse.get("form_string", "")
    odds = parse_odds(horse.get("forecast_odds", 10.0))
    draw = int(horse.get("draw", 5))
    weight = float(horse.get("weight", 56.0))
    jockey = horse.get("jockey", "")
    trainer = horse.get("trainer", "")
    runs = int(horse.get("runs", 0))
    first_timer = bool(horse.get("first_timer", False))
    horse_mr = horse.get("merit_rating")

    # component scores
    form_score = score_form(form_string)
    momentum_score = compute_momentum(form_string)
    
    # 2. Market signal
    market_signal = 1.0 / odds if odds > 0.0 else 0.10
    
    # 3. MR advantage
    mr_adv = compute_mr_advantage(horse_mr, 70.0)
    
    # 4. Weight advantage
    avg_weight = context.get("avg_weight", 56.0)
    wgt_adv = compute_weight_advantage(avg_weight, weight)
    
    # 5. Trainer & Jockey boosts
    trainer_boost = TRAINER_ELITE_BOOST_TFV311.get(trainer, 1.0)
    jockey_boost = JOCKEY_ELITE_BOOST_TFV311.get(jockey, 1.0)
    
    # 6. Draw bias
    distance = context.get("distance", 1000)
    field_size = context.get("field_size", 14)
    draw_bias = compute_draw_bias_turffontein_v311(draw, distance, field_size)
    
    # 7. Apprentice multiplier
    apprentice_mult = compute_apprentice_multiplier(jockey)
    
    # 8. Maiden Juvenile specialist boost
    race_type = context.get("race_type", "")
    maiden_boost = compute_maiden_juvenile_boost(race_type, first_timer)
    
    # Combine with weights
    raw_score = (
        (form_score * 0.09) + 
        (momentum_score * 0.07) + 
        market_signal + 
        mr_adv + 
        wgt_adv
    )
    
    # Apply multipliers
    final_score = raw_score * draw_bias * trainer_boost * jockey_boost * apprentice_mult * maiden_boost
    
    return max(final_score, 0.0001)


def run_race_v311_turffontein(
    horses:       list,
    race_context: dict,
) -> tuple[list[Prediction], int]:
    if not horses:
        return [], 0

    odds_map   = race_context.get("odds_map", {}) or {}
    horse_dicts: list[dict] = []

    for h in horses:
        if isinstance(h, dict):
            hd = h.copy()
        else:
            hd = {
                "horse":        getattr(h, "horse",        "Unknown"),
                "draw":         getattr(h, "draw",          0),
                "weight":       getattr(h, "weight",        56.0),
                "forecast_odds": getattr(h, "forecast_odds", 10.0),
                "form_string":  getattr(h, "form_string",  ""),
                "jockey":       getattr(h, "jockey",       "Unknown"),
                "trainer":      getattr(h, "trainer",      "Unknown"),
                "first_timer":   getattr(h, "first_timer",   False),
                "merit_rating":  getattr(h, "merit_rating",  None),
                "runs":          getattr(h, "runs",          0),
            }

        name = hd.get("horse", "")
        if name in odds_map and float(odds_map[name] or 0) > 1.0:
            hd["forecast_odds"] = float(odds_map[name])

        horse_dicts.append(hd)

    # ── Run core engine ───────────────────────────────────────────────────────
    active = [h for h in horse_dicts if h]
    if not active:
        return [], 0

    field_size = len(active)
    avg_weight = sum(h.get("weight", 56.0) for h in active) / field_size
    
    context = dict(race_context)
    context["avg_weight"] = avg_weight
    context["field_size"] = field_size

    results = []
    # Score each horse
    for h in active:
        final_score = compute_probability_v311_turffontein(h, context)
        results.append({
            "horse":         h.get("horse",        "Unknown"),
            "draw":          h.get("draw",          0),
            "weight":        h.get("weight",        56.0),
            "odds":          parse_odds(h.get("forecast_odds", 10.0)),
            "form_string":   h.get("form_string",   ""),
            "jockey":        h.get("jockey",        "Unknown"),
            "trainer":       h.get("trainer",       "Unknown"),
            "final_score":   final_score,
        })

    # Normalise to probabilities
    total = sum(r["final_score"] for r in results)
    for r in results:
        r["probability"] = r["final_score"] / total if total > 0 else 1.0 / field_size
        r["ev"] = r["probability"] * (r["odds"] - 1) - (1 - r["probability"])

    # Sort by probability descending
    results.sort(key=lambda x: x["probability"], reverse=True)
    
    # Convert result dicts → Prediction dataclass objects
    predictions: list[Prediction] = []

    for i, r in enumerate(results):
        rank  = i + 1
        prob  = r["probability"]
        odds  = r["odds"]
        ev    = r["ev"]
        
        # Determine confidence, value bet, and longshot alert flags
        conf  = "Low"
        if prob > 0.18 and ev > 0.05:
            conf = "High"
        elif prob > 0.10 and ev > 0.0:
            conf = "Medium"
            
        val_bet  = ev > 0.30 and rank <= 3 and odds >= 4.0
        # Longshot Alerts:
        # 10/1-14/1 with EV > 25%, rank <= 8
        # 15/1+ with EV > 30%, rank <= 8
        longshot = (10.0 <= odds < 15.0 and ev > 0.25 and rank <= 8) or (odds >= 15.0 and ev > 0.30 and rank <= 8)

        predictions.append(Prediction(
            rank        = rank,
            horse       = r["horse"],
            draw        = r["draw"],
            jockey      = r["jockey"],
            trainer     = r["trainer"],
            odds        = round(odds, 2),
            probability = round(prob, 4),
            ev          = round(ev, 4),
            rule_score  = round(r["final_score"], 4),
            confidence  = conf,
            value_bet   = val_bet,
            longshot    = longshot,
            features    = [round(r["final_score"], 4)],
        ))

    logger.info(
        "[v3.11] %d runners — top: %s (%.1f%% prob, EV %+.3f)",
        field_size,
        predictions[0].horse if predictions else "—",
        (predictions[0].probability * 100) if predictions else 0.0,
        predictions[0].ev if predictions else 0.0,
    )

    return predictions, field_size


# ============================================================
# FULL V3.13 GREYVILLE POLYTRACK ENGINE
# ============================================================

def compute_v313_boosts(jockey: str, trainer: str) -> tuple[float, float]:
    j_boost = 1.0
    t_boost = 1.0
    
    j_clean = str(jockey).strip()
    t_clean = str(trainer).strip()
    
    # Match K. de Melo
    if "de Melo" in j_clean or "De Melo" in j_clean:
        j_boost = 1.18
        
    # Match C. Bass / C Bass
    if "Bass" in j_clean or "Bass" in t_clean:
        if "Bass" in j_clean:
            j_boost = 1.22
        else:
            t_boost = 1.22
            
    # Fallback to general v3.11 boosts if not matched
    if j_boost == 1.0:
        j_boost = JOCKEY_ELITE_BOOST_TFV311.get(jockey, 1.0)
    if t_boost == 1.0:
        t_boost = TRAINER_ELITE_BOOST_TFV311.get(trainer, 1.0)
        
    return j_boost, t_boost


def compute_probability_v313_greyville(horse: dict, context: dict) -> float:
    form_string = horse.get("form_string", "")
    odds = parse_odds(horse.get("forecast_odds", 10.0))
    draw = int(horse.get("draw", 5))
    weight = float(horse.get("weight", 56.0))
    jockey = horse.get("jockey", "")
    trainer = horse.get("trainer", "")
    first_timer = bool(horse.get("first_timer", False))
    horse_mr = horse.get("merit_rating")

    # 1. Form component scores
    form_score = score_form(form_string)
    momentum_score = compute_momentum(form_string)
    
    # 2. Market signal
    market_signal = 1.0 / odds if odds > 0.0 else 0.10
    
    # 3. MR advantage
    mr_adv = compute_mr_advantage(horse_mr, 70.0)
    
    # 4. Weight advantage
    avg_weight = context.get("avg_weight", 56.0)
    wgt_adv = compute_weight_advantage(avg_weight, weight)
    
    # 5. Trainer & Jockey boosts (v3.13 Greyville specific)
    jockey_boost, trainer_boost = compute_v313_boosts(jockey, trainer)
    
    # 6. Draw bias (Greyville specific: favors low draws <= 3 in sprints <= 1400m)
    distance = context.get("distance", 1200)
    
    if distance <= 1400:
        if draw <= 3:
            draw_bias = 1.20 # Strong low draw bias for sprints
        elif draw >= 8:
            draw_bias = 0.85 # Penalty for wide draws
        else:
            draw_bias = 1.0
    else:
        if draw <= 3:
            draw_bias = 1.08
        else:
            draw_bias = 0.95
    
    # 7. Apprentice multiplier
    apprentice_mult = compute_apprentice_multiplier(jockey)
    
    # Combine with weights (no longshot boost added here)
    raw_score = (
        (form_score * 0.09) + 
        (momentum_score * 0.07) + 
        market_signal + 
        mr_adv + 
        wgt_adv
    )
    
    # Apply multipliers
    final_score = raw_score * draw_bias * trainer_boost * jockey_boost * apprentice_mult
    
    return max(final_score, 0.0001)


def run_race_v313_greyville(
    horses:       list,
    race_context: dict,
) -> tuple[list[Prediction], int]:
    if not horses:
        return [], 0

    odds_map   = race_context.get("odds_map", {}) or {}
    horse_dicts: list[dict] = []

    for h in horses:
        if isinstance(h, dict):
            hd = h.copy()
        else:
            hd = {
                "horse":        getattr(h, "horse",        "Unknown"),
                "draw":         getattr(h, "draw",          0),
                "weight":       getattr(h, "weight",        56.0),
                "forecast_odds": getattr(h, "forecast_odds", 10.0),
                "form_string":  getattr(h, "form_string",  ""),
                "jockey":       getattr(h, "jockey",       "Unknown"),
                "trainer":      getattr(h, "trainer",      "Unknown"),
                "first_timer":   getattr(h, "first_timer",   False),
                "merit_rating":  getattr(h, "merit_rating",  None),
                "runs":          getattr(h, "runs",          0),
            }

        name = hd.get("horse", "")
        if name in odds_map and float(odds_map[name] or 0) > 1.0:
            hd["forecast_odds"] = float(odds_map[name])

        horse_dicts.append(hd)

    active = [h for h in horse_dicts if h]
    if not active:
        return [], 0

    field_size = len(active)
    avg_weight = sum(h.get("weight", 56.0) for h in active) / field_size
    
    context = dict(race_context)
    context["avg_weight"] = avg_weight
    context["field_size"] = field_size

    results = []
    # Score each horse
    for h in active:
        final_score = compute_probability_v313_greyville(h, context)
        results.append({
            "horse":         h.get("horse",        "Unknown"),
            "draw":          h.get("draw",          0),
            "weight":        h.get("weight",        56.0),
            "odds":          parse_odds(h.get("forecast_odds", 10.0)),
            "form_string":   h.get("form_string",   ""),
            "jockey":        h.get("jockey",        "Unknown"),
            "trainer":       h.get("trainer",       "Unknown"),
            "final_score":   final_score,
        })

    # Normalise to probabilities
    total = sum(r["final_score"] for r in results)
    for r in results:
        r["probability"] = r["final_score"] / total if total > 0 else 1.0 / field_size

    # Apply Odds-on floor rule (odds < 2.0 gets at least 35% probability)
    has_odds_on = any(r["odds"] < 2.0 for r in results)
    if has_odds_on:
        for r in results:
            if r["odds"] < 2.0:
                r["probability"] = max(r["probability"], 0.35)
        # Re-normalize
        total_p = sum(r["probability"] for r in results)
        if total_p > 0:
            for r in results:
                r["probability"] = r["probability"] / total_p

    for r in results:
        r["ev"] = r["probability"] * (r["odds"] - 1) - (1 - r["probability"])

    # Sort by probability descending
    results.sort(key=lambda x: x["probability"], reverse=True)
    
    # Convert to Prediction dataclass objects
    predictions: list[Prediction] = []

    for i, r in enumerate(results):
        rank  = i + 1
        prob  = r["probability"]
        odds  = r["odds"]
        ev    = r["ev"]
        
        conf  = "Low"
        if prob > 0.18 and ev > 0.05:
            conf = "High"
        elif prob > 0.10 and ev > 0.0:
            conf = "Medium"
            
        # Value bet: positive EV and High/Medium confidence
        val_bet = ev > 0.05 and conf in ("High", "Medium")
        # Longshot alert: odds >= 11.0, EV > 0.0, rank <= 4
        longshot = odds >= 11.0 and ev > 0.0 and rank <= 4

        predictions.append(Prediction(
            rank        = rank,
            horse       = r["horse"],
            draw        = r["draw"],
            jockey      = r["jockey"],
            trainer     = r["trainer"],
            odds        = round(odds, 2),
            probability = round(prob, 4),
            ev          = round(ev, 4),
            rule_score  = round(r["final_score"], 4),
            confidence  = conf,
            value_bet   = val_bet,
            longshot    = longshot,
            features    = [round(r["final_score"], 4)],
        ))

    logger.info(
        "[v3.13] %d runners — top: %s (%.1f%% prob, EV %+.3f)",
        field_size,
        predictions[0].horse if predictions else "—",
        (predictions[0].probability * 100) if predictions else 0.0,
        predictions[0].ev if predictions else 0.0,
    )

    return predictions, field_size
