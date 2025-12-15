#!/usr/bin/env python3
"""Create a SQLite database from a CSV file containing media catalog data.

Input:
- A CSV file with columns: Title, Year, IMDbID, Type, Rating, Votes

Output:
- A SQLite database file with a table named 'media_catalog'

Usage:
  python 04_make_database.py <csv_file> [--db_file <db_file>]
"""

import sqlite3
import csv
import argparse


def main():
    parser = argparse.ArgumentParser(description="Create SQLite database from CSV")
    parser.add_argument("csv_file", help="Path to the CSV file")
    parser.add_argument("--db_file", default="media_catalog.db", help="Path to the output SQLite database file")
    args = parser.parse_args()

    # Connect to SQLite database
    conn = sqlite3.connect(args.db_file)
    cursor = conn.cursor()

    # Create table if it doesn't exist
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS media_catalog (
            Title TEXT,
            Year INTEGER,
            IMDbID TEXT,
            Type TEXT,
            Rating REAL,
            Votes INTEGER
        )
    ''')

    # Read CSV and insert data
    with open(args.csv_file, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            # Handle potential empty strings for nullable fields
            year = int(row['Year']) if row['Year'].strip() else None
            rating = float(row['Rating']) if row['Rating'].strip() else None
            votes = int(row['Votes']) if row['Votes'].strip() else None

            cursor.execute('''
                INSERT INTO media_catalog (Title, Year, IMDbID, Type, Rating, Votes)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (
                row['Title'],
                year,
                row['IMDbID'],
                row['Type'],
                rating,
                votes
            ))

    # Commit and close
    conn.commit()
    conn.close()

    print(f"Database created successfully: {args.db_file}")


if __name__ == "__main__":
    main()