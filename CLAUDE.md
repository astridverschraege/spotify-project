# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**Project R.E.M.** (Regulation of Emotion through Music) is a research project that studies whether personalized music playlists can regulate emotional states. The system generates three playlist types (calm, neutral, energy) from participants' Spotify data, cross-referenced with smartwatch biometrics and self-reported mood check-ins.

Participants are anonymized using fruit codenames: `bosbes`, `kiwi`, `kokosnoot`, `limoen`, `peer`, `watermeloen`, etc.

**Contact:** rem.studie@gmail.com

---

## Research Framework

### Core Principle: ISO

The **ISO principle** is the scientific basis for playlist construction. Rather than jumping directly to a target emotional state, music is ordered to *gradually transition* from the listener's current arousal level toward the desired state — mirroring established music therapy practice.

- **Calm playlist**: Descends in BPM and energy → stress reduction / relaxation
- **Energy playlist**: Ascends in BPM and energy → arousal / alertness
- **Neutral playlist**: Stable BPM and energy → control condition, no directional shift

### Why Participants' Own Music?

Research shows self-chosen music is significantly more effective at emotion regulation than unfamiliar selections. The system is therefore built around each participant's personal Spotify library (exported via Exportify), not a curated library.

### Spotify Audio Features Used

| Feature | Range | Role |
|---------|-------|------|
| `tempo` | BPM | Primary filter — defines calm/neutral/energy boundary |
| `energy` | 0–1 | Secondary filter — perceptual intensity |
| `valence` | 0–1 | Musical positivity; min threshold on energy playlist |
| `danceability` | 0–1 | Beat regularity; used in energy playlist |
| `acousticness` | 0–1 | Acoustic vs electronic; tunable for calm |
| `loudness` | dB | Volume dynamics; min/max thresholds per playlist type |

### Research Questions

1. Can ISO-ordered personalized playlists measurably reduce stress (objectively, via smartwatch)?
2. Does reduced physiological stress correlate with improved self-reported mood?
3. Can we classify playlist type from biometric signals alone?
4. Can we predict mood outcome from physiological state + playlist type?
5. Can unsupervised music clustering (audio features) optimize playlist generation beyond manual parameter tuning?

### ML Tracks

Four ML tracks explored across `notebooks/ml/` and `scripts/analysis/`:

- **Circadian ML** — Ridge/RF/GBM predicting mood_delta / stress_delta from circadian baseline deviations + session features. Best model: Ridge (LOO R²=0.318 for mood_delta).
- **Bayesian recommender** — Hierarchical PyMC model inferring optimal playlist type per participant from posterior mood deltas.
- **Supervised music classification** — Classifies songs as Calm/Neutral/Energy using trained models on audio features; produces per-participant `classified_songs.csv`.
- **Unsupervised music clustering** — GMM (k=3) on audio features; validates whether data-driven clusters align with ISO arousal framework.

### Current ML Metrics (mood_delta, LOO-CV — as of 2026-06-06)

N=82 sessions, 4 participants with biometric data. Per-fold median imputation within Pipeline to prevent leakage.

| Model | MAE | RMSE | R² (LOO) | Overfit gap |
|---|---|---|---|---|
| Dummy basislijn | 1.817 | 2.460 | −0.025 | — |
| **Ridge regressie** | **1.578** | **2.007** | **0.318** | — |
| Random Forest | 1.666 | 2.128 | 0.233 | — |
| Gradient Boosting | 1.778 | 2.295 | 0.108 | 0.712 |

Best model: Ridge (MAE=1.578, R²=0.318). GB overfits severely (train R²=0.820 vs LOO R²=0.108). Ridge also best for stress_delta (LOO R²=0.870), but stress predictions do not generalize across participants (LOPO MAE=5.868 vs LOO MAE=2.866). `mood_before_score` and `baseline_deviation_entry` are top predictors. Results remain exploratory at N=82.

### Final Output

A **Shiny for Python app** styled like "Spotify Wrapped" — per-participant summary with biometric arcs, model explainability, and Bayesian recommendations. Fully built with 9 modules. Run with `uv run shiny run ui/app.py` or `./ui/run_app.sh`.

---

## Setup & Dependencies

```bash
# Install dependencies (uses uv package manager)
uv sync
```

Uses a `.venv` managed by uv. All dependencies are tracked in `pyproject.toml` and `uv.lock`. Run commands with `uv run <command>` or activate the venv (`source .venv/Scripts/activate` on Windows Git Bash).

Requires Python 3.12+. Key dependencies: `pandas`, `numpy`, `matplotlib`, `seaborn`, `scikit-learn`, `scipy`, `statsmodels`, `plotly`, `shiny`, `fitparse`, `rich`, `questionary`, `pymc`, `arviz`, `torch`, `shap`.

