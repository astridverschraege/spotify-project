# Recovery Analysis Pipeline — Project R.E.M.

## What was built

A 4-stage Python pipeline (`scripts/analysis/`) that measures whether music sessions accelerate physiological recovery compared to a participant's personal baseline, and produces a flat ML feature table for downstream modelling.

### Stage 1 — Activity State Classification (`activity_classifier.py`)

Labels every minute of smartwatch data as **Sleep / Rest / Light / Medium / Heavy**.

- Uses HR + Garmin stress score (0–100) + body battery trend as inputs
- Falls back to Garmin's own `intensity` label from FIT monitoring messages when available (extracted by `fit_extractor.py`)
- **Overnight presumption**: between 22:00–08:00 every minute defaults to Sleep unless the watch sees clear wakefulness (steps > 0 or HR > 95). This correctly handles REM sleep where HR sits at 75–90 bpm.
- **No-wear gaps**: minutes where both HR and stress are absent return `None` (unknown) rather than a forced classification. Kokosnoot, who doesn't wear the watch at night, has ~20% of minutes as `None` — these are excluded from baseline fitting and Stage 3 falls back to `"Rest"` when the pre-session window is missing.

### Stage 2 — Per-Person Baselines (`baselines.py`)

Builds a normal recovery model per participant from **non-session days only**.

- Computes mean ± std of HR, stress, body battery per activity state and per hour-of-day (controls for circadian rhythm, same approach as `cross_participant_analysis.ipynb`)
- Detects state transitions (e.g. Heavy → Rest) and fits an exponential decay curve: `f(t) = baseline + (start − baseline) × exp(−t/τ)`
- Outputs τ (time constant in minutes), asymptote, t₉₀ (time to 90% recovery), and R² per `(from_state, signal)` pair
- **Transition quality filter** (`_MIN_STATE_STAY_MIN = 3`): the prior state must have held for ≥3 consecutive minutes before a transition is counted. This prevents single-minute noise spikes from generating hundreds of low-quality curve fits.

### Stage 3 — Session Effect Analysis (`session_effect.py`)

For each music session: compares actual recovery to the expected recovery for that person and prior state.

- Classifies the dominant activity state in the 30 minutes before session start
- Looks up the expected recovery curve (τ_expected) from Stage 2
- Fits the actual exponential decay to the during + post session trace (τ_actual)
- **Recovery advantage** = τ_expected − τ_actual (positive = faster recovery with music)
- Curve fits that hit the 500-min max bound are discarded as non-converged

### Stage 4 — ML Feature Table (`session_features.py`)

Joins Stage 2 + Stage 3 outputs with `session_biometrics.csv` into a flat table — one row per session — ready for ML/DL.

- Per-participant: `data/analysis/{codename}/session_features.csv`
- Pooled: `data/analysis/all_session_features.csv`
- Columns: participant, date, playlist, pre_state, pre_hr_mean, bb_start, bb_delta, tau_expected, tau_actual, tau_advantage, r2_actual, n_points, mood_before, mood_after, mood_delta, hour_of_day, day_of_week

### Running it

```bash
# Full pipeline, all participants
python scripts/analysis/pipeline.py

# Specific participants, skip FIT re-extraction
python scripts/analysis/pipeline.py --participants bosbes kokosnoot --skip-extraction

# Build ML feature tables only (after pipeline has run)
python scripts/analysis/session_features.py --participants kokosnoot bosbes
```

Then open `notebooks/recovery_analysis.ipynb` for plots and statistics.

### Output files

```
data/analysis/
├── all_session_features.csv              ← pooled ML table (all participants)
├── cross_participant_effects.csv
├── cross_participant_stats.json
└── {codename}/
    ├── classified_minutes.csv            ← Stage 1: per-minute activity states
    ├── recovery_baselines.csv            ← Stage 2: τ curves per (state, signal)
    ├── session_effects.csv               ← Stage 3: per-session τ advantage
    └── session_features.csv             ← Stage 4: flat ML feature table
```

---

## Current results (updated 2026-04-30)

| Participant | Device | No-wear | Sessions w/ biometrics | Valid τ advantages | Mean advantage | Notes |
|-------------|--------|---------|------------------------|-------------------|----------------|-------|
| bosbes      | Garmin | 1.5%    | 7                      | 6                 | **+75.5 min**  | Strong positive signal |
| kokosnoot   | Garmin | 20.0%   | 9 of 16                | 7                 | **+25.3 min**  | 3 reliable fits (r²>0.05); see interpretation below |
| limoen      | Huawei | —       | 1 (no session trace)   | 0                 | —              | Run; no τ computed |

Cross-participant t-test: p=0.011, n=13, mean advantage +48.5 min. Technically significant but driven by bosbes; treat as a preliminary signal.

### Interpreting kokosnoot's result

**Mean advantage +25.3 min across 7 valid fits, but only 3 are reliable (r²>0.05).** The three reliable sessions give a mean of ~+28 min. The remaining 4 fits have r²≈0 — the exponential model failed to converge on the stress trace; those τ_actual values are noise.

