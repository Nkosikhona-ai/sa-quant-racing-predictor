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
from typing import Dict, List, Optional, Tuple

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

        horses.append(Horse(
            horse=name,
            draw=draw_confirmed,
            saddle=draw,  # Original draw from line regex represents saddle number
            weight=weight,
            jockey=jockey,
            trainer="Unknown",  # trainer not in structured section
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
            is_apprentice=is_apprentice,
            fb_odds_str=fb_str,       # raw string e.g. "15/10"
            market_odds=dec_odds,     # editable copy; UI may update this
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
                            break
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

        logger.info(f"[INFO] Horses Parsed (total): {len(all_horses)}")

        # ── Step 7: Build and print report ───────────────────────────────────
        report = _build_report(races_dict, skipped_page_reasons, warnings)
        print(report)
        logger.info(report)

        confidence = min(len(all_horses) / 40.0, 1.0) if all_horses else 0.0

        return ExtractionResult(
            horses=all_horses,
            confidence=confidence,
            warnings=warnings,
            raw_text=raw_text_sample,
            pages_read=pages_read,
            pages_skipped=pages_skipped,
            report=report,
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
