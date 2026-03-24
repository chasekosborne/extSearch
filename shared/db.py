import os
import psycopg2
from psycopg2.extras import RealDictCursor
from contextlib import contextmanager


def get_connection():
    return psycopg2.connect(
        os.environ.get("DATABASE_URL", "postgresql://localhost/extsearch_dev"),
        cursor_factory=RealDictCursor,
    )


@contextmanager
def get_cursor(commit=True):
    conn = get_connection()
    cur = conn.cursor()
    try:
        yield conn, cur
        if commit:
            conn.commit()
    finally:
        cur.close()
        conn.close()
