# Project Cleanup Checklist

Audit date: 2026-05-07

## Priority 1: Safe to delete now

- [ ] `docs/info_deelnemers/smartwatch_instructies/~$mazfit.docx` -- Word temp/lock file
- [ ] `scripts/analysis/__pycache__/` -- 9 .pyc files
- [ ] `scripts/playlists/spotify_modules/__pycache__/` -- 4 .pyc files
- [ ] `scripts/wearables/__pycache__/` -- 1 .pyc file
- [ ] `data/check_in/old_check/check_in2.csv` -- old version (24 rows, Feb 24)
- [ ] `data/check_in/old_check/check_in_2.csv` -- old version (28 rows, Feb 27)
- [ ] `data/check_in/old_check/check_in_27022026.csv` -- old version, dated filename (28 rows, Feb 27)
- [ ] Consider deleting `data/check_in/old_check/` entirely -- only `data/check_in/check_in.csv` is used

## Priority 2: Needs decision

### Undocumented scripts
- [ ] `scripts/playlists/spotify_tui.py` -- TUI version of the CLI. Actively maintained or superseded by `spotify_cli.py`?
- [ ] `scripts/playlists/update_playlist_gen.py` -- Hardcoded generator for kokosnoot & peer. One-off utility or still needed?
- [ ] `scripts/wearables/garmin_pipeline_easy.py` -- Simplified Garmin pipeline. Duplicate of `garmin_pipeline.py` or separate use case?

### Archived notebooks
- [ ] `notebooks/_old/` -- 11 archived notebooks (~11 MB). Has `.gitkeep` so intentionally kept. Still needed for reference?
- [ ] `docs/playgrounds/av_playground/_old/` -- Old AcousticBrainz feature experiments. Still relevant?

### Unclear model files
- [ ] `models/config.json` -- What uses this? Document or remove.
- [ ] `models/scaler.pkl` -- Sklearn scaler pickle. What model/notebook produced this? Document or remove.

## Priority 3: Data organization

### Empty participant directories
- [ ] `data/analysis/aardbei/` -- empty
- [ ] `data/analysis/citroen/` -- empty
- [ ] `data/playlists/kokosnoot/` -- empty (participant has wearables data but no playlists)

### Misplaced data
- [ ] `data/persoonlijk/` -- Personal Spotify & Garmin exports. Should these be under `data/playlists/` and `data/wearables/` respectively?
- [ ] `data/persoonlijk/*.zip` -- Unprocessed raw archives (~41 MB). Process or remove?

### Inconsistent playlist structures
Different participants have different subdirectory layouts:
- `bosbes/`: only `playlists_generated/`
- `courgette/`: `playlists_generated/` + `playlists_output/` + `playlist_ml/` + `losse_csv/`
- `peer/`: `playlists_generated/` + `playlist_ml/` + raw CSVs at root

Should these be standardized?

## Priority 4: Optional

- [ ] `scripts/pipeline/` -- BRONZE/SILVER/GOLD stubs (~5% implemented). Keep as scaffolding or remove dead code?
- [ ] `data/wearables/kokosnoot/processed/` -- Missing `garmin_health_snapshots.csv` that other participants have. Expected?
- [ ] Add `__pycache__/` and `*.pyc` to `.gitignore` if not already there (prevent future commits)
