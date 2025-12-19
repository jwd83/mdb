#!/usr/bin/env python3
"""Download IMDb bulk datasets needed by this project.

Outputs (written under --dir):
- title.basics.tsv.gz
- title.ratings.tsv.gz

Usage:
  python 01_download_imdb.py --dir <folder>
"""

from __future__ import annotations

import argparse
from pathlib import Path
import shutil
import urllib.request


URLS = {
    "title.basics.tsv.gz": "https://datasets.imdbws.com/title.basics.tsv.gz",
    "title.ratings.tsv.gz": "https://datasets.imdbws.com/title.ratings.tsv.gz",
}


def _download(url: str, out_path: Path, *, overwrite: bool) -> None:
    if out_path.exists() and not overwrite:
        return

    out_path.parent.mkdir(parents=True, exist_ok=True)
    with urllib.request.urlopen(url) as r, out_path.open("wb") as f:
        shutil.copyfileobj(r, f)


def main() -> None:
    p = argparse.ArgumentParser(description="Download required IMDb datasets.")
    p.add_argument("--dir", type=Path, required=True, help="Output folder")
    p.add_argument(
        "--overwrite",
        action="store_true",
        help="Overwrite existing files if present",
    )
    args = p.parse_args()

    workdir = args.dir.resolve()
    workdir.mkdir(parents=True, exist_ok=True)

    for filename, url in URLS.items():
        _download(url, workdir / filename, overwrite=bool(args.overwrite))


if __name__ == "__main__":
    main()
