import psycopg2
from werkzeug.security import generate_password_hash, check_password_hash

from auth_server.db.connection import get_auth_cursor


def create_user(username, email, password):
    username = (username or "").strip().lower()
    email = (email or "").strip().lower()
    if not username or not email:
        return None, "Username and email are required."
    if not password or len(password) < 8:
        return None, "Password must be at least 8 characters."

    password_hash = generate_password_hash(password, method="pbkdf2:sha256")

    try:
        with get_auth_cursor() as (conn, cur):
            cur.execute(
                """
                INSERT INTO users (username, email, display_name, password_hash)
                VALUES (%s, %s, %s, %s)
                RETURNING id
                """,
                (username, email, username, password_hash),
            )
            row = cur.fetchone()
            return (row["id"], None) if row else (None, "Failed to create account.")
    except psycopg2.IntegrityError:
        return None, "Username or email is already in use."


def verify_user(identifier, password):
    identifier = (identifier or "").strip().lower()
    if not identifier:
        return None
    with get_auth_cursor() as (conn, cur):
        cur.execute(
            """
            SELECT id, username, email, display_name, password_hash
            FROM users
            WHERE LOWER(username) = %s OR LOWER(email) = %s
            LIMIT 1
            """,
            (identifier, identifier),
        )
        user = cur.fetchone()
    if not user or not user.get("password_hash"):
        return None
    if not check_password_hash(user["password_hash"], password):
        return None
    return user


def get_user_by_id(user_id):
    with get_auth_cursor() as (conn, cur):
        cur.execute(
            """
            SELECT id, username, email, display_name, created_at
            FROM users WHERE id = %s LIMIT 1
            """,
            (user_id,),
        )
        return cur.fetchone()


def update_user_email(user_id, new_email):
    new_email = (new_email or "").strip().lower()
    if not new_email:
        return False, "Email is required."
    try:
        with get_auth_cursor() as (conn, cur):
            cur.execute(
                "UPDATE users SET email = %s WHERE id = %s RETURNING id",
                (new_email, user_id),
            )
            row = cur.fetchone()
            return (True, None) if row else (False, "User not found.")
    except psycopg2.IntegrityError:
        return False, "Email is already in use."


def update_user_password(user_id, current_password, new_password):
    if not new_password or len(new_password) < 8:
        return False, "Password must be at least 8 characters."
    with get_auth_cursor() as (conn, cur):
        cur.execute(
            "SELECT password_hash FROM users WHERE id = %s LIMIT 1",
            (user_id,),
        )
        user = cur.fetchone()
        if not user or not user.get("password_hash"):
            return False, "User not found."
        if not check_password_hash(user["password_hash"], current_password):
            return False, "Current password is incorrect."
        password_hash = generate_password_hash(new_password, method="pbkdf2:sha256")
        try:
            cur.execute(
                "UPDATE users SET password_hash = %s WHERE id = %s RETURNING id",
                (password_hash, user_id),
            )
            row = cur.fetchone()
            return (True, None) if row else (False, "Failed to update password.")
        except psycopg2.Error as e:
            return False, str(e)
