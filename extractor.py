"""
extractor.py — Dedicated Computaform PDF Parser (v6.0)
South African racecard extraction — text-block based, per-page parsing.

Computaform PDF Structure (confirmed from inspection):
  - Each race spans multiple pages.
  - Page header line: "RACE N HOLLYWOODBETS ..."  (used to assign race number)
  - Horse entry line: "<draw>  <HORSE NAME IN ALL CAPS>"  (all-caps name, own line)
  - After horse bio block, the following labels appear as separate lines:
      "CF Rate Headgear"
      "Jockey"
      "KGs"
      "MR"
      "Draw"
    followed by their values on subsequent lines.
  - Skipped pages: those containing index/stats keywords.
"""

import io
import logging
import os
import re
import tempfile
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

# ─── OCR Dependencies (optional) ──────────────────────────────────────────────
try:
    import pytesseract
    from PIL import Image
    import pdf2image
    OCR_AVAILABLE = True
except ImportError:
    OCR_AVAILABLE = False

logger = logging.getLogger(__name__)

# ─── Constants ────────────────────────────────────────────────────────────────

_MAX_PAGES = 200

# Pages containing these strings are SKIPPED entirely.
_SKIP_PAGE_KEYWORDS = [
    "ALPHABETICAL INDEX TO HORSES",
    "JOCKEY INDEX",
    "TRAINER INDEX",
    "WHO'S HOT",
    "WHO'S COLD",
    "STATISTICS SA HORSERACING",
    "EXPLANATORY NOTES",
    "HOW TO READ",
]

# Race page header: "RACE 1 HOLLYWOODBETS..." or "RACE 6 HOLLYWOODBETS..."
_RACE_PAGE_HEADER_RE = re.compile(r"^RACE\s+(\d{1,2})\s+", re.IGNORECASE)

# Horse entry line: <draw_number>  <ALL CAPS NAME>  (name is all caps, own line)
# Must be: 1-2 digit number, 1+ spaces, all-caps name (letters, spaces, apostrophes, &, -)
_HORSE_ENTRY_RE = re.compile(r"^\s*(\d{1,2})\s{1,}([A-Z][A-Z\s'’‘&\-\.\(\)]{2,})\s*$")

# ComputaForm F/B odds: fractional notation with '/' or '-' separator.
# Matches standalone lines (e.g. "15/10", "4/1", "33-10") OR the
# trailing token on a comment line (e.g. "Fair debut-can score 15-10").
# Groups: (numerator, denominator)
_FB_ODDS_RE = re.compile(r"(?:^|\s)(\d{1,4})[/\-](\d{1,2})\s*$")

# Bad horse name tokens (to filter false positives).
# NOTE: Do NOT add common English words that can begin horse names (e.g. NEVER, WINTER).
_BAD_NAME_TOKENS = frozenset([
    "RACE", "HORSE", "DRAW", "JOCKEY", "TRAINER", "WEIGHT", "FORM", "ODDS",
    "FCST", "MR", "RATING", "WT", "SADDLE", "NO", "DR", "BARRIER",
    "COMMENT", "DAYS", "SINCE", "LAST", "WINNER", "RIDES", "WON",
    "INDEX", "STATISTICS", "RATINGS", "SHOES", "KGS", "LIFE", "EARN",
    "TURF", "CRSE", "GOOD", "DIST", "WET", "REST", "CLAS", "DATE", "CRS",
    "REF", "CLASS", "SP", "RR", "SR", "BRED", "OWNER", "CF", "RATE",
    "HEADGEAR", "END", "COPYRIGHT", "NATIONAL", "BUREAU", "HOLLYWOODBETS",
    "SPRINT", "MILE", "COLLATERAL", "FORMLINES",
])

# First-page marker: Computaform "overview" pages start with TURF or RIGHT-HAND
# TURN (or LEFT-HAND TURN / STRAIGHT) followed shortly by the race time.
_FIRST_PAGE_MARKERS = frozenset(["TURF", "POLYTRACK", "DIRT"])

# Inside a first-page we scan the first 30 lines for a lone race digit 1-12.
_LONE_RACE_NUM_RE = re.compile(r"^\s*(\d{1,2})\s*$")

# Jockey names often appear in the form section as "MR Jockey" combined
_JOCKEY_LINE_RE = re.compile(r"^\*?([A-Z][A-Za-z\s\.\-']{2,30})$")


# ─── Data Classes ─────────────────────────────────────────────────────────────

@dataclass
class Horse:
    """Full horse entry for a Computaform racecard."""
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

    merit_rating: Optional[int] = None
    course_runs: int = 0
    horse_gear: str = ""
    first_timer: bool = False
    running_comment: str = ""
    comment_history: List[str] = field(default_factory=list)
    race: int = 1

    sire: Optional[str] = None
    race_class: Optional[str] = None
    scratched: bool = False
    is_apprentice: bool = False

    # ComputaForm F/B odds — populated automatically during PDF extraction.
    # fb_odds_str : raw fractional string from the PDF (e.g. "15/10", "4/1").
    # forecast_odds : decimal equivalent (e.g. 2.50).  Never changed by user.
    # market_odds   : editable decimal; starts == forecast_odds.
    #                 The UI writes the user's live adjustments here.
    #                 The prediction engine uses this value via odds_map.
    fb_odds_str: str = ""
    market_odds: float = 0.0

    # Phase 3 Forensic Data Expansion & Leakage Firewall Fields
    normalized_data: Dict[str, Any] = field(default_factory=dict)
    past_performance: List[Dict[str, Any]] = field(default_factory=list)
    ml_readiness: Dict[str, str] = field(default_factory=dict)

    @property
    def form_figures(self) -> List[int]:
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
        figs = self.form_figures
        if not figs:
            return 50.0
        weights = [0.4 ** (len(figs) - 1 - i) for i in range(len(figs))]
        total_w = sum(weights)
        weighted = sum((1 / max(f, 1)) * w for f, w in zip(figs, weights))
        return min(max(weighted / total_w * 100, 0), 100)


@dataclass
class ExtractionResult:
    horses: List[Horse]
    confidence: float
    warnings: List[str] = field(default_factory=list)
    raw_text: str = ""
    pages_read: int = 0
    pages_skipped: int = 0
    report: str = ""
    races_meta: Dict[int, Dict[str, Any]] = field(default_factory=dict)

    @property
    def is_valid(self) -> bool:
        return len([h for h in self.horses if h.horse and h.horse != "Unknown"]) >= 2

    @property
    def confidence_label(self) -> str:
        if self.confidence >= 0.85:
            return "High"
        elif self.confidence >= 0.60:
            return "Medium"
        return "Low"


# ─── Pure Helper Functions ────────────────────────────────────────────────────

def parse_odds(odds_str: str) -> float:
    if not odds_str:
        return 0.0
    s = str(odds_str).strip()
    m = re.match(r"(\d+)[/\-](\d+)", s)
    if m:
        den = float(m.group(2))
        return float(m.group(1)) / den if den else 0.0
    try:
        return float(s)
    except ValueError:
        return 0.0


def fractional_to_decimal(frac_str: str) -> float:
    """Convert a ComputaForm fractional odds string to European decimal odds.

    Handles both '/' and '-' separators.  Returns 0.0 if unparseable.

    Examples::

        fractional_to_decimal("15/10") -> 2.50
        fractional_to_decimal("4/1")   -> 5.00
        fractional_to_decimal("7/10")  -> 1.70
        fractional_to_decimal("9/2")   -> 5.50
        fractional_to_decimal("10/1")  -> 11.00
        fractional_to_decimal("15-10") -> 2.50
        fractional_to_decimal("99/1")  -> 100.00
    """
    if not frac_str:
        return 0.0
    s = str(frac_str).strip()
    m = re.match(r"^(\d{1,4})[/\-](\d{1,2})$", s)
    if not m:
        return 0.0
    num = float(m.group(1))
    den = float(m.group(2))
    if den == 0:
        return 0.0
    return round(num / den + 1.0, 4)


