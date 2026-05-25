# Project R.E.M.: Full Pipeline Walkthrough for Participant "peer"

## What is Project R.E.M.?

**Project R.E.M.** (**Regulation of Emotion through Music**) is a research study that investigates whether personalized music playlists can effectively regulate emotional states. The system is built around each participant's own Spotify library (exported via Exportify) rather than a curated music collection, because research shows that self-chosen music is significantly more effective at emotion regulation than unfamiliar songs.

The core research principle is the **ISO principle**: instead of jumping directly to a target emotional state, music is ordered to gradually transition from the listener's current arousal level toward the desired state — matching established music therapy practice. Three playlist types are generated (calm, neutral, energy) that either descend, maintain, or ascend in BPM and energy, allowing participants to gradually reach the desired emotional state. The system cross-references these playlists with smartwatch biometrics (Garmin) and self-reported mood check-ins from Google Forms to measure effectiveness.

---

## Phase 1: Playlist Generation (`spotify_cli.py all peer`)

### Overview
The playlist generation phase takes a participant's raw Spotify library export and creates three ISO-ordered playlists optimized for stress reduction, baseline control, and energy enhancement.

### Three Sub-Steps

**[1/3] Prepare CSV Files**
- **Input:** `Liked_Songs.csv` (raw Exportify export with Spotify audio features)
- **Process:**
  - Find and combine all CSV files in the participant directory
  - Standardize column names (Exportify uses verbose names; internally shortened to: name, artists, uri, tempo, energy, duration_ms, etc.)
  - Remove duplicate songs (deduplicate by Spotify URI)
  - Filter unsuitable songs: drops any track with speechiness >0.7 (podcasts/spoken word) or liveness >0.8 (live recordings), as these don't produce the desired emotional effect
- **Output:** `combined.csv` (691 tracks for peer after dedup/filtering)

**[2/3] Generate Playlists**
For each playlist type, the process filters songs and applies ISO ordering:

| Playlist Type | Filter Criteria | ISO Ordering | Goal |
|---|---|---|---|
| **Calm** | BPM 50–95, energy <0.9 | **Descending** BPM + energy | Stress reduction / relaxation |
| **Neutral** | BPM 95–115, energy 0.2–0.8 | **Stable** (consistency score) | Control condition, no emotional shift |
| **Energy** | BPM 120–180, energy >0.7, valence >0.2 | **Ascending** BPM + energy | Arousal / alertness / motivation |

Each playlist is trimmed to the top 12 songs (approximately 30 minutes) for the study protocol.

**[3/3] Analyse & Validate**
- Load the 3 generated playlists and compute statistics (mean/std tempo, energy, etc.)
- Validate 4 criteria:
  1. **Tempo ranges:** calm ≤95 BPM, energy ≥120 BPM ✓
  2. **Energy separation:** calm vs energy differ by >0.2 ✓
  3. **Substantial tempo difference:** calm and energy differ by ≥15 BPM ✓
  4. **Duration:** each playlist ≥25 min (80% of 30 min target) ✓
- Generate 4 visualisation plots:
  - Feature comparison (boxplot of tempo/energy per playlist)
  - Tempo vs Energy scatter (ISO trajectory visible)
  - Feature distributions per playlist (histograms)
  - Mood quadrant (valence vs energy)
- Write human-readable analysis report (peer_analysis_report.txt)

### Phase 1 Result for Peer
```
✓ Calm:    85→12 songs,  314.5 min → 30.8 min,  95.0→89.3 BPM (descending)
✓ Neutral: 126→12 songs, 485.3 min → 30.8 min,  104.5 BPM (stable)
✓ Energy:  45→12 songs,  163.1 min → 30.8 min,  120.0→124.0 BPM (ascending)
✓ Validation: 4/4 checks PASSED
```

**Output files:** `peer_calm_playlist.csv`, `peer_neutral_playlist.csv`, `peer_energy_playlist.csv`, `peer_analysis_report.txt`, + 4 JPG plots

---

