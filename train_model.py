"""
train_model.py — Generate calibration_model_v42.pkl
=====================================================
Run this script once to create the ML calibration model.
It generates synthetic SA horse racing training data,
trains a GradientBoostingClassifier, wraps it with
CalibratedClassifierCV (isotonic regression), and
saves the result as calibration_model_v42.pkl.

Usage:
    python train_model.py

If you have a real calibration_model_v42.pkl, drop it
into the same folder — this script will not overwrite it.
"""

import os
import sys
import numpy as np
import logging

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

MODEL_PATH = os.path.join(os.path.dirname(__file__), "calibration_model_v42.pkl")


def generate_synthetic_data(n_races: int = 2500, avg_runners: int = 8, seed: int = 42):
    """
    Simulate n_races SA horse races, producing one row per runner.
    Returns X (features), y (1 if winner, 0 otherwise).

    Feature order matches predictor.build_features():
      0  draw_bias
      1  form_score
      2  jockey_wr
      3  trainer_wr
      4  weight_penalty
      5  rating_norm
      6  experience
      7  field_size_norm
      8  has_form
      9  win_rate_form
      10 top3_rate_form
      11 composite_v38
    """
    rng = np.random.default_rng(seed)
    X_list, y_list = [], []

    DRAW_BIAS = {i: max(0.83, 1.06 - (i - 1) * 0.015) for i in range(1, 17)}

    for _ in range(n_races):
        n_runners = rng.integers(5, 16)
        field_size_norm = 1.0 / n_runners

        # Generate raw "ability" for each runner (hidden true strength)
        ability = rng.exponential(1.0, size=n_runners)

        rows = []
        for idx in range(n_runners):
            draw     = idx + 1
            db       = DRAW_BIAS.get(draw, 0.83)
            form_s   = rng.uniform(0.2, 1.0)
            jwr      = rng.uniform(0.10, 0.30)
            twr      = rng.uniform(0.10, 0.30)
            wt_pen   = rng.uniform(0.82, 1.00)
            rat_norm = rng.uniform(0.4, 1.0)
            exp_norm = rng.uniform(0.1, 0.9)
            has_form = float(rng.random() > 0.1)
            wrf      = rng.uniform(0.0, 0.4) if has_form else 0.0
            top3r    = rng.uniform(wrf, 0.7) if has_form else 0.0

            comp = (
                0.30 * form_s
              + 0.22 * rat_norm
              + 0.18 * (jwr / 0.30)
              + 0.12 * (twr / 0.30)
              + 0.10 * db
              + 0.08 * wt_pen
            )
            comp = np.clip(comp, 0.0, 1.0)

            # True win probability ∝ ability × comp × draw_bias
            latent = ability[idx] * (0.6 + 0.4 * comp) * db

            feats = [
                db, form_s, jwr, twr, wt_pen, rat_norm,
                exp_norm, field_size_norm, has_form, wrf, top3r, comp
            ]
            rows.append((feats, latent))

        # Winner is the horse with highest latent score
        latents = np.array([r[1] for r in rows])
        winner  = int(np.argmax(latents))

        for idx, (feats, _) in enumerate(rows):
            X_list.append(feats)
            y_list.append(1 if idx == winner else 0)

    X = np.array(X_list, dtype=np.float32)
    y = np.array(y_list, dtype=np.int32)
    logger.info("Generated %d samples, %d winners (%.2f%%)",
                len(y), y.sum(), 100 * y.mean())
    return X, y


def train_and_save():
    if os.path.exists(MODEL_PATH):
        logger.info("Model already exists at %s — skipping training.", MODEL_PATH)
        logger.info("Delete the file if you want to retrain.")
        return

    try:
        import joblib
        from sklearn.ensemble import GradientBoostingClassifier
        from sklearn.calibration import CalibratedClassifierCV
        from sklearn.model_selection import train_test_split
        from sklearn.metrics import (
            roc_auc_score, brier_score_loss, classification_report
        )
    except ImportError as e:
        logger.error("Missing dependency: %s", e)
        logger.error("Run: pip install scikit-learn joblib")
        sys.exit(1)

    logger.info("Generating synthetic training data...")
    X, y = generate_synthetic_data(n_races=3000)

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.20, random_state=42, stratify=y
    )

    logger.info("Training GradientBoostingClassifier...")
    base = GradientBoostingClassifier(
        n_estimators   = 200,
        max_depth       = 4,
        learning_rate   = 0.08,
        subsample       = 0.8,
        min_samples_leaf= 20,
        random_state    = 42,
    )

    logger.info("Wrapping with CalibratedClassifierCV (isotonic)...")
    model = CalibratedClassifierCV(base, method="isotonic", cv=5)
    model.fit(X_train, y_train)

    # ── Evaluate ──────────────────────────────────────────────────────────────
    probs = model.predict_proba(X_test)[:, 1]
    preds = (probs >= 0.5).astype(int)

    auc    = roc_auc_score(y_test, probs)
    brier  = brier_score_loss(y_test, probs)

    logger.info("─" * 50)
    logger.info("  ROC-AUC:     %.4f  (>0.70 is good)", auc)
    logger.info("  Brier Score: %.4f  (<0.15 is good)", brier)
    logger.info("─" * 50)
    print(classification_report(y_test, preds, target_names=["Non-winner", "Winner"]))

    # ── Save ──────────────────────────────────────────────────────────────────
    joblib.dump(model, MODEL_PATH, compress=3)
    size_kb = os.path.getsize(MODEL_PATH) / 1024
    logger.info("Model saved → %s  (%.1f KB)", MODEL_PATH, size_kb)


if __name__ == "__main__":
    train_and_save()
