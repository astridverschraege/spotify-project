"""
fit_extractor.py — Extract additional per-minute signals from Garmin FIT monitoring messages.

Complements the existing garmin_pipeline.py extraction (which only captures HR, stress, and
body battery). This module additionally extracts activity_type, intensity, step count, and
calories from the same monitoring messages.

Output: garmin_minute_activity.csv
Columns: timestamp (UTC, index), intensity, activity_type, steps_per_min, calories_per_min
"""

import datetime
import tempfile
import zipfile
from pathlib import Path

import numpy as np
import pandas as pd


# Garmin FIT intensity enum values
_INTENSITY_MAP = {0: "active", 1: "rest", 2: "activity_detected", 3: "highly_active", 4: "sedentary", 5: "light"}

# Garmin FIT activity_type enum values
_ACTIVITY_MAP = {
    0: "generic", 1: "running", 2: "cycling", 3: "transition",
    4: "fitness_equipment", 5: "swimming", 6: "walking", 7: "sedentary",
    254: "unknown",
}

# current_activity_type_intensity encoding: bits 0-4 = activity_type, bits 5-7 = intensity
_ACTIVITY_MASK = 0b00011111
_INTENSITY_SHIFT = 5


def extract_monitoring_activity(fit_zips: list[Path], date_range: tuple = None) -> pd.DataFrame:
    """Extract per-minute activity signals from FIT monitoring messages.

    Args:
        fit_zips: List of paths to Garmin FIT zip archives.
        date_range: Optional (start, end) datetime tuple to skip out-of-range files.

    Returns:
        DataFrame indexed by UTC timestamp with columns:
        intensity, activity_type, steps_per_min, calories_per_min
    """
    try:
        import fitparse
    except ImportError:
        raise ImportError("fitparse is required: pip install fitparse")

    rows = []

    with tempfile.TemporaryDirectory() as tmpdir:
        fit_paths = []
        for zp in fit_zips:
            try:
                with zipfile.ZipFile(zp) as z:
                    for name in z.namelist():
                        if name.endswith(".fit"):
                            z.extract(name, tmpdir)
                            fit_paths.append(Path(tmpdir) / name)
            except Exception:
                pass

        for fp in fit_paths:
            try:
                base_ts = None
                # Cumulative cycles (steps proxy) per file — differentiate later
                prev_cycles = None
                prev_ts = None

                for msg in fitparse.FitFile(str(fp)).get_messages():
                    f = {field.name: field.value for field in msg.fields}

                    if msg.name == "monitoring_info":
                        base_ts = f.get("timestamp")
                        prev_cycles = None
                        prev_ts = None
                        continue

                    if msg.name != "monitoring":
                        continue

                    # Reconstruct timestamp (same logic as garmin_pipeline.py HR extraction)
                    ts = f.get("timestamp")
                    if not ts and f.get("timestamp_16") and base_ts:
                        base_s = int(base_ts.timestamp())
                        full = (base_s & ~0xFFFF) | (f["timestamp_16"] & 0xFFFF)
                        if full < base_s:
                            full += 0x10000
                        ts = datetime.datetime.fromtimestamp(
                            full, tz=datetime.timezone.utc
                        ).replace(tzinfo=None)
                    if not ts:
                        continue

                    if date_range and (ts < date_range[0] or ts > date_range[1]):
                        continue

                    # Decode activity_type and intensity
                    activity_type = None
                    intensity = None
                    combined = f.get("current_activity_type_intensity")
                    if combined is not None:
                        try:
                            val = int(combined)
                            activity_type = _ACTIVITY_MAP.get(val & _ACTIVITY_MASK, str(val & _ACTIVITY_MASK))
                            intensity = _INTENSITY_MAP.get(val >> _INTENSITY_SHIFT, str(val >> _INTENSITY_SHIFT))
                        except (ValueError, TypeError):
                            pass
                    else:
                        raw_at = f.get("activity_type")
                        raw_in = f.get("intensity")
                        if raw_at is not None:
                            activity_type = _ACTIVITY_MAP.get(int(raw_at), str(raw_at))
                        if raw_in is not None:
                            intensity = _INTENSITY_MAP.get(int(raw_in), str(raw_in))

                    # Steps: cycles field represents accumulated steps (1 cycle ≈ 1 step for Garmin monitoring)
                    # Differentiate to get per-minute count
                    raw_cycles = f.get("cycles")
                    steps_per_min = None
                    if raw_cycles is not None:
                        try:
                            cycles = float(raw_cycles)
                            if prev_cycles is not None and prev_ts is not None:
                                dt_min = (ts - prev_ts).total_seconds() / 60
                                if 0 < dt_min <= 5:  # skip gaps > 5 min
                                    delta_cycles = cycles - prev_cycles
                                    if delta_cycles >= 0:
                                        steps_per_min = round(delta_cycles / dt_min, 1)
                            prev_cycles = cycles
                            prev_ts = ts
                        except (ValueError, TypeError):
                            pass

                    # Calories: active calories for this monitoring period
                    raw_cal = f.get("active_calories") or f.get("calories")
                    calories_per_min = None
                    if raw_cal is not None:
                        try:
                            calories_per_min = float(raw_cal)
                        except (ValueError, TypeError):
                            pass

                    if activity_type is not None or intensity is not None:
                        rows.append({
                            "timestamp":       ts,
                            "intensity":       intensity,
                            "activity_type":   activity_type,
                            "steps_per_min":   steps_per_min,
                            "calories_per_min": calories_per_min,
                        })

            except Exception:
                pass

    if not rows:
        return pd.DataFrame(columns=["intensity", "activity_type", "steps_per_min", "calories_per_min"])

    df = (pd.DataFrame(rows)
          .drop_duplicates("timestamp")
          .sort_values("timestamp")
          .set_index("timestamp"))

    print(f"  Activity: {len(df)} monitoring records extracted from {len(fit_zips)} zip(s)")
    return df


def run(codename: str, data_root: Path = None) -> pd.DataFrame:
    """Extract monitoring activity for one participant and write garmin_minute_activity.csv.

    Args:
        codename: Participant identifier (e.g. 'bosbes').
        data_root: Root of the data directory. Defaults to ../data relative to this script.

    Returns:
        The extracted DataFrame (also written to disk if non-empty).
    """
    if data_root is None:
        data_root = Path(__file__).parent.parent.parent / "data"

    processed_dir = data_root / "wearables" / codename / "processed"
    raw_dir = data_root / "wearables" / codename / "raw" / "export"

    if not raw_dir.exists():
        print(f"  [{codename}] No raw export directory found at {raw_dir} — skipping activity extraction")
        return pd.DataFrame()

    fit_zips = sorted(raw_dir.rglob("*.zip"))
    if not fit_zips:
        print(f"  [{codename}] No FIT zip files found — skipping activity extraction")
        return pd.DataFrame()

    print(f"[{codename}] Extracting monitoring activity from {len(fit_zips)} zip(s)...")
    df = extract_monitoring_activity(fit_zips)

    if not df.empty:
        out = processed_dir / "garmin_minute_activity.csv"
        df.to_csv(out)
        print(f"  → Wrote {len(df)} records to {out.name}")

    return df
