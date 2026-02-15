"""Database connection and helpers."""

import hashlib
import json
import math
import os
import psycopg2
from psycopg2.extras import RealDictCursor
from contextlib import contextmanager
from werkzeug.security import generate_password_hash, check_password_hash


def get_connection():
    """Return a new database connection using DATABASE_URL from environment."""
    return psycopg2.connect(
        os.environ.get("DATABASE_URL", "postgresql://localhost/extsearch_dev"),
        cursor_factory=RealDictCursor,
    )


@contextmanager
def get_cursor(commit=True):
    """Context manager for a database cursor. Yields (conn, cur)."""
    conn = get_connection()
    cur = conn.cursor()
    try:
        yield conn, cur
        if commit:
            conn.commit()
    finally:
        cur.close()
        conn.close()


def create_guest_user():
    """
    Create a new guest user in the users table.
    Guest users have NULL email and username (allowed by schema).
    Returns the new user's id, or None on failure.
    """
    with get_cursor() as (conn, cur):
        cur.execute(
            """
            INSERT INTO users (email, username, display_name)
            VALUES (NULL, NULL, 'Guest')
            RETURNING id
            """
        )
        row = cur.fetchone()
        return row["id"] if row else None


def create_user(username, email, password):
    """
    Create a new registered user with a hashed password.
    Username and email must be unique. Display name equals username.
    Returns (user_id, None) on success, or (None, error_message) on failure.
    """
    username = (username or "").strip().lower()
    email = (email or "").strip().lower()
    if not username or not email:
        return None, "Username and email are required."
    if not password or len(password) < 8:
        return None, "Password must be at least 8 characters."

    password_hash = generate_password_hash(password, method="pbkdf2:sha256")

    try:
        with get_cursor() as (conn, cur):
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


def get_user_by_username_or_email(identifier):
    """
    Fetch a user by username or email (case-insensitive).
    Returns the user dict or None.
    """
    identifier = (identifier or "").strip().lower()
    if not identifier:
        return None
    with get_cursor() as (conn, cur):
        cur.execute(
            """
            SELECT id, username, email, display_name, password_hash
            FROM users
            WHERE LOWER(username) = %s OR LOWER(email) = %s
            LIMIT 1
            """,
            (identifier, identifier),
        )
        return cur.fetchone()


def verify_user(identifier, password):
    """
    Verify credentials. Returns user dict if valid, None otherwise.
    """
    user = get_user_by_username_or_email(identifier)
    if not user or not user.get("password_hash"):
        return None
    if not check_password_hash(user["password_hash"], password):
        return None
    return user


def get_or_create_fit_instance():
    """
    Return (instance_id, quant_scale) for the Fit game.
    Creates a problem_instance row if none exists for domain 'square_packing_rotatable'.
    """
    with get_cursor() as (conn, cur):
        cur.execute(
            """
            SELECT id, quant_scale
            FROM problem_instances
            WHERE domain = 'square_packing_rotatable'
            LIMIT 1
            """
        )
        row = cur.fetchone()
        if row:
            return row["id"], row["quant_scale"]
        cur.execute(
            """
            INSERT INTO problem_instances (domain, n, square_size, container_type, allow_rotation, quant_scale)
            VALUES ('square_packing_rotatable', 0, 56, 'square', true, 1000000000)
            RETURNING id, quant_scale
            """
        )
        row = cur.fetchone()
        return (row["id"], row["quant_scale"]) if row else (None, None)


def _corners_to_cx_cy_ux_uy(corners, quant_scale):
    """Convert 4 geometric corners [{x,y}, ...] to (cx, cy, ux, uy) and quantized.

    corners[0..3] are the actual square corners (TL, TR, BR, BL before
    rotation).  corners[1] (the rotated top-right) is used as the reference
    direction for the unit vector.
    """
    c0, c1, c2, c3 = corners[0], corners[1], corners[2], corners[3]
    cx = (c0["x"] + c1["x"] + c2["x"] + c3["x"]) / 4
    cy = (c0["y"] + c1["y"] + c2["y"] + c3["y"]) / 4
    dx = c1["x"] - cx
    dy = c1["y"] - cy
    L = math.hypot(dx, dy)
    if L < 1e-9:
        ux, uy = 1.0, 0.0
    else:
        ux, uy = dx / L, dy / L
    q = quant_scale
    return (
        cx, cy, ux, uy,
        round(cx * q), round(cy * q), round(ux * q), round(uy * q),
    )