**Important:** Always use `uv run python` instead of bare `python` — bare `python` may pick up a conda environment with incompatible package versions.

---

## Key Commands

### Full Pipeline (extraction → baseline → sessions)

```bash
# Run all 3 pipeline stages for all participants
./scripts/pipeline.sh

# Run for specific participants
./scripts/pipeline.sh bosbes peer

# Or via Python directly
uv run python scripts/main.py --all
uv run python scripts/main.py --participants bosbes peer
```

### Notebooks (regenerate ML outputs)

```bash
# Fast mode — reuses pre-fitted models (~1–3 min)
./scripts/notebooks.sh

# Fresh mode — refits all models from scratch (~10 min)
./scripts/notebooks.sh --fresh
```

### Shiny App

```bash
uv run shiny run ui/app.py
# or
./ui/run_app.sh
./ui/run_app.sh --reload  # dev mode
```

### Playlist Generation

```bash
# Via shell wrapper
./scripts/playlists.sh all [codename]
./scripts/playlists.sh generate [codename] --calm-tempo-max 95

# Or directly
uv run python scripts/playlists/spotify_cli.py all [codename]
uv run python scripts/playlists/spotify_cli.py prepare [codename]
uv run python scripts/playlists/spotify_cli.py generate [codename]
uv run python scripts/playlists/spotify_cli.py analyse [codename]

# Quick analysis of existing playlists
uv run python scripts/playlists/quick_playlist_analysis.py --calm path/to/calm.csv --upbeat path/to/upbeat.csv --id [codename]

# CLI help
uv run python scripts/playlists/spotify_cli.py --help
uv run python scripts/playlists/spotify_cli.py --help-full
```

### One-shot Analysis Scripts

```bash
# LSTM biometric arc predictor (~5 min, requires torch)
uv run python scripts/analysis/lstm_arc.py

# GMM clustering validation
uv run python scripts/analysis/gmm_clustering_validation.py

# Music classification validation
uv run python scripts/analysis/music_classification_validation.py

# Data gap audit
uv run python scripts/analysis/trace_gap_audit.py
```

### Syntax Checking (no test suite yet)

```bash
uv run python -m py_compile scripts/playlists/spotify_cli.py
```

### SSL note

Conda sets `SSL_CERT_DIR` and `SSL_CERT_FILE` env vars that conflict with uv. If `uv add` or `uv sync` fails with `UnknownIssuer`, run with:
```bash
SSL_CERT_DIR="" SSL_CERT_FILE="" uv add <package> --system-certs
```

---

## Architecture

### Overview

```
scripts/main.py           ← orchestrates 3 pipeline stages
scripts/pipeline.sh       ← shell wrapper for main.py
scripts/notebooks.sh      ← runs notebooks/ml/*.ipynb to regenerate outputs
scripts/playlists.sh      ← shell wrapper for playlist CLI

scripts/extraction/       ← Pipeline 1: raw exports → per-minute CSVs
scripts/baseline/         ← Pipeline 2: per-minute → baselines + feature matrix
scripts/sessions/         ← Pipeline 3: feature matrix → session effects + significance

scripts/playlists/        ← Playlist generator (standalone, ISO ordering)
scripts/analysis/         ← One-shot diagnostic/validation scripts

notebooks/ml/             ← 4 ML notebooks (produce outputs consumed by UI)
models/                   ← Pre-fitted models (committed for reproducibility)
ui/                       ← Shiny for Python app (9 modules)
```

### Pipeline 1 — Extraction (`scripts/extraction/`)

Converts raw wearable GDPR exports → per-minute CSVs with activity classifications.

- `pipeline.py` — Entry point; auto-detects device type (Garmin: `*.zip`; Huawei: `health detail data*.json`); skip logic based on file freshness
- `garmin_pipeline.py` — Parses Garmin FIT files → `garmin_minute_stress.csv`, `garmin_minute_hr.csv`, `garmin_minute_activity.csv`
- `huawei_pipeline.py` — Parses Huawei JSON + Excel fallback → `huawei_minute_stress.csv`, `huawei_minute_hr.csv`
- `activity_classifier.py` — Labels activity state per minute from HR + body battery
- `checkin_utils.py` — Loads & normalizes mood check-in CSV; **note:** Google Forms exports dates as D-M-YYYY; fix applied automatically
- `fit_extractor.py` — Low-level Garmin FIT binary parser
- Outputs land in `data/wearables/[codename]/processed/`
- Timezone note: FIT files are UTC; check-in times are CET (UTC+1)
- Check-in date format: `Welke dag deed je een check-in?` exports as `YYYY-MM-DD` (ISO 8601). The `Tijdstempel` column uses `YYYY/MM/DD H:MM:SS a.m./p.m.`. `checkin_utils.py` auto-detects day/month swaps (mobile form bug) and emits a warning per corrected row.

### Pipeline 2 — Baseline (`scripts/baseline/`)

