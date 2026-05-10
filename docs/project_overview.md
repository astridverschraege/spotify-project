# Project R.E.M. — Overview

**Regulation of Emotion through Music**

## Overview

Project R.E.M. is a research project investigating whether personalized music playlists can measurably regulate emotional states. The core idea is the **ISO principle** from music therapy: instead of jumping to a target mood, music is ordered to *gradually transition* the listener's arousal level — descending BPM for calm, ascending for energy, stable for neutral. Because self-chosen music is more effective than unfamiliar tracks, all playlists are built from each participant's own Spotify library.

Participants (anonymized with fruit codenames like `bosbes`, `kokosnoot`, `limoen`) export their Spotify data, receive three personalized playlists, then listen while wearing a Garmin or Huawei smartwatch. After each session they fill in a Google Forms check-in reporting their mood. The system then cross-references playlist type, biometric signals (heart rate, stress, body battery), and self-reported mood to determine if and how the music affected their state.

The project has three production-ready subsystems (playlist generation, wearables pipeline, analysis scripts) and one major remaining deliverable: a Streamlit dashboard presenting per-participant results. Deadline: June 20, 2026.

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                             DATA SOURCES                                    │
├───────────────────────┬───────────────────────┬─────────────────────────────┤
│   Spotify Library     │   Smartwatch Export    │   Google Forms Check-ins    │
│   (Exportify CSVs)    │   (Garmin FIT/JSON,    │   (mood, playlist type,     │
│                       │    Huawei GDPR)        │    timestamp)               │
└───────────┬───────────┴───────────┬───────────┴──────────────┬──────────────┘
            │                       │                          │
            ▼                       ▼                          │
┌───────────────────────┐ ┌─────────────────────────┐         │
│  PLAYLIST GENERATION  │ │   WEARABLES PIPELINE    │         │
│  scripts/playlists/   │ │   scripts/wearables/    │         │
│                       │ │                         │         │
│  prepare (clean CSVs) │ │  garmin_pipeline.py     │         │
│  generate (ISO order) │ │  huawei_pipeline.py     │         │
│  analyse (validate)   │ │                         │         │
│                       │ │  Output:                │         │
│  Output: 3 playlists  │ │  daily/minute stress,   │         │
│  (calm/neutral/energy)│ │  HR, session biometrics  │         │
└───────────┬───────────┘ └────────────┬────────────┘         │
            │                          │                       │
            └────────────┬─────────────┘───────────────────────┘
                         ▼
          ┌──────────────────────────────────────┐
          │          ANALYSIS LAYER              │
          │        scripts/analysis/             │
          ├──────────────────────────────────────┤
          │                                      │
          │  Circadian Baselines                 │
          │    → hourly stress norms per person  │
          │    → baseline deviation = key signal │
          │                                      │
          │  ML Models (Ridge, RF, GBR)          │
          │    → predict mood/stress delta       │
          │    → SHAP explainability             │
          │                                      │
          │  Bayesian Recommender (NumPyro)      │
          │    → hierarchical model              │
          │    → per-participant playlist recs    │
          │    → posterior uncertainty estimates  │
          │                                      │
          └─────────────────┬────────────────────┘
                            ▼
          ┌──────────────────────────────────────┐
          │          STREAMLIT APP               │
          │      ┄┄┄ not started ┄┄┄            │
          │                                      │
          │   "Spotify Wrapped" per-participant  │
          │   dashboard with recommendations     │
          └──────────────────────────────────────┘
