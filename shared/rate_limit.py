import os
from shared.db import get_cursor

RATE_LIMIT_WINDOW_SECONDS = int(os.environ.get("RATE_LIMIT_WINDOW", 3600))
RATE_LIMIT_MAX = int(os.environ.get("RATE_LIMIT_MAX", 60))


# Returns (allowed, info_dict)
def check_rate_limit(user_id):
    if user_id is None:
        return True, {
            "remaining": RATE_LIMIT_MAX,
            "limit": RATE_LIMIT_MAX,
            "window_seconds": RATE_LIMIT_WINDOW_SECONDS,
        }

    with get_cursor(commit=False) as (conn, cur):
        cur.execute(
            """
            SELECT COUNT(*) AS cnt,
                   MIN(created_at) AS oldest
            FROM submissions
            WHERE user_id = %s
              AND created_at > NOW() - INTERVAL '%s seconds'
            """,
            (user_id, RATE_LIMIT_WINDOW_SECONDS),
        )
        row = cur.fetchone()
        count = row["cnt"]
        remaining = max(0, RATE_LIMIT_MAX - count)

        info = {
            "remaining": remaining,
            "limit": RATE_LIMIT_MAX,
            "window_seconds": RATE_LIMIT_WINDOW_SECONDS,
            "used": count,
        }

        if count >= RATE_LIMIT_MAX:
            if row["oldest"]:
                cur.execute(
                    "SELECT EXTRACT(EPOCH FROM (%s + INTERVAL '%s seconds' - NOW())) AS retry",
                    (row["oldest"], RATE_LIMIT_WINDOW_SECONDS),
                )
                retry_row = cur.fetchone()
                info["retry_after"] = max(1, int(retry_row["retry"]))
            else:
                info["retry_after"] = RATE_LIMIT_WINDOW_SECONDS
            return False, info

        return True, info
