# IMDb Media Catalog

This project provides scripts to download and process IMDb datasets to create an offline media catalog for autosuggest functionality.


## Daily build
```bash
python main.py
```
Defaults:
- `--out-root builds`
- `--min-votes 250`

This creates `builds/YYYY-MM-DD/` (or `builds/YYYY-MM-DD_2/`, etc.) and writes all outputs there.


## Scripts
- `main.py`: Runs 01 → 04 as a single “daily build”, creating a new date-stamped folder each run.
- `01_download_imdb.py`: Downloads required IMDb bulk datasets into a working folder (`--dir`).
- `02_create_catalog.py`: Builds `media_catalog.csv` in a working folder (`--dir`).
- `03_filter_catalog.py`: Optionally filters the catalog by min votes in the same working folder (`--dir`).
- `04_make_database.py`: Builds a SQLite DB from a catalog CSV and writes it into a working folder (`--dir`).
- `optional_compare_catalogs.py`: (Optional) compares two catalog CSVs and generates a self-contained HTML trending report.

## Compare two daily catalogs (optional trending report)
```bash
python optional_compare_catalogs.py --dir builds media_catalog_2025-12-15.csv media_catalog_2025-12-18.csv --out report.html
```

Optional flags:
- `--out report.html`: output HTML path
- `--top 100`: number of rows per section
- `--min-old-votes-for-percent 1000`: baseline threshold for percent-vote-gainers table
- `--new-title-min-votes 500`: hide very low-vote new titles