def _extract_fb_odds(block_lines: List[str]) -> str:
    """Scan a horse block for a ComputaForm F/B odds string.

    Searches block_lines (bottom-up, skipping the first line which is the
    horse name) for a standalone fractional odds token such as ``15/10``,
    ``4/1``, ``33-10``, or as the trailing token on a comment/description
    line such as ``"Fair debut-can score 15-10"``.

    Returns the raw fractional string (e.g. ``"15/10"``) or ``""``.
    """
    # Standalone line: just a fraction, nothing else
    _standalone = re.compile(r"^(\d{1,4})[/\-](\d{1,2})$")
    # Trailing token on a comment line
    _trailing   = re.compile(r"(?:^|\s)(\d{1,4})[/\-](\d{1,2})\s*$")

    # Scan from the bottom of the block upwards (odds appear near the end)
    for line in reversed(block_lines[1:]):
        stripped = line.strip()
        if not stripped:
            continue
        m = _standalone.match(stripped)
        if m:
            return stripped  # e.g. "33/10"
        m = _trailing.search(stripped)
        if m:
            # Reconstruct with canonical '/' separator
            raw = f"{m.group(1)}/{m.group(2)}"
            return raw
    return ""


def extract_positions(form_str: str) -> Tuple[int, int, int]:
    if not form_str:
        return 0, 0, 0
    parts = [p.strip() for p in re.split(r"[-/\s]", form_str) if p.strip()]
    wins = thirds = top3 = runs = 0
    for p in parts:
        if p.isdigit():
            v = int(p)
            runs += 1
            if v == 1:
                wins += 1; top3 += 1
            elif v == 2:
                top3 += 1
            elif v == 3:
                thirds += 1; top3 += 1
        elif p.upper() in ("W",):
            wins += 1; top3 += 1; runs += 1
    f3 = int(top3 / runs * 100) if runs else 0
    return wins, thirds, f3


def _count_form_runs(form: str) -> int:
    if not form:
        return 0
    # Use LIFE stats if available: "LIFE: 21-4-3-5-2"  -> runs=21
    return len([x for x in re.split(r"[-/]", form) if x.strip()])


def detect_first_timer(form_str: str) -> bool:
    return not bool(form_str and form_str.strip())


def _horse_name_is_valid(name: str) -> bool:
    """Return True if the name looks like a real horse name (not a label/heading)."""
    if not name or len(name) < 3:
        return False
    name_up = name.strip().upper()
    # Reject if exactly matches a bad token
    if name_up in _BAD_NAME_TOKENS:
        return False
    # Reject if starts with a bad token
    for tok in _BAD_NAME_TOKENS:
        if name_up.startswith(tok + " ") or name_up == tok:
            return False
    # Must start with a letter
    if not re.match(r"^[A-Za-z]", name):
        return False
    # Reject pure numbers
    if name.strip().isdigit():
        return False
    return True


def _page_should_skip(text: str) -> Optional[str]:
    """Return the keyword that caused the skip, or None.

    A page is only skipped when its PRIMARY content is an index/stats section.
    Race card continuation pages contain statistics keywords inside the runner
    form-history blocks — those pages must NOT be skipped.
    """
    # Never skip pages that carry a race-card header.
    if _RACE_PAGE_HEADER_RE.search(text):
        return None
    text_upper = text.upper()
    for kw in _SKIP_PAGE_KEYWORDS:
        if kw in text_upper:
            return kw
    return None


def extract_race_metadata(all_page_lines: List[List[str]]) -> Dict[int, Dict[str, Any]]:
    """Extract race metadata strictly tied to each race_number from ComputaForm PDF lines."""
    races_meta: Dict[int, Dict[str, Any]] = {}

    def get_meta(rn: int) -> Dict[str, Any]:
        if rn not in races_meta:
            races_meta[rn] = {
                "venue": None,
                "surface": None,
                "distance": None,
                "race_time": None,
                "stake": None,
                "race_number": rn,
                "betting_leg": None,
            }
        return races_meta[rn]

    full_text = "\n".join("\n".join(lines) for lines in all_page_lines)
    meeting_venue = None

    m_v = re.search(r"FIELDS,?\s+RATINGS\s+FOR\s+([A-Za-z\s]+)", full_text, re.IGNORECASE)
    if m_v:
        raw_v = m_v.group(1).strip()
        parts = re.split(r"\s+(?:Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday|\d)", raw_v, flags=re.IGNORECASE)
        v = parts[0].strip()
        v = re.sub(r"^(HOLLYWOODBETS|HWB|TAB)\s+", "", v, flags=re.IGNORECASE).strip()
        v = re.sub(r"\s+(TURF|POLYTRACK|SAND|DIRT)$", "", v, flags=re.IGNORECASE).strip()
        if v:
            meeting_venue = v.title()

    if not meeting_venue:
        m_v2 = re.search(r"RACE\s+\d{1,2}\s+(?:HOLLYWOODBETS\s+)?([A-Za-z]+)", full_text, re.IGNORECASE)
        if m_v2:
            cand = m_v2.group(1).strip()
            if cand.upper() in ("VAAL", "FAIRVIEW", "KENILWORTH", "TURFFONTEIN", "GREYVILLE", "SCOTTSVILLE", "DURBANVILLE"):
                meeting_venue = cand.title()

    # Pass 1: Parse overview page blocks
    for lines in all_page_lines:
        pg_text = "\n".join(lines)
        if "FIELDS, RATINGS FOR" in pg_text or "12:15" in pg_text or "12:25" in pg_text or "12:45" in pg_text:
            for i, line in enumerate(lines):
                sline = line.strip()
                if sline.isdigit() and 1 <= int(sline) <= 25:
                    r_num = int(sline)
                    meta = get_meta(r_num)
                    if meeting_venue and not meta["venue"]:
                        meta["venue"] = meeting_venue

                    next_lines = [lines[j].strip() for j in range(i + 1, min(i + 7, len(lines)))]
                    combined_block = " ".join(next_lines)

                    m_time = re.search(r"\b(\d{1,2}:\d{2})\b", combined_block)
                    if m_time and not meta["race_time"]:
                        meta["race_time"] = m_time.group(1)

                    m_stake = re.search(r"\b(R[\d,]+)\b", combined_block)
                    if m_stake and not meta["stake"]:
                        meta["stake"] = m_stake.group(1)

                    m_dist = re.search(r"\b(\d{3,4})\s*m\b(?![a-zA-Z])", combined_block, re.IGNORECASE)
                    if m_dist and not meta["distance"]:
                        meta["distance"] = f"{m_dist.group(1)}m"

                    m_surf = re.search(r"\b(TURF|POLYTRACK|SAND|DIRT)\b", combined_block, re.IGNORECASE)
                    if m_surf and not meta["surface"]:
                        meta["surface"] = m_surf.group(1).capitalize()

                    legs = []
                    for m in re.finditer(r"\bBIPOT\s*(?:LEG)?\s*(\d+)\b", combined_block, re.IGNORECASE):
                        legs.append(f"Bipot Leg {m.group(1)}")
                    for m in re.finditer(r"\b(?:PICK\s*6|PICK6)\s*(?:LEG)?\s*(\d+)\b", combined_block, re.IGNORECASE):
                        legs.append(f"Pick 6 Leg {m.group(1)}")
                    for m in re.finditer(r"\b(?:JACKPOT|JKPT)\s*(\d*)\s*(?:LEG)?\s*(\d+)\b", combined_block, re.IGNORECASE):
                        j_n = f"{m.group(1)} " if m.group(1) else ""
                        legs.append(f"Jackpot {j_n}Leg {m.group(2)}".replace("  ", " "))
                    for m in re.finditer(r"\b(?:PLACE\s*ACCUMULATOR|P/?A)\s*(?:LEG)?\s*(\d+)\b", combined_block, re.IGNORECASE):
                        legs.append(f"Place Accumulator Leg {m.group(1)}")

                    if legs and not meta["betting_leg"]:
                        seen = set()
                        meta["betting_leg"] = ", ".join([l for l in legs if not (l in seen or seen.add(l))])

    # Pass 2: Per-race detail pages for missing fields
    for lines in all_page_lines:
        rn = None
        for l in lines[:5]:
            m_hdr = re.search(r"^RACE\s+(\d{1,2})\b", l.strip(), re.IGNORECASE)
            if m_hdr:
                rn = int(m_hdr.group(1))
                break

        if not rn and lines:
            first_line = lines[0].strip().upper()
            if first_line in ("TURF", "POLYTRACK", "DIRT", "SAND"):
                for l in lines[1:10]:
                    if l.strip().isdigit() and 1 <= int(l.strip()) <= 25:
                        rn = int(l.strip())
                        break

        if rn and 1 <= rn <= 25:
            meta = get_meta(rn)
            if meeting_venue and not meta["venue"]:
                meta["venue"] = meeting_venue

            pg_block = " ".join([l.strip() for l in lines[:35]])

            if not meta["venue"]:
                m_v = re.search(r"FIELDS,?\s+RATINGS\s+FOR\s+([A-Za-z\s]+)", pg_block, re.IGNORECASE)
                if m_v:
                    raw_v = m_v.group(1).strip()
                    parts = re.split(r"\s+(?:Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday|\d)", raw_v, flags=re.IGNORECASE)
                    meta["venue"] = parts[0].strip().title()

            if not meta["race_time"]:
                m_time = re.search(r"\b(\d{1,2}:\d{2})\b", pg_block)
                if m_time:
                    meta["race_time"] = m_time.group(1)

            if not meta["stake"]:
                m_stake = re.search(r"\b(R[\d,]+)\b", pg_block)
                if m_stake:
                    meta["stake"] = m_stake.group(1)

            if not meta["distance"]:
                m_dist = re.search(r"\b(\d{3,4})\s*m\b(?![a-zA-Z])", pg_block, re.IGNORECASE)
                if m_dist:
                    meta["distance"] = f"{m_dist.group(1)}m"

            if not meta["surface"]:
                m_surf = re.search(r"\b(TURF|POLYTRACK|SAND|DIRT)\b", pg_block, re.IGNORECASE)
                if m_surf:
                    meta["surface"] = m_surf.group(1).capitalize()

            if not meta["betting_leg"]:
                legs = []
                for m in re.finditer(r"\bBIPOT\s*(?:LEG)?\s*(\d+)\b", pg_block, re.IGNORECASE):
                    legs.append(f"Bipot Leg {m.group(1)}")
                for m in re.finditer(r"\b(?:PICK\s*6|PICK6)\s*(?:LEG)?\s*(\d+)\b", pg_block, re.IGNORECASE):
                    legs.append(f"Pick 6 Leg {m.group(1)}")
                for m in re.finditer(r"\b(?:JACKPOT|JKPT)\s*(\d*)\s*(?:LEG)?\s*(\d+)\b", pg_block, re.IGNORECASE):
                    j_n = f"{m.group(1)} " if m.group(1) else ""
                    legs.append(f"Jackpot {j_n}Leg {m.group(2)}".replace("  ", " "))
                for m in re.finditer(r"\b(?:PLACE\s*ACCUMULATOR|P/?A)\s*(?:LEG)?\s*(\d+)\b", pg_block, re.IGNORECASE):
                    legs.append(f"Place Accumulator Leg {m.group(1)}")

                if legs:
                    seen = set()
                    meta["betting_leg"] = ", ".join([l for l in legs if not (l in seen or seen.add(l))])

    cleaned_meta = {
        r: meta for r, meta in races_meta.items()
        if 1 <= r <= 25 and any(meta[k] for k in ("venue", "surface", "distance", "race_time", "stake", "betting_leg"))
    }
    return cleaned_meta