def _compute_objective_value(squares_payload, square_size=56):
    """
    Compute the bounding-square side length (in unit squares) from a list of
    4-corner arrays.  Each corner has {x, y} in board pixels.
    Returns the side length normalised by square_size, rounded to avoid
    floating-point noise (e.g. when squares are snapped to 0.01 grid).
    """
    min_x = min_y = float("inf")
    max_x = max_y = float("-inf")
    for corners in squares_payload:
        for pt in corners:
            min_x = min(min_x, pt["x"])
            min_y = min(min_y, pt["y"])
            max_x = max(max_x, pt["x"])
            max_y = max(max_y, pt["y"])
    width = (max_x - min_x) / square_size
    height = (max_y - min_y) / square_size
    side = max(width, height)
    return round(side, 5)  # hundred-thousands place to match manual precision


def create_fit_submission(user_id, squares_payload):
    """
    Store a Fit game solution. squares_payload is a list of [top, right, bottom, left]
    with each point as {"x": float, "y": float}.
    Returns (submission_id, None) on success, (None, error_message) on failure.
    """
    if not squares_payload:
        return None, "No squares to submit."
    instance_id, quant_scale = get_or_create_fit_instance()
    if not instance_id:
        return None, "Could not get problem instance."

    objective_value = _compute_objective_value(squares_payload)
    n_squares = len(squares_payload)

    canonical = json.dumps(squares_payload, sort_keys=True)
    solution_hash = hashlib.sha256(canonical.encode()).digest()
    try:
        with get_cursor() as (conn, cur):
            # Check for duplicate: same instance, same square count, same objective
            cur.execute(
                """
                SELECT s.id
                FROM submissions s
                LEFT JOIN submission_squares ss ON s.id = ss.submission_id
                WHERE s.instance_id = %s
                  AND s.objective_value = %s
                GROUP BY s.id
                HAVING COUNT(ss.idx) = %s
                LIMIT 1
                """,
                (instance_id, objective_value, n_squares),
            )
            if cur.fetchone():
                return None, (
                    "A solution with the same bounding square side length "
                    "(s = %.5f) for %d squares already exists."
                    % (objective_value, n_squares)
                )

            cur.execute(
                """
                INSERT INTO submissions
                    (instance_id, user_id, status, objective_value, solution_hash)
                VALUES (%s, %s, 'pending', %s, %s)
                RETURNING id
                """,
                (instance_id, user_id, objective_value,
                 psycopg2.Binary(solution_hash)),
            )
            row = cur.fetchone()
            if not row:
                return None, "Failed to create submission."
            submission_id = row["id"]
            for idx, corners in enumerate(squares_payload):
                cx, cy, ux, uy, cx_q, cy_q, ux_q, uy_q = _corners_to_cx_cy_ux_uy(
                    corners, quant_scale
                )
                cur.execute(
                    """
                    INSERT INTO submission_squares
                    (submission_id, idx, cx, cy, ux, uy, cx_q, cy_q, ux_q, uy_q, pinned)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, false)
                    """,
                    (submission_id, idx, cx, cy, ux, uy, cx_q, cy_q, ux_q, uy_q),
                )
            return submission_id, None
    except psycopg2.Error as e:
        return None, str(e)


def get_user_submissions(user_id, page=1, per_page=50):
    """
    Get a page of submissions for a user, ordered by created_at DESC.
    Returns (rows, total_count).
    """
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


def get_available_square_counts():
    """
    Return a sorted list of distinct square counts that have at least one
    submission in the Fit problem (domain = 'square_packing_rotatable').
    Each element is a dict with 'square_count' and 'submission_count'.
    """
    with get_cursor() as (conn, cur):
        cur.execute(
            """
            SELECT COUNT(ss.idx) AS square_count,
                   COUNT(DISTINCT s.id) AS submission_count
            FROM submissions s
            JOIN problem_instances pi ON s.instance_id = pi.id
            LEFT JOIN submission_squares ss ON s.id = ss.submission_id
            WHERE pi.domain = 'square_packing_rotatable'
            GROUP BY s.id
            """
        )
        # The inner query gives one row per submission with its square_count.
        # We need to aggregate those.
        rows = cur.fetchall()
        counts = {}
        for r in rows:
            n = r["square_count"]
            counts[n] = counts.get(n, 0) + 1
        return sorted(
            [{"square_count": k, "submission_count": v} for k, v in counts.items()],
            key=lambda x: x["square_count"],
        )


