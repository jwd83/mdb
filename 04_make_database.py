#!/usr/bin/env python3
"""Create a SQLite database from a CSV file containing media catalog data.

Input:
- A CSV file with columns:
  Title, Year, IMDbID, Type, primary_genre, runtime, Rating, Votes

Output:
- A SQLite database file with a table named 'media_catalog'

Usage:
  python 04_make_database.py --dir <folder> [<csv_file>] [--db_file <db_file>]

Notes:
- If <csv_file> is omitted, defaults to <dir>/media_catalog.csv.
- If --db_file is a relative path (default: media_catalog.db), it's written under <dir>/.
"""

from __future__ import annotations

import sqlite3
import csv
import argparse
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(description="Create SQLite database from CSV")
    parser.add_argument(
        "--dir",
        type=Path,
        required=True,
        help="Working folder for resolving default input CSV and output DB paths",
    )
    parser.add_argument(
        "csv_file",
        nargs="?",
        default=None,
        help="Path to the CSV file (default: <dir>/media_catalog.csv)",
    )
    parser.add_argument(
        "--db_file",
        default="media_catalog.db",
        help="Path to the output SQLite database file (default: <dir>/media_catalog.db)",
    )
    args = parser.parse_args()

    workdir = args.dir.resolve()
    csv_path = Path(args.csv_file) if args.csv_file is not None else (workdir / "media_catalog.csv")
    if not csv_path.is_absolute():
        csv_path = workdir / csv_path

    db_path = Path(args.db_file)
    if not db_path.is_absolute():
        db_path = workdir / db_path

    # Connect to SQLite database
    conn = sqlite3.connect(str(db_path))
    cursor = conn.cursor()

    # Create table if it doesn't exist.
    cursor.execute(
        '''
        CREATE TABLE IF NOT EXISTS media_catalog (
            Title TEXT,
            Year INTEGER,
            IMDbID TEXT,
            Type TEXT,
            primary_genre TEXT,
            runtime INTEGER,
            Rating REAL,
            Votes INTEGER
        )
    '''
    )

    # Read CSV and insert data
    with open(csv_path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            # Handle potential empty strings for nullable fields
            year = int(row["Year"]) if row.get("Year", "").strip() else None
            rating = float(row["Rating"]) if row.get("Rating", "").strip() else None
            votes = int(row["Votes"]) if row.get("Votes", "").strip() else None
            runtime = int(row["runtime"]) if row.get("runtime", "").strip() else None
            primary_genre = row.get("primary_genre") or None

            cursor.execute(
                '''
                INSERT INTO media_catalog (Title, Year, IMDbID, Type, primary_genre, runtime, Rating, Votes)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''',
                (
                    row.get("Title"),
                    year,
                    row.get("IMDbID"),
                    row.get("Type"),
                    primary_genre,
                    runtime,
                    rating,
                    votes,
                ),
            )

    # Commit and close
    conn.commit()
    conn.close()

    print(f"Database created successfully: {db_path}")


if __name__ == "__main__":
    main()