# ─── Computaform Per-Page Parser ──────────────────────────────────────────────

def try_parse_jockey_and_fields(vals: List[str]) -> Optional[Tuple[str, float, Optional[int], int, bool, str]]:
    """
    Scans a list of values after the Draw label to find the jockey and associated fields.
    Returns (jockey, weight, mr, draw, is_apprentice, headgear).
    """
    start_idx = 0
    if len(vals) > 0 and len(vals[0]) == 1 and vals[0].upper() in "ABCDEFGXYZ":
        start_idx = 1
        if len(vals) > 1 and vals[1].isdigit():
            start_idx = 2

    for j_idx in range(start_idx, len(vals) - 2):
        candidate = vals[j_idx]
        if not candidate:
            continue
        if not re.match(r"^\*?[A-Za-z]", candidate):
            continue
        if any(w in candidate.upper() for w in ["ON LAST", "OFF LAST", "HEADGEAR", "RATE", "SHOES"]):
            continue
        
        is_apprentice = candidate.startswith("*")

        # Case A: with weight adj (j_idx + 1 is weight adj, j_idx + 2 is KGs, j_idx + 3 is MR, j_idx + 4 is Draw)
        if j_idx + 4 < len(vals):
            w_adj_str = vals[j_idx + 1]
            kgs_str = vals[j_idx + 2]
            mr_str = vals[j_idx + 3]
            draw_str = vals[j_idx + 4]
            if re.match(r"^\d+(?:\.\d+)?$", kgs_str) and re.match(r"^\d+$", draw_str):
                jockey = re.sub(r"^\*", "", re.sub(r"\s*[+-]?\d+\.\d+\s*$", "", candidate)).strip()
                weight = float(kgs_str)
                mr = int(mr_str) if mr_str.isdigit() else None
                draw = int(draw_str)
                
                # Headgear extraction
                headgear = ""
                if j_idx >= 3:
                    for idx in range(j_idx - 1, 1, -1):
                        tokens = vals[idx].strip().split()
                        if tokens:
                            first = tokens[0].upper()
                            if first.isalpha() and len(first) <= 4 and first not in ("NO", "ON", "OFF", "A", "S", "Y"):
                                headgear = first
                                break

                return jockey, weight, mr, draw, is_apprentice, headgear

        # Case B: no weight adj (j_idx + 1 is KGs, j_idx + 2 is MR, j_idx + 3 is Draw)
        if j_idx + 3 < len(vals):
            kgs_str = vals[j_idx + 1]
            mr_str = vals[j_idx + 2]
            draw_str = vals[j_idx + 3]
            if re.match(r"^\d+(?:\.\d+)?$", kgs_str) and re.match(r"^\d+$", draw_str):
                jockey = re.sub(r"^\*", "", re.sub(r"\s*[+-]?\d+\.\d+\s*$", "", candidate)).strip()
                weight = float(kgs_str)
                mr = int(mr_str) if mr_str.isdigit() else None
                draw = int(draw_str)

                # Headgear extraction
                headgear = ""
                if j_idx >= 3:
                    for idx in range(j_idx - 1, 1, -1):
                        tokens = vals[idx].strip().split()
                        if tokens:
                            first = tokens[0].upper()
                            if first.isalpha() and len(first) <= 4 and first not in ("NO", "ON", "OFF", "A", "S", "Y"):
                                headgear = first
                                break

                return jockey, weight, mr, draw, is_apprentice, headgear
    return None


# ─── Phase 3 Data Dictionary & Leakage Firewall Helpers ───────────────────────

def build_field_node(
    source_label: str,
    raw_value: Any,
    normalized_value: Any,
    normalization_status: str = "VERIFIED",
    ml_candidate: bool = True,
    leakage_class: str = "PRE_RACE"
) -> Dict[str, Any]:
    return {
        "source_label": source_label,
        "raw_value": raw_value,
        "normalized_value": normalized_value,
        "normalization_status": normalization_status,
        "ml_candidate": ml_candidate,
        "leakage_class": leakage_class
    }


