from __future__ import annotations
from pathlib import Path

import duckdb
import polars as pl

class Database:
    def __init__(self, path: str, read_only: bool = False):
        """Connect to the DuckDB database, store connection as self._conn."""
        self._conn = duckdb.connect(str(path), read_only=read_only)

    def execute(self, sql, params=None):
        """Run SQL with no return value"""
        self._conn.execute(sql, params or [])

    def query(self, sql, params=None) -> list[dict]:
        """Run SELECT and return results as list of dicts."""
        return self._conn.execute(sql, params or []).pl().to_dicts()

    def query_df(self, sql, params=None) -> pl.DataFrame:
        """Run SELECT and return results as a Polars DataFrame."""
        return self._conn.execute(sql, params or []).pl()

    def list_tables(self) -> list[str]:
        """Return sorted list of table names in main schema."""
        result = self._conn.execute(
            """
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'main' 
            ORDER BY table_name
            """
        ).fetchall()
        tables = [row[0] for row in result]
        return tables

    def describe_table(self, table_name: str) -> list[dict]:
        """Return list of dicts {name, type, nullable}. Raise ValueError if unknown"""
        result = self._conn.execute(
            """
            SELECT column_name, data_type, is_nullable
            FROM information_schema.columns
            WHERE table_schema = 'main' AND table_name = ?
            ORDER BY ordinal_position
            """,
            (table_name,)
        ).fetchall()
        if not result:
            raise ValueError(f"Table '{table_name}' not found")
        return [{"name": row[0], "type": row[1], "nullable": row[2] == 'YES'} for row in result]

    def close(self):
        """Close the database connection."""
        if self._conn is not None:
            self._conn.close()
            self._conn = None

    def __enter__(self):
        """Support with statement."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Ensure connection is closed when exiting with block."""
        self.close()
        return False  # Don't suppress exceptions