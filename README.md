# 🏇 SA Quant Racing Predictor

> **A professional quantitative horse racing intelligence platform for South African racing — built for serious bettors.**

Upload any **SA Computaform / PhotoForm PDF** → configure track parameters → generate ranked predictions, Expected Value scores, value bets, longshot alerts, and full exotic betting intelligence (Exacta, Trifecta, Quartet, Swinger, Pick 6, BiPot, Jackpot).

---

## 📸 Preview

| Race Predictions | Exotics Intelligence |
|---|---|
| *(Race card with ranked predictions, EV scores, and signal tags)* | *(Exacta, Trifecta, Quartet, Swinger panels with probability math)* |

---

## ✨ Features

- **PDF Extraction**: Parses SA Computaform / PhotoForm race cards automatically — extracts horse name, draw, jockey, trainer, weight, form, rating, and race number per page.
- **Multi-Race Support**: Full meeting card extraction — navigate every race from the sidebar.
- **v3.13 Greyville Polytrack Engine**: Highly tuned draw-bias, jockey/trainer ratings, form scoring, and market signal capping.
- **v3.11 Turffontein Engine**: Separate Turffontein-specific model with independent draw-bias and factor weighting.
- **v4.2 ML Calibration Mode**: Gradient Boosting + Isotonic Regression calibrated probability engine (requires `calibration_model_v42.pkl`).
- **v3.9 7-Track Adaptive**: One model per SA track — Greyville, Turffontein, Kenilworth, Durbanville, Fairview, Scottsville, Vaal.
- **Expected Value (EV)**: `EV = p × (odds − 1) − (1 − p)` computed for every runner.
- **Value Bet Detection**: Automatically flags overlays where EV > 5% and confidence is Medium or High.
- **Longshot Alerts**: Flags high-yield runners at 10/1+ with positive EV.
- **🧬 Exotics Intelligence Panel**:
  - **Exacta** (1st & 2nd) with Harville probability and fair market odds.
  - **Swinger** (any 2 of top 3) — primary, secondary, coverage pairings.
  - **Trifecta** (1st, 2nd, 3rd) with Harville sequential probability and banker combinations.
  - **Quartet** (1st–4th) with straight and banked combinations.
  - **Multi-Race Permutations**: Pick 6, BiPot, Jackpot 1 & 2 across the full meeting.
- **EV Meeting Matrix**: Race-by-race expected value heatmap grid in the right panel.
- **Copyable Plain-Text Tables**: Monospace race result tables for copy/paste into messaging apps.
- **Demo Mode**: Fully synthetic demo race — no PDF needed to explore.

---

## 🛠️ Installation

### Requirements
- Python 3.10+
- pip

### Step 1 — Clone the repository
```bash
git clone https://github.com/YOUR_USERNAME/sa-quant-racing-predictor.git
cd sa-quant-racing-predictor
```

### Step 2 — Install dependencies
```bash
pip install -r requirements.txt
```

### Step 3 — Run the application
```bash
streamlit run app.py
```

The app will open at `http://localhost:8501`.

---

## 🚀 Usage

1. **Upload a PDF** — drag and drop your SA Computaform / PhotoForm PDF into the sidebar upload area.
2. **Click "Process Race"** — extracts all horses across all races in the document.
3. **Enter Odds (optional)** — input decimal market odds per horse (leave 0 to use model-estimated fair odds).
4. **Click "Generate Predictions"** — runs the full quantitative prediction engine across the entire meeting.
5. **Navigate Races** — click any race in the sidebar to switch between races.
6. **View Results**:
   - Top Prediction card with win probability and EV.
   - Race Rankings Table with signals.
   - Exotics Intelligence Panel (Exacta, Swinger, Trifecta, Quartet, Multi-Race).
   - Plain-text copyable tables for sharing.

---

## 🏁 Track Configuration

| Setting | Options |
|---|---|
| **Model Mode** | Greyville Poly v3.13 ⭐, Turffontein v3.11 ⭐, 7-Track Adaptive v3.9, ML Calibrated v4.2, Legacy Rule v3.8 |
| **Track / Venue** | Turffontein, Greyville, Kenilworth, Durbanville, Fairview, Scottsville, Vaal |
| **Surface** | Polytrack (Greyville only), Turf |
| **Distance** | 800m – 3200m (step 100m) |
| **Race Class** | Grade 1/2/3, Listed, MR Handicap, Maiden Plate, Pinnacle Stakes, Other Handicap |

---

## 📐 Prediction Engine

