#!/usr/bin/env python3
"""Compare two media catalog CSV files and generate a trending HTML report.

Inputs are CSVs produced by `02_create_catalog.py` with columns:
  Title, Year, IMDbID, Type, primary_genre, runtime, Rating, Votes

(Older CSVs without primary_genre/runtime are also supported.)

Example:
  python optional_compare_catalogs.py media_catalog_2025-12-15.csv media_catalog_2025-12-18.csv \
    --out report.html

The report highlights:
- New / removed titles
- Largest vote increases (absolute and percent)
- Largest rating changes (up/down)
- Biggest rank jumps by vote-rank

Notes:
- Percent vote changes can be noisy for tiny baselines; use --min-old-votes-for-percent.
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass
import datetime as dt
import html
from pathlib import Path
import re
from typing import Any

import pandas as pd


DATE_RE = re.compile(r"(\d{4}-\d{2}-\d{2})")


def _parse_date_from_path(path: Path) -> str | None:
    m = DATE_RE.search(path.name)
    if not m:
        return None
    s = m.group(1)
    try:
        # Validate it is a real date.
        dt.date.fromisoformat(s)
    except ValueError:
        return None
    return s


def _read_catalog(path: Path) -> pd.DataFrame:
    header_cols = set(pd.read_csv(path, nrows=0).columns)
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

    df = pd.read_csv(path, dtype=dtypes)

    required = {"Title", "Year", "IMDbID", "Type", "Rating", "Votes"}
    missing = required - set(df.columns)
    if missing:
        raise ValueError(f"{path} is missing columns: {sorted(missing)}")

    # Optional columns for richer display (keep backward compatibility with older catalogs).
    if "primary_genre" not in df.columns:
        df["primary_genre"] = pd.NA
    if "runtime" not in df.columns:
        df["runtime"] = pd.NA

    # Normalize a bit.
    df["IMDbID"] = df["IMDbID"].astype("string")
    df = df[df["IMDbID"].notna()].copy()
    df = df[df["IMDbID"].str.strip() != ""].copy()

    # Keep one row per IMDbID (should already be unique). If duplicates exist, keep the max Votes row.
    if df["IMDbID"].duplicated().any():
        df["_VotesSort"] = df["Votes"].fillna(0).astype(int)
        df = (
            df.sort_values(by=["IMDbID", "_VotesSort"], ascending=[True, False])
            .drop_duplicates(subset=["IMDbID"], keep="first")
            .drop(columns=["_VotesSort"])
            .reset_index(drop=True)
        )

    # Rank by Votes (descending). Missing votes are treated as 0.
    votes_for_rank = df["Votes"].fillna(0).astype(int)
    df["VotesRank"] = votes_for_rank.rank(method="min", ascending=False).astype("Int64")

    return df


def _imdb_url(imdb_id: str) -> str:
    return f"https://www.imdb.com/title/{imdb_id}/"


def _fmt_int(x: Any) -> str:
    if x is None or pd.isna(x):
        return ""
    try:
        return f"{int(x):,}"
    except Exception:
        return ""


def _fmt_float(x: Any, digits: int = 1) -> str:
    if x is None or pd.isna(x):
        return ""
    try:
        return f"{float(x):.{digits}f}"
    except Exception:
        return ""


def _fmt_pct(x: Any, digits: int = 1) -> str:
    if x is None or pd.isna(x):
        return ""
    try:
        return f"{100.0 * float(x):.{digits}f}%"
    except Exception:
        return ""


def _fmt_signed_int(x: Any) -> str:
    if x is None or pd.isna(x):
        return ""
    try:
        xi = int(x)
        return f"{xi:+,}"
    except Exception:
        return ""


def _fmt_signed_float(x: Any, digits: int = 2) -> str:
    if x is None or pd.isna(x):
        return ""
    try:
        xf = float(x)
        return f"{xf:+.{digits}f}"
    except Exception:
        return ""


def _fmt_score(latest_rating: Any, rating_delta: Any) -> str:
    """Format a consistent 'score' cell: <latest> (<+/-delta>) or <latest> (n/a)."""
    latest = _fmt_float(latest_rating, 1)
    if latest == "":
        return ""

    if rating_delta is None or pd.isna(rating_delta):
        return f"{latest} (—)"

    delta = _fmt_signed_float(rating_delta, 1)
    if delta == "":
        return f"{latest} (—)"

    return f"{latest} ({delta})"


def _escape(s: Any) -> str:
    if s is None or (isinstance(s, float) and pd.isna(s)):
        return ""
    return html.escape(str(s))


@dataclass(frozen=True)
class TableSpec:
    title: str
    description: str
    columns: list[str]
    rows: list[dict[str, Any]]


def _render_table(spec: TableSpec) -> str:
    cols = spec.columns
    thead = "".join(f"<th>{_escape(c)}</th>" for c in cols)

    def cell_html(col: str, val: Any) -> str:
        if col == "Title":
            if isinstance(val, dict):
                title_text = _escape(val.get("text", ""))
                imdb_id = val.get("IMDbID")
            else:
                title_text = _escape(val)
                imdb_id = None

            if imdb_id:
                url = _imdb_url(str(imdb_id))
                return f"<td><a href=\"{_escape(url)}\" target=\"_blank\" rel=\"noreferrer\">{title_text}</a></td>"
            return f"<td>{title_text}</td>"

        return f"<td>{_escape(val)}</td>"

    body_rows = []
    for r in spec.rows:
        tds = []
        for c in cols:
            if c == "Title":
                tds.append(cell_html(c, {"text": r.get("Title", ""), "IMDbID": r.get("IMDbID", "")}))
            else:
                tds.append(cell_html(c, r.get(c, "")))
        body_rows.append("<tr>" + "".join(tds) + "</tr>")

    tbody = "\n".join(body_rows) if body_rows else f"<tr><td colspan=\"{len(cols)}\" class=\"muted\">No rows</td></tr>"

    return (
        "<section class=\"card\">"
        f"<h2>{_escape(spec.title)}</h2>"
        f"<p class=\"muted\">{_escape(spec.description)}</p>"
        "<div class=\"table-wrap\">"
        "<table>"
        f"<thead><tr>{thead}</tr></thead>"
        f"<tbody>{tbody}</tbody>"
        "</table>"
        "</div>"
        "</section>"
    )


def _make_report(
    old_path: Path,
    new_path: Path,
    out_path: Path,
    *,
    top_n: int,
    min_old_votes_for_percent: int,
    new_title_min_votes: int,
) -> None:
    old_df = _read_catalog(old_path)
    new_df = _read_catalog(new_path)

    merged = old_df.merge(
        new_df,
        on="IMDbID",
        how="outer",
        suffixes=("_old", "_new"),
        indicator=True,
    )

    # Helper columns
    merged["Votes_old"] = merged["Votes_old"].fillna(0).astype(int)
    merged["Votes_new"] = merged["Votes_new"].fillna(0).astype(int)

    merged["Rating_old"] = merged["Rating_old"].astype(float)
    merged["Rating_new"] = merged["Rating_new"].astype(float)

    merged["VotesDelta"] = merged["Votes_new"] - merged["Votes_old"]
    merged["VotesDeltaPct"] = merged.apply(
        lambda r: (r["VotesDelta"] / r["Votes_old"]) if r["Votes_old"] > 0 else float("nan"),
        axis=1,
    )

    merged["RatingDelta"] = merged["Rating_new"] - merged["Rating_old"]

    # Rank deltas (only meaningful for titles present in each respective file)
    merged["VotesRank_old"] = merged["VotesRank_old"].astype("Int64")
    merged["VotesRank_new"] = merged["VotesRank_new"].astype("Int64")
    merged["RankChange"] = merged["VotesRank_old"] - merged["VotesRank_new"]

    # Labels
    old_label = _parse_date_from_path(old_path) or old_path.name
    new_label = _parse_date_from_path(new_path) or new_path.name

    # Slices
    common = merged[merged["_merge"] == "both"].copy()
    new_only = merged[merged["_merge"] == "right_only"].copy()
    removed_only = merged[merged["_merge"] == "left_only"].copy()

    # Trending sections
    top_vote_gainers = (
        common.sort_values(by=["VotesDelta", "Votes_new"], ascending=[False, False])
        .head(top_n)
        .copy()
    )

    top_pct_vote_gainers = (
        common[common["Votes_old"] >= min_old_votes_for_percent]
        .sort_values(by=["VotesDeltaPct", "VotesDelta"], ascending=[False, False])
        .head(top_n)
        .copy()
    )

    biggest_rating_up = (
        common.sort_values(by=["RatingDelta", "Votes_new"], ascending=[False, False])
        .head(top_n)
        .copy()
    )

    biggest_rating_down = (
        common.sort_values(by=["RatingDelta", "Votes_new"], ascending=[True, False])
        .head(top_n)
        .copy()
    )

    biggest_rank_jumps = (
        common.dropna(subset=["RankChange"])
        .sort_values(by=["RankChange", "Votes_new"], ascending=[False, False])
        .head(top_n)
        .copy()
    )

    new_titles = (
        new_only[new_only["Votes_new"] >= int(new_title_min_votes)]
        .sort_values(by=["Votes_new", "Rating_new"], ascending=[False, False])
        .head(top_n)
        .copy()
    )

    removed_titles = (
        removed_only.sort_values(by=["Votes_old", "Rating_old"], ascending=[False, False])
        .head(top_n)
        .copy()
    )

    def rows_for(df: pd.DataFrame, kind: str) -> list[dict[str, Any]]:
        rows: list[dict[str, Any]] = []
        for _, r in df.iterrows():
            title = r.get("Title_new") if pd.notna(r.get("Title_new")) else r.get("Title_old")
            year = r.get("Year_new") if pd.notna(r.get("Year_new")) else r.get("Year_old")
            typ = r.get("Type_new") if pd.notna(r.get("Type_new")) else r.get("Type_old")
            primary_genre = (
                r.get("primary_genre_new")
                if pd.notna(r.get("primary_genre_new"))
                else r.get("primary_genre_old")
            )
            runtime = r.get("runtime_new") if pd.notna(r.get("runtime_new")) else r.get("runtime_old")

            # Always include a consistent left-most "Score" column:
            # latest rating + delta (when available), e.g. "8.4 (+0.2)".
            if kind in {"new"}:
                score = _fmt_score(r.get("Rating_new"), None)
            elif kind in {"removed"}:
                score = _fmt_score(r.get("Rating_old"), None)
            else:
                score = _fmt_score(r.get("Rating_new"), r.get("RatingDelta"))

            row: dict[str, Any] = {
                "IMDbID": r.get("IMDbID", ""),
                "Score": score,
                "Title": str(title) if title is not None and not pd.isna(title) else "",
                "Year": "" if year is None or pd.isna(year) else int(year),
                "Type": str(typ) if typ is not None and not pd.isna(typ) else "",
                "primary_genre": (
                    str(primary_genre)
                    if primary_genre is not None and not pd.isna(primary_genre)
                    else ""
                ),
                "runtime": _fmt_int(runtime),
            }

            if kind in {"common", "votes", "pct", "rating", "rank"}:
                row.update(
                    {
                        f"Votes ({old_label})": _fmt_int(r.get("Votes_old")),
                        f"Votes ({new_label})": _fmt_int(r.get("Votes_new")),
                        "Votes Δ": _fmt_signed_int(r.get("VotesDelta")),
                        "Votes Δ%": _fmt_pct(r.get("VotesDeltaPct")),
                        f"Rank ({old_label})": _fmt_int(r.get("VotesRank_old")),
                        f"Rank ({new_label})": _fmt_int(r.get("VotesRank_new")),
                        "Rank Δ": _fmt_signed_int(r.get("RankChange")),
                    }
                )

            if kind == "new":
                row.update(
                    {
                        f"Votes ({new_label})": _fmt_int(r.get("Votes_new")),
                        f"Rank ({new_label})": _fmt_int(r.get("VotesRank_new")),
                    }
                )

            if kind == "removed":
                row.update(
                    {
                        f"Votes ({old_label})": _fmt_int(r.get("Votes_old")),
                        f"Rank ({old_label})": _fmt_int(r.get("VotesRank_old")),
                    }
                )

            rows.append(row)
        return rows

    tables: list[TableSpec] = []

    tables.append(
        TableSpec(
            title=f"Top vote gainers ({old_label} → {new_label})",
            description=f"Largest absolute increase in votes among titles present in both files (top {top_n}).",
            columns=[
                "Score",
                "Title",
                "Year",
                "Type",
                "primary_genre",
                "runtime",
                f"Votes ({old_label})",
                f"Votes ({new_label})",
                "Votes Δ",
                "Votes Δ%",
            ],
            rows=rows_for(top_vote_gainers, "votes"),
        )
    )

    tables.append(
        TableSpec(
            title=f"Top percent vote gainers ({old_label} → {new_label})",
            description=(
                f"Largest percent increase in votes among titles present in both files. "
                f"Filtered to old votes ≥ {min_old_votes_for_percent:,} to reduce noise (top {top_n})."
            ),
            columns=[
                "Score",
                "Title",
                "Year",
                "Type",
                "primary_genre",
                "runtime",
                f"Votes ({old_label})",
                f"Votes ({new_label})",
                "Votes Δ",
                "Votes Δ%",
            ],
            rows=rows_for(top_pct_vote_gainers, "pct"),
        )
    )

    tables.append(
        TableSpec(
            title=f"Biggest rating increases ({old_label} → {new_label})",
            description=f"Largest positive rating change among titles present in both files (top {top_n}).",
            columns=[
                "Score",
                "Title",
                "Year",
                "Type",
                "primary_genre",
                "runtime",
                f"Votes ({new_label})",
                "Votes Δ",
            ],
            rows=rows_for(biggest_rating_up, "rating"),
        )
    )

    tables.append(
        TableSpec(
            title=f"Biggest rating decreases ({old_label} → {new_label})",
            description=f"Largest negative rating change among titles present in both files (top {top_n}).",
            columns=[
                "Score",
                "Title",
                "Year",
                "Type",
                "primary_genre",
                "runtime",
                f"Votes ({new_label})",
                "Votes Δ",
            ],
            rows=rows_for(biggest_rating_down, "rating"),
        )
    )

    tables.append(
        TableSpec(
            title=f"Biggest rank jumps by votes ({old_label} → {new_label})",
            description=(
                f"Rank is by total votes (descending). Positive Rank Δ means it moved up (toward rank 1). "
                f"(top {top_n})"
            ),
            columns=[
                "Score",
                "Title",
                "Year",
                "Type",
                "primary_genre",
                "runtime",
                f"Rank ({old_label})",
                f"Rank ({new_label})",
                "Rank Δ",
                "Votes Δ",
                f"Votes ({new_label})",
            ],
            rows=rows_for(biggest_rank_jumps, "rank"),
        )
    )

    tables.append(
        TableSpec(
            title=f"New titles (only in {new_label})",
            description=f"Present only in the new file, sorted by votes (min new votes: {new_title_min_votes:,}).",
            columns=[
                "Score",
                "Title",
                "Year",
                "Type",
                "primary_genre",
                "runtime",
                f"Votes ({new_label})",
                f"Rank ({new_label})",
            ],
            rows=rows_for(new_titles, "new"),
        )
    )

    tables.append(
        TableSpec(
            title=f"Removed titles (only in {old_label})",
            description="Present only in the old file, sorted by votes.",
            columns=[
                "Score",
                "Title",
                "Year",
                "Type",
                "primary_genre",
                "runtime",
                f"Votes ({old_label})",
                f"Rank ({old_label})",
            ],
            rows=rows_for(removed_titles, "removed"),
        )
    )

    generated_at = dt.datetime.now().astimezone().strftime("%Y-%m-%d %H:%M:%S %Z")

    css = """