def _parse_horse_bio_and_form(block_lines: List[str]) -> Dict[str, Any]:
    """Parse bio block lines for pedigree, fitness, career tuples, and connection info."""
    norm: Dict[str, Any] = {}

    colour_map = {"B": "Bay", "Ch": "Chestnut", "Gr": "Grey", "Ro": "Roan", "Bl": "Black"}
    sex_map = {"g": "gelding", "f": "filly", "m": "mare", "c": "colt", "h": "horse"}

    # 1. Bio & Pedigree line (e.g. "7 B g  Futura - Archerfield (USA) by Arch (USA)")
    for bl in block_lines:
        s = bl.strip()
        m_bio = re.match(r"^(\d{1,2})\s+([A-Za-z]+)\s+([a-z])(?:\s+(.*))?$", s)
        if m_bio:
            age_val = int(m_bio.group(1))
            colour_code = m_bio.group(2)
            sex_code = m_bio.group(3)
            ped_text = m_bio.group(4) or ""

            norm["age"] = build_field_node("Bio line", s, age_val, "VERIFIED", True, "PRE_RACE")
            norm["colour"] = build_field_node("Bio line", colour_code, colour_map.get(colour_code, colour_code), "VERIFIED", False, "PRE_RACE")
            norm["sex"] = build_field_node("Bio line", sex_code, sex_map.get(sex_code, sex_code), "VERIFIED", True, "PRE_RACE")

            if ped_text:
                ped_m = re.match(r"^(.+?)\s+-\s+(.+?)(?:\s+by\s+(.+))?$", ped_text)
                if ped_m:
                    norm["sire"] = build_field_node("Pedigree line", ped_text, ped_m.group(1).strip(), "VERIFIED", True, "PRE_RACE")
                    norm["dam"] = build_field_node("Pedigree line", ped_text, ped_m.group(2).strip(), "VERIFIED", False, "PRE_RACE")
                    if ped_m.group(3):
                        norm["dam_sire"] = build_field_node("Pedigree line", ped_text, ped_m.group(3).strip(), "VERIFIED", False, "PRE_RACE")
            break

    # 2. Foaled / Gelded date lines
    for bl in block_lines:
        s = bl.strip()
        m_f = re.search(r"Foaled:\s*(\d{1,2}\s+[A-Za-z]{3}\s+\d{4})", s)
        if m_f:
            norm["foaled_date"] = build_field_node("Foaled line", m_f.group(0), m_f.group(1), "VERIFIED", False, "PRE_RACE")
        m_g = re.search(r"Gelded:\s*(\d{1,2}\s+[A-Za-z]{3}\s+\d{4})", s)
        if m_g:
            norm["gelded_date"] = build_field_node("Gelded line", m_g.group(0), m_g.group(1), "VERIFIED", False, "PRE_RACE")

    # 3. Trainer line e.g. "M N Houdalakis (V)" or "J S Snaith (PC)"
    # Pass 3a: Explicit venue code parenthetical e.g. "J S Snaith (PC)"
    for bl in block_lines:
        s = bl.strip()
        m_t_code = re.match(r"^([A-Z][A-Za-z\s\.\'\-]+?)\s+\(([A-Z]{1,4})\)\s*$", s)
        if m_t_code:
            cand = m_t_code.group(1).strip()
            cand_tokens = set(re.findall(r"[A-Za-z]+", cand.upper()))
            if not cand_tokens.intersection(_BAD_NAME_TOKENS) and len(cand) >= 4 and ' ' in cand:
                norm["trainer"] = build_field_node("Trainer line", s, cand, "VERIFIED", True, "PRE_RACE")
                break

    # Pass 3b: Fallback for lines before LIFE/Shoes/CF Rate
    if "trainer" not in norm:
        for bl in block_lines:
            s = bl.strip()
            if any(k in s.upper() for k in ["LIFE:", "SHOES", "CF RATE", "SP RATE", "FOALED:", "GELDED:", "BY:"]):
                break
            m_t = re.match(r"^([A-Z][A-Za-z\s\.\'\-]+?)\s*$", s)
            if m_t:
                cand = m_t.group(1).strip()
                cand_tokens = set(re.findall(r"[A-Za-z]+", cand.upper()))
                if not cand_tokens.intersection(_BAD_NAME_TOKENS) and len(cand) >= 4 and ' ' in cand:
                    norm["trainer"] = build_field_node("Trainer line", s, cand, "VERIFIED", True, "PRE_RACE")
                    break

    # 4. Info line e.g. "12 Days Since Last Race - 656 Days Since Last Win BRED BY: ... R140,000 A2YS21 OWNER/S: ..."
    for bl in block_lines:
        s = bl.strip()
        if "Days Since Last" in s or "OWNER/S:" in s or "BRED BY:" in s:
            m_dlr = re.search(r"(\d+)\s+Days?\s+Since\s+Last\s+Race", s, re.IGNORECASE)
            if m_dlr:
                norm["days_since_last_race"] = build_field_node("Info line", m_dlr.group(0), int(m_dlr.group(1)), "VERIFIED", True, "PRE_RACE")
            m_dlw = re.search(r"(\d+)\s+Days?\s+Since\s+Last\s+Win", s, re.IGNORECASE)
            if m_dlw:
                norm["days_since_last_win"] = build_field_node("Info line", m_dlw.group(0), int(m_dlw.group(1)), "VERIFIED", True, "PRE_RACE")

            m_bred = re.search(r"BRED\s+BY:\s*(.+?)(?=\s+R\d|\s+OWNER|$)", s)
            if m_bred:
                norm["breeder"] = build_field_node("Info line", m_bred.group(0), m_bred.group(1).strip(), "VERIFIED", False, "PRE_RACE")

            m_price = re.search(r"(R[\d,]+)\s+([A-Z]\d[A-Z]{2}\d{2})", s)
            if m_price:
                raw_p = m_price.group(1).replace("R", "").replace(",", "")
                p_val = int(raw_p) if raw_p.isdigit() else None
                norm["purchase_price_zar"] = build_field_node("Info line", m_price.group(0), p_val, "requires_verification", False, "PRE_RACE")
                norm["auction_code"] = build_field_node("Info line", m_price.group(2), m_price.group(2), "requires_verification", False, "PRE_RACE")

            m_own = re.search(r"OWNER/S:\s*(.+?)$", s)
            if m_own:
                norm["owner"] = build_field_node("Info line", m_own.group(0), m_own.group(1).strip(), "VERIFIED", False, "PRE_RACE")

    # 5. Career stats tuples
    tuple_keys = ["LIFE", "2026", "2025", "J+H", "J+T", "TURF", "POLY", "CRSE", "DIST", "C&D", "Good", "Wet", "Hdgr", "Rest+7", "Rest+14", "Rest+1", "ClasB", "ClasA", "ClasC", "ClasD", "ClasE", "Dcat"]
    for bl in block_lines:
        s = bl.strip()
        for tk in tuple_keys:
            pat = r"\b" + re.escape(tk) + r":\s*(\d+)-(\d+)-(\d+)-(\d+)-(\d+)"
            m_tup = re.search(pat, s)
            if m_tup:
                raw_str = m_tup.group(0)
                runs = int(m_tup.group(1))
                wins = int(m_tup.group(2))
                seconds = int(m_tup.group(3))
                thirds = int(m_tup.group(4))
                unplaced = int(m_tup.group(5))
                status = "requires_verification" if tk in ("Rest+7", "Rest+14", "Rest+1", "ClasA", "ClasB", "ClasC", "ClasD", "ClasE", "Dcat") else "VERIFIED"
                norm[tk.lower().replace("+", "_")] = build_field_node(
                    tk,
                    raw_str,
                    {"runs": runs, "wins": wins, "seconds": seconds, "thirds": thirds, "fourths": unplaced},
                    status,
                    True,
                    "HISTORICAL"
                )

    # 6. WPR & Best vs Ave
    for bl in block_lines:
        s = bl.strip()
        m_wpr = re.search(r"WPR:\s*(\d+)-(\d+)m", s)
        if m_wpr:
            norm["wpr"] = build_field_node("WPR", m_wpr.group(0), {"raw_components": [m_wpr.group(1), f"{m_wpr.group(2)}m"]}, "requires_verification", True, "HISTORICAL")
        m_bva = re.search(r"Best\s+vs\s+Ave:\s*([+-]?\d+\.\d+)", s)
        if m_bva:
            norm["best_vs_average"] = build_field_node("Best vs Ave", m_bva.group(0), float(m_bva.group(1)), "VERIFIED", True, "HISTORICAL")

    return norm


