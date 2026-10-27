"""
Interactive SQL console for the project database. No installs needed.

Usage:
    python query.py                          # type SQL at the prompt
    python query.py reports/03_readmissions_30_day.sql   # run a .sql file
    python query.py "SELECT COUNT(*) FROM patients"      # run one query

At the prompt:
    End a query with ;  (it can span multiple lines)
    .tables          list tables
    .schema TABLE    show a table's columns
    .save FILE.csv   save the last result to a CSV
    .quit            exit
"""
import csv
import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).parent
DB = next((p for p in ROOT.glob("*.db")), None)
MAX_ROWS = 40


def show(cur):
    if cur.description is None:
        print(f"OK ({cur.rowcount} rows affected)")
        return None
    headers = [d[0] for d in cur.description]
    rows = cur.fetchall()
    shown = rows[:MAX_ROWS]
    widths = [min(40, max([len(h)] + [len(str(r[i])) for r in shown])) for i, h in enumerate(headers)]
    line = "  ".join(h[:w].ljust(w) for h, w in zip(headers, widths))
    print(line)
    print("-" * len(line))
    for r in shown:
        print("  ".join(str(v)[:w].ljust(w) for v, w in zip(r, widths)))
    extra = f", showing first {MAX_ROWS}" if len(rows) > MAX_ROWS else ""
    print(f"({len(rows)} rows{extra})")
    return headers, rows


def run(con, sql):
    try:
        return show(con.execute(sql))
    except sqlite3.Error as e:
        print(f"SQL error: {e}")
        return None


def main():
    if DB is None:
        sys.exit("No database found. Run: python build_database.py")
    con = sqlite3.connect(DB)

    if len(sys.argv) > 1:
        arg = sys.argv[1]
        sql = Path(arg).read_text(encoding="utf-8") if arg.endswith(".sql") else arg
        run(con, sql)
        return

    print(f"Connected to {DB.name}. Type SQL ending with ; or .tables / .schema TABLE / .save FILE.csv / .quit")
    last, buf = None, []
    while True:
        try:
            line = input("sql> " if not buf else "...> ")
        except (EOFError, KeyboardInterrupt):
            print()
            break
        cmd = line.strip()
        if not buf and cmd.startswith("."):
            parts = cmd.split()
            if parts[0] in (".quit", ".exit"):
                break
            elif parts[0] == ".tables":
                run(con, "SELECT name FROM sqlite_master WHERE type = 'table' ORDER BY name")
            elif parts[0] == ".schema" and len(parts) > 1:
                run(con, f"SELECT name AS column, type, \"notnull\" AS required, pk AS primary_key FROM pragma_table_info('{parts[1]}')")
            elif parts[0] == ".save" and len(parts) > 1:
                if last:
                    with open(parts[1], "w", newline="", encoding="utf-8") as f:
                        w = csv.writer(f)
                        w.writerow(last[0])
                        w.writerows(last[1])
                    print(f"Saved {len(last[1])} rows to {parts[1]}")
                else:
                    print("Nothing to save yet.")
            else:
                print("Commands: .tables  .schema TABLE  .save FILE.csv  .quit")
            continue
        buf.append(line)
        if cmd.endswith(";"):
            result = run(con, "\n".join(buf))
            if result:
                last = result
            buf = []
    con.close()


if __name__ == "__main__":
    main()