:root {
  --bg: #0b1020;
  --card: #121a33;
  --text: #e8ecff;
  --muted: #aab3d8;
  --border: #243055;
  --accent: #7aa2ff;
}
html, body { height: 100%; }
body {
  margin: 0;
  font-family: ui-sans-serif, system-ui, -apple-system, Segoe UI, Roboto, Arial, "Apple Color Emoji", "Segoe UI Emoji";
  background: radial-gradient(1200px 700px at 10% 10%, #15204a 0%, var(--bg) 55%);
  color: var(--text);
}
.container { max-width: 1200px; margin: 0 auto; padding: 24px; }
header h1 { margin: 0 0 8px 0; font-size: 26px; }
header .meta { color: var(--muted); margin: 0; }
.card {
  background: color-mix(in srgb, var(--card) 94%, black);
  border: 1px solid var(--border);
  border-radius: 12px;
  padding: 16px;
  margin: 16px 0;
  box-shadow: 0 10px 30px rgba(0,0,0,.25);
}
.card h2 { margin: 0 0 6px 0; font-size: 18px; }
.muted { color: var(--muted); }
.summary { display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); gap: 12px; }
.kpi { background: rgba(255,255,255,.03); border: 1px solid var(--border); border-radius: 10px; padding: 12px; }
.kpi .label { color: var(--muted); font-size: 12px; }
.kpi .value { font-size: 18px; margin-top: 4px; }
.table-wrap { overflow-x: auto; }
table { width: 100%; border-collapse: collapse; font-size: 12.5px; }
th, td { padding: 8px 10px; border-bottom: 1px solid var(--border); vertical-align: top; }
th { text-align: left; color: var(--muted); font-weight: 600; position: sticky; top: 0; background: rgba(18,26,51,.95); backdrop-filter: blur(6px); }
tr:hover td { background: rgba(255,255,255,.03); }
a { color: var(--accent); text-decoration: none; }
a:hover { text-decoration: underline; }
.footer { color: var(--muted); margin-top: 20px; font-size: 12px; }
@media (max-width: 900px) {
  .summary { grid-template-columns: repeat(2, minmax(0, 1fr)); }
}
"""

    summary_html = (
        "<section class=\"card\">"
        "<div class=\"summary\">"
        f"<div class=\"kpi\"><div class=\"label\">Common titles</div><div class=\"value\">{len(common):,}</div></div>"
        f"<div class=\"kpi\"><div class=\"label\">New titles</div><div class=\"value\">{len(new_only):,}</div></div>"
        f"<div class=\"kpi\"><div class=\"label\">Removed titles</div><div class=\"value\">{len(removed_only):,}</div></div>"
        f"<div class=\"kpi\"><div class=\"label\">Report generated</div><div class=\"value\">{_escape(generated_at)}</div></div>"
        "</div>"
        "</section>"
    )

    body = "\n".join([summary_html] + [_render_table(t) for t in tables])

    html_doc = f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>Media catalog diff: {html.escape(old_label)} → {html.escape(new_label)}</title>
  <style>{css}</style>
</head>
<body>
  <div class="container">
    <header class="card">
      <h1>Media catalog diff: {html.escape(old_label)} → {html.escape(new_label)}</h1>
      <p class="meta">Old: {html.escape(str(old_path))}<br/>New: {html.escape(str(new_path))}</p>
    </header>
    {body}
    <div class="footer">
      Tip: percent vote changes are filtered by <code>--min-old-votes-for-percent</code> to reduce noise.
    </div>
  </div>
</body>
</html>
"""

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(html_doc, encoding="utf-8")