def get_best_submissions(square_count, page=1, per_page=50):
    """
    Get the best Fit submissions for a given number of squares,
    ranked by objective_value ASC (smallest bounding box first).
    Returns (rows, total_count).
    """
    offset = (page - 1) * per_page
    with get_cursor() as (conn, cur):
        # Count total submissions with this square count
        cur.execute(
            """
            SELECT COUNT(*) AS cnt
            FROM (
                SELECT s.id
                FROM submissions s
                JOIN problem_instances pi ON s.instance_id = pi.id
                LEFT JOIN submission_squares ss ON s.id = ss.submission_id
                WHERE pi.domain = 'square_packing_rotatable'
                GROUP BY s.id
                HAVING COUNT(ss.idx) = %s
            ) sub
            """,
            (square_count,),
        )
        total = cur.fetchone()["cnt"]

        cur.execute(
            """
            SELECT s.id, s.status, s.objective_value, s.min_slack, s.created_at,
                   u.username, u.display_name,
                   COUNT(ss.idx) AS square_count
            FROM submissions s
            JOIN problem_instances pi ON s.instance_id = pi.id
            LEFT JOIN submission_squares ss ON s.id = ss.submission_id
            LEFT JOIN users u ON s.user_id = u.id
            WHERE pi.domain = 'square_packing_rotatable'
            GROUP BY s.id, s.status, s.objective_value, s.min_slack, s.created_at,
                     u.username, u.display_name
            HAVING COUNT(ss.idx) = %s
            ORDER BY s.objective_value ASC NULLS LAST, s.created_at ASC
            LIMIT %s OFFSET %s
            """,
            (square_count, per_page, offset),
        )
        return cur.fetchall(), total


def get_submission_squares(submission_id):
    """
    Return the squares for a submission as a list of dicts with
    cx, cy, ux, uy (floats in board-pixel space).
    """
    with get_cursor() as (conn, cur):
        cur.execute(
            """
            SELECT idx, cx, cy, ux, uy
            FROM submission_squares
            WHERE submission_id = %s
            ORDER BY idx
            """,
            (submission_id,),
        )
        return cur.fetchall()


def get_user_by_id(user_id):
    """
    Fetch a user by id. Returns user dict or None.
    """
    with get_cursor() as (conn, cur):
        cur.execute(
            """
            SELECT id, username, email, display_name, created_at
            FROM users
            WHERE id = %s
            LIMIT 1
            """,
            (user_id,),
        )
        return cur.fetchone()


def update_user_email(user_id, new_email):
    """
    Update user's email. Returns (True, None) on success, (False, error_message) on failure.
    """
    new_email = (new_email or "").strip().lower()
    if not new_email:
        return False, "Email is required."
    try:
        with get_cursor() as (conn, cur):
            cur.execute(
                """
                UPDATE users
                SET email = %s
                WHERE id = %s
                RETURNING id
                """,
                (new_email, user_id),
            )
            row = cur.fetchone()
            return (True, None) if row else (False, "User not found.")
    except psycopg2.IntegrityError:
        return False, "Email is already in use."


def update_user_password(user_id, current_password, new_password):
    """
    Update user's password. Verifies current password first.
    Returns (True, None) on success, (False, error_message) on failure.
    """
    if not new_password or len(new_password) < 8:
        return False, "Password must be at least 8 characters."
    with get_cursor() as (conn, cur):
        cur.execute(
            """
            SELECT password_hash
            FROM users
            WHERE id = %s
            LIMIT 1
            """,
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
                """
                UPDATE users
                SET password_hash = %s
                WHERE id = %s
                RETURNING id
                """,
                (password_hash, user_id),
            )
            row = cur.fetchone()
            return (True, None) if row else (False, "Failed to update password.")
        except psycopg2.Error as e:
            return False, str(e)