```

---

## Subsystems

### 1. Playlist Generation (`scripts/playlists/`) — COMPLETE

Takes a participant's Spotify library (exported via Exportify) and produces three playlists:

| Playlist | Tempo (BPM) | Energy | ISO Order |
|----------|-------------|--------|-----------|
| Calm     | 50–95       | < 0.9  | Descending BPM |
| Neutral  | 95–115      | 0.2–0.8 | Stable |
| Energy   | 120–180     | > 0.7  | Ascending BPM |

**Pipeline:** `prepare` (combine/clean CSVs) → `generate` (filter by BPM/energy, apply ISO ordering, smooth loudness) → `analyse` (validate 4 criteria, generate plots).

**Validation criteria:** tempo in range, energy separation between types, ≥15 BPM gap calm↔energy, ≥25 min duration each. Target: 12 songs (~30 min) per playlist.

**Entry point:** `python scripts/playlists/spotify_cli.py all [codename]`

**Output:** `data/playlists/[codename]/playlists_generated/` — CSV per playlist type + analysis plots.

---

### 2. Wearables Pipeline (`scripts/wearables/`) — COMPLETE

Extracts biometric data from Garmin/Huawei GDPR exports and structures it for analysis.

**Garmin pipeline** parses:
- JSON daily aggregates (stress, body battery, steps)
- FIT binary files (per-minute heart rate and stress)
- Joins with check-in timestamps to create session windows

**Outputs** (in `data/wearables/[codename]/processed/`):
- `garmin_daily.csv` — daily aggregates
- `garmin_minute_stress.csv` / `garmin_minute_hr.csv` — per-minute biometrics
- `session_biometrics.csv` — aggregated per session
- `session_traces/` — individual biometric traces per session
- `garmin_vitals_report.pdf` — summary report

**Timezone note:** FIT files are UTC; check-in times are CET (UTC+1).

**Privacy:** Raw exports are gitignored (contain PII). Only processed/anonymized data is committed.

---

### 3. Analysis & ML (`scripts/analysis/`) — ~80% COMPLETE

Three analysis tracks that all feed into the final recommendations:

**Circadian Baselines** (`circadian_baseline.py`)
- Computes each participant's normal hourly stress pattern from non-session days
- The **baseline deviation** (session stress vs. expected stress at that hour) is the strongest predictive feature across all models

**ML Models** (`circadian_ml.py`)
- Ridge Regression, Random Forest, Gradient Boosting — predicting mood delta and stress delta
- Leave-one-session-out cross-validation
- SHAP explainability (with data quality warnings at N=42)
- Best model: GradientBoosting (MAE=1.64, R²=0.39 for mood_delta)
- Top features: baseline_deviation, playlist type, hour_of_day

**Bayesian Recommender** (`bayesian_recommender.py`)
- Hierarchical model via JAX/NumPyro with partial pooling across participants
- Per-participant intercepts + playlist effects + biometric covariates
- Produces mood predictions for each playlist type with 89% credible intervals
- Output: `recommendations.json` with per-participant optimal playlist + confidence

**Supporting scripts:**
- `activity_classifier.py` — classifies activity state (Sleep/Rest/Light/Medium/Heavy)
- `baselines.py` — exponential recovery curve fitting
- `session_effect.py` — computes recovery advantage (music vs. expected)
- `session_features.py` — joins everything into a flat ML table
- `fit_extractor.py` — extracts activity signals from FIT files

---

### 4. Notebooks (`notebooks/`)

| Notebook | Purpose |
|----------|---------|
| `circadian_ml_analysis.ipynb` | ML model results, SHAP beeswarms, circadian curves |
| `bayesian_recommender_viz.ipynb` | Posterior distributions, shrinkage, sensitivity analysis |
| `recovery_analysis.ipynb` | Recovery curve fitting, session effect analysis |
| `who_needs_reminding.ipynb` | Colab tool: flags participants inactive 3+ days |

Archived experimental notebooks live in `notebooks/_old/`.

---

### 5. Streamlit App — NOT STARTED

The final deliverable: a "Spotify Wrapped"-style per-participant dashboard showing:
- Playlist effectiveness (which type works best for them)
- Biometric trends across sessions
- Circadian stress patterns
- Bayesian recommendations with uncertainty
- Key stats (e.g., least stressful hour, mood improvement trends)

Data is ready — `recommendations.json`, `feature_matrix.csv`, model results, and plots all exist. This is purely a frontend/presentation task.

---

## How It All Fits Together

The ISO principle is the scientific thread connecting everything:

1. **Generate** playlists that apply ISO ordering to the participant's own music
2. **Measure** what happens physiologically (smartwatch) and subjectively (check-in) when they listen
3. **Analyze** whether the gradual BPM transitions actually shift stress/mood, controlling for circadian rhythm (baseline deviation)
4. **Recommend** the optimal playlist type per participant using a Bayesian model that pools evidence across all participants while respecting individual differences
5. **Present** everything in a Streamlit dashboard for the final presentation

The key insight from analysis so far: **baseline deviation** (how your stress during a session compares to your typical stress at that time of day) is the strongest signal. This means the circadian control is essential — without it, you can't tell if mood changed because of the music or because it was just a low-stress time of day.

---

## What's Still Missing

- **Streamlit dashboard** — The main remaining deliverable. All backend data and analysis outputs exist; this is a frontend/visualization task. Zero code exists yet.

- **Music classification ML in production** — Trained classifiers that could auto-suggest optimal playlists from a participant's full library exist only in archived notebooks (`notebooks/_old/`). Not integrated into the CLI pipeline.

- **More data** — Currently 42 sessions across ~6 participants. ML models work but SHAP results carry data quality warnings. More sessions would improve reliability.

- **Automated tests** — The `tests/` directory is empty. Only `py_compile` syntax checks are used. Not critical for the deadline but a gap.

- **BRONZE/SILVER/GOLD pipeline** — A generalized data framework was scaffolded in `scripts/pipeline/` (~5% done). The production wearables pipelines work fine without it. Low priority.