def _extract_historical_performance(all_page_lines: List[List[str]], valid_horse_names: Optional[set] = None) -> Dict[str, List[Dict[str, Any]]]:
    """Forensically parse detailed collateral formlines table rows for each horse across all pages."""
    historical_by_horse: Dict[str, List[Dict[str, Any]]] = {}
    current_horse = None

    _HEADER_SKIPS = frozenset({'COLLATERAL', 'FORMLINES', 'HORSE', 'DATE', 'CRSE', 'RACE', 'DIST', 'WGT', 'WINNER', 'W/TIME', 'FIN/LTH'})

    for page_lines in all_page_lines:
        pg_text = "\n".join(page_lines)
        if "COLLATERAL FORMLINES" not in pg_text and "W/Time 400F" not in pg_text:
            continue

        i = 0
        while i < len(page_lines):
            l = page_lines[i].strip()
            title_cand = l.title()
            
            # Check horse header match
            if valid_horse_names and title_cand in valid_horse_names:
                current_horse = title_cand
                historical_by_horse.setdefault(current_horse, [])
            elif not valid_horse_names and l.isupper() and len(l) >= 3 and not any(k in l for k in _HEADER_SKIPS):
                if any(c.isalpha() for c in l):
                    current_horse = title_cand
                    historical_by_horse.setdefault(current_horse, [])

            elif current_horse and re.match(r"^\d{1,2}[A-Za-z]{3}\d{2}\s+[A-Z]{2,4}", l):
                date_venue = l
                sub_lines = [page_lines[j].strip() for j in range(i + 1, min(len(page_lines), i + 15))]

                going = sub_lines[0] if sub_lines else ""
                r_class = sub_lines[1] if len(sub_lines) > 1 else ""
                dist_grade = sub_lines[2] if len(sub_lines) > 2 else ""

                # Token 3 could be MR (if digit e.g. 82, 96) or Jockey name (in Maiden races)
                cur_idx = 3
                mr_val = None
                if cur_idx < len(sub_lines) and sub_lines[cur_idx].isdigit():
                    mr_val = int(sub_lines[cur_idx])
                    cur_idx += 1

                jockey_val = sub_lines[cur_idx] if cur_idx < len(sub_lines) else ""
                cur_idx += 1

                wgt_str = sub_lines[cur_idx] if cur_idx < len(sub_lines) else ""
                wgt_val = None
                dr_field_str = ""

                m_w = re.match(r"^(\d+(?:\.\d+)?)$", wgt_str)
                if m_w:
                    wgt_val = float(m_w.group(1))
                    cur_idx += 1
                    dr_field_str = sub_lines[cur_idx] if cur_idx < len(sub_lines) else ""
                else:
                    m_w_dr = re.match(r"^(\d+(?:\.\d+)?)\s+(\d+-\d+)$", wgt_str)
                    if m_w_dr:
                        wgt_val = float(m_w_dr.group(1))
                        dr_field_str = m_w_dr.group(2)
                        cur_idx += 1

                dr_val = None
                fn_val = None
                if "-" in dr_field_str:
                    parts = dr_field_str.split("-")
                    if parts[0].isdigit(): dr_val = int(parts[0])
                    if parts[1].isdigit(): fn_val = int(parts[1])

                ob_str = sub_lines[cur_idx] if cur_idx < len(sub_lines) else ""

                dist_val = None
                m_dst = re.search(r"(\d+)", dist_grade)
                if m_dst:
                    try:
                        dist_val = int(m_dst.group(1))
                    except ValueError:
                        dist_val = None

                row = {
                    "source_label": "COLLATERAL FORMLINES",
                    "raw_line": l,
                    "date_venue_raw": date_venue,
                    "going_raw": going,
                    "race_class_raw": r_class,
                    "distance_grade_raw": dist_grade,
                    "mr_raw": str(mr_val) if mr_val is not None else "",
                    "jockey_raw": jockey_val,
                    "weight_raw": wgt_str,
                    "draw_field_raw": dr_field_str,
                    "opening_odds_raw": ob_str,
                    "normalized": {
                        "historical_race_date": date_venue.split()[0] if date_venue else None,
                        "venue_code": date_venue.split()[1] if len(date_venue.split()) > 1 else None,
                        "going": going,
                        "race_class": r_class,
                        "distance_m": dist_val,
                        "merit_rating": mr_val,
                        "jockey": jockey_val,
                        "weight_kg": wgt_val,
                        "draw": dr_val,
                        "field_size": fn_val,
                        "opening_odds": ob_str,
                    },
                    "normalization_status": "VERIFIED",
                    "leakage_class": "HISTORICAL",
                    "ml_candidate": True
                }
                historical_by_horse[current_horse].append(row)

            i += 1

    return historical_by_horse


def validate_ml_eligibility(horse: Horse) -> Dict[str, Any]:
    """
    Multi-stage Leakage Firewall:
    Audits all pre-race, historical, and market features on a Horse instance.
    Explicitly blocks post-race leakage fields (today_finish_position, today_official_sp, etc.).
    Returns dict containing allowed_features, blocked_features, blocked_reasons, and field_statuses.
    """
    allowed_features: List[str] = []
    blocked_features: List[str] = []
    blocked_reasons: Dict[str, str] = {}
    field_statuses: Dict[str, str] = {}

    _BLOCKED_POST_RACE_KEYS = frozenset([
        "today_finish_position",
        "today_official_sp",
        "today_winning_time",
        "today_defeat_margin",
        "today_speed_rating",
        "today_ability_rating",
        "today_sectional",
        "winner_of_this_race",
    ])

    for field_name, node in horse.normalized_data.items():
        lclass = node.get("leakage_class", "PRE_RACE")
        status = node.get("normalization_status", "VERIFIED")

        if field_name in _BLOCKED_POST_RACE_KEYS or lclass in ("POST_RACE_LEAKAGE", "TARGET"):
            blocked_features.append(field_name)
            blocked_reasons[field_name] = f"Blocked by Leakage Firewall: {lclass}"
            field_statuses[field_name] = "BLOCKED"
        elif status == "requires_verification":
            field_statuses[field_name] = "REQUIRES_VERIFICATION"
            allowed_features.append(field_name)
        else:
            field_statuses[field_name] = "ML_READY"
            allowed_features.append(field_name)

    base_pre_race = ["draw", "weight", "jockey", "trainer", "merit_rating", "forecast_odds", "market_odds", "is_apprentice"]
    for bfk in base_pre_race:
        if bfk not in field_statuses:
            field_statuses[bfk] = "ML_READY"
            allowed_features.append(bfk)

    field_statuses["past_performance_rows"] = "ML_READY" if horse.past_performance else "EXTRACTED"
    allowed_features.append("past_performance_rows")

    return {
        "horse_name": horse.horse,
        "race_number": horse.race,
        "allowed_features_count": len(allowed_features),
        "allowed_features": sorted(allowed_features),
        "blocked_features_count": len(blocked_features),
        "blocked_features": sorted(blocked_features),
        "blocked_reasons": blocked_reasons,
        "field_statuses": field_statuses,
        "leakage_violations_count": len(blocked_features)
    }


def generate_extraction_audit(result: ExtractionResult) -> str:
    """Generate diagnostic extraction quality and leakage firewall report."""
    total_races = len(set(h.race for h in result.horses))
    total_horses = len(result.horses)

    lines = [
        "=" * 65,
        "  COMPUTAFORM FORENSIC EXTRACTION & LEAKAGE AUDIT REPORT",
        "=" * 65,
        f"  Races detected         : {total_races}",
        f"  Horses detected        : {total_horses}",
        f"  Pages read             : {result.pages_read}",
        f"  Pages skipped          : {result.pages_skipped}",
        f"  Extraction confidence  : {result.confidence:.0%} ({result.confidence_label})",
        "-" * 65,
        "  PRE-RACE FIELD FILL RATES & STATUSES:",
    ]

    target_fields = [
        ("draw", "PRE_RACE"),
        ("weight", "PRE_RACE"),
        ("jockey", "PRE_RACE"),
        ("trainer", "PRE_RACE"),
        ("merit_rating", "PRE_RACE"),
        ("forecast_odds", "MARKET"),
        ("fb_odds_str", "MARKET"),
        ("market_odds", "MARKET"),
        ("is_apprentice", "PRE_RACE"),
        ("runs", "HISTORICAL"),
        ("wins", "HISTORICAL"),
        ("third_places", "HISTORICAL"),
    ]

    for fname, lclass in target_fields:
        vals = [getattr(h, fname, None) for h in result.horses]
        filled = sum(1 for v in vals if v not in (None, "", 0, 0.0, False, []))
        pct = int(filled / total_horses * 100) if total_horses else 0
        lines.append(f"    {fname:<24} [{lclass:<10}] {filled:>3}/{total_horses} ({pct:>3}%)")

    total_leakage_violations = 0
    for h in result.horses:
        val_res = validate_ml_eligibility(h)
        total_leakage_violations += val_res["leakage_violations_count"]

    hist_rows_count = sum(len(h.past_performance) for h in result.horses)

    lines.extend([
        "-" * 65,
        f"  Historical rows extracted : {hist_rows_count}",
        f"  Leakage violations        : {total_leakage_violations} (MUST BE 0)",
        f"  Parsing warnings          : {len(result.warnings)}",
        "=" * 65,
    ])

    return "\n".join(lines)


