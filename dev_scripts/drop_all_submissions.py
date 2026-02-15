#!/usr/bin/env python3
"""
Delete all submission-related rows from the database.

Order: validation_runs → submission_squares → submissions
(Child tables first because of foreign keys.)

Usage:
  python scripts/drop_all_submissions.py           # dry run (counts only)
  python scripts/drop_all_submissions.py --yes   # actually delete

Requires DATABASE_URL (e.g. from .env).
"""
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)
os.chdir(ROOT)

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

from db.connection import get_cursor


def main():
    do_it = "--yes" in sys.argv or "-y" in sys.argv
    with get_cursor() as (conn, cur):
        for name, sql in [
            ("validation_runs", "SELECT COUNT(*) FROM validation_runs"),
            ("submission_squares", "SELECT COUNT(*) FROM submission_squares"),
            ("submissions", "SELECT COUNT(*) FROM submissions"),
        ]:
            cur.execute(sql)
            n = cur.fetchone()["count"]
            print("%s: %d rows" % (name, n))
        if not do_it:
            print("\nRun with --yes to delete all of the above.")
            return
        print("\nDeleting...")
        cur.execute("DELETE FROM validation_runs")
        cur.execute("DELETE FROM submission_squares")
        cur.execute("DELETE FROM submissions")
        print("Done. All submission-related rows removed.")


if __name__ == "__main__":
    main()
