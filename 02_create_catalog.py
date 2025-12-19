#!/usr/bin/env python3
"""Build an offline media autosuggest catalog CSV from IMDb bulk datasets.

Inputs (read from --dir):
- title.basics.tsv.gz
- title.ratings.tsv.gz

Output (written to --dir):
- media_catalog.csv

Usage:
  python 02_create_catalog.py --dir <folder>
"""

from __future__ import annotations

import argparse
from pathlib import Path
import gzip

import pandas as pd


ALLOWED_TYPES = {"movie", "tvSeries"}


def read_basics(basics_path: Path) -> pd.DataFrame:
    """Read title.basics.tsv.gz directly from gzip."""
    with gzip.open(basics_path, "rt", encoding="utf-8") as f:
        return pd.read_csv(
            f,
            sep="\t",
            usecols=["tconst", "titleType", "primaryTitle", "startYear", "runtimeMinutes", "genres"],
            dtype={
                "tconst": "string",
                "titleType": "string",
                "primaryTitle": "string",
                "startYear": "string",
                "runtimeMinutes": "string",
                "genres": "string",
            },
            na_values=["\\N"],
            keep_default_na=False,
        )


def read_ratings(ratings_path: Path) -> pd.DataFrame:
    """Read title.ratings.tsv.gz directly from gzip."""
    with gzip.open(ratings_path, "rt", encoding="utf-8") as f:
        return pd.read_csv(
            f,
            sep="\t",
            usecols=["tconst", "averageRating", "numVotes"],
            dtype={
                "tconst": "string",
                "averageRating": "string",
                "numVotes": "string",
            },
            na_values=["\\N"],
            keep_default_na=False,
        )


def main() -> None:
    p = argparse.ArgumentParser(description="Create media_catalog.csv from IMDb TSV datasets.")
    p.add_argument("--dir", type=Path, required=True, help="Working folder (inputs and outputs)")
    args = p.parse_args()

    workdir = args.dir.resolve()

    basics_path = workdir / "title.basics.tsv.gz"
    ratings_path = workdir / "title.ratings.tsv.gz"
    output_path = workdir / "media_catalog.csv"

    # Load input datasets.
    basics = read_basics(basics_path)
    ratings = read_ratings(ratings_path)

    # Filter to supported title types (movie, tvSeries).
    basics = basics[basics["titleType"].isin(ALLOWED_TYPES)].copy()

    # Drop rows with missing/invalid Title.
    basics["primaryTitle"] = basics["primaryTitle"].astype("string")
    basics = basics[basics["primaryTitle"].notna()].copy()
    basics = basics[basics["primaryTitle"].str.strip() != ""].copy()

    # Convert Year to integer and drop missing/invalid Year.
    basics["startYear"] = pd.to_numeric(basics["startYear"], errors="coerce")
    basics = basics[basics["startYear"].notna()].copy()
    basics["startYear"] = basics["startYear"].astype(int)

    # Parse runtime (minutes). Allow missing/invalid runtime.
    basics["runtimeMinutes"] = pd.to_numeric(basics["runtimeMinutes"], errors="coerce").astype(
        "Int64"
    )

    # Derive a single primary genre from the comma-separated genres list.
    # Example: "Action,Drama" -> "Action". Missing genres remain missing.
    basics["primary_genre"] = basics["genres"].astype("string").str.split(",").str[0]

    # Prepare ratings fields (allow missing Rating and Votes).
    ratings["averageRating"] = pd.to_numeric(ratings["averageRating"], errors="coerce")
    ratings["numVotes"] = pd.to_numeric(ratings["numVotes"], errors="coerce").astype("Int64")

    # Join datasets on IMDb ID (tconst).
    merged = basics.merge(ratings, on="tconst", how="left")

    # Map fields to the requested output schema.
    out = merged.rename(
        columns={
            "primaryTitle": "Title",
            "startYear": "Year",
            "tconst": "IMDbID",
            "titleType": "Type",
            "averageRating": "Rating",
            "numVotes": "Votes",
            "primary_genre": "primary_genre",
            "runtimeMinutes": "runtime",
        }
    )[["Title", "Year", "IMDbID", "Type", "primary_genre", "runtime", "Rating", "Votes"]]

    # Sort by Votes (descending) then Rating (descending). Missing values sort last.
    out["_VotesSort"] = out["Votes"].fillna(0).astype(int)
    out["_RatingSort"] = out["Rating"].fillna(-1.0)
    out = (
        out.sort_values(by=["_VotesSort", "_RatingSort"], ascending=[False, False])
        .drop(columns=["_VotesSort", "_RatingSort"])
        .reset_index(drop=True)
    )

    # Write output CSV.
    out.to_csv(output_path, index=False, encoding="utf-8")


if __name__ == "__main__":
    main()