## Phase 2: Wearables Pipeline (`garmin_pipeline.py peer`)

### Overview
The wearables pipeline extracts biometric data from a Garmin Connect GDPR export (JSON daily summaries + FIT binary files) and cross-references it with participant's playlist listening sessions (from Google Form check-ins) to measure physiological response.

### Data Sources
Garmin exports contain two data types:
1. **JSON daily aggregates** (`UDS_*.json` files) — daily steps, HR, stress, body battery, respiration
2. **FIT binary files** (inside ZIP archives) — minute-level stress and HR during the day

### Pipeline Steps

1. **Discover & extract files**
   - Recursively search the export directory for JSON files and ZIP archives
   - Extract minute-level FIT biometric data from ZIPs (one ZIP per day)

2. **Parse daily aggregates**
   - Load JSON files and extract: date, steps, avg HR, stress readings, body battery, respiration rate
   - Calculate daily metrics: km walked (from steps), goal met (yes/no), 7-day rolling averages

3. **Parse FIT binaries**
   - Deserialize Garmin FIT format to extract minute-level stress and HR time series
   - **Known limitation:** Body Battery field (`unknown_3`) is reverse-engineered from FIT spec; not guaranteed stable across firmware updates
   - Filter out no-wear periods (zero HR, zero stress)

4. **Build daily and minute-level CSVs**
   - `garmin_daily.csv` — one row per day with aggregates
   - `garmin_minute_stress.csv` — timestamp, stress value (0–100)
   - `garmin_minute_hr.csv` — timestamp, heart rate (BPM)
   - `garmin_health_snapshots.csv` — health metrics snapshots

5. **Cross-reference with check-ins**
   - Load Google Forms check-in data (`check_in.csv`, with participant codename, date, time, playlist type, mood before/after)
   - For each check-in, extract a **±60 minute biometric window** around the session start time
   - Match session to check-in by participant + date + time alignment
   - Compute: pre-session stress mean, during-session stress trajectory, post-session recovery

6. **Session biometrics table** (`session_biometrics.csv`)
   - One row per playlist session with aggregated metrics:
     - Participant, date, time, playlist type
     - Pre-session stress (mean from -60 to 0 min window)
     - During-session stress (mean from 0 to +N min window)
     - Post-session stress (mean from +N to +60 min window)
     - Recovery slope (how fast stress declined after session)
     - Pre/during/post heart rate averages

7. **Session traces**
   - `session_traces_all.csv` — all sessions' minute-by-minute stress/HR combined
   - `session_traces/trace_DATE_PLAYLIST.csv` — individual trace files per session

8. **PDF Report**
   - `garmin_vitals_report.pdf` — visual summary of stress/HR patterns, session annotations

### Phase 2 Result for Peer
- 6 processed CSV files generated
- 6 session trace files (one per playlist session: 2026-01-28 energy, 2026-02-02 calm, etc.)
- PDF report with visualisations
- **Biometric window alignment note:** UTC offset hardcoded to +1 (CET); sessions in CEST period (late March–Oct) will be off by ±1 hour

**Output files:** `garmin_daily.csv`, `garmin_minute_stress.csv`, `garmin_minute_hr.csv`, `session_biometrics.csv`, `session_traces_all.csv`, `session_traces/*.csv`, `garmin_vitals_report.pdf`

---

## Phase 3: Circadian Baseline (`circadian_baseline.py`)

### Overview
Establishes a per-participant hourly stress baseline from non-session days, allowing later phases to compute how much a session deviates from normal circadian rhythm.

### Process

1. **Load wearables for all participants**
   - Read `garmin_minute_stress.csv` from each participant's processed folder
   - Read `session_biometrics.csv` to identify which dates/times had playlist sessions

2. **Filter to non-session days**
   - Exclude any minute-level data from days when a participant had a playlist session
   - Keep only "baseline" days (typical daily rhythms, no intervention)

3. **Compute hourly baselines**
   - For each participant, for each hour of day (0–23):
     - Calculate mean stress and std across all non-session occurrences of that hour
     - **Hours with <5 observations → NaN** (not enough data for reliable baseline)
   - Output: `hourly_baseline.csv` per participant with mean_stress and std_stress per hour

4. **Build feature matrix**
   - For each session, compute: **baseline_deviation**
     - `baseline_deviation = pre_session_stress_mean - expected_stress_at_hour`
     - Example: if peer usually has stress=30 at 4 PM, but measured 45 during a pre-session window at 4 PM, deviation = +15 (elevated)
   - Combine all participants' sessions into `feature_matrix.csv` with columns: participant, date, playlist_type, baseline_deviation, mood_delta, stress_delta, hour_of_day, day_of_week, etc.

### Key Insight
**Baseline deviation** is the strongest biometric signal for predicting playlist effectiveness because it controls for natural circadian rhythm — comparing apples to apples (4 PM to 4 PM, not 4 PM to midnight).

### Phase 3 Output
- Per-participant: `data/analysis/peer/circadian_baselines/hourly_baseline.csv` + circadian curve plot
- Combined: `data/analysis/circadian_baselines/feature_matrix.csv` (all participants, all sessions)

---

## Phase 4: Circadian ML (`circadian_ml.py`)

### Overview
Trains machine learning models to predict mood and stress change from biometric baseline deviation and circadian features.

### Models Trained
Three regressors, each evaluated with **Leave-One-Out (LOO) Cross-Validation**:
1. **Ridge Regression** — L2 penalized linear model, stable baseline
2. **Random Forest** — ensemble of decision trees, captures non-linearities
3. **Gradient Boosting Regressor (GBR)** — boosted trees, often best predictive power

### Target Variables
- `mood_delta` — change in self-reported mood from pre-session to post-session (from check-in form)
- `stress_delta` — change in physiological stress (biometric) from pre to post session

### Features
- `baseline_deviation_entry` — key predictor (pre-session stress vs hourly baseline)
- `hour_of_day` — circadian phase (0–23)
- `day_of_week` — whether weekend vs weekday
- `participant_code` — account for individual differences (one-hot encoded)
- Additional: session duration, average stress during, recovery slope

### Evaluation
- **Metrics:** MAE (mean absolute error), RMSE (root mean squared error), R² (coefficient of determination)
- **LOO-CV:** leave out one session, train on rest, test on held-out session — repeated N times (where N = total sessions)
- No p-values or significance testing; this is predictive modeling, not inference

### Explainability: SHAP

For each model, compute SHAP (Shapley Additive exPlanations) values:
- Shows how much each feature contributes to the model's prediction for each individual session
- Beeswarm plots: each point = one session, colored by feature value, positioned by SHAP contribution
- Summary: `baseline_deviation` should emerge as the top driver if biometric response is real

### Phase 4 Output
- `model_results_mood_delta.csv` — LOO-CV predictions and errors for mood
- `model_results_stress_delta.csv` — LOO-CV predictions and errors for stress delta
- SHAP beeswarm plots per model per target
- Per-participant: SHAP plots in `data/analysis/peer/`

---

## Phase 5: Bayesian Recommender (`bayesian_recommender.py`)

### Overview
Builds a hierarchical Bayesian model that learns which playlist type (calm, neutral, energy) is best for each participant, accounting for individual variability and session-level randomness.

### Model Architecture

**Hierarchical structure** (partial pooling):
```
Population level:
  - α ~ Normal(μ_α, σ_α)           [global mean playlist effectiveness]
  - β_playlist ~ Normal(μ_β, σ_β)  [playlist-type effect]

Per-participant level:
  - α_participant ~ Normal(α, σ_α_participant)       [individual deviate from population]
  - β_participant[playlist] ~ ...                    [how each person responds to each playlist type]

Session level:
  - outcome ~ Normal(α_participant + β_participant[playlist] + ε_session, σ_noise)
```

**Benefits of this structure:**
- Participants with few sessions "borrow strength" from others (shrinkage)
- Estimates are regularized, reducing overfitting
- Uncertainty quantified at all levels

