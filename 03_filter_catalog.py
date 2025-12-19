"""
this script will load media_catalog.csv and
filter it to only include only entries with over
a specified number of votes. the resulting file
will be saved as media_catalog_X.csv where X is the minimum
number of votes.

"""

import argparse
import pandas as pd
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(description="Filter media catalog by minimum votes.")
    parser.add_argument("min_votes", type=int, help="Minimum number of votes to include")
    parser.add_argument(
        "--dir",
        type=Path,
        required=True,
        help="Working folder containing media_catalog.csv (and where output is written)",
    )
    args = parser.parse_args()

    workdir = args.dir.resolve()
    input_path = workdir / "media_catalog.csv"
    output_path = workdir / f"media_catalog_{args.min_votes}.csv"

    # Load the catalog (keep stable dtypes for known columns; extra columns are preserved).
    # Backwards compatible with older catalogs that don't include primary_genre/runtime.
    header_cols = set(pd.read_csv(input_path, nrows=0).columns)
    desired_dtypes = {
        "Title": "string",
        "Year": "Int64",
        "IMDbID": "string",
        "Type": "string",
        "primary_genre": "string",
        "runtime": "Int64",
        "Rating": "float64",
        "Votes": "Int64",
    }
    dtypes = {k: v for k, v in desired_dtypes.items() if k in header_cols}
    df = pd.read_csv(input_path, dtype=dtypes)

    # Filter entries with more than min_votes
    filtered_df = df[df["Votes"] > args.min_votes]

    # Save the filtered catalog
    filtered_df.to_csv(output_path, index=False, encoding="utf-8")
    print(f"Filtered catalog saved to {output_path}")


if __name__ == "__main__":
    main()
