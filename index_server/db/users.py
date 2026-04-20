import os
from datetime import datetime

import requests

from shared.db import get_cursor


def _coerce_user_created_at(user):
    """Auth API JSON uses ISO strings; templates expect datetime for strftime."""
    if not user:
        return user
    ca = user.get("created_at")
    if ca is None or hasattr(ca, "strftime"):
        return user
    if isinstance(ca, str):
        s = ca.strip()
        if not s:
            return {**user, "created_at": None}
        try:
            if s.endswith("Z"):
                s = s[:-1] + "+00:00"
            return {**user, "created_at": datetime.fromisoformat(s)}
        except ValueError:
            return user
    return user

AUTH_SERVER_URL = os.environ.get("AUTH_SERVER_URL", "").rstrip("/")


def _auth_post(path, payload):
    try:
        r = requests.post(f"{AUTH_SERVER_URL}{path}", json=payload, timeout=5)
        return r.json(), r.status_code
    except (requests.RequestException, ValueError):
        return {"error": "Auth server unreachable."}, 503


def _auth_get(path, token):
    try:
        r = requests.get(
            f"{AUTH_SERVER_URL}{path}",
            headers={"Authorization": f"Bearer {token}"},
            timeout=5,
        )
        return r.json(), r.status_code
    except (requests.RequestException, ValueError):
        return {"error": "Auth server unreachable."}, 503


def _auth_put(path, token, payload):
    try:
        r = requests.put(
            f"{AUTH_SERVER_URL}{path}",
            json=payload,
            headers={"Authorization": f"Bearer {token}"},
            timeout=5,
        )
        return r.json(), r.status_code
    except (requests.RequestException, ValueError):
        return {"error": "Auth server unreachable."}, 503


def login_user(identifier, password):
    if not AUTH_SERVER_URL:
        return _login_user_direct(identifier, password)

    data, status = _auth_post("/auth/login", {
        "username": identifier,
        "password": password,
    })
    if status == 200 and "token" in data:
        return data["token"], data["user"]
    return None, data.get("error", "Login failed.")


def register_user(username, email, password):
    if not AUTH_SERVER_URL:
        return _register_user_direct(username, email, password)

    data, status = _auth_post("/auth/register", {
        "username": username,
        "email": email,
        "password": password,
    })
    if status == 200 and "token" in data:
        return data["token"], data["user"]
    return None, data.get("error", "Registration failed.")


def get_user_by_id(user_id, token=None):
    if AUTH_SERVER_URL and token:
        data, status = _auth_get(f"/auth/user/{user_id}", token)
        if status == 200 and "user" in data:
            return _coerce_user_created_at(data["user"])

    return _get_user_by_id_direct(user_id)


def update_user_email(user_id, new_email, token=None):
    if not AUTH_SERVER_URL or not token:
        return _update_user_email_direct(user_id, new_email)

    data, status = _auth_put(f"/auth/user/{user_id}/email", token, {"email": new_email})
    if status == 200 and data.get("success"):
        return True, None
    return False, data.get("error", "Failed to update email.")


def update_user_password(user_id, current_password, new_password, token=None):
    if not AUTH_SERVER_URL or not token:
        return _update_user_password_direct(user_id, current_password, new_password)

    data, status = _auth_put(f"/auth/user/{user_id}/password", token, {
        "current_password": current_password,
        "new_password": new_password,
    })
    if status == 200 and data.get("success"):
        return True, None
    return False, data.get("error", "Failed to update password.")


def get_user_submissions(user_id, page=1, per_page=50):
    offset = (page - 1) * per_page
    with get_cursor() as (conn, cur):
        cur.execute(
            "SELECT COUNT(*) AS cnt FROM submissions WHERE user_id = %s",
            (user_id,),
        )
        total = cur.fetchone()["cnt"]
        cur.execute(
            """
            SELECT s.id, s.status, s.objective_value, s.min_slack, s.created_at,
                   pi.domain,
                   COUNT(ss.idx) as square_count
            FROM submissions s
            JOIN problem_instances pi ON s.instance_id = pi.id
            LEFT JOIN submission_squares ss ON s.id = ss.submission_id
            WHERE s.user_id = %s
            GROUP BY s.id, s.status, s.objective_value, s.min_slack, s.created_at,
                     pi.domain
            ORDER BY s.created_at DESC
            LIMIT %s OFFSET %s
            """,
            (user_id, per_page, offset),
        )
        return cur.fetchall(), total