### Data
- **Input:** `session_biometrics.csv` (biometric response per session) + check-in CSV (mood outcome)
- **Join key:** participant + playlist type + date + time
- **Note:** Known issue — if same participant listened to same playlist type twice, matching may select wrong session

### Sampling
- Uses **JAX/NumPyro** backend for fast probabilistic inference
- ~30 second sampling (~2000 draws per chain, 2 chains)
- Generates posterior distributions over α (intercept), β (playlist effects), individual participants

### Output
- `recommendations.json` — per participant: ranked playlist effectiveness with posterior mean + credible intervals
- `posterior_peer.png` — trace plots and posterior distributions for peer's individual effects
- `trace.nc` — full posterior samples (can be reused with `--reuse-trace` to skip resampling)
- **Warning:** `--reuse-trace` can silently produce wrong recommendations if participant list changed

### Phase 5 Output
- `data/analysis/bayesian_recommender/recommendations.json`
- `data/analysis/peer/bayesian_recommender/plots/posterior_peer.png`
- `data/analysis/bayesian_recommender/trace.nc` (posterior samples)

---

## Phase 6: Notebooks (Visualization & Analysis)

Three Jupyter notebooks execute the pipeline outputs to generate interactive visualisations and deeper insights.

### Notebook 1: `circadian_ml_analysis.ipynb`

**Purpose:** Visualize circadian ML model results and SHAP explanations

**Loads:**
- `feature_matrix.csv` (feature table from Phase 3)
- `model_results_mood_delta.csv`, `model_results_stress_delta.csv` (Phase 4)
- Individual SHAP plots for peer

**Produces:**
- **Predicted vs Actual plots** — scatter of model predictions vs ground truth, colored by playlist type
- **Residual diagnostics** — check for bias, heteroscedasticity
- **Permutation importance** — relative contribution of each feature
- **SHAP summary plots** — which features drive predictions most strongly
- **Circadian plots** — hourly stress baseline curve ± std for peer

**Key insight:** baseline_deviation_entry should consistently rank as top-3 predictor

---

### Notebook 2: `bayesian_recommender_viz.ipynb`

**Purpose:** Visualize Bayesian model posteriors and individual recommendations

**Loads:**
- `trace.nc` (posterior samples from Phase 5)
- `recommendations.json`
- Session metadata (playlist types, dates, counts)

**Produces:**
- **Posterior trace plots** — convergence diagnostics (should look like "hairy caterpillars")
- **Posterior distributions** — credible interval plots for global α, per-playlist β effects
- **Shrinkage illustration** — compare population-level vs participant-level estimates
- **Recommendations table** — ranked playlist effectiveness per participant
- **Sensitivity analysis** — how sensitive are recommendations to the choice of priors?

**Key insight:** Participants with few sessions show more shrinkage toward population mean

---

### Notebook 3: `recovery_analysis.ipynb`

**Purpose:** Analyze physiological recovery patterns within sessions

**Loads:**
- `session_traces/*.csv` — minute-by-minute stress/HR during sessions
- Session metadata

**Produces:**
- **Per-session recovery curves** — stress trajectory before/during/after each playlist session
- **Recovery metrics** — tau_actual (observed recovery time constant) vs tau_expected (baseline)
- **Playlist type comparison** — do calm/energy playlists show different recovery profiles?

---

### Notebook 4 (Skipped): `who_needs_reminding.ipynb`
This is a Google Colab tool that flags participants who haven't checked in for 3+ days. Not runnable locally; skip.

---

## Full Data Flow Diagram

