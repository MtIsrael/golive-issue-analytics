"""
Build golive.db (SQLite) from the CSVs in ./data using sql/schema.sql.

Usage:
    python build_database.py
"""
import csv
import sqlite3
from pathlib import Path

ROOT = Path(__file__).parent
DB_PATH = ROOT / "golive.db"
LOAD_ORDER = ["departments", "workstations", "tdr_results", "sla_targets", "tickets"]


def main():
    if DB_PATH.exists():
        DB_PATH.unlink()
    con = sqlite3.connect(DB_PATH)
    con.executescript((ROOT / "sql" / "schema.sql").read_text(encoding="utf-8"))

    for table in LOAD_ORDER:
        with open(ROOT / "data" / f"{table}.csv", newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            cols = reader.fieldnames
            rows = [[r[c] if r[c] != "" else None for c in cols] for r in reader]
        placeholders = ", ".join("?" for _ in cols)
        con.executemany(f"INSERT INTO {table} ({', '.join(cols)}) VALUES ({placeholders})", rows)
        print(f"loaded {table:12s} {len(rows):>7,} rows")

    con.commit()
    bad = con.execute("PRAGMA foreign_key_check").fetchall()
    print("foreign key check:", "OK" if not bad else f"{len(bad)} problems")
    con.close()
    print(f"\nDatabase ready: {DB_PATH.name}")


if __name__ == "__main__":
    main()