def _default_out_path(old_path: Path, new_path: Path) -> Path:
    old_label = _parse_date_from_path(old_path) or old_path.stem
    new_label = _parse_date_from_path(new_path) or new_path.stem
    safe_old = re.sub(r"[^A-Za-z0-9._-]+", "_", str(old_label))
    safe_new = re.sub(r"[^A-Za-z0-9._-]+", "_", str(new_label))
    return Path(f"catalog_diff_{safe_old}_to_{safe_new}.html")


def main() -> None:
    p = argparse.ArgumentParser(
        description="Compare two media_catalog CSVs and generate a trending HTML report."
    )
    p.add_argument(
        "--dir",
        type=Path,
        default=None,
        help=(
            "Optional base folder. If provided, relative old/new/out paths are resolved under it."
        ),
    )
    p.add_argument("old_csv", type=Path, help="Older CSV file (baseline)")
    p.add_argument("new_csv", type=Path, help="Newer CSV file")
    p.add_argument(
        "--out",
        type=Path,
        default=None,
        help="Output HTML path (default: catalog_diff_<old>_to_<new>.html)",
    )
    p.add_argument(
        "--top",
        type=int,
        default=50,
        help="Number of rows to include per section (default: 50)",
    )
    p.add_argument(
        "--min-old-votes-for-percent",
        type=int,
        default=1000,
        help="Minimum old votes to consider for percent vote gainer table (default: 1000)",
    )
    p.add_argument(
        "--new-title-min-votes",
        type=int,
        default=0,
        help="Minimum votes in the new file to include a new title in the report (default: 0)",
    )
    args = p.parse_args()

    base_dir = args.dir.resolve() if args.dir is not None else None

    old_path = args.old_csv
    new_path = args.new_csv

    if base_dir is not None:
        if not old_path.is_absolute():
            old_path = base_dir / old_path
        if not new_path.is_absolute():
            new_path = base_dir / new_path

    if not old_path.exists():
        raise SystemExit(f"old_csv not found: {old_path}")
    if not new_path.exists():
        raise SystemExit(f"new_csv not found: {new_path}")

    out_path = args.out if args.out is not None else _default_out_path(old_path, new_path)
    if base_dir is not None and not out_path.is_absolute():
        out_path = base_dir / out_path

    _make_report(
        old_path,
        new_path,
        out_path,
        top_n=max(1, int(args.top)),
        min_old_votes_for_percent=max(0, int(args.min_old_votes_for_percent)),
        new_title_min_votes=max(0, int(args.new_title_min_votes)),
    )

    print(str(out_path))


if __name__ == "__main__":
    main()