### Expected Value Formula

```
EV = p × (odds − 1) − (1 − p)
```

| Symbol | Meaning |
|---|---|
| `p` | Model win probability |
| `odds` | Decimal odds (user-entered or model-estimated) |
| `EV > 0` | Positive expectation |
| `EV > 0.05 + Medium+` | **Value Bet ✅** |
| `Odds ≥ 11 + EV > 0 + Rank ≤ 4` | **Longshot Alert 🔥** |

### v3.13 / v3.9 Engine Rules

1. **Track-Specific Draw Bias** — distance-aware, per-track tables.
2. **Jockey Win-Rate Scoring** — SA 2024/25 season baselines + track boosts.
3. **Trainer Win-Rate Scoring** — SA 2024/25 season baselines + track boosts.
4. **Form Score Calculation** — recency-weighted recent finishing positions.
5. **Weight Penalty** — 0.4% per 0.5 kg above 56 kg base weight.
6. **Merit Rating Normalization** — rated relative to field and class standard.
7. **Apprentice Jockey Allowance** — -2.5 kg effective weight reduction.
8. **Veteran Bonus** — form-scaled bonus for ≥ 15 run horses.
9. **Post-Race Distress Penalty** — -6% for last-start bottom-tier finishes.
10. **Second-Place Adjustment** — "knocking on door" boost / "bridesmaid" penalty.
11. **First-Timer Calibration** — set to moderate baseline with draw/jockey/trainer guidance.
12. **Market Signal Caps & Floors** — prevents wild divergences from market implied probability.

---

## 📁 Project Structure

```
sa-quant-racing-predictor/
├── app.py                    # Streamlit UI — main application
├── predictor.py              # Prediction engine (v3.13, v3.11, v3.9, v4.2, v3.8)
├── extractor.py              # PDF extraction engine (Computaform parser v6.0)
├── train_model.py            # ML model trainer for v4.2 calibration
├── calibration_model_v42.pkl # Pre-trained v4.2 GBM + isotonic calibration model
├── requirements.txt          # Python dependencies
├── test_extractor.py         # Extractor unit tests
├── style.css                 # Global UI stylesheet (referenced by index.html)
├── index.html                # Static web fallback version
├── data.js                   # Static race data for index.html
├── run.bat                   # Windows launcher menu
└── README.md                 # This file
```

---

## 🌐 Deployment

### Streamlit Community Cloud (recommended)

1. Push this repo to GitHub.
2. Go to [share.streamlit.io](https://share.streamlit.io).
3. Connect your GitHub repo.
4. Set **Main file path** to `app.py`.
5. Click **Deploy** — live in 2 minutes.

### Vercel (API/Static)

Vercel does not natively support Python/Streamlit. For Vercel deployment, use the static HTML fallback (`index.html`) or deploy the Streamlit app on a separate platform and embed it.

### Local Docker (advanced)

```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
EXPOSE 8501
CMD ["streamlit", "run", "app.py", "--server.port=8501", "--server.address=0.0.0.0"]
```

```bash
docker build -t sa-quant-racing .
docker run -p 8501:8501 sa-quant-racing
```

---

## 📋 Requirements

| Package | Version | Purpose |
|---|---|---|
| `streamlit` | ≥1.45.0 | Web app framework |
| `pandas` | ≥2.1.0 | Data handling |
| `numpy` | ≥1.26.0 | Numerical computing |
| `plotly` | ≥5.20.0 | Interactive charts |
| `pdfplumber` | ≥0.10.4 | PDF text extraction |
| `PyMuPDF` | ≥1.23.0 | PDF rendering fallback |
| `scikit-learn` | ≥1.4.0 | ML model (v4.2 mode) |
| `joblib` | ≥1.3.2 | Model serialisation |
| `Pillow` | ≥10.0.0 | Image processing (OCR) |
| `pytesseract` | ≥0.3.10 | OCR engine wrapper (optional) |
| `pdf2image` | ≥1.16.3 | PDF→image for OCR (optional) |

> **Note**: `pytesseract` requires Tesseract OCR installed on the system. OCR is used only as a fallback when text extraction fails.

---

## ⚖️ Disclaimer

This software is provided for **informational and research purposes only**. It does not constitute financial, betting, or gambling advice. Horse racing involves risk — past model performance does not guarantee future results. Always bet responsibly within your means.

---

## 📜 License

MIT License — see [LICENSE](LICENSE) for details.

---

*Built with ❤️ for the SA racing community.*