Computes circadian baselines and per-session ML feature matrix.

- `pipeline.py` — Entry point; runs circadian baseline → feature matrix → recovery curves; skip logic based on file freshness
- `circadian_baseline.py` — Per-participant hourly stress/HR means on non-session days; exports `hourly_baseline.csv`
- `baselines.py` — `PersonBaseline` class; exponential recovery curve fitting per activity state; computes baseline deviations for ML features
- Outputs land in `data/analysis/[codename]/circadian_baselines/` and `data/analysis/circadian_baselines/feature_matrix.csv`

### Pipeline 3 — Sessions (`scripts/sessions/`)

Analyzes session effects, arc patterns, significance, and recovery.

- `pipeline.py` — Entry point; runs 5 sub-stages: session_effect → session_features → arc_analysis → significance → recovery
- `session_effect.py` — Per-session recovery advantage vs baseline curve; Wilcoxon tests
- `session_features.py` — Builds flat feature table per session (stress_arc_slope, max_stress, etc.)
- `session_arc_analysis.py` — Stress arc heatmaps, rolling baselines, long-term trend plots
- `circadian_significance.py` — Wilcoxon signed-rank tests (pre vs during/post), mood_delta tests, OLS trend; outputs `significance_tests.csv`
- `recovery_analysis.py` — Quality-filtered recovery metrics (R²≥0.5 threshold)

### Playlist Generator (`scripts/playlists/`)

Standalone subsystem — generates ISO-ordered playlists per participant from Exportify CSV exports.

- `spotify_cli.py` — Entry point; subcommands: prepare, generate, analyse, all
- `spotify_modules/prepare.py` — Combines and cleans Exportify CSV exports
- `spotify_modules/generate.py` — BPM/energy filtering, ISO principle ordering, loudness smoothing
- `spotify_modules/analyse.py` — Validates outputs against 4 criteria; generates visualizations
- `spotify_modules/iso_validation.py` — ISO principle-specific validation logic
- Outputs land in `data/playlists/[codename]/playlists_generated/`

### One-shot Analysis Scripts (`scripts/analysis/`)

Standalone diagnostic and validation tools — not part of the main pipeline.

- `lstm_arc.py` — 1-layer LSTM (32 hidden units) on per-minute stress/HR → mood_delta; LOO-CV with 5× augmentation; gradient saliency; requires `torch`
- `gmm_clustering_validation.py` — Cross-tabulates GMM clusters vs rule-based labels; outputs heatmaps + cluster profiles
- `music_classification_validation.py` — Kruskal-Wallis + regression: playlist type vs mood_delta
- `trace_gap_audit.py` — Biometric data gap diagnostics per session

### ML Notebooks (`notebooks/ml/`)

Four notebooks that produce all model outputs consumed by the Shiny app. Run via `./scripts/notebooks.sh`.

| Notebook | Purpose | Output |
|----------|---------|--------|
| `1_circadian_ml.ipynb` | Ridge/RF/GBM baseline deviation regression + SHAP | `model_results_*.csv`, `models/circadian_ml/models.pkl` |
| `2_bayesian_recommender.ipynb` | Per-participant Bayesian posterior inference | `recommendations.json`, `models/bayesian_recommender/trace.nc` |
| `3_music_class_supervised.ipynb` | Supervised playlist classification per participant | `classified_songs.csv`, `models/music_classification/` |
| `4_music_class_unsupervised.ipynb` | GMM clustering for song arousal (k=3) | `classified_songs_k3.csv`, `models/music_unsupervised/` |

Other notebooks: `notebooks/visualisation/recovery_analysis.ipynb`, `notebooks/experimental/shadow_session_detection.ipynb`, `notebooks/who_needs_reminding.ipynb` (Colab — flags participants not checked in for 3+ days).

### Shiny App (`ui/`)

9-module interactive Shiny for Python app for exploring study results per participant.

| Module | Purpose |
|--------|---------|
| `home.py` | Landing page — study overview |
| `circadian.py` | Circadian baseline and deviation plots |
| `model.py` | ML model results and SHAP visualizations |
| `results.py` | Session results and arc comparisons |
| `recovery.py` | Recovery curve analysis |
| `recommendation.py` | Bayesian playlist recommendations |
| `session_replay.py` | Individual session replay with per-minute traces |
| `music_browser.py` | Browse classified songs, filter by mood/energy |
| `pipeline.py` | Data pipeline status monitor |
| `science.py` | Study background and methods |

Utilities in `ui/utils/`: `data_loader.py` (loads all analysis outputs, caches `PARTICIPANTS`), `chart_helpers.py`, `mood_valence.py`, `playlist_salt.py`.

### Data Flow

