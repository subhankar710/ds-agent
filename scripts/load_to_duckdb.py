"""Loads Olist CSVs from data/raw/ into a single DuckDB file.

Idempotent: each table is CREATE OR REPLACE'd, so reruns are safe.

Usage:
    python scripts/load_to_duckdb.py
"""
from __future__ import annotations

import sys
from pathlib import Path

import duckdb

RAW_DIR = Path("data/raw")
DB_PATH = Path("data/ds_agent.duckdb")


def table_name_from_csv(path: Path) -> str:
    """olist_orders_dataset.csv → olist_orders_dataset"""
    return path.stem


def main() -> int:
    csvs = sorted(RAW_DIR.glob("*.csv"))
    if not csvs:
        print(
            f"ERROR: no CSVs found in {RAW_DIR}/. Run scripts/download_data.py first.",
            file=sys.stderr,
        )
        return 1

    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = duckdb.connect(str(DB_PATH))

    try:
        for csv in csvs:
            table = table_name_from_csv(csv)
            print(f"[load] {csv.name} → {table}")
            conn.execute(
                f"CREATE OR REPLACE TABLE {table} AS "
                f"SELECT * FROM read_csv_auto(?)",
                [str(csv)],
            )

        # Sanity print: tables, row counts, column counts.
        result = conn.execute(
            "SELECT table_name, "
            "(SELECT COUNT(*) FROM information_schema.columns "
            " WHERE table_name = t.table_name) AS n_cols "
            "FROM information_schema.tables t "
            "WHERE table_schema = 'main' "
            "ORDER BY table_name"
        ).fetchall()
        print("\n[done] tables in DB:")
        for table, n_cols in result:
            n_rows = conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
            print(f"  {table}: {n_rows:,} rows × {n_cols} cols")
    finally:
        conn.close()

    print(f"\n[ok] DB at {DB_PATH} ({DB_PATH.stat().st_size / 1024 / 1024:.1f} MB)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
