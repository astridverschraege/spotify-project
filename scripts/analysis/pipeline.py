"""
pipeline.py — Orchestrator for the 3-stage physiological recovery analysis pipeline.

Stages:
    1. Activity State Classification  (activity_classifier.py)
    2. Per-Person Baselines           (baselines.py)
    3. Music Session Effect Analysis  (session_effect.py)
    4. ML Feature Table               (session_features.py)

Usage:
    python scripts/analysis/pipeline.py
    python scripts/analysis/pipeline.py --participants bosbes kokosnoot
    python scripts/analysis/pipeline.py --skip-extraction   # skip FIT re-extraction

Outputs (per participant):
    data/analysis/{codename}/classified_minutes.csv   — per-minute with activity_state
    data/analysis/{codename}/recovery_baselines.csv   — Stage 2 curve parameters
    data/analysis/{codename}/session_effects.csv      — Stage 3 per-session results
    data/analysis/{codename}/session_features.csv     — Stage 4 flat ML feature table

Cross-participant summary:
    data/analysis/cross_participant_effects.csv
    data/analysis/cross_participant_stats.json
    data/analysis/all_session_features.csv            — pooled ML feature table
"""

import argparse
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

# Add this directory to path so relative imports work when run as script
sys.path.insert(0, str(Path(__file__).parent))
sys.path.insert(0, str(Path(__file__).parent.parent / "wearables"))

from activity_classifier import ActivityClassifier
from baselines import PersonBaseline
from session_effect import analyze_sessions, run_statistics, load_participant_data
from session_features import build_session_features
import fit_extractor

DATA_ROOT = Path(__file__).parent.parent.parent / "data"
ANALYSIS_ROOT = DATA_ROOT / "analysis"

PARTICIPANTS = ["bosbes", "citroen", "kiwi", "kokosnoot", "limoen", "peer", "watermeloen", "aardbei"]


def load_minute_data(codename: str) -> pd.DataFrame:
    """Merge per-minute HR, stress, body_battery, and activity (if available) into one DataFrame."""
    processed = DATA_ROOT / "wearables" / codename / "processed"
    frames = []

    # Stress + body_battery
    stress_path = processed / "garmin_minute_stress.csv"
    if stress_path.exists():
        df = pd.read_csv(stress_path, index_col="timestamp", parse_dates=True)
        frames.append(df[["stress", "body_battery"]])

    # Heart rate
    for hr_name in ("garmin_minute_hr.csv", "huawei_minute_hr.csv"):
        hr_path = processed / hr_name
        if hr_path.exists():
            df = pd.read_csv(hr_path, index_col="timestamp", parse_dates=True)
            frames.append(df[["heart_rate"]])
            break

    # FIT-extracted activity signals (optional)
    activity_path = processed / "garmin_minute_activity.csv"
    if activity_path.exists():
        df = pd.read_csv(activity_path, index_col="timestamp", parse_dates=True)
        frames.append(df)

    if not frames:
        return pd.DataFrame()

    # Merge on timestamp using outer join, then resample to 1-min grid to align all sources
    merged = frames[0]
    for df in frames[1:]:
        merged = merged.join(df, how="outer")

    merged = merged.sort_index()
    merged.index.name = "timestamp"
    return merged


def run_participant(codename: str, skip_extraction: bool = False) -> dict:
    """Run the full 3-stage pipeline for one participant.

    Returns a summary dict with participant-level results.
    """
    print(f"\n{'='*60}")
    print(f"  Participant: {codename}")
    print(f"{'='*60}")

    out_dir = ANALYSIS_ROOT / codename
    out_dir.mkdir(parents=True, exist_ok=True)

    # ── Stage 0: FIT extraction (optional) ──────────────────────────────────
    if not skip_extraction:
        try:
            fit_extractor.run(codename, DATA_ROOT)
        except Exception as e:
            print(f"  [FIT extraction] {e} — continuing without activity signals")

    # ── Load and merge per-minute data ───────────────────────────────────────
    minute_df = load_minute_data(codename)
    if minute_df.empty:
        print(f"  No per-minute data found for {codename} — skipping")
        return {"participant": codename, "status": "no_data"}

    print(f"  Loaded {len(minute_df):,} per-minute records")

    # ── Stage 1: Activity Classification ─────────────────────────────────────
    print("  Stage 1: Classifying activity states...")
    classifier = ActivityClassifier()
    states = classifier.predict(minute_df)
    minute_df["activity_state"] = states

    state_counts = states.value_counts()
    print("  State distribution:")
    for state, count in state_counts.items():
        pct = 100 * count / len(states)
        print(f"    {state:<10} {count:>6,} min  ({pct:.1f}%)")

    classified_path = out_dir / "classified_minutes.csv"
    minute_df.to_csv(classified_path)
    print(f"  → Wrote classified_minutes.csv")

    # ── Stage 2: Baselines & Recovery Curves ─────────────────────────────────
    print("  Stage 2: Fitting baselines and recovery curves...")
    traces, biometrics = load_participant_data(codename, DATA_ROOT)
    session_dates = biometrics["date"].tolist() if not biometrics.empty else []

    baseline = PersonBaseline(participant=codename)
    baseline.fit(minute_df, session_dates)

    summary_df = baseline.summary()
    if not summary_df.empty:
        baseline_path = out_dir / "recovery_baselines.csv"
        summary_df.to_csv(baseline_path, index=False)
        print(f"  → Fitted {len(summary_df)} recovery curves")
        print(f"  → Wrote recovery_baselines.csv")
    else:
        print("  ⚠ No recovery curves fitted (insufficient transition data)")

    # ── Stage 3: Music Session Effect Analysis ────────────────────────────────
    print("  Stage 3: Analyzing music session effects...")
    if traces.empty or biometrics.empty:
        print(f"  ⚠ No session data for {codename} — skipping Stage 3")
        return {"participant": codename, "status": "no_sessions", "n_sessions": 0}

    effects_df = analyze_sessions(traces, biometrics, minute_df, baseline)

    if effects_df.empty:
        print(f"  ⚠ No effects computed for {codename}")
        return {"participant": codename, "status": "no_effects", "n_sessions": len(biometrics)}

    # Add participant column for cross-participant pooling
    effects_df["participant"] = codename
    effects_path = out_dir / "session_effects.csv"
    effects_df.to_csv(effects_path, index=False)

    n_valid = effects_df["advantage"].notna().sum()
    mean_adv = effects_df["advantage"].mean() if n_valid > 0 else None
    print(f"  → {len(effects_df)} sessions, {n_valid} with valid advantage scores")
    if mean_adv is not None:
        print(f"  → Mean recovery advantage: {mean_adv:+.1f} min (positive = faster recovery with music)")
    print(f"  → Wrote session_effects.csv")

    return {
        "participant": codename,
        "status": "ok",
        "n_sessions": len(effects_df),
        "n_valid_advantages": int(n_valid),
        "mean_advantage_min": round(float(mean_adv), 2) if mean_adv is not None else None,
    }


