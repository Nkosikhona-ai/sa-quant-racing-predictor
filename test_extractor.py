"""
test_extractor.py — Validate Computaform parser against Kenilworth PDF
Run: python test_extractor.py
"""

import logging
import sys
import os
import json
from collections import defaultdict

# Set up verbose logging so we see all [INFO] / [WARNING] messages
logging.basicConfig(
    level=logging.INFO,
    format="%(levelname)s  %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)

# ── Load extractor ────────────────────────────────────────────────────────────
sys.path.insert(0, os.path.dirname(__file__))
from extractor import extract_from_pdf, ExtractionResult, Horse

# ── PDF path ──────────────────────────────────────────────────────────────────
PDF_PATH = r"C:\Users\Ndlamini\OneDrive - City of Joburg\Documents\houses\KENILWORTH\HOLLYWOODBETS KENILWORTH@2026.06.21.pdf"

def main():
    print(f"\nLoading PDF: {PDF_PATH}")
    if not os.path.exists(PDF_PATH):
        print(f"ERROR: File not found: {PDF_PATH}")
        sys.exit(1)

    with open(PDF_PATH, "rb") as f:
        file_bytes = f.read()

    print(f"File size: {len(file_bytes):,} bytes\n")

    # ── Run extraction ────────────────────────────────────────────────────────
    result: ExtractionResult = extract_from_pdf(file_bytes)

    # ── Extraction report (already printed inside extractor) ─────────────────
    print(result.report)

    # ── Accuracy / validation report ─────────────────────────────────────────
    print("\n" + "=" * 55)
    print("  VALIDATION REPORT")
    print("=" * 55)

    # Group horses by race
    races = defaultdict(list)
    for h in result.horses:
        races[h.race].append(h)

    # Duplicate detection
    all_names = [h.horse.lower() for h in result.horses]
    seen = set()
    duplicates = []
    for h in result.horses:
        key = h.horse.lower()
        if key in seen:
            duplicates.append((h.race, h.horse))
        seen.add(key)

    print(f"  Pages read         : {result.pages_read}")
    print(f"  Pages skipped      : {result.pages_skipped}")
    print(f"  Races detected     : {len(races)}")
    print(f"  Horses detected    : {len(result.horses)}")
    print(f"  Duplicate horses   : {len(duplicates)}")
    for race_num, horse_name in duplicates:
        print(f"    -> Race {race_num}: {horse_name}")
    print(f"  Warnings           : {len(result.warnings)}")
    for w in result.warnings:
        print(f"    -> {w}")

    # Per-race detail
    print("\n  Per-race breakdown:")
    for rn in sorted(races.keys()):
        runners = races[rn]
        names = [h.horse for h in runners]
        print(f"    Race {rn:2d}: {len(runners)} runners")
        for h in runners:
            print(f"      #{h.draw:02d} {h.horse:<28} J:{h.jockey:<20} Odds:{h.forecast_odds:.2f}")

    # Confidence
    print(f"\n  Extraction confidence: {result.confidence:.0%} ({result.confidence_label})")
    print(f"  Valid result        : {result.is_valid}")
    print("=" * 55)

    # ── JSON dump (optional) ──────────────────────────────────────────────────
    out_path = os.path.join(os.path.dirname(PDF_PATH), "extraction_result.json")
    data = {
        "pages_read": result.pages_read,
        "pages_skipped": result.pages_skipped,
        "total_races": len(races),
        "total_horses": len(result.horses),
        "duplicates": [{"race": r, "horse": h} for r, h in duplicates],
        "warnings": result.warnings,
        "races": {
            str(rn): [
                {
                    "draw": h.draw,
                    "horse": h.horse,
                    "jockey": h.jockey,
                    "trainer": h.trainer,
                    "weight": h.weight,
                    "forecast_odds": h.forecast_odds,
                    "form": h.form_string,
                    "merit_rating": h.merit_rating,
                }
                for h in races[rn]
            ]
            for rn in sorted(races.keys())
        },
    }
    with open(out_path, "w", encoding="utf-8") as jf:
        json.dump(data, jf, indent=2, ensure_ascii=False)
    print(f"\n  Full JSON saved to: {out_path}")

if __name__ == "__main__":
    main()
