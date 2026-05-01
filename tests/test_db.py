import pytest

def test_query_returns_list_of_dicts(in_memory_db):
    """Build an in-memory DuckDB (path :memory:), CREATE TABLE and INSERT two rows, call query("SELECT ..."), assert the result is a list of two dicts with the expected keys and values."""
    create_table_sql = """
    CREATE TABLE users (
        id INTEGER,
        name TEXT
    );
    """
    in_memory_db.execute(create_table_sql)

    insert_sql = """
    INSERT INTO users (id, name) VALUES
        (1, 'Alice'),
        (2, 'Bob');
    """
    in_memory_db.execute(insert_sql)

    results = in_memory_db.query("SELECT * FROM users;")
    assert isinstance(results, list)
    assert len(results) == 2
    assert results[0] == {"id": 1, "name": "Alice"}
    assert results[1] == {"id": 2, "name": "Bob"}

def test_query_with_no_rows_returns_empty_list(in_memory_db):
    """Tests that query() returns an empty list when no rows match the query."""
    create_table_sql = """
    CREATE TABLE users (
        id INTEGER,
        name TEXT
    );
    """
    in_memory_db.execute(create_table_sql)

    results = in_memory_db.query("SELECT * FROM users;")
    assert isinstance(results, list)
    assert len(results) == 0

def test_query_df_returns_polars_dataframe(in_memory_db):
    """After loading data, result = db.query_df("SELECT ..."). Assert isinstance(result, pl.DataFrame) and result.shape[0] == <expected_row_count>."""
    import polars as pl

    create_table_sql = """
    CREATE TABLE users (
        id INTEGER,
        name TEXT
    );
    """
    in_memory_db.execute(create_table_sql)

    insert_sql = """
    INSERT INTO users (id, name) VALUES
        (1, 'Alice'),
        (2, 'Bob');
    """
    in_memory_db.execute(insert_sql)

    df = in_memory_db.query_df("SELECT * FROM users;")
    assert isinstance(df, pl.DataFrame)
    assert df.shape[0] == 2

def test_list_tables_returns_user_tables_sorted(in_memory_db):
    """CREATE TABLE two tables (e.g., zebra and aardvark), assert list_tables() == ["aardvark", "zebra"] — sorted, and DOES NOT include DuckDB's internal tables."""
    create_zebra_sql = """
    CREATE TABLE zebra (
        id INTEGER
    );
    """
    in_memory_db.execute(create_zebra_sql)

    create_aardvark_sql = """
    CREATE TABLE aardvark (
        id INTEGER
    );
    """
    in_memory_db.execute(create_aardvark_sql)

    tables = in_memory_db.list_tables()
    assert tables == ["aardvark", "zebra"]

def test_describe_table_returns_column_info(in_memory_db):
    """CREATE TABLE foo (id INTEGER, name VARCHAR NOT NULL), call describe_table("foo"), assert the result is a list of dicts with correct column name, type, and nullability info."""
    create_table_sql = """
    CREATE TABLE foo (
        id INTEGER,
        name VARCHAR NOT NULL
    );
    """
    in_memory_db.execute(create_table_sql)

    description = in_memory_db.describe_table("foo")
    expected_description = [
        {"name": "id", "type": "INTEGER", "nullable": True},
        {"name": "name", "type": "VARCHAR", "nullable": False},
    ]
    assert description == expected_description

def test_describe_table_raises_on_unknown_table(in_memory_db):
    """Calling describe_table() on a table that doesn't exist should raise an exception."""
    with pytest.raises(ValueError):
        in_memory_db.describe_table("does_not_exist")