def run_cross_participant(all_effects: list[pd.DataFrame]) -> None:
    """Pool all participants and run cross-participant statistics."""
    print(f"\n{'='*60}")
    print("  Cross-participant analysis")
    print(f"{'='*60}")

    combined = pd.concat(all_effects, ignore_index=True)
    combined_path = ANALYSIS_ROOT / "cross_participant_effects.csv"
    combined.to_csv(combined_path, index=False)
    print(f"  Pooled {len(combined)} sessions from {combined['participant'].nunique()} participants")

    stats = run_statistics(combined)

    # Print key results
    if "ttest" in stats:
        t = stats["ttest"]
        print(f"\n  One-sample t-test (advantage ≠ 0):")
        print(f"    n={t['n']}, mean={t['mean_advantage_min']:+.2f} min, "
              f"t={t['statistic']:.3f}, p={t['p_value']:.4f}")
        print(f"    → {t['interpretation']}")

    if "anova_playlist" in stats:
        a = stats["anova_playlist"]
        print(f"\n  ANOVA by playlist type: F={a['f_statistic']:.3f}, p={a['p_value']:.4f}")

    if "mixed_effects" in stats and "error" not in stats["mixed_effects"]:
        me = stats["mixed_effects"]
        print(f"\n  Mixed-effects model: AIC={me.get('aic', 'N/A')}, converged={me.get('converged')}")

    stats_path = ANALYSIS_ROOT / "cross_participant_stats.json"
    with open(stats_path, "w") as f:
        json.dump(stats, f, indent=2)
    print(f"\n  → Wrote cross_participant_effects.csv and cross_participant_stats.json")


def main():
    parser = argparse.ArgumentParser(
        description="Physiological recovery analysis pipeline for Project R.E.M."
    )
    parser.add_argument(
        "--participants", nargs="+", default=None,
        help="Participant codenames to process. Defaults to all known participants.",
    )
    parser.add_argument(
        "--skip-extraction", action="store_true",
        help="Skip FIT file re-extraction (use existing garmin_minute_activity.csv if present).",
    )
    args = parser.parse_args()

    participants = args.participants or PARTICIPANTS
    ANALYSIS_ROOT.mkdir(parents=True, exist_ok=True)

    all_effects = []
    summaries = []

    for codename in participants:
        try:
            summary = run_participant(codename, skip_extraction=args.skip_extraction)
            summaries.append(summary)

            effects_path = ANALYSIS_ROOT / codename / "session_effects.csv"
            if effects_path.exists():
                df = pd.read_csv(effects_path)
                if not df.empty and "participant" not in df.columns:
                    df["participant"] = codename
                all_effects.append(df)
        except Exception as e:
            print(f"\n  ✗ {codename}: {e}")
            summaries.append({"participant": codename, "status": "error", "error": str(e)})

    # Cross-participant analysis
    if len(all_effects) >= 2:
        run_cross_participant(all_effects)
    elif len(all_effects) == 1:
        print("\n  Only 1 participant with data — skipping cross-participant stats")

    # Stage 4 — Build ML feature tables
    print(f"\n{'='*60}")
    print("  Stage 4 — ML feature tables")
    print(f"{'='*60}")
    all_features = []
    for codename in participants:
        features = build_session_features(codename)
        if features is not None and not features.empty:
            feat_path = ANALYSIS_ROOT / codename / "session_features.csv"
            features.to_csv(feat_path, index=False)
            print(f"  [{codename}] {len(features)} sessions → {feat_path}")
            all_features.append(features)
    if all_features:
        import pandas as _pd
        combined = _pd.concat(all_features, ignore_index=True)
        combined_path = ANALYSIS_ROOT / "all_session_features.csv"
        combined.to_csv(combined_path, index=False)
        print(f"\n  Pooled table: {len(combined)} sessions → {combined_path}")

    # Final summary table
    print(f"\n{'='*60}")
    print("  Summary")
    print(f"{'='*60}")
    for s in summaries:
        status = s["status"]
        p = s["participant"]
        if status == "ok":
            print(f"  {p:<15} ✓  {s['n_sessions']} sessions, "
                  f"mean advantage {s.get('mean_advantage_min', 0):+.1f} min")
        else:
            print(f"  {p:<15} ✗  {status}")


if __name__ == "__main__":
    main()