def _parse_page(page_num: int, lines: List[str], race_num: Optional[int] = None) -> Tuple[Optional[int], List[Horse]]:
    """
    Parse a single Computaform page.
    Returns (race_number, list_of_horses).
    """
    if race_num is None:
        for line in lines[:5]:   # header is always in first few lines
            m = _RACE_PAGE_HEADER_RE.match(line.strip())
            if m:
                race_num = int(m.group(1))
                break

    if race_num is None:
        return None, []

    logger.info(f"[INFO] Page {page_num}: Race Assigned = {race_num}")

    horses: List[Horse] = []
    # Find all horse entry positions
    horse_entries: List[Tuple[int, int, str]] = []  # (line_idx, draw, name)
    for idx, line in enumerate(lines):
        m = _HORSE_ENTRY_RE.match(line)
        if m:
            draw = int(m.group(1))
            name = m.group(2).strip()
            # Filter false positives
            if not _horse_name_is_valid(name):
                continue
            # Reject single-word all-caps that are known labels
            if name.upper() in _BAD_NAME_TOKENS:
                continue
            # Minimum: name must have at least one space or be >5 chars
            if len(name) < 4 and ' ' not in name:
                continue
            horse_entries.append((idx, draw, name.title()))

    # ── Step 3: for each horse entry, extract the structured fields ────────
    for entry_idx, (line_idx, draw, name) in enumerate(horse_entries):
        # Search window: from this horse line to the next horse line (or end of page)
        next_line_idx = horse_entries[entry_idx + 1][0] if entry_idx + 1 < len(horse_entries) else len(lines)
        block_lines = lines[line_idx: next_line_idx]

        jockey = "Unknown"
        weight = 0.0
        mr = None
        draw_confirmed = draw
        is_apprentice = False
        headgear = ""

        try:
            # Find the "CF Rate Headgear" label position — everything hangs off this
            cf_label_idx = None
            for bi, bl in enumerate(block_lines):
                if "CF Rate Headgear" in bl:
                    cf_label_idx = bi
                    break

            if cf_label_idx is not None:
                # Count how many label lines follow: Jockey, KGs, MR, Draw
                label_positions = {}
                for bi in range(cf_label_idx, min(cf_label_idx + 10, len(block_lines))):
                    stripped = block_lines[bi].strip()
                    if stripped == "Jockey":
                        label_positions["Jockey"] = bi
                    elif stripped == "KGs":
                        label_positions["KGs"] = bi
                    elif stripped == "MR":
                        label_positions["MR"] = bi
                    elif stripped == "Draw":
                        label_positions["Draw"] = bi

                # Values start after the "Draw" label
                if "Draw" in label_positions:
                    values_start = label_positions["Draw"] + 1
                    vals = []
                    for bi in range(values_start, min(values_start + 12, len(block_lines))):
                        vals.append(block_lines[bi].strip())

                    res = try_parse_jockey_and_fields(vals)
                    if res:
                        jockey, weight, mr, draw_confirmed, is_apprentice, headgear = res
        except (IndexError, ValueError):
            pass

        # Extract LIFE stats for form/runs: "LIFE: 21-4-3-5-2"
        life_wins = life_thirds = life_runs = 0
        for bl in block_lines:
            lm = re.match(r"LIFE:\s*(\d+)-(\d+)-(\d+)-(\d+)-(\d+)", bl.strip())
            if lm:
                life_runs = int(lm.group(1))
                life_wins = int(lm.group(2))
                life_thirds = int(lm.group(4))
                break

        f3_pct = int((life_wins + life_thirds) / life_runs * 100) if life_runs else 0

        # ── Extract ComputaForm F/B odds from this horse's block ────────────
        fb_str = _extract_fb_odds(block_lines)
        dec_odds = fractional_to_decimal(fb_str) if fb_str else 0.0

        logger.info(
            f"[INFO]   Race {race_num} #{draw_confirmed:02d} {name:<30} "
            f"J:{jockey:<22} KGs:{weight:.1f} MR:{mr} "
            f"F/B:{fb_str or 'N/A'} ({dec_odds:.2f})"
        )

        # ── Parse Phase 3 Bio & Form Normalized Data ───────────────────────
        norm_data = _parse_horse_bio_and_form(block_lines)

        # Extract trainer and sire from normalized_data if available
        parsed_trainer = norm_data.get("trainer", {}).get("normalized_value") or "Unknown"
        parsed_sire = norm_data.get("sire", {}).get("normalized_value")

        horses.append(Horse(
            horse=name,
            draw=draw_confirmed,
            saddle=draw,  # Original draw from line regex represents saddle number
            weight=weight,
            jockey=jockey,
            trainer=parsed_trainer,
            forecast_odds=dec_odds,   # decimal equivalent of ComputaForm F/B
            form_string="",
            runs=life_runs,
            wins=life_wins,
            third_places=life_thirds,
            f3_pct=f3_pct,
            merit_rating=mr,
            course_runs=0,
            horse_gear=headgear,
            first_timer=(life_runs == 0),
            running_comment="",
            comment_history=[],
            race=race_num,
            sire=parsed_sire,
            is_apprentice=is_apprentice,
            fb_odds_str=fb_str,       # raw string e.g. "15/10"
            market_odds=dec_odds,     # editable copy; UI may update this
            normalized_data=norm_data,
        ))

    logger.info(f"[INFO] Page {page_num}: Runner Count = {len(horses)}")
    return race_num, horses



# ─── Validation ───────────────────────────────────────────────────────────────

def _validate_races(
    races: Dict[int, List[Horse]], warnings: List[str]
) -> Dict[int, List[Horse]]:
    """Validate race numbers, runner counts. Return cleaned dict."""
    cleaned: Dict[int, List[Horse]] = {}
    sorted_race_nums = sorted(races.keys())
    if not sorted_race_nums:
        return cleaned

    expected = sorted_race_nums[0]

    for rn in sorted_race_nums:
        runners = races[rn]

        # Sequential check
        if rn != expected:
            msg = f"[WARNING] Invalid Race: expected {expected} but got {rn}"
            logger.warning(msg)
            warnings.append(msg)

        if len(runners) < 2:
            msg = f"[WARNING] Race {rn} has only {len(runners)} runner(s) — below minimum of 2. Skipping."
            logger.warning(msg)
            warnings.append(msg)
            expected = rn + 1
            continue

        if len(runners) > 25:
            msg = f"[WARNING] Race {rn} has {len(runners)} runners — above maximum of 25. Truncating."
            logger.warning(msg)
            warnings.append(msg)
            runners = runners[:25]

        cleaned[rn] = runners
        expected = rn + 1

    return cleaned


# ─── Extraction Report ────────────────────────────────────────────────────────

def _build_report(
    races: Dict[int, List[Horse]],
    skipped_pages: List[str],
    warnings: List[str],
) -> str:
    lines = [
        "",
        "=" * 60,
        "  COMPUTAFORM EXTRACTION REPORT",
        "=" * 60,
    ]
    total_horses = 0
    for rn in sorted(races.keys()):
        count = len(races[rn])
        total_horses += count
        lines.append(f"  Race {rn:2d} = {count} runners")
    lines.append("-" * 60)
    lines.append(f"  Total Races  = {len(races)}")
    lines.append(f"  Total Horses = {total_horses}")
    lines.append(f"  Pages Skipped = {len(skipped_pages)}")
    if warnings:
        lines.append(f"  Warnings = {len(warnings)}")
        for w in warnings:
            lines.append(f"    {w}")
    lines.append("=" * 60)
    return "\n".join(lines)


