import hashlib
import json
import math

import psycopg2

from shared.db import get_cursor 

SQUARE_SIZE = 56
HALF = SQUARE_SIZE / 2
QUANT_SCALE = 1_000_000_000

SIDE_TOL = 0.05
ORTHO_TOL = 1e-4
UNIT_VEC_TOL = 1e-4
DIAGONAL_TOL = 0.05


# Returns (instance_id, quant_scale), creating the row if  needed
def get_or_create_fit_instance():
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
            INSERT INTO problem_instances
                (domain, n, square_size, container_type, allow_rotation, quant_scale)
            VALUES ('square_packing_rotatable', 0, 56, 'square', true, 1000000000)
            RETURNING id, quant_scale
            """
        )
        row = cur.fetchone()
        return (row["id"], row["quant_scale"]) if row else (None, None)


def _corners_to_cx_cy_ux_uy(corners, quant_scale):
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
    return round(side, 5)


def _corners_from_float(cx, cy, ux, uy):
    d = HALF * math.sqrt(2)
    return [
        (cx + d * ux, cy + d * uy),
        (cx - d * uy, cy + d * ux),
        (cx - d * ux, cy - d * uy),
        (cx + d * uy, cy - d * ux),
    ]


def _corners_from_quantized(cx_q, cy_q, ux_q, uy_q):
    d_q = round(HALF * math.sqrt(2) * QUANT_SCALE)
    return [
        (cx_q * QUANT_SCALE + d_q * ux_q,
         cy_q * QUANT_SCALE + d_q * uy_q),
        (cx_q * QUANT_SCALE - d_q * uy_q,
         cy_q * QUANT_SCALE + d_q * ux_q),
        (cx_q * QUANT_SCALE - d_q * ux_q,
         cy_q * QUANT_SCALE - d_q * uy_q),
        (cx_q * QUANT_SCALE + d_q * uy_q,
         cy_q * QUANT_SCALE - d_q * ux_q),
    ]


# Returns True if interiors overlap; touching edges are non-overlapping
def _sat_overlap_int(corners_a, corners_b):
    for poly in (corners_a, corners_b):
        n = len(poly)
        for i in range(n):
            x1, y1 = poly[i]
            x2, y2 = poly[(i + 1) % n]
            ax = -(y2 - y1)
            ay = x2 - x1
            if ax == 0 and ay == 0:
                continue

            min_a = max_a = corners_a[0][0] * ax + corners_a[0][1] * ay
            for cx, cy in corners_a[1:]:
                d = cx * ax + cy * ay
                if d < min_a:
                    min_a = d
                elif d > max_a:
                    max_a = d

            min_b = max_b = corners_b[0][0] * ax + corners_b[0][1] * ay
            for cx, cy in corners_b[1:]:
                d = cx * ax + cy * ay
                if d < min_b:
                    min_b = d
                elif d > max_b:
                    max_b = d

            if max_a <= min_b or max_b <= min_a:
                return False
    return True


# Returns None on success or an error string
def _pre_validate(square_data_list):
    n = len(square_data_list)
    int_corners_list = []
    expected_diag = SQUARE_SIZE * math.sqrt(2)

    for idx, sd in enumerate(square_data_list):
        cx, cy, ux, uy = sd["cx"], sd["cy"], sd["ux"], sd["uy"]
        cx_q, cy_q, ux_q, uy_q = sd["cx_q"], sd["cy_q"], sd["ux_q"], sd["uy_q"]

        unit_len = math.hypot(ux, uy)
        if abs(unit_len - 1.0) > UNIT_VEC_TOL:
            return f"Square {idx}: unit vector length {unit_len:.8f} != 1"

        unit_len_q = math.hypot(ux_q, uy_q)
        if abs(unit_len_q - float(QUANT_SCALE)) / QUANT_SCALE > UNIT_VEC_TOL:
            return f"Square {idx}: quantized unit vector length mismatch"

        corners_f = _corners_from_float(cx, cy, ux, uy)

        for i in range(4):
            x1, y1 = corners_f[i]
            x2, y2 = corners_f[(i + 1) % 4]
            side = math.hypot(x2 - x1, y2 - y1)
            if abs(side - SQUARE_SIZE) > SIDE_TOL:
                return (
                    f"Square {idx}: side {i} length {side:.6f}, "
                    f"expected {SQUARE_SIZE} (tol={SIDE_TOL})"
                )

        for i in range(4):
            x1, y1 = corners_f[i]
            x2, y2 = corners_f[(i + 1) % 4]
            x3, y3 = corners_f[(i + 2) % 4]
            e1x, e1y = x2 - x1, y2 - y1
            e2x, e2y = x3 - x2, y3 - y2
            dot = e1x * e2x + e1y * e2y
            if abs(dot) > ORTHO_TOL * SQUARE_SIZE * SQUARE_SIZE:
                return f"Square {idx}: edges not perpendicular (dot={dot:.6f})"

        diag1 = math.hypot(
            corners_f[2][0] - corners_f[0][0],
            corners_f[2][1] - corners_f[0][1],
        )
        diag2 = math.hypot(
            corners_f[3][0] - corners_f[1][0],
            corners_f[3][1] - corners_f[1][1],
        )
        if abs(diag1 - expected_diag) > DIAGONAL_TOL:
            return f"Square {idx}: diagonal length {diag1:.6f}, expected {expected_diag:.6f}"
        if abs(diag2 - expected_diag) > DIAGONAL_TOL:
            return f"Square {idx}: diagonal length {diag2:.6f}, expected {expected_diag:.6f}"
        if abs(diag1 - diag2) > DIAGONAL_TOL:
            return f"Square {idx}: diagonals not equal ({diag1:.6f} vs {diag2:.6f})"

        int_corners_list.append(_corners_from_quantized(cx_q, cy_q, ux_q, uy_q))

    for i in range(n):
        for j in range(i + 1, n):
            if _sat_overlap_int(int_corners_list[i], int_corners_list[j]):
                return f"Squares {i} and {j} overlap."

    return None


# Returns (submission_id, None) or (None, error)
def create_fit_submission(user_id, squares_payload):
    if not squares_payload:
        return None, "No squares to submit."
    instance_id, quant_scale = get_or_create_fit_instance()
    if not instance_id:
        return None, "Could not get problem instance."

    for corners in squares_payload:
        if not isinstance(corners, list) or len(corners) != 4:
            return None, "Each square must have exactly 4 corner points."
        for pt in corners:
            if not isinstance(pt, dict) or "x" not in pt or "y" not in pt:
                return None, "Each corner must be {\"x\": number, \"y\": number}."
            try:
                float(pt["x"])
                float(pt["y"])
            except (TypeError, ValueError):
                return None, "Corner coordinates must be numbers."

    objective_value = _compute_objective_value(squares_payload)
    n_squares = len(squares_payload)

    square_data_list = []
    for idx, corners in enumerate(squares_payload):
        cx, cy, ux, uy, cx_q, cy_q, ux_q, uy_q = _corners_to_cx_cy_ux_uy(
            corners, quant_scale
        )
        square_data_list.append({
            "idx": idx, "cx": cx, "cy": cy, "ux": ux, "uy": uy,
            "cx_q": cx_q, "cy_q": cy_q, "ux_q": ux_q, "uy_q": uy_q,
        })

    validation_err = _pre_validate(square_data_list)
    if validation_err:
        return None, validation_err

    canonical = json.dumps(squares_payload, sort_keys=True)
    solution_hash = hashlib.sha256(canonical.encode()).digest()
    try:
        with get_cursor() as (conn, cur):
            cur.execute(
                "SELECT id FROM submissions "
                "WHERE instance_id = %s AND solution_hash = %s LIMIT 1",
                (instance_id, psycopg2.Binary(solution_hash)),
            )
            if cur.fetchone():
                return None, "An identical solution has already been submitted."

            cur.execute(
                """
                SELECT COUNT(*) AS cnt
                FROM submissions s
                LEFT JOIN submission_squares ss ON s.id = ss.submission_id
                WHERE s.instance_id = %s
                  AND s.objective_value = %s
                GROUP BY s.id
                HAVING COUNT(ss.idx) = %s
                """,
                (instance_id, objective_value, n_squares),
            )
            existing_count = len(cur.fetchall())
            is_duplicate = existing_count > 0
            duplicate_number = existing_count + 1 if is_duplicate else None

            cur.execute(
                """
                INSERT INTO submissions
                    (instance_id, user_id, status, objective_value,
                     solution_hash, is_duplicate, duplicate_number)
                VALUES (%s, %s, 'pending', %s, %s, %s, %s)
                RETURNING id
                """,
                (instance_id, user_id, objective_value,
                 psycopg2.Binary(solution_hash),
                 is_duplicate, duplicate_number),
            )
            row = cur.fetchone()
            if not row:
                return None, "Failed to create submission."
            submission_id = row["id"]

            if is_duplicate and existing_count == 1:
                cur.execute(
                    """
                    UPDATE submissions SET is_duplicate = true, duplicate_number = 1
                    WHERE id = (
                        SELECT s.id FROM submissions s
                        LEFT JOIN submission_squares ss ON s.id = ss.submission_id
                        WHERE s.instance_id = %s
                          AND s.objective_value = %s
                          AND s.is_duplicate = false
                          AND s.id != %s
                        GROUP BY s.id
                        HAVING COUNT(ss.idx) = %s
                        ORDER BY s.created_at ASC
                        LIMIT 1
                    )
                    """,
                    (instance_id, objective_value, submission_id, n_squares),
                )

            for sd in square_data_list:
                cur.execute(
                    """
                    INSERT INTO submission_squares
                    (submission_id, idx, cx, cy, ux, uy, cx_q, cy_q, ux_q, uy_q, pinned)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, false)
                    """,
                    (submission_id, sd["idx"], sd["cx"], sd["cy"],
                     sd["ux"], sd["uy"], sd["cx_q"], sd["cy_q"],
                     sd["ux_q"], sd["uy_q"]),
                )
            return submission_id, None
    except psycopg2.Error as e:
        return None, str(e)


def create_submission(user_id, shapes_payload):
    return create_fit_submission(user_id, shapes_payload)


def get_available_square_counts():
    with get_cursor() as (conn, cur):
        cur.execute(
            """
            SELECT COUNT(ss.idx) AS square_count,
                   COUNT(DISTINCT s.id) AS submission_count
            FROM submissions s
            JOIN problem_instances pi ON s.instance_id = pi.id
            LEFT JOIN submission_squares ss ON s.id = ss.submission_id
            WHERE pi.domain = 'square_packing_rotatable'
              AND s.status = 'valid'
            GROUP BY s.id
            """
        )
        rows = cur.fetchall()
        counts = {}
        for r in rows:
            n = r["square_count"]
            counts[n] = counts.get(n, 0) + 1
        return sorted(
            [{"square_count": k, "submission_count": v} for k, v in counts.items()],
            key=lambda x: x["square_count"],
        )


def get_best_submissions(square_count, page=1, per_page=50, hide_duplicates=False):
    offset = (page - 1) * per_page
    dup_filter = "AND (s.is_duplicate = false OR s.duplicate_number = 1)" if hide_duplicates else ""

    with get_cursor() as (conn, cur):
        cur.execute(
            f"""
            SELECT COUNT(*) AS cnt
            FROM (
                SELECT s.id
                FROM submissions s
                JOIN problem_instances pi ON s.instance_id = pi.id
                LEFT JOIN submission_squares ss ON s.id = ss.submission_id
                WHERE pi.domain = 'square_packing_rotatable'
                  AND s.status = 'valid'
                  {dup_filter}
                GROUP BY s.id
                HAVING COUNT(ss.idx) = %s
            ) sub
            """,
            (square_count,),
        )
        total = cur.fetchone()["cnt"]

        cur.execute(
            f"""
            SELECT s.id, s.user_id, s.status, s.objective_value, s.min_slack,
                   s.created_at, s.is_duplicate, s.duplicate_number,
                   COUNT(ss.idx) AS square_count
            FROM submissions s
            JOIN problem_instances pi ON s.instance_id = pi.id
            LEFT JOIN submission_squares ss ON s.id = ss.submission_id
            WHERE pi.domain = 'square_packing_rotatable'
              AND s.status = 'valid'
              {dup_filter}
            GROUP BY s.id, s.user_id, s.status, s.objective_value, s.min_slack,
                     s.created_at, s.is_duplicate, s.duplicate_number
            HAVING COUNT(ss.idx) = %s
            ORDER BY s.objective_value ASC NULLS LAST, s.created_at ASC
            LIMIT %s OFFSET %s
            """,
            (square_count, per_page, offset),
        )
        return cur.fetchall(), total


# IDs of top N valid submissions with distinct bounds (for medals)
def get_top_valid_ids(square_count, limit=3):
    with get_cursor() as (conn, cur):
        cur.execute(
            """
            SELECT DISTINCT ON (s.objective_value) s.id
            FROM submissions s
            JOIN problem_instances pi ON s.instance_id = pi.id
            LEFT JOIN submission_squares ss ON s.id = ss.submission_id
            WHERE pi.domain = 'square_packing_rotatable'
              AND s.status = 'valid'
              AND (s.is_duplicate = false OR s.duplicate_number = 1)
            GROUP BY s.id, s.objective_value, s.created_at
            HAVING COUNT(ss.idx) = %s
            ORDER BY s.objective_value ASC NULLS LAST, s.created_at ASC
            LIMIT %s
            """,
            (square_count, limit),
        )
        return [row["id"] for row in cur.fetchall()]


def get_submission_squares(submission_id):
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
