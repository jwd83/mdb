# Agents

This project provides scripts to download and process IMDb datasets to create an offline media catalog for autosuggest functionality.

## Scripts
- `01_download_imdb.py`: Downloads required IMDb bulk datasets into a working folder (`--dir`).
- `02_create_catalog.py`: Builds `media_catalog.csv` in a working folder (`--dir`).
- `03_filter_catalog.py`: Optionally filters the catalog by min votes in the same working folder (`--dir`).
- `04_make_database.py`: Builds a SQLite DB from a catalog CSV and writes it into a working folder (`--dir`).
- `main.py`: Runs 01 → 04 as a single “daily build”, creating a new date-stamped folder each run.

## Usage
Run a daily build (creates a new folder under `builds/` each run):
1. `python main.py --out-root builds --min-votes 50000`

Optionally create a trending report:
2. `python optional_compare_catalogs.py <old.csv> <new.csv> --out report.html`