```
PARTICIPANT "peer"
│
├─→ Spotify Export (Liked_Songs.csv, 691 tracks)
│   │
│   └─→ [PHASE 1] spotify_cli.py all peer
│       ├─ Prepare: combine, deduplicate, filter (→ 691 combined)
│       ├─ Generate: filter by tempo/energy, ISO order (→ calm/neutral/energy)
│       └─ Analyse: validate, visualize (→ 4 JPGs + report)
│           └─→ playlists_generated/ (3 CSVs)
│
├─→ Garmin Export (raw/export/ folder with JSON + FIT ZIPs)
│   │
│   └─→ [PHASE 2] garmin_pipeline.py peer
│       ├─ Extract JSON daily aggregates
│       ├─ Parse FIT binaries (minute-level)
│       ├─ Cross-reference with check-in.csv (by time window)
│       └─ Aggregate session-level biometrics (stress, HR, recovery)
│           └─→ processed/ (6 CSVs + PDF)
│
├─→ Check-in Form (check_in.csv, participant mood/playlist entries)
│
└─→ [ALL PARTICIPANTS] data/analysis/
    │
    ├─→ [PHASE 3] circadian_baseline.py
    │   ├─ Load all participants' wearables
    │   ├─ Filter to non-session days only
    │   ├─ Compute hourly baselines (mean/std per hour)
    │   └─ Build feature_matrix.csv with baseline_deviation
    │
    ├─→ [PHASE 4] circadian_ml.py
    │   ├─ Train Ridge/RF/GBR on feature_matrix
    │   ├─ LOO-CV evaluation (MAE, RMSE, R²)
    │   └─ SHAP explainability (beeswarm plots)
    │       └─→ model_results/*.csv + SHAP plots
    │
    ├─→ [PHASE 5] bayesian_recommender.py
    │   ├─ Hierarchical Bayesian model (NumPyro/JAX)
    │   ├─ Sample posteriors (~30s)
    │   └─ Output recommendations + trace
    │       └─→ bayesian_recommender/ (recommendations.json, trace.nc, plots)
    │
    └─→ [PHASE 6] Jupyter Notebooks
        ├─ circadian_ml_analysis.ipynb → predicted vs actual, SHAP plots
        ├─ bayesian_recommender_viz.ipynb → posterior plots, recommendations
        └─ recovery_analysis.ipynb → session recovery curves

FINAL OUTPUT:
  - Predictions of mood/stress change from circadian baseline
  - Per-participant playlist recommendations ranked by effectiveness
  - Explainability: which features (hour, baseline deviation) matter most
```

---

## Key Assumptions & Known Limitations

1. **UTC offset hardcoded to +1 (CET)** — sessions in CEST (late Mar–Oct) misaligned by 1 hour
2. **Body Battery is reverse-engineered** — FIT field `unknown_3` not guaranteed stable
3. **No automated tests** — any refactor carries regression risk
4. **Check-in CSV has two possible paths** — legacy code searches both `data/check_in/` and `data/checkins/`
5. **Analysis scripts must run from project root** — relative paths, no absolute path resolution
6. **No inferential statistics** — no p-values, significance tests, or confidence intervals; purely predictive

---

## Quick Reference: How to Run

```bash
cd C:\Users\astri\Desktop\Data_Scientist\Eindwerk\spotify-project

# Phase 1
PYTHONIOENCODING=utf-8 uv run python scripts/playlists/spotify_cli.py all peer

# Phase 2
PYTHONIOENCODING=utf-8 uv run python scripts/wearables/garmin_pipeline.py peer

# Phase 3
PYTHONIOENCODING=utf-8 uv run python scripts/analysis/circadian_baseline.py

# Phase 4
PYTHONIOENCODING=utf-8 uv run python scripts/analysis/circadian_ml.py

# Phase 5
PYTHONIOENCODING=utf-8 uv run python scripts/analysis/bayesian_recommender.py

# Phase 6
uv run jupyter nbconvert --to notebook --execute --inplace notebooks/circadian_ml_analysis.ipynb
uv run jupyter nbconvert --to notebook --execute --inplace notebooks/bayesian_recommender_viz.ipynb
uv run jupyter nbconvert --to notebook --execute --inplace notebooks/recovery_analysis.ipynb
```

---

**Document compiled:** May 13, 2026
**Participant:** peer
**Pipeline status:** Complete
