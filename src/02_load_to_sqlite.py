"""
LedgerGuard: Load the CSVs into a SQLite database
=================================================

Creates  data/ledgerguard.db  with two tables (shipments, contract_terms)
and the v_exceptions view from sql/02_exceptions.sql.
The answer key is deliberately not loaded, so the analysis cannot use it.

Run:  python src/02_load_to_sqlite.py
"""

import sqlite3
from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
RAW_DIR = PROJECT_ROOT / "data" / "raw"
DB_PATH = PROJECT_ROOT / "data" / "ledgerguard.db"
SCHEMA = PROJECT_ROOT / "sql" / "00_schema.sql"
VIEWS = [PROJECT_ROOT / "sql" / "02_exceptions.sql"]   # analysis views built on top of the tables


def main():
    shipments = pd.read_csv(RAW_DIR / "shipments.csv")
    terms = pd.read_csv(RAW_DIR / "contract_terms.csv")

    # SQL convention: lowercase column names
    shipments.columns = shipments.columns.str.lower()
    terms.columns = terms.columns.str.lower()

    with sqlite3.connect(DB_PATH) as conn:
        conn.execute("PRAGMA foreign_keys = ON")
        conn.executescript(SCHEMA.read_text())      # build empty tables from the schema

        # if_exists="append" fills the tables we just created rather than replacing them
        terms.to_sql("contract_terms", conn, if_exists="append", index=False)
        shipments.to_sql("shipments", conn, if_exists="append", index=False)

        # Build the analysis views so a rebuild always includes them
        for view_file in VIEWS:
            if view_file.exists():
                conn.executescript(view_file.read_text())

        # Quick checks: row counts and that every shipment matches a contract
        n_ship = conn.execute("SELECT COUNT(*) FROM shipments").fetchone()[0]
        n_terms = conn.execute("SELECT COUNT(*) FROM contract_terms").fetchone()[0]
        orphans = conn.execute("""
            SELECT COUNT(*) FROM shipments s
            LEFT JOIN contract_terms c USING (retailer, product)
            WHERE c.retailer IS NULL
        """).fetchone()[0]

    print(f"Loaded {n_ship} shipments and {n_terms} contract terms into {DB_PATH.name}")
    print(f"Shipments with no matching contract: {orphans}")


if __name__ == "__main__":
    main()