# ─── OCR Helpers ──────────────────────────────────────────────────────────────

def preprocess_image_for_ocr(image: "Image.Image") -> "Image.Image":
    from PIL import ImageEnhance, ImageFilter
    if image.mode != "L":
        image = image.convert("L")
    image = ImageEnhance.Contrast(image).enhance(2.0)
    image = ImageEnhance.Sharpness(image).enhance(1.5)
    return image.filter(ImageFilter.MedianFilter(size=3))


def extract_with_ocr(file_bytes: bytes, dpi: int = 300) -> List[Tuple[str, str]]:
    """Returns list of (page_text) for pages that pass the skip filter."""
    if not OCR_AVAILABLE:
        return []
    results = []
    try:
        with tempfile.TemporaryDirectory() as tmp:
            pdf_path = os.path.join(tmp, "input.pdf")
            with open(pdf_path, "wb") as f:
                f.write(file_bytes)
            images = pdf2image.convert_from_path(pdf_path, dpi=dpi, fmt="jpeg")
            for i, img in enumerate(images):
                logger.info(f"OCR: page {i + 1}/{len(images)}")
                img = preprocess_image_for_ocr(img)
                text = pytesseract.image_to_string(img, config="--psm 6 --oem 3", lang="eng")
                if not _page_should_skip(text):
                    results.append(text)
    except Exception as e:
        logger.warning(f"OCR failed: {e}")
    return results


# ─── Main Entry Point ─────────────────────────────────────────────────────────

