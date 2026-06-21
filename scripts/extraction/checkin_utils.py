"""
checkin_utils.py — Check-in date parsing and auto-correction for Project R.E.M.

Background
----------
Google Forms exports check-in dates as YYYY-MM-DD (ISO 8601).  On some mobile
clients the date-picker shows day and month fields in the wrong order, causing
participants to produce YYYY-DD-MM instead of YYYY-MM-DD (e.g., March 10 →
"2026-10-03" instead of "2026-03-10").

Detection
---------
The 'Tijdstempel' column is the server-side form submission timestamp and is
always correct.  A check-in date outside the plausible window (more than 7 days
before the submission or more than 1 day after) is flagged as suspicious.

Correction
----------
When a suspicious date is detected, month and day are swapped (YYYY-DD-MM →
YYYY-MM-DD) and re-parsed with the same strict ISO format.  If the result falls
within the plausible window, the correction is accepted and a UserWarning is
emitted.  If the swap still does not produce a plausible date, the original
value is kept and a warning is emitted so the researcher can inspect the row.
"""

import re
import warnings
import pandas as pd

CHECKIN_DATE_COL = "Welke dag deed je een check-in?"
TIMESTAMP_COL    = "Tijdstempel"

# How far a check-in date may deviate from the submission timestamp before it
# is flagged as suspicious.  1 day covers midnight / clock-skew edge cases;
# 7 days past covers rare cases where a participant back-fills a missed entry.
_FUTURE_TOLERANCE = pd.Timedelta(days=1)
_PAST_TOLERANCE   = pd.Timedelta(days=7)


def fix_checkin_dates(sessions: pd.DataFrame) -> pd.Series:
    """Return a Series of corrected pd.Timestamps for the check-in date column.

    Applies row-by-row validation: if the parsed check-in date is outside the
    plausible window around the submission timestamp, a YYYY-DD-MM → YYYY-MM-DD
    swap is attempted.  A UserWarning is emitted for every corrected or
    unresolvable row so problems surface in pipeline output.

    Parameters
    ----------
    sessions : pd.DataFrame
        Must contain CHECKIN_DATE_COL and TIMESTAMP_COL.

    Returns
    -------
    pd.Series of timezone-naive pd.Timestamp, one per row.
    """

    def _fix_row(row):
        # ── Submission timestamp (anchor) ─────────────────────────────────────
        # Format: "YYYY/MM/DD H:MM:SS a.m./p.m. EET" — strip timezone suffix,
        # normalise a.m./p.m. → AM/PM, then parse with an explicit strptime format.
        ts_clean = re.sub(r"\s+[A-Z]{2,5}$", "", str(row[TIMESTAMP_COL]).strip())
        ts_clean = ts_clean.replace("a.m.", "AM").replace("p.m.", "PM")
        submit_dt = pd.to_datetime(ts_clean, format="%Y/%m/%d %I:%M:%S %p")

        # ── Check-in date (participant-entered) ───────────────────────────────
        raw = str(row[CHECKIN_DATE_COL]).strip()

        # Primary parse: strict YYYY-MM-DD (Google Forms ISO export).
        try:
            checkin_dt = pd.to_datetime(raw, format="%Y-%m-%d")
        except ValueError:
            # Unexpected format (e.g., if the export locale ever changes).
            # Use pandas mixed-format inference and warn so it is visible.
            warnings.warn(
                f"[check-in date] '{raw}' is not YYYY-MM-DD — "
                f"falling back to format inference; please verify this row manually",
                stacklevel=2,
            )
            try:
                checkin_dt = pd.to_datetime(raw, format="mixed", dayfirst=True)
            except ValueError:
                warnings.warn(
                    f"[check-in date] Could not parse '{raw}' at all — returning NaT",
                    stacklevel=2,
                )
                return pd.NaT

        # ── Happy path ────────────────────────────────────────────────────────
        if submit_dt - _PAST_TOLERANCE <= checkin_dt <= submit_dt + _FUTURE_TOLERANCE:
            return checkin_dt

        # ── Suspicious: try YYYY-DD-MM → YYYY-MM-DD swap ─────────────────────
        # Mobile bug: date picker on some clients shows day before month, so
        # participants produce "YYYY-DD-MM" when they should enter "YYYY-MM-DD".
        parts = raw.split("-")
        if len(parts) == 3:
            swapped_raw = f"{parts[0]}-{parts[2]}-{parts[1]}"
            try:
                swapped_dt = pd.to_datetime(swapped_raw, format="%Y-%m-%d")
                if submit_dt - _PAST_TOLERANCE <= swapped_dt <= submit_dt + _FUTURE_TOLERANCE:
                    warnings.warn(
                        f"[check-in date] Submitted {submit_dt.date()}: "
                        f"'{raw}' looks month/day-swapped (YYYY-DD-MM mobile bug) — "
                        f"auto-corrected to {swapped_dt.date()}",
                        stacklevel=2,
                    )
                    return swapped_dt
            except ValueError:
                pass

        # ── Could not auto-correct ────────────────────────────────────────────
        warnings.warn(
            f"[check-in date] Submitted {submit_dt.date()}: "
            f"date '{raw}' is outside plausible range and could not be auto-corrected — "
            f"please verify this row manually",
            stacklevel=2,
        )
        return checkin_dt

    return sessions.apply(_fix_row, axis=1)
