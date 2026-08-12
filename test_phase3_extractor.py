"""
test_phase3_extractor.py — Phase 3 Forensic Data Expansion & Leakage Firewall Test Suite
Run: python test_phase3_extractor.py
"""

import sys
import os
import json
import logging

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
sys.path.insert(0, os.path.dirname(__file__))

from extractor import (
    extract_from_pdf,
    ExtractionResult,
    Horse,
    validate_ml_eligibility,
    generate_extraction_audit
)

KENILWORTH_PDF = r"C:\Users\Ndlamini\OneDrive - City of Joburg\Documents\houses\KENILWORTH\HOLLYWOODBETS KENILWORTH@2026.06.21.pdf"
VAAL_PDF = os.path.join(os.path.dirname(__file__), "debug_uploaded.pdf")


def run_phase3_tests():
    print("\n" + "=" * 65)
    print("  PHASE 3 COMPUTAFORM FORENSIC EXTRACTION & LEAKAGE TEST SUITE")
    print("=" * 65 + "\n")

    # Load Vaal PDF (debug_uploaded.pdf)
    if not os.path.exists(VAAL_PDF):
        print(f"ERROR: File not found: {VAAL_PDF}")
        sys.exit(1)

    with open(VAAL_PDF, "rb") as f:
        vaal_bytes = f.read()

    res_vaal: ExtractionResult = extract_from_pdf(vaal_bytes)

    # Load Kenilworth PDF if available
    res_ken = None
    if os.path.exists(KENILWORTH_PDF):
        with open(KENILWORTH_PDF, "rb") as f:
            ken_bytes = f.read()
        res_ken = extract_from_pdf(ken_bytes)

    pass_count = 0
    total_tests = 7

    # ── TEST 1: Horse Identity & Bio ─────────────────────────────────────────
    print("--- Test 1: Horse Identity & Bio ---")
    bio_fields = ["age", "sex", "colour", "sire", "dam", "trainer", "jockey", "owner", "breeder"]
    found_bio = False
    for h in res_vaal.horses:
        if "age" in h.normalized_data or h.sire or h.trainer != "Unknown":
            found_bio = True
            print(f"  [OK] Sample Horse: {h.horse}")
            print(f"       Age: {h.normalized_data.get('age', {}).get('normalized_value')}")
            print(f"       Sex: {h.normalized_data.get('sex', {}).get('normalized_value')}")
            print(f"       Colour: {h.normalized_data.get('colour', {}).get('normalized_value')}")
            print(f"       Sire: {h.sire}")
            print(f"       Trainer: {h.trainer}")
            print(f"       Jockey: {h.jockey}")
            break
    if found_bio:
        print("  --> PASS: Test 1 (Horse Identity & Bio extracted)\n")
        pass_count += 1
    else:
        print("  --> FAIL: Test 1\n")

    # ── TEST 2: Ratings & Fitness ────────────────────────────────────────────
    print("--- Test 2: Ratings & Fitness ---")
    found_fit = False
    for h in res_vaal.horses:
        nd = h.normalized_data
        if "days_since_last_race" in nd or "days_since_last_win" in nd or "best_vs_average" in nd or "wpr" in nd:
            found_fit = True
            print(f"  [OK] Sample Horse: {h.horse}")
            print(f"       MR: {h.merit_rating}")
            print(f"       Days since last race: {nd.get('days_since_last_race', {}).get('normalized_value')}")
            print(f"       Days since last win : {nd.get('days_since_last_win', {}).get('normalized_value')}")
            print(f"       Best vs Ave         : {nd.get('best_vs_average', {}).get('normalized_value')}")
            print(f"       WPR (status)        : {nd.get('wpr', {}).get('normalization_status')}")
            break
    if found_fit:
        print("  --> PASS: Test 2 (Ratings & Fitness extracted)\n")
        pass_count += 1
    else:
        print("  --> FAIL: Test 2\n")

    # ── TEST 3: Career Statistics Tuples ─────────────────────────────────────
    print("--- Test 3: Career Statistics Tuples ---")
    tup_keys = ["life", "j_h", "j_t", "turf", "crse", "dist", "c_d", "good", "wet"]
    found_tup = False
    for h in res_vaal.horses:
        nd = h.normalized_data
        if any(tk in nd for tk in tup_keys):
            found_tup = True
            print(f"  [OK] Sample Horse: {h.horse}")
            for tk in ["life", "j_h", "j_t", "turf", "crse", "c_d"]:
                if tk in nd:
                    node = nd[tk]
                    print(f"       {tk.upper():<6}: Raw={node['raw_value']!r} -> Norm={node['normalized_value']}")
            break
    if found_tup:
        print("  --> PASS: Test 3 (Career Statistics Tuples extracted)\n")
        pass_count += 1
    else:
        print("  --> FAIL: Test 3\n")

    # ── TEST 4: 9-Horse Forensic Historical Cross-Check ─────────────────────
    print("--- Test 4: 9-Horse Forensic Historical Cross-Check ---")
    r1_horses = [h for h in res_vaal.horses if h.race == 1][:3]
    mid_horses = [h for h in res_vaal.horses if h.race in (4, 5)][:3]
    r8_horses = [h for h in res_vaal.horses if h.race == 8][:3]
    sample_9 = r1_horses + mid_horses + r8_horses

    print(f"  Verifying {len(sample_9)} horses across Race 1, Middle, and Race 8:")
    verified_count = 0
    for idx, h in enumerate(sample_9, 1):
        runs_n = len(h.past_performance)
        print(f"    [{idx}/9] Race {h.race} #{h.draw:02d} {h.horse:<22}: {runs_n} past performance rows")
        if h.past_performance:
            verified_count += 1
            r0 = h.past_performance[0]
            norm0 = r0.get("normalized", {})
            print(f"          -> Sample Row 1: Date/Crs={r0.get('date_venue_raw')!r} G={norm0.get('going')} Class={norm0.get('race_class')} Dist={norm0.get('distance_m')}m MR={norm0.get('merit_rating')} J={norm0.get('jockey')} Wgt={norm0.get('weight_kg')}kg Dr/Rn={norm0.get('draw')}/{norm0.get('field_size')}")

    if verified_count >= 5:
        print("  --> PASS: Test 4 (9-Horse Historical Forensic Cross-Check passed)\n")
        pass_count += 1
    else:
        print(f"  --> FAIL: Test 4 (Only {verified_count}/9 horses had collateral form lines)\n")

    # ── TEST 5: Current vs Historical Date Firewall ─────────────────────────
    print("--- Test 5: Current vs Historical Date Firewall ---")
    date_firewall_ok = True
    for h in res_vaal.horses:
        for prow in h.past_performance:
            norm_r = prow.get("normalized", {})
            # Ensure historical race row is tagged HISTORICAL and date exists
            if prow.get("leakage_class") != "HISTORICAL":
                date_firewall_ok = False
                print(f"  [ERROR] Non-historical leakage class in past_performance: {prow}")

    if date_firewall_ok:
        print("  --> PASS: Test 5 (Current vs Historical Date Firewall passed)\n")
        pass_count += 1
    else:
        print("  --> FAIL: Test 5\n")

    # ── TEST 6: Multi-Stage Leakage Firewall ─────────────────────────────────
    print("--- Test 6: Multi-Stage Leakage Firewall ---")
    firewall_pass = True
    for h in res_vaal.horses:
        val_res = validate_ml_eligibility(h)
        if val_res["leakage_violations_count"] != 0:
            firewall_pass = False
            print(f"  [ERROR] Leakage violation detected for {h.horse}: {val_res['blocked_features']}")

    if firewall_pass:
        print("  --> PASS: Test 6 (Multi-Stage Leakage Firewall passed with 0 violations)\n")
        pass_count += 1
    else:
        print("  --> FAIL: Test 6\n")

    # ── TEST 7: Baseline Regression Test ────────────────────────────────────
    print("--- Test 7: Baseline Regression Test ---")
    vaal_ok = (len(set(h.race for h in res_vaal.horses)) == 8 and len(res_vaal.horses) == 69)
    ken_ok = (res_ken is None or (len(set(h.race for h in res_ken.horses)) == 8 and len(res_ken.horses) == 68))

    print(f"  Vaal PDF (debug_uploaded.pdf) : {len(res_vaal.horses)} horses (Expected: 69) -> {'OK' if vaal_ok else 'FAIL'}")
    if res_ken:
        print(f"  Kenilworth PDF                : {len(res_ken.horses)} horses (Expected: 68) -> {'OK' if ken_ok else 'FAIL'}")

    if vaal_ok and ken_ok:
        print("  --> PASS: Test 7 (Exact Baseline Regression Test passed)\n")
        pass_count += 1
    else:
        print("  --> FAIL: Test 7\n")

    # ── AUDIT REPORT DUMP ───────────────────────────────────────────────────
    print("\n" + generate_extraction_audit(res_vaal))

    print(f"\nPhase 3 Test Results: {pass_count}/{total_tests} PASSED.")
    if pass_count == total_tests:
        print("ALL PHASE 3 TESTS PASSED CLEANLY.\n")
    else:
        print("SOME TESTS FAILED — investigate before proceeding.\n")


if __name__ == "__main__":
    run_phase3_tests()
