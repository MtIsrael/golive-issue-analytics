"""
Run every query in ./queries against golive.db.
Prints a preview of each and saves the full result to ./results/<report>.csv

Usage:
    python run_queries.py            # all queries
    python run_queries.py 03         # just query 03
"""
import csv
import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).parent
PREVIEW_ROWS = 8


def print_table(headers, rows):
    widths = [max(len(str(h)), *(len(str(r[i])) for r in rows)) if rows else len(str(h))
              for i, h in enumerate(headers)]
    line = "  ".join(str(h).ljust(w) for h, w in zip(headers, widths))
    print(line)
    print("-" * len(line))
    for r in rows:
        print("  ".join(str(v).ljust(w) for v, w in zip(r, widths)))


def main():
    db = ROOT / "golive.db"
    if not db.exists():
        sys.exit("golive.db not found. Run: python build_database.py")
    con = sqlite3.connect(db)
    (ROOT / "results").mkdir(exist_ok=True)
    only = sys.argv[1] if len(sys.argv) > 1 else ""

    for path in sorted((ROOT / "queries").glob("*.sql")):
        if only and not path.name.startswith(only):
            continue
        cur = con.execute(path.read_text(encoding="utf-8"))
        headers = [d[0] for d in cur.description]
        rows = cur.fetchall()
        with open(ROOT / "results" / f"{path.stem}.csv", "w", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            w.writerow(headers)
            w.writerows(rows)
        title = path.read_text(encoding="utf-8").splitlines()[0].lstrip("- ")
        print(f"\n=== {title}  ({len(rows)} rows) ===")
        print_table(headers, rows[:PREVIEW_ROWS])
        if len(rows) > PREVIEW_ROWS:
            print(f"... full results in results/{path.stem}.csv")
    con.close()


if __name__ == "__main__":
    main()
