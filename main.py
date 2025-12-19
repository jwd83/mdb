#!/usr/bin/env python3
"""Run the daily build pipeline.

This creates a new date-stamped output folder under --out-root and runs:
  01_download_imdb.py -> 02_create_catalog.py -> (optional) 03_filter_catalog.py -> 04_make_database.py

Outputs (in the created daily folder):
- title.basics.tsv.gz
- title.ratings.tsv.gz
- media_catalog.csv
- optional: media_catalog_<minVotes>.csv
- media_catalog.db (or --db-name)

Usage:
  python main.py [--out-root builds] [--min-votes 250] [--db-name media_catalog.db]

Folder naming:
- Default folder name is today in local time: YYYY-MM-DD
- If that folder already exists, we create YYYY-MM-DD_2, YYYY-MM-DD_3, ...
"""

from __future__ import annotations

import argparse
import datetime as dt
from pathlib import Path
import subprocess
import sys


def _today_iso() -> str:
    return dt.datetime.now().astimezone().date().isoformat()


def _make_daily_dir(out_root: Path, base_name: str) -> Path:
    out_root.mkdir(parents=True, exist_ok=True)

    candidate = out_root / base_name
    if not candidate.exists():
        candidate.mkdir(parents=True, exist_ok=False)
        return candidate

    i = 2
    while True:
        candidate = out_root / f"{base_name}_{i}"
        if not candidate.exists():
            candidate.mkdir(parents=True, exist_ok=False)
            return candidate
        i += 1


def _run(script_name: str, args: list[str]) -> None:
    script_path = Path(__file__).resolve().parent / script_name
    cmd = [sys.executable, str(script_path), *args]
    subprocess.run(cmd, check=True)


def main() -> None:
    p = argparse.ArgumentParser(description="Run the full daily build pipeline.")
    p.add_argument(
        "--out-root",
        type=Path,
        default=Path("builds"),
        help="Root folder to create daily build folders under (default: builds)",
    )
    p.add_argument(
        "--date",
        default=None,
        help="Override folder date label (default: today in local time, YYYY-MM-DD)",
    )
    p.add_argument(
        "--min-votes",
        type=int,
        default=250,
        help=(
            "Minimum votes for filtered catalog/DB build (default: 250). "
            "Set to 0 to effectively disable filtering."
        ),
    )
    p.add_argument(
        "--db-name",
        default="media_catalog.db",
        help="DB filename to create inside the daily folder (default: media_catalog.db)",
    )
    p.add_argument(
        "--download-overwrite",
        action="store_true",
        help="Overwrite title.*.tsv.gz if already present in the daily folder",
    )

    args = p.parse_args()

    date_label = str(args.date) if args.date else _today_iso()
    daily_dir = _make_daily_dir(args.out_root.resolve(), date_label)

    # 01: download datasets
    dl_args = ["--dir", str(daily_dir)]
    if args.download_overwrite:
        dl_args.append("--overwrite")
    _run("01_download_imdb.py", dl_args)

    # 02: create catalog
    _run("02_create_catalog.py", ["--dir", str(daily_dir)])

    # 03: optional filter
    csv_for_db = daily_dir / "media_catalog.csv"
    mv = int(args.min_votes)
    if mv > 0:
        _run("03_filter_catalog.py", [str(mv), "--dir", str(daily_dir)])
        csv_for_db = daily_dir / f"media_catalog_{mv}.csv"

    # 04: make database (from filtered if provided)
    _run(
        "04_make_database.py",
        ["--dir", str(daily_dir), str(csv_for_db.name), "--db_file", str(args.db_name)],
    )

    print(str(daily_dir))


if __name__ == "__main__":
    main()
