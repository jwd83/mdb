#!/usr/bin/env python3
"""Build an offline media autosuggest catalog CSV from IMDb bulk datasets.

Inputs (must be in the same directory as this script):
- title.basics.tsv.gz
- title.ratings.tsv.gz

Output:
- media_catalog.csv

Usage:
  python build_catalog.py
"""

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
            usecols=["tconst", "titleType", "primaryTitle", "startYear"],
            dtype={
                "tconst": "string",
                "titleType": "string",
                "primaryTitle": "string",
                "startYear": "string",
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
    script_dir = Path(__file__).resolve().parent

    basics_path = script_dir / "title.basics.tsv.gz"
    ratings_path = script_dir / "title.ratings.tsv.gz"
    output_path = script_dir / "media_catalog.csv"

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
        }
    )[["Title", "Year", "IMDbID", "Type", "Rating", "Votes"]]

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