```
Participant → Exportify CSV → playlists/prepare → generate → analyse → Playlist CSVs
Participant → Garmin/Huawei GDPR export → extraction/ → baseline/ → sessions/ → Analysis CSVs
Participant → Google Form → data/checkins/ (or data/check_in/ on this machine)
                                                          ↓
                                              notebooks/ml/ → models/ + data/analysis/
                                                          ↓
                                                      ui/app.py
```

### Data Layout

```
data/
├── playlists/[codename]/         # Input Exportify CSVs + generated playlists
│   └── playlists_generated/      # Output: calm/neutral/energy CSVs + analysis plots
├── check_in/                     # Google Forms check-in export (single CSV)
├── wearables/[codename]/
│   ├── raw/                      # Gitignored — contains PII (email, profile, location)
│   └── processed/                # Committed — anonymized pipeline outputs
│       ├── garmin_minute_stress.csv / huawei_minute_stress.csv
│       ├── garmin_minute_hr.csv / huawei_minute_hr.csv
│       ├── garmin_minute_activity.csv
│       └── session_traces/       # Per-minute CSV per session
└── analysis/
    ├── [codename]/               # Per-participant analysis outputs
    │   ├── circadian_baselines/  # hourly_baseline.csv + plots
    │   ├── bayesian_recommender/ # recommended_songs.json + plots
    │   ├── session_effects.csv
    │   ├── session_features.csv
    │   ├── recovery_baselines.csv
    │   └── classified_minutes.csv
    ├── circadian_baselines/      # feature_matrix.csv, model_results_*.csv, significance_tests.csv
    ├── bayesian_recommender/     # recommendations.json, parameter_summary.csv
    ├── music_classification/     # classified_songs_k3.csv
    └── session_arc/              # Arc deviations and significance results

models/                           # Pre-fitted models (committed for reproducibility)
├── circadian_ml/models.pkl
├── bayesian_recommender/trace.nc
├── music_classification/         # Per-participant scalers & configs
└── music_unsupervised/
```

### Baseline Deviation — How It Is Computed

**Baseline deviation** is the strongest biometric signal: it compares session-window stress against the participant's typical stress at that same time of day on non-session days, controlling for circadian rhythm.

```
baseline_deviation = pre_stress_mean - expected_stress_at_hour
hr_baseline_deviation = pre_hr_mean - expected_hr_at_hour
```
- `pre_stress_mean` / `pre_hr_mean` — participant's measured stress/HR during the pre-session window
- `expected_stress_at_hour` / `expected_hr_at_hour` — mean stress/HR at that same hour on non-session days (hours with <5 obs → NaN)
- Raw unit difference, not normalized (not a z-score)

**Two baselines, two purposes:**
- **All-days baseline** (non-session days) → ML features (`baseline_deviation_entry`, `hr_baseline_deviation`). More data = more stable per-session deviation estimates.
- **Pre-study baseline** (days before first session only) → long-term trend analysis. Fixed reference point, not contaminated by cumulative session effects.

### Significance Testing

Handled by `scripts/sessions/circadian_significance.py`. Per-participant only (no pooling). Three test types:
- **Immediate effects** (Wilcoxon signed-rank): pre vs during/post stress & HR — unstratified, by playlist, by playlist × activity state
- **Mood effect** (one-sample Wilcoxon): mood_delta ≠ 0 per playlist type
- **Long-term trend** (OLS): pre_study deviation over session sequence number
All two-tailed, N≥5 guard. Output: `data/analysis/circadian_baselines/significance_tests.csv`

### Playlist Parameters (defaults in `spotify_cli.py`)

| Playlist | Tempo (BPM) | Energy  | ISO Order      |
|----------|-------------|---------|----------------|
| Calm     | 50–95       | < 0.9   | Descending BPM |
| Neutral  | 95–115      | 0.2–0.8 | Stable         |
| Energy   | 120–180     | > 0.7   | Ascending BPM  |

Validation passes when 3–4 of 4 criteria are met: tempo ranges, energy separation, ≥15 BPM gap between calm/energy, ≥25 min duration each. Target playlist size: 12 songs (~30 min), minimum 10.

---

## Important Notes

- `data/wearables/*/raw/` is gitignored — never commit raw wearable data (contains participant PII)
- The check-in CSV is the join key between playlist sessions and biometric data — participant codename + date + time must align across both sources. The extraction pipeline searches `data/checkins/*.csv` by default; use `--checkin <path>` to override.
- `outlier_detection.py` is a QA debug tool — use when validation fails or biometric trajectories look anomalous, not routinely
- No automated test suite (`tests/` is empty); run `py_compile` checks before committing
- `spotify_tui.py` uses hardcoded relative paths (`data/playlists/...`) — must be run from the project root. All other scripts resolve paths relative to `__file__` and work from any directory.
- Pre-fitted models in `models/` are committed so the app and notebooks can run without refitting. Use `./scripts/notebooks.sh --fresh` to refit from scratch.
