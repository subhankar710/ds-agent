# Lesson Plan — Week 1, Step 2: Olist data + DuckDB

> **For agentic workers:** This plan is a **learning-first lesson**. Each substep names a mode (**Tutor** = Claude codes + narrates; **Coach** = Subhankar codes, Claude reviews) before any code is written. Steps use checkbox (`- [ ]`) syntax for tracking.

- **Date:** 2026-04-30
- **Step in Week 1:** 2 of 7
- **Estimated time:** ~2-3 hours (~30 min Tutor for ingestion + ~75 min Coach for `db.py` + ~15 min Tutor for CLI demo + reflection)
- **Prerequisites:** see [Section 0](#0-prerequisites)

> **Commit policy:** every "Suggested commit" block lists exact `git add` / `git commit` commands. **Subhankar runs these — Claude does not.**

---

## 0. Prerequisites

- [ ] **Lesson 1 merged to `main`.** Status log in the spec confirms this.
- [ ] **`ds-agent` conda env activates** and Lesson 1's tests still pass:
  ```bash
  conda activate ds-agent
  pytest -v        # expect 7 passed
  ```
- [ ] **Kaggle account.** Free signup at https://www.kaggle.com if you don't have one.
- [ ] **Working from a fresh feature branch:**
  ```bash
  git switch main
  git pull
  git switch -c feat/lesson-2-duckdb-olist
  git push -u origin feat/lesson-2-duckdb-olist
  ```

---

## 1. Concept — what this lesson teaches

### 1.1 Why a separate "data layer"

In Lesson 1 we built `LLMClient` — a wrapper around the Anthropic API. Lesson 2 builds the symmetric piece: a wrapper around DuckDB. Both follow the same production pattern: **isolate the external dependency behind a small, typed Python class**.

Why this matters: in Lesson 3 the agent will call SQL via tool use. The tool implementation will say "given a SQL string, run it and return rows." It does NOT contain DuckDB-specific code — that lives in `db.py`. If we ever swap DuckDB for Postgres or BigQuery, only `db.py` changes. The tool, the agent loop, the CLI — all unchanged.

### 1.2 Why DuckDB

DuckDB is an **embedded analytical SQL engine** — like SQLite but optimized for analytics queries (aggregations, joins, group-bys). For this project:

- Zero install / zero server (it's a Python library; the database is a single `.duckdb` file).
- Reads CSV / Parquet / JSON natively. We can `SELECT * FROM 'data/raw/olist_orders.csv'` without an explicit load step (though we'll do an explicit load for performance).
- Real, standards-compliant SQL — same syntax as Postgres for 95% of queries.
- Polars + DuckDB share **Arrow** (a columnar in-memory format), so converting a DuckDB result to a polars DataFrame is **zero-copy** — no memory shuffling.

### 1.3 Why polars (not pandas)

- Faster: polars uses Rust + multi-threaded execution by default.
- Cleaner API: explicit, expression-based, fewer footguns than pandas (no implicit index, no `SettingWithCopyWarning`).
- Native Arrow interop with DuckDB.
- Modern: polars is what new analytical Python projects pick in 2025-2026.

We use `list[dict]` as the **primary** return type (LLM-friendly, JSON-serializable for tool results in Lesson 3) and `polars.DataFrame` as a separate method for human / notebook use.

### 1.4 Why **schema introspection** matters for an LLM

The agent has to write SQL against tables it has never seen. So we need ways to ask the database "what tables exist?" and "what columns does this table have?" — then we feed the answer into the LLM's context. Two methods:

- `list_tables() -> list[str]`
- `describe_table(name) -> list[dict]` — column name, type, nullability

These are the building blocks of the `get_relevant_schema` tool we'll build in Lesson 3.

### 1.5 Why **read-only** mode matters

DuckDB lets us connect with `read_only=True`. When we expose SQL execution to the LLM in Lesson 3, the safest baseline is "read-only by default — no destructive operations possible at the connection level." This is **defense in depth**: even if the SQL guardrail (Step 5) fails, the connection can't write.

For this lesson we'll write the class with a `read_only` flag, default `False` (loading data needs write access), but tests verify the read-only path works.

---

## 2. Goal (the done definition)

By the end of Lesson 2, you can:

1. Run `python scripts/download_data.py` and have the Olist zip land in `data/raw/`.
2. Run `python scripts/load_to_duckdb.py` and have a `data/ds_agent.duckdb` file with 9 tables.
3. Open a Python REPL inside the conda env, do:
   ```python
   from ds_agent.db import Database
   db = Database("data/ds_agent.duckdb", read_only=True)
   db.list_tables()                                                         # ['olist_customers_dataset', ...]
   rows = db.query("SELECT COUNT(*) AS n FROM olist_orders_dataset")        # [{"n": 99441}]
   ```
4. Run `pytest -v` and see **13 tests pass** (7 from Lesson 1 + 6 new for `db.py`).
5. Run `ds-agent db tables` and `ds-agent db schema olist_orders_dataset` from the terminal and see formatted output.

**Quantitative done test:**

```bash
ls -lh data/ds_agent.duckdb                    # file exists, ~10-30 MB
pytest -v                                      # 13 passed
ds-agent db tables                             # prints 9 table names
ds-agent ask "say hi"                          # Lesson 1 still works, untouched
```

---

## 3. File map

```
ds-agent/
├── data/
│   ├── raw/                              # NEW (gitignored — already)
│   │   └── brazilian-ecommerce.zip       # NEW (downloaded)
│   │   └── *.csv                         # NEW (extracted, gitignored)
│   └── ds_agent.duckdb                   # NEW (built by load script, gitignored)
├── pyproject.toml                        # MODIFY — add `kaggle` and `polars` deps
├── README.md                             # MODIFY — add data download instructions
├── scripts/
│   ├── download_data.py                  # NEW (uses Kaggle API)
│   └── load_to_duckdb.py                 # NEW (CSVs → DuckDB)
├── src/ds_agent/
│   ├── cli.py                            # MODIFY — add `db tables` / `db schema` subcommands
│   └── db.py                             # NEW — Database class
└── tests/
    ├── conftest.py                       # MODIFY — add in_memory_db fixture
    └── test_db.py                        # NEW
```

Files we will NOT touch in this lesson: anything LLM-related (`llm.py`, `config.py`, `test_llm.py`, `test_config.py`).

---

## 4. Substep (a) — Kaggle API setup [Subhankar local action]

> **Why this isn't Tutor or Coach:** it's authentication setup on Subhankar's machine. Claude can't run it. Claude guides; Subhankar executes.

### 4.1 Steps

- [ ] **(a.1)** Sign in at https://www.kaggle.com (or sign up if needed — free).

- [ ] **(a.2)** Go to https://www.kaggle.com/settings → scroll to **API** section → click **"Create New Token"**. A file `kaggle.json` downloads to your `~/Downloads/` folder. Contents look like:
  ```json
  {"username":"yourname","key":"abcdef1234567890..."}
  ```

- [ ] **(a.3)** Move it to the standard location and lock down permissions:
  ```bash
  mkdir -p ~/.kaggle
  mv ~/Downloads/kaggle.json ~/.kaggle/kaggle.json
  chmod 600 ~/.kaggle/kaggle.json
  ```
  The `chmod 600` is required — the Kaggle CLI refuses to use the file if it's world-readable (your home directory is shared with all OS users in principle).

- [ ] **(a.4)** Add `kaggle` to `pyproject.toml` and add `polars` while we're at it. Edit `pyproject.toml` and replace the `dependencies = [...]` block with:

  ```toml
  dependencies = [
    "anthropic>=0.40.0",
    "pydantic>=2.7",
    "pydantic-settings>=2.4",
    "python-dotenv>=1.0",
    "typer>=0.12",
    "rich>=13.7",
    "duckdb>=1.0",
    "polars>=1.0",                # NEW — DataFrame library for query_df
    "kaggle>=1.6",                # NEW — Kaggle API client for data download
  ]
  ```

- [ ] **(a.5)** Reinstall the package so the new deps land:
  ```bash
  conda activate ds-agent
  pip install -e .[dev]
  ```

- [ ] **(a.6)** Verify Kaggle auth works:
  ```bash
  kaggle datasets list -s "brazilian-ecommerce" | head -3
  ```
  **Expected:** a header line and at least one row mentioning `olistbr/brazilian-ecommerce`. If you see `403 Unauthorized`, the kaggle.json wasn't found or has wrong permissions.

### 4.2 Suggested commit (after substep a)

```bash
git add pyproject.toml
git commit -m "chore(deps): add polars and kaggle for Lesson 2"
git push
```

---

## 5. Substep (b) — `scripts/download_data.py` [Tutor]

> **Why Tutor:** mechanical Kaggle-API glue. Worth seeing once and moving on.

### 5.1 What Claude writes

A standalone script (NOT part of the package) that fetches the Olist dataset zip into `data/raw/`.

The Kaggle Python API has a small surface:

```python
from kaggle.api.kaggle_api_extended import KaggleApi

api = KaggleApi()
api.authenticate()                                                    # reads ~/.kaggle/kaggle.json
api.dataset_download_files(
    "olistbr/brazilian-ecommerce",
    path="data/raw",
    unzip=True,
)
```

That's the whole thing — `unzip=True` extracts the CSVs in place and removes the zip.

The script will also:
- Create `data/raw/` if it doesn't exist.
- Print a small summary (file count, total size).
- Be idempotent — if files already exist, skip the download.

Concrete file Claude will write in this substep: `scripts/download_data.py`. Full content shown below.

```python
"""Fetches the Olist Brazilian E-commerce dataset into data/raw/.

Idempotent: if the CSVs already exist, exits without re-downloading.

Usage:
    python scripts/download_data.py
"""
from __future__ import annotations

import sys
from pathlib import Path

DATASET_SLUG = "olistbr/brazilian-ecommerce"
RAW_DIR = Path("data/raw")
EXPECTED_CSV_PREFIX = "olist_"


def already_downloaded() -> bool:
    if not RAW_DIR.exists():
        return False
    csvs = list(RAW_DIR.glob(f"{EXPECTED_CSV_PREFIX}*.csv"))
    return len(csvs) >= 8  # The dataset has 9 CSVs; tolerate 1 missing


def main() -> int:
    if already_downloaded():
        print(f"[skip] CSVs already present in {RAW_DIR}/. Delete them to force re-download.")
        return 0

    RAW_DIR.mkdir(parents=True, exist_ok=True)

    # Import here so the script gives a clear error if kaggle isn't installed.
    try:
        from kaggle.api.kaggle_api_extended import KaggleApi
    except ImportError:
        print("ERROR: 'kaggle' package not installed. Run: pip install -e .[dev]", file=sys.stderr)
        return 1

    api = KaggleApi()
    api.authenticate()

    print(f"[download] {DATASET_SLUG} → {RAW_DIR}/")
    api.dataset_download_files(DATASET_SLUG, path=str(RAW_DIR), unzip=True)

    csvs = sorted(RAW_DIR.glob("*.csv"))
    total_mb = sum(p.stat().st_size for p in csvs) / (1024 * 1024)
    print(f"[done] {len(csvs)} CSV files, {total_mb:.1f} MB total.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

### 5.2 What Subhankar does

- [ ] **(b.1)** After Claude creates the file, run it:
  ```bash
  python scripts/download_data.py
  ```
  **Expected output:** `[download] ...` then `[done] 9 CSV files, ~45 MB total.` (size approximate).

- [ ] **(b.2)** Verify:
  ```bash
  ls data/raw/
  ```
  Expected: nine files starting `olist_*` plus one `product_category_name_translation.csv`.

- [ ] **(b.3)** Confirm gitignored:
  ```bash
  git status
  ```
  No `data/raw/*.csv` should appear in untracked files. (Our `.gitignore` from Lesson 1 already covers `data/`.)

### 5.3 Suggested commit

```bash
git add scripts/download_data.py
git commit -m "feat(scripts): Kaggle-API-based Olist downloader"
git push
```

---

## 6. Substep (c) — `scripts/load_to_duckdb.py` [Tutor]

> **Why Tutor:** mechanical CSV → DuckDB ingestion. The DuckDB syntax is the only learnable bit; rest is glue.

### 6.1 Concept — DuckDB's `read_csv_auto`

DuckDB can read a CSV directly with `SELECT * FROM read_csv_auto('path.csv')`. To create a persistent table:

```python
import duckdb

conn = duckdb.connect("data/ds_agent.duckdb")
conn.execute("CREATE OR REPLACE TABLE olist_orders_dataset AS SELECT * FROM read_csv_auto('data/raw/olist_orders_dataset.csv')")
conn.close()
```

`read_csv_auto` infers types automatically. Faster and more reliable than pandas-loading + `to_sql`. **`CREATE OR REPLACE TABLE`** lets us re-run the script without clearing the DB first.

### 6.2 What Claude writes

`scripts/load_to_duckdb.py`:

```python
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
        print(f"ERROR: no CSVs found in {RAW_DIR}/. Run scripts/download_data.py first.", file=sys.stderr)
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

        # Sanity print
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
```

A few production-grade choices to call out:

- **Parameterized SQL with `?` and `[str(csv)]`** — prevents path-injection issues. Even though we control the input, parameterization is the habit.
- **`try/finally` around `conn.close()`** — connections must be closed even if an error mid-loop fires.
- **Explicit `information_schema` query** — same SQL standard as Postgres, transferable.

### 6.3 What Subhankar does

- [ ] **(c.1)** Run it:
  ```bash
  python scripts/load_to_duckdb.py
  ```
  **Expected:** 9 `[load]` lines, then a summary like:
  ```
  [done] tables in DB:
    olist_customers_dataset: 99,441 rows × 5 cols
    olist_geolocation_dataset: 1,000,163 rows × 5 cols
    olist_order_items_dataset: 112,650 rows × 7 cols
    ...
  [ok] DB at data/ds_agent.duckdb (~30 MB)
  ```

- [ ] **(c.2)** Quick sanity check via the DuckDB CLI (optional but informative):
  ```bash
  duckdb data/ds_agent.duckdb -c "SELECT COUNT(*) FROM olist_orders_dataset;"
  # 99441 (or similar)
  ```

### 6.4 Suggested commit

```bash
git add scripts/load_to_duckdb.py
git commit -m "feat(scripts): load Olist CSVs into DuckDB"
git push
```

---

## 7. Substep (d) — `db.py` + tests [Coach]

> **Why Coach:** this is the substantive code. The class shape will be referenced by Lesson 3's tools, Lesson 5's guardrails, and Lesson 6's tracing. Designing it well now pays compound interest.

### 7.1 Concept primer — context managers

A **context manager** is an object you can use with `with`. Python calls `__enter__` on entry and `__exit__` on exit (even on exceptions). The standard pattern for resource management:

```python
with Database("...") as db:
    rows = db.query("SELECT 1")
# connection auto-closed here
```

Implementing it requires two dunder (double-underscore) methods on the class:

```python
def __enter__(self):
    return self

def __exit__(self, exc_type, exc_val, exc_tb):
    self.close()
    return False           # don't suppress exceptions
```

This is production-grade — file handles, network connections, and DB connections should all support it.

### 7.2 The spec — `src/ds_agent/db.py`

```python
class Database:
    def __init__(self, path: str | Path, read_only: bool = False) -> None: ...

    def query(self, sql: str, params: list | None = None) -> list[dict]:
        """Execute SQL, return rows as a list of dicts (column → value)."""

    def query_df(self, sql: str, params: list | None = None) -> pl.DataFrame:
        """Execute SQL, return rows as a polars DataFrame (zero-copy from DuckDB)."""

    def list_tables(self) -> list[str]:
        """Return names of user tables in the 'main' schema."""

    def describe_table(self, name: str) -> list[dict]:
        """Return column metadata: list of {'name': str, 'type': str, 'nullable': bool}.
        Raises ValueError if the table doesn't exist."""

    def close(self) -> None: ...

    def __enter__(self): ...
    def __exit__(self, exc_type, exc_val, exc_tb): ...
```

**Behavior requirements:**

1. `__init__` connects: `self._conn = duckdb.connect(str(path), read_only=read_only)`. Convert `Path` to `str` (DuckDB's API takes a string).
2. `query(sql, params=None)` runs `self._conn.execute(sql, params or [])` and returns `list[dict]`. Convert via `[dict(zip(col_names, row)) for row in rows]` or via DuckDB's polars/pandas conversion.
3. `query_df(sql, params=None)` returns a polars DataFrame. DuckDB's connection has a `.execute(sql).pl()` method that returns a polars DataFrame zero-copy.
4. `list_tables()` queries `information_schema.tables` filtered by `table_schema = 'main'`. Returns list of strings, sorted alphabetically.
5. `describe_table(name)` queries `information_schema.columns` for the given table. If no rows, raise `ValueError(f"unknown table: {name}")`. Returns list of dicts with keys `name`, `type`, `nullable` (a bool — `is_nullable` in info_schema is a string `'YES'`/`'NO'`, you convert).
6. `close()` calls `self._conn.close()`. Idempotent — calling twice is fine. Set `self._conn = None` after close so a second `query` raises a clear error.
7. Context manager protocol — `__enter__` returns `self`, `__exit__` calls `self.close()` and returns `False` (don't swallow exceptions).

### 7.3 The 6 tests for `tests/test_db.py`

Write all six. Each pins a specific behavior.

#### Test 1 — `test_query_returns_list_of_dicts`

Build an in-memory DuckDB (path `:memory:`), `CREATE TABLE` and `INSERT` two rows, call `query("SELECT ...")`, assert the result is a list of two dicts with the expected keys and values.

#### Test 2 — `test_query_with_no_rows_returns_empty_list`

Same setup, query something that returns no rows, assert `result == []`.

#### Test 3 — `test_query_df_returns_polars_dataframe`

After loading data, `result = db.query_df("SELECT ...")`. Assert `isinstance(result, pl.DataFrame)` and `result.shape[0] == <expected_row_count>`.

#### Test 4 — `test_list_tables_returns_user_tables_sorted`

`CREATE TABLE` two tables (e.g., `zebra` and `aardvark`), assert `list_tables() == ["aardvark", "zebra"]` — sorted, and DOES NOT include DuckDB's internal tables.

#### Test 5 — `test_describe_table_returns_column_info`

`CREATE TABLE foo(id INTEGER, name VARCHAR NOT NULL)`. Assert `describe_table("foo")` returns:
```python
[
    {"name": "id", "type": "INTEGER", "nullable": True},
    {"name": "name", "type": "VARCHAR", "nullable": False},
]
```
(DuckDB's `information_schema.columns` reports types as e.g. `INTEGER`, `VARCHAR`. The `nullable` field comes from `is_nullable` which is `'YES'`/`'NO'` — convert to bool.)

#### Test 6 — `test_describe_table_raises_on_unknown_table`

```python
with pytest.raises(ValueError):
    db.describe_table("does_not_exist")
```

### 7.4 Hints for the implementation

- Imports you'll need:
  ```python
  from __future__ import annotations
  from pathlib import Path
  import duckdb
  import polars as pl
  ```
- Inside `query()`, after `self._conn.execute(sql, params or []):`, you can get the column names from `cursor.description` (a list of column-info tuples; element 0 of each is the name). Then `rows = cursor.fetchall()`. Then zip + dict.
- Or — easier — DuckDB's connection object has `.execute(sql, params).pl()` that returns a polars DataFrame, and polars has `df.to_dicts() -> list[dict]`. So:
  ```python
  return self._conn.execute(sql, params or []).pl().to_dicts()
  ```
  One line, type-correct, fast (Arrow zero-copy).
- Same for `query_df`:
  ```python
  return self._conn.execute(sql, params or []).pl()
  ```
- For `list_tables`:
  ```python
  rows = self._conn.execute(
      "SELECT table_name FROM information_schema.tables "
      "WHERE table_schema = 'main' ORDER BY table_name"
  ).fetchall()
  return [r[0] for r in rows]
  ```
- For `describe_table`, parameterize the table name (`?`):
  ```python
  rows = self._conn.execute(
      "SELECT column_name, data_type, is_nullable "
      "FROM information_schema.columns "
      "WHERE table_schema = 'main' AND table_name = ? "
      "ORDER BY ordinal_position",
      [name],
  ).fetchall()
  if not rows:
      raise ValueError(f"unknown table: {name}")
  return [
      {"name": r[0], "type": r[1], "nullable": r[2] == "YES"}
      for r in rows
  ]
  ```
- For `close()`:
  ```python
  if self._conn is not None:
      self._conn.close()
      self._conn = None
  ```

### 7.5 Add a fixture to `conftest.py`

In `tests/conftest.py`, add a fixture that yields a fresh in-memory `Database` per test (so tests don't pollute each other):

```python
@pytest.fixture
def in_memory_db():
    """A Database backed by an in-memory DuckDB. Auto-closed after the test."""
    from ds_agent.db import Database
    db = Database(":memory:")
    try:
        yield db
    finally:
        db.close()
```

`yield` (not `return`) makes this a fixture with **teardown** — code after `yield` runs at the end of the test, even on failure.

### 7.6 Order

1. Add `in_memory_db` fixture to `tests/conftest.py`.
2. Write `tests/test_db.py` with all 6 tests (the test for `query_df` will need to set up data first — keep it simple: insert one row).
3. Run `pytest tests/test_db.py -v` — expect 6 failures with `ModuleNotFoundError`.
4. Write `src/ds_agent/db.py`.
5. Run `pytest -v` — expect **13 passed** (7 from Lesson 1 + 6 new).

Share both files (or just say "done") and Claude will review before you run.

### 7.7 Suggested commit

```bash
git add src/ds_agent/db.py tests/conftest.py tests/test_db.py
git status
git commit -m "feat(db): Database class with query/list_tables/describe_table + tests"
git push
```

---

## 8. Substep (e) — CLI `db` subcommand group [Tutor]

> **Why Tutor:** Typer sub-app pattern + Rich table rendering. One demo of each.

### 8.1 Concept — Typer sub-apps

To get `ds-agent db tables` (a two-word command), we add a sub-app:

```python
db_app = typer.Typer(name="db", help="Inspect the local DuckDB.")
app.add_typer(db_app, name="db")

@db_app.command("tables")
def db_tables() -> None: ...

@db_app.command("schema")
def db_schema(table: str) -> None: ...
```

Now `ds-agent --help` shows `db` as a command group; `ds-agent db --help` shows `tables` and `schema` underneath.

### 8.2 What Claude adds to `cli.py`

Adds at the bottom of the existing file (no changes to what's already there):

```python
from rich.table import Table

from .db import Database

db_app = typer.Typer(name="db", help="Inspect the local DuckDB.")
app.add_typer(db_app, name="db")


def _open_db() -> Database:
    settings = get_settings()
    return Database(settings.duckdb_path, read_only=True)


@db_app.command("tables")
def db_tables() -> None:
    """List user tables in the local DuckDB."""
    with _open_db() as db:
        tables = db.list_tables()

    table = Table(title="Tables")
    table.add_column("name", style="cyan")
    for name in tables:
        table.add_row(name)
    console.print(table)


@db_app.command("schema")
def db_schema(
    table: str = typer.Argument(..., help="Table name."),
) -> None:
    """Show column info for one table."""
    try:
        with _open_db() as db:
            cols = db.describe_table(table)
    except ValueError as e:
        console.print(f"[red]{e}[/red]")
        raise typer.Exit(code=1)

    rendered = Table(title=f"Schema: {table}")
    rendered.add_column("column", style="cyan")
    rendered.add_column("type", style="magenta")
    rendered.add_column("nullable", style="green")
    for col in cols:
        rendered.add_row(col["name"], col["type"], "yes" if col["nullable"] else "no")
    console.print(rendered)
```

A few notes:

- We open the DB **read-only** in the CLI — defense in depth, even though the CLI doesn't write.
- `with _open_db() as db:` — the context manager closes the connection automatically.
- Rich's `Table` renders nicely styled tables in the terminal.
- `typer.Exit(code=1)` on missing table — Unix convention.

### 8.3 What Subhankar runs

- [ ] **(e.1)** Verify the demo:
  ```bash
  ds-agent --help                           # shows ask + db
  ds-agent db --help                        # shows tables + schema
  ds-agent db tables                        # styled table of 9 names
  ds-agent db schema olist_orders_dataset   # styled table of columns
  ds-agent db schema does_not_exist         # red error, exit code 1
  ```
- [ ] **(e.2)** Verify exit code on the error case:
  ```bash
  ds-agent db schema does_not_exist; echo "exit=$?"
  # exit=1
  ```

### 8.4 Suggested commit

```bash
git add src/ds_agent/cli.py
git commit -m "feat(cli): db tables / db schema subcommands"
git push
```

---

## 9. Final verification

```bash
conda activate ds-agent
pytest -v                                                    # 13 passed
ds-agent ask "say hi in pirate"                              # Lesson 1 still works
ds-agent db tables                                           # Lesson 2 works
ds-agent db schema olist_order_reviews_dataset               # Lesson 2 works
python -c "from ds_agent.db import Database; db = Database('data/ds_agent.duckdb', read_only=True); print(db.query('SELECT COUNT(*) AS n FROM olist_orders_dataset'))"
# [{'n': 99441}]
```

---

## 10. Reflection prompts

Think on these. Answer in chat if any are fuzzy.

1. **Why a wrapper around DuckDB?** We could call `duckdb.connect(...).execute(...)` directly throughout the codebase. Same question as Lesson 1 about `LLMClient`. What does `Database` give us that direct duckdb calls don't?
2. **`list[dict]` vs `polars.DataFrame`** — why did we choose `list[dict]` as the *primary* return for `query()`, with polars as a separate method? (Hint: think about what the Lesson 3 tool will return to the LLM as a tool result.)
3. **The 9-table Olist dataset** — open `ds-agent db schema olist_order_reviews_dataset` and look at the columns. There's a `review_comment_message` column. What's interesting about its data type compared to `review_score`? This matters for Iteration B (RAG over reviews).
4. **Read-only mode** — we exposed a `read_only` parameter but defaulted to `False`. The CLI uses `read_only=True` by passing it explicitly. Should the default be flipped to `True`? What's the tradeoff?

---

## 11. Connects to Lesson 3

Lesson 3 (Tool use: `run_sql`) connects today's `Database` to Lesson 1's `LLMClient`:

- The agent is given a **tool schema** for `run_sql(sql: str)`.
- When Claude emits a tool call like `run_sql("SELECT ...")`, our code runs `db.query(sql)` and feeds the rows back to Claude as a tool result.
- The same agent loop also has access to a `get_relevant_schema(...)` tool that wraps `db.list_tables()` and `db.describe_table(...)` — Claude uses it to figure out what tables exist before writing SQL.

Today's `Database` interface (`query`, `list_tables`, `describe_table`) is exactly the surface those two tools wrap. **No changes to `db.py` needed in Lesson 3** — that's the test of a well-designed interface.

---

## 12. Mode summary

| Substep | Mode | Why | Estimated time |
|---|---|---|---|
| (a) Kaggle API setup | Subhankar local action | Auth setup; not codeable | 10 min |
| (b) `download_data.py` | Tutor | Mechanical Kaggle glue | 10 min |
| (c) `load_to_duckdb.py` | Tutor | Mechanical CSV→DuckDB glue | 15 min |
| (d) `db.py` + tests | **Coach** | Substantive code; future tools depend on this interface | 60-90 min |
| (e) CLI `db` subcommands | Tutor | Typer sub-app pattern + Rich table demo | 15 min |

Total: ~2-2.5 hours.

---

## 13. Status update

When Lesson 2 is merged to main, append to the spec's Status Log:

```
- 2026-MM-DD EOD — Lesson 2 complete and merged to main. Next: write Lesson 3 plan (tool use — run_sql + get_relevant_schema).
```