def _get_auth_cursor():
    from auth_server.db.connection import get_auth_cursor
    return get_auth_cursor()


def _login_user_direct(identifier, password):
    from werkzeug.security import check_password_hash
    from shared.auth import generate_token

    identifier = (identifier or "").strip().lower()
    if not identifier:
        return None, "Username is required."
    with _get_auth_cursor() as (conn, cur):
        cur.execute(
            """
            SELECT id, username, email, display_name, password_hash
            FROM users WHERE LOWER(username) = %s OR LOWER(email) = %s
            LIMIT 1
            """,
            (identifier, identifier),
        )
        user = cur.fetchone()
    if not user or not user.get("password_hash"):
        return None, "Invalid username or password."
    if not check_password_hash(user["password_hash"], password):
        return None, "Invalid username or password."
    token = generate_token(user["id"], user["username"])
    return token, {"id": user["id"], "username": user["username"], "email": user.get("email")}


def _register_user_direct(username, email, password):
    import psycopg2
    from werkzeug.security import generate_password_hash
    from shared.auth import generate_token

    username = (username or "").strip().lower()
    email = (email or "").strip().lower()
    if not username or not email:
        return None, "Username and email are required."
    if not password or len(password) < 8:
        return None, "Password must be at least 8 characters."
    password_hash = generate_password_hash(password, method="pbkdf2:sha256")
    try:
        with _get_auth_cursor() as (conn, cur):
            cur.execute(
                """
                INSERT INTO users (username, email, display_name, password_hash)
                VALUES (%s, %s, %s, %s) RETURNING id
                """,
                (username, email, username, password_hash),
            )
            row = cur.fetchone()
            if not row:
                return None, "Failed to create account."
            token = generate_token(row["id"], username)
            return token, {"id": row["id"], "username": username, "email": email}
    except psycopg2.IntegrityError:
        return None, "Username or email is already in use."


def _get_user_by_id_direct(user_id):
    with _get_auth_cursor() as (conn, cur):
        cur.execute(
            "SELECT id, username, email, display_name, created_at FROM users WHERE id = %s LIMIT 1",
            (user_id,),
        )
        return cur.fetchone()


def _update_user_email_direct(user_id, new_email):
    import psycopg2
    new_email = (new_email or "").strip().lower()
    if not new_email:
        return False, "Email is required."
    try:
        with _get_auth_cursor() as (conn, cur):
            cur.execute("UPDATE users SET email = %s WHERE id = %s RETURNING id", (new_email, user_id))
            return (True, None) if cur.fetchone() else (False, "User not found.")
    except psycopg2.IntegrityError:
        return False, "Email is already in use."


def _update_user_password_direct(user_id, current_password, new_password):
    import psycopg2
    from werkzeug.security import generate_password_hash, check_password_hash
    if not new_password or len(new_password) < 8:
        return False, "Password must be at least 8 characters."
    with _get_auth_cursor() as (conn, cur):
        cur.execute("SELECT password_hash FROM users WHERE id = %s LIMIT 1", (user_id,))
        user = cur.fetchone()
        if not user or not user.get("password_hash"):
            return False, "User not found."
        if not check_password_hash(user["password_hash"], current_password):
            return False, "Current password is incorrect."
        ph = generate_password_hash(new_password, method="pbkdf2:sha256")
        try:
            cur.execute("UPDATE users SET password_hash = %s WHERE id = %s RETURNING id", (ph, user_id))
            return (True, None) if cur.fetchone() else (False, "Failed to update password.")
        except psycopg2.Error as e:
            return False, str(e)