def extract_from_pdf(file_bytes: bytes) -> ExtractionResult:
    """
    Main extraction entry point for Computaform South African racecards.
    """
    warnings: List[str] = []
    pages_read = 0
    pages_skipped = 0
    skipped_page_reasons: List[str] = []

    # Dict[race_num -> list of Horse]
    races_dict: Dict[int, List[Horse]] = {}
    raw_text_sample = ""

    try:
        # ── Step 1: Extract and filter candidate pages ───────────────────────
        candidate_pages = []
        all_page_lines: List[List[str]] = []   # ALL non-skipped pages (for cross-ref)
        use_fitz = False
        try:
            import fitz
            doc = fitz.open(stream=file_bytes, filetype="pdf")
            pages_read = len(doc)
            use_fitz = True
            for page_num_0, page in enumerate(doc):
                if page_num_0 >= _MAX_PAGES:
                    break
                text = page.get_text("text") or ""
                if not raw_text_sample and text.strip():
                    raw_text_sample = text[:3000]

                lines = text.splitlines()
                # Always collect ALL page lines for the Step 4b F/B cross-reference
                # pass — even skipped pages can contain the overview F/B table.
                all_page_lines.append(lines)

                skip_reason = _page_should_skip(text)
                if skip_reason:
                    reason = f"Page {page_num_0 + 1}: Skipped ({skip_reason})"
                    logger.info(f"[INFO] {reason}")
                    skipped_page_reasons.append(reason)
                    pages_skipped += 1
                    continue

                race_num_header = None
                for line in lines[:5]:
                    m = _RACE_PAGE_HEADER_RE.match(line.strip())
                    if m:
                        race_num_header = int(m.group(1))
                        break
                has_race_ref = "Race Ref" in text or "RACE REF" in text.upper()

                # ── Detect Computaform "first pages" ─────────────────────────
                # These pages start with the surface keyword (TURF / POLYTRACK)
                # and contain a lone race number within the first 30 lines.
                # They hold the first batch of runner detail cards for each race
                # and lack the "RACE N ... Continued" header.
                first_page_race_num = None
                if race_num_header is None and lines:
                    first_line = lines[0].strip().upper()
                    if first_line in _FIRST_PAGE_MARKERS:
                        for line in lines[1:30]:
                            m2 = _LONE_RACE_NUM_RE.match(line)
                            if m2:
                                candidate_num = int(m2.group(1))
                                if 1 <= candidate_num <= 20:
                                    first_page_race_num = candidate_num
                                    break

                if race_num_header is not None or has_race_ref or first_page_race_num is not None:
                    candidate_pages.append({
                        "page_num": page_num_0 + 1,
                        "lines": lines,
                        "text": text,
                        "race_num_header": race_num_header if race_num_header is not None else first_page_race_num,
                        "has_race_ref": has_race_ref,
                        "race_num": None,
                        "is_first_page": first_page_race_num is not None and race_num_header is None,
                    })
                    if not raw_text_sample:
                        raw_text_sample = text[:3000]
                else:
                    reason = f"Page {page_num_0 + 1}: No race header or race ref — skipped"
                    logger.info(f"[INFO] {reason}")
                    skipped_page_reasons.append(reason)
                    pages_skipped += 1
            doc.close()
        except Exception as e:
            logger.warning(f"PyMuPDF failed: {e}; falling back to pdfplumber")
            use_fitz = False

        if not use_fitz:
            try:
                import pdfplumber
                with pdfplumber.open(io.BytesIO(file_bytes)) as pdf:
                    pages_read = len(pdf.pages)
                    for pg_idx, pg in enumerate(pdf.pages):
                        if pg_idx >= _MAX_PAGES:
                            break
                        text = pg.extract_text() or ""
                        skip_reason = _page_should_skip(text)
                        if skip_reason:
                            reason = f"Page {pg_idx + 1}: Skipped ({skip_reason})"
                            logger.info(f"[INFO] {reason}")
                            skipped_page_reasons.append(reason)
                            pages_skipped += 1
                            continue

                        lines = text.splitlines()
                        race_num_header = None
                        for line in lines[:5]:
                            m = _RACE_PAGE_HEADER_RE.match(line.strip())
                            if m:
                                race_num_header = int(m.group(1))
                                break
                        has_race_ref = "Race Ref" in text or "RACE REF" in text.upper()

                        # ── Detect Computaform "first pages" ─────────────────
                        first_page_race_num = None
                        if race_num_header is None and lines:
                            first_line = lines[0].strip().upper()
                            if first_line in _FIRST_PAGE_MARKERS:
                                for line in lines[1:30]:
                                    m2 = _LONE_RACE_NUM_RE.match(line)
                                    if m2:
                                        candidate_num = int(m2.group(1))
                                        if 1 <= candidate_num <= 20:
                                            first_page_race_num = candidate_num
                                            break

                        if race_num_header is not None or has_race_ref or first_page_race_num is not None:
                            candidate_pages.append({
                                "page_num": pg_idx + 1,
                                "lines": lines,
                                "text": text,
                                "race_num_header": race_num_header if race_num_header is not None else first_page_race_num,
                                "has_race_ref": has_race_ref,
                                "race_num": None,
                                "is_first_page": first_page_race_num is not None and race_num_header is None,
                            })
                            if not raw_text_sample:
                                raw_text_sample = text[:3000]
                        else:
                            reason = f"Page {pg_idx + 1}: No race header or race ref — skipped"
                            logger.info(f"[INFO] {reason}")
                            skipped_page_reasons.append(reason)
                            pages_skipped += 1
                        # Always collect lines for the cross-reference pass
                        all_page_lines.append(lines)
            except Exception as e2:
                logger.warning(f"pdfplumber also failed: {e2}")

        # ── Step 2: Propagate race numbers to overview pages ─────────────────
        for i in range(len(candidate_pages)):
            cp = candidate_pages[i]
            if cp["race_num_header"] is not None:
                cp["race_num"] = cp["race_num_header"]
            else:
                # Look ahead for the first race header
                for j in range(i + 1, min(i + 4, len(candidate_pages))):
                    if candidate_pages[j]["race_num_header"] is not None:
                        cp["race_num"] = candidate_pages[j]["race_num_header"]
                        break

        # ── Step 3: Parse each assigned page ────────────────────────────────
        for cp in candidate_pages:
            race_num = cp["race_num"]
            if race_num is None:
                reason = f"Page {cp['page_num']}: No race number assigned — skipped"
                logger.info(f"[INFO] {reason}")
                skipped_page_reasons.append(reason)
                pages_skipped += 1
                continue

            race_num, horses = _parse_page(cp["page_num"], cp["lines"], race_num)
            if race_num not in races_dict:
                races_dict[race_num] = []

            # Merge runners; dedup by draw/horse name within same race
            existing_names = {h.horse.lower() for h in races_dict[race_num]}
            for h in horses:
                name_key = h.horse.lower()
                if name_key in existing_names:
                    logger.warning(f"[WARNING] Duplicate Horse: {h.horse} in Race {race_num}")
                    continue
                existing_names.add(name_key)
                races_dict[race_num].append(h)

        logger.info(f"[INFO] Raw race blocks detected: {len(races_dict)}")

        # ── Step 4: OCR fallback (only when nothing extracted) ───────────────
        if not races_dict:
            is_results_sheet = any(
                kw in raw_text_sample.upper()
                for kw in ["OFFICIAL RACE RESULTS", "WINNER & TAB", "POOL RESULTS", "TOTE FAVOURITE"]
            )
            if is_results_sheet:
                msg = "[WARNING] Uploaded PDF is a Results Sheet ('Official Race Results'), not an upcoming ComputaForm Race Card. Please upload an upcoming race card PDF."
                logger.warning(msg)
                warnings.append(msg)
            elif OCR_AVAILABLE:
                logger.info("[INFO] No horses from text — attempting OCR fallback")
                ocr_page_texts = extract_with_ocr(file_bytes)
                for i, text in enumerate(ocr_page_texts):
                    race_num, horses = _parse_page(i + 1, text.splitlines())
                    if race_num and horses:
                        races_dict.setdefault(race_num, []).extend(horses)
            else:
                msg = "[WARNING] No horses extracted and OCR is not available."
                logger.warning(msg)
                warnings.append(msg)

        # ── Step 4: Sort runners within each race by draw ───────────────────
        for rn in races_dict:
            races_dict[rn].sort(key=lambda h: h.draw)

        # ── Step 4b: Overview-page authoritative F/B override ────────────────
        # The ComputaForm overview page ("FIELDS, RATINGS FOR ...") contains the
        # definitive bookmaker board prices in the F/B column.  The per-horse
        # bio-card block may contain historical or ante-post odds that differ.
        # Strategy: scan ALL pages for the overview-table pattern and ALWAYS
        # overwrite fb_odds_str / market_odds with the overview value.  If no
        # overview match is found, the bio-card value already extracted is kept.
        #
        # Overview layout (consecutive lines):
        #   HORSE NAME <weight>        ← all-caps horse name
        #   <form marks>               ← e.g. "XX \t" or "X \t"  (optional)
        #   <comment text>             ← free text
        #   <fraction>                 ← standalone "4/1" or "16/10" etc.
        #
        _standalone_re = re.compile(r"^(\d{1,4})[/\-](\d{1,2})$")
        all_horses_flat = [h for rn in races_dict for h in races_dict[rn]]

        _no_dr_prefix_re = re.compile(r"^\d+\s*[-–]\s*\d+\s+")  # "8 - 13 " prefix

        for page_lines in all_page_lines:
            for line_idx, line in enumerate(page_lines):
                stripped = line.strip()
                stripped_up = stripped.upper()
                # Remove optional NO-DR prefix (e.g. "8 - 13 ") before matching
                stripped_core = _no_dr_prefix_re.sub("", stripped_up).strip()
                for h in all_horses_flat:
                    name_up = h.horse.upper()
                    if not (stripped_up.startswith(name_up) or stripped_core.startswith(name_up)):
                        continue
                    # Form marks like 'X', 'XX', 'XXX' are all-caps but are NOT
                    # horse names — don't stop on them.  Only bail if the line
                    # looks like a real multi-word name (2+ words with letters)
                    # AND is longer than 3 characters (not a single mark).
                    _FORM_MARKS = frozenset({'X', 'XX', 'XXX', 'XXXX', 'STOP'})
                    for ahead in page_lines[line_idx + 1: line_idx + 7]:
                        a = ahead.strip()
                        if not a:
                            continue
                        if _standalone_re.match(a):
                            if a != h.fb_odds_str:
                                logger.info(
                                    f"[INFO] Overview override: {h.horse} "
                                    f"{h.fb_odds_str!r} -> {a!r}"
                                )
                            h.fb_odds_str   = a
                            h.forecast_odds = fractional_to_decimal(a)
                            h.market_odds   = h.forecast_odds

                        # Extract trainer if missing or unresolved
                        if h.trainer in ("Unknown", "Distorted Humor", "William Longsword", "CF Rate Headgear") or not h.trainer:
                            m_tr = re.match(r"^([A-Z][A-Za-z\s\.\'\-]+?)\s+\d+(?:\.\d+)?%", a)
                            if m_tr:
                                cand_tr = m_tr.group(1).strip()
                                cand_tokens = set(re.findall(r"[A-Za-z]+", cand_tr.upper()))
                                if not cand_tokens.intersection(_BAD_NAME_TOKENS) and len(cand_tr) >= 3:
                                    h.trainer = cand_tr
                        # Stop scanning if we hit another horse name line
                        # (all-caps, 2+ words, contains letters, not a form mark)
                        words = a.split()
                        if (a.isupper()
                                and len(words) >= 2
                                and a not in _FORM_MARKS
                                and any(c.isalpha() for c in a)):
                            break

        # ── Step 5: Validate ─────────────────────────────────────────────────
        races_dict = _validate_races(races_dict, warnings)

        # ── Step 6: Flatten ──────────────────────────────────────────────────
        all_horses: List[Horse] = []
        for rn in sorted(races_dict.keys()):
            all_horses.extend(races_dict[rn])

        # ── Step 6b: Extract Historical Performance Rows & Audit Readiness ──
        valid_names = set(h.horse.title() for h in all_horses)
        hist_by_horse = _extract_historical_performance(all_page_lines, valid_horse_names=valid_names)
        for h in all_horses:
            key_match = h.horse.title()
            if key_match in hist_by_horse:
                h.past_performance = hist_by_horse[key_match]
            # Run Leakage Firewall audit per horse
            audit_res = validate_ml_eligibility(h)
            h.ml_readiness = audit_res["field_statuses"]

        logger.info(f"[INFO] Horses Parsed (total): {len(all_horses)}")

        # ── Step 7: Build and print report ───────────────────────────────────
        report = _build_report(races_dict, skipped_page_reasons, warnings)
        print(report)
        logger.info(report)

        confidence = min(len(all_horses) / 40.0, 1.0) if all_horses else 0.0

        raw_races_meta = extract_race_metadata(all_page_lines)
        races_meta = {r: raw_races_meta[r] for r in races_dict if r in raw_races_meta}

        return ExtractionResult(
            horses=all_horses,
            confidence=confidence,
            warnings=warnings,
            raw_text=raw_text_sample,
            pages_read=pages_read,
            pages_skipped=pages_skipped,
            report=report,
            races_meta=races_meta,
        )

    except Exception as e:
        logger.exception(f"extract_from_pdf failed: {e}")
        return ExtractionResult(
            horses=[],
            confidence=0.0,
            warnings=[f"Extraction error: {e}"],
            raw_text="",
            pages_read=0,
            pages_skipped=0,
            report="Extraction failed.",
        )


# ─── Backward-compat helpers ──────────────────────────────────────────────────

def _get_col_value(row_dict: dict, keywords: list) -> Optional[str]:
    for col in row_dict:
        if col is None:
            continue
        col_lower = str(col).lower()
        for key in keywords:
            if key in col_lower:
                val = row_dict[col]
                return str(val).strip() if val is not None else None
    return None


def _page_is_relevant(text: str) -> bool:
    keywords = ("race", "draw", "jockey", "trainer", "form", "odds", "fcst",
                 "maiden", "plate", "handicap", "stakes", "mile", "sprint")
    return any(kw in text.lower() for kw in keywords)


# ─── Demo Data ────────────────────────────────────────────────────────────────

def get_demo_horses() -> List[Horse]:
    return [
        Horse(
            horse="African Gold", draw=5, saddle=5, weight=60.0,
            jockey="W. Marwing", trainer="S. Tarry", forecast_odds=1.90,
            form_string="1-1-1-2-1", runs=5, wins=4, third_places=0, f3_pct=80,
            merit_rating=116, course_runs=3, horse_gear="B", first_timer=False,
            running_comment="Impressive win in last start.", comment_history=[],
            race=1
        ),
    ]