Note: the individual `session_effects.csv` for kokosnoot is from an older pipeline run and shows different pre_state classifications and a mean of −10.5 min. The `cross_participant_effects.csv` reflects the current run and is the authoritative source for the notebook.

Root causes of poor fit quality:
- **Stress signal sparsity**: only ~40% of stress readings are valid for kokosnoot; many session windows have too few points for a clean decay fit
- **Early morning sessions**: most sessions start at 07:00–10:00 CET, classified as Light or Rest pre-state; τ_expected values are reasonable but the stress trace within sessions is often too flat to fit
- **Watch sync failure after 2026-02-17**: 7 of 16 sessions have no biometric data at all; mood scores exist for these sessions but no τ can be computed

Body battery drained during every session (bb_delta negative throughout) — expected, as sessions are active listening time, not passive rest. Not a recovery failure signal.

---

## Known limitations & assumptions

1. **No raw accelerometer** — activity classification relies on HR, Garmin stress, and body battery trend. No 3-axis accelerometer data is exposed in the existing pipeline.
2. **No explicit HRV column** — Garmin Body Battery is a proxy (derived from HRV + stress + sleep). R-to-R intervals are not extracted from FIT files.
3. **Body battery recovery curves are unreliable** — BB changes over many hours; the 90-min recovery window is too short to fit a converging exponential. HR and stress are the reliable signals for recovery analysis. `bb_delta` (scalar start−end) is a useful complementary metric.
4. **Huawei participants (limoen) lack body battery** — recovery curves fit on HR + stress only, which may be noisier.
5. **Exponential decay assumption** — recovery may not be strictly monotone (e.g. a second activity bout mid-session). Non-converging fits are discarded.
6. **Session selection bias** — participants chose when to listen; high-stress days may be over- or under-represented per playlist type.
7. **Small sample** — 3 participants, 17 sessions total, 13 with valid advantages. Cross-participant statistics are indicative only.
8. **r2_actual is the quality gate** — τ_actual values from fits with r2_actual < 0.05 should be treated as unreliable. The pipeline does not yet filter on r2 automatically.

---

## Next steps

### Immediate

- [ ] **Add r2 threshold filter in Stage 3** — automatically discard τ_actual values where r2_actual < 0.05 rather than relying on manual inspection. Update mean advantage calculation accordingly.
- [ ] **Add heart_rate as fallback primary signal** — for sessions where stress is too sparse to fit, fall back to HR. HR coverage for kokosnoot is similar but less gappy within session windows.
- [ ] **Run on limoen** — Huawei participant; has HR and stress but no body battery. Verify the no-BB degradation path works.
- [ ] **Add peer** when data becomes available (`data/wearables/peer/processed/` is currently empty).

### Analysis quality

- [x] **Improve transition detection in Stage 2** — now requires ≥3 consecutive minutes in the prior state (`_MIN_STATE_STAY_MIN = 3`) before counting a transition. Prevents noise spikes from diluting curve fits.
- [ ] **Investigate the pre-session state distribution** — most of kokosnoot's sessions are early mornings → all classified as Sleep pre-state. The Sleep→stress baseline has n_obs=2, which is too fragile. Consider a minimum n_obs threshold before accepting a baseline curve.
- [ ] **Use bb_delta as primary target for participants with sparse stress** — already in `session_features.csv`; doesn't require an exponential fit and is available for all 9 biometric sessions.

### ML upgrade path

- [ ] **Train a Random Forest on Garmin's intensity labels** — `fit_extractor.py` can pull `intensity` (sedentary / active / highly_active) and `activity_type` from FIT monitoring messages. Once extracted for one participant, these become ground-truth labels for training a proper classifier. `ActivityClassifier` already has the sklearn interface — it's a drop-in swap.
- [ ] **Consider an HMM for Sleep/Wake** — sleep is a sequence state, not a per-minute independent label. A simple 2-state HMM (Sleep / Awake) fit on HR + time-of-day could replace the overnight presumption heuristic with a proper probabilistic model.
- [ ] **Recovery advantage prediction (Track B)** — use `session_features.csv` as training input: predict tau_advantage from pre_state + pre_hr_mean + bb_start + hour_of_day + playlist. Start with a linear mixed-effects model (already scaffolded in `session_effect.py`).
- [ ] **Mood outcome model (Track C)** — predict mood_delta from physiological pre-state + playlist type. Sessions 9–15 for kokosnoot have mood scores but no biometrics — usable for mood-only modelling even without τ.

### Towards the Streamlit app (deadline June 20, 2026)

`session_features.csv` and `recovery_baselines.csv` are the ready-made inputs. Natural Streamlit cards:

- *"Your stress recovers X min faster with Calm music"*
- *"After a Medium-effort day, your normal stress recovery takes ~41 min — with music it took ~22 min"*
- *"Your fastest recovery playlist: [Energy / Calm / Neutral]"*
- Waterfall chart: τ_expected vs τ_actual per session, coloured by playlist type
