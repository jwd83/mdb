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
    args = parser.parse_args()

    script_dir = Path(__file__).resolve().parent
    input_path = script_dir / "media_catalog.csv"
    output_path = script_dir / f"media_catalog_{args.min_votes}.csv"

    # Load the catalog
    df = pd.read_csv(input_path, dtype={"Votes": "Int64"})

    # Filter entries with more than min_votes
    filtered_df = df[df["Votes"] > args.min_votes]

    # Save the filtered catalog
    filtered_df.to_csv(output_path, index=False, encoding="utf-8")
    print(f"Filtered catalog saved to {output_path}")


if __name__ == "__main__":
    main()
