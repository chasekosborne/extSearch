import os
import requests

AUTH_SERVER_URL = os.environ.get("AUTH_SERVER_URL", "").rstrip("/")


# Returns {user_id: username} for resolved IDs
def resolve_usernames(user_ids):
    user_ids = [uid for uid in user_ids if uid is not None]
    if not user_ids:
        return {}

    if AUTH_SERVER_URL:
        return _resolve_via_auth_server(user_ids)
    return _resolve_direct(user_ids)


def _resolve_via_auth_server(user_ids):
    try:
        r = requests.post(
            f"{AUTH_SERVER_URL}/auth/users/batch",
            json={"user_ids": user_ids},
            timeout=5,
        )
        if r.status_code == 200:
            data = r.json().get("users", {})
            return {
                int(uid): info.get("username") or info.get("display_name")
                for uid, info in data.items()
            }
    except (requests.RequestException, ValueError, KeyError):
        pass
    return {}


def _resolve_direct(user_ids):
    from auth_server.db.connection import get_auth_cursor
    with get_auth_cursor(commit=False) as (conn, cur):
        cur.execute(
            "SELECT id, username, display_name FROM users WHERE id = ANY(%s)",
            (user_ids,),
        )
        return {
            row["id"]: row["username"] or row.get("display_name")
            for row in cur.fetchall()
        }


# Adds 'username' key to each submission dict in place
def enrich_submissions_with_usernames(submissions):
    user_ids = list({s.get("user_id") for s in submissions if s.get("user_id")})
    name_map = resolve_usernames(user_ids)
    for sub in submissions:
        uid = sub.get("user_id")
        sub["username"] = name_map.get(uid, "Anonymous") if uid else "Anonymous"
