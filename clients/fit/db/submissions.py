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

SQUARE_DOMAIN = "square_packing_rotatable"
SQUARE_CONTAINER = "square"
RECTANGLE_CONTAINER = "rectangle"
SQUARES_TABLE = "submission_squares"
RECTANGLE_SQUARES_TABLE = "submission_rectangle_squares"


def ensure_rectangle_submission_table():
    with get_cursor() as (conn, cur):
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS submission_rectangle_squares (
              submission_id bigint NOT NULL,
              idx integer NOT NULL,
              cx double precision NOT NULL,
              cy double precision NOT NULL,
              ux double precision NOT NULL,
              uy double precision NOT NULL,
              cx_q bigint NOT NULL,
              cy_q bigint NOT NULL,
              ux_q bigint NOT NULL,
              uy_q bigint NOT NULL,
              width double precision NOT NULL DEFAULT 56,
              height double precision NOT NULL DEFAULT 56,
              pinned boolean NOT NULL DEFAULT false,
              PRIMARY KEY (submission_id, idx),
              FOREIGN KEY (submission_id) REFERENCES submissions (id)
            )
            """
        )
        cur.execute(
            "ALTER TABLE submission_rectangle_squares "
            "ADD COLUMN IF NOT EXISTS width double precision NOT NULL DEFAULT 56"
        )
        cur.execute(
            "ALTER TABLE submission_rectangle_squares "
            "ADD COLUMN IF NOT EXISTS height double precision NOT NULL DEFAULT 56"
        )


def _sat_overlap_float(corners_a, corners_b):
    eps = 1e-8
    for poly in (corners_a, corners_b):
        n = len(poly)
        for i in range(n):
            x1, y1 = poly[i]
            x2, y2 = poly[(i + 1) % n]
            ax = -(y2 - y1)
            ay = x2 - x1
            if abs(ax) < eps and abs(ay) < eps:
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

            if max_a <= min_b + eps or max_b <= min_a + eps:
                return False
    return True


def _normalize_rectangle_payload(shape_payload):
    corners = shape_payload
    if isinstance(shape_payload, dict):
        corners = shape_payload.get("corners")

    if not isinstance(corners, list) or len(corners) != 4:
        return None, None, None, "Each rectangle must include exactly 4 corners."

    pts = []
    for pt in corners:
        if not isinstance(pt, dict) or "x" not in pt or "y" not in pt:
            return None, None, None, "Each corner must be {\"x\": number, \"y\": number}."
        try:
            x = float(pt["x"])
            y = float(pt["y"])
        except (TypeError, ValueError):
            return None, None, None, "Corner coordinates must be numbers."
        pts.append((x, y))

    p0, p1, p2, p3 = pts
    e1 = (p1[0] - p0[0], p1[1] - p0[1])
    e2 = (p2[0] - p1[0], p2[1] - p1[1])
    width = math.hypot(e1[0], e1[1])
    height = math.hypot(e2[0], e2[1])
    if width < 1e-8 or height < 1e-8:
        return None, None, None, "Rectangle width/height must be positive."

    dot = e1[0] * e2[0] + e1[1] * e2[1]
    if abs(dot) > ORTHO_TOL * max(width * height, 1.0):
        return None, None, None, "Rectangle edges must be perpendicular."

    e3 = (p3[0] - p2[0], p3[1] - p2[1])
    e4 = (p0[0] - p3[0], p0[1] - p3[1])
    if abs(math.hypot(e3[0], e3[1]) - width) > SIDE_TOL:
        return None, None, None, "Opposite rectangle sides must be equal."
    if abs(math.hypot(e4[0], e4[1]) - height) > SIDE_TOL:
        return None, None, None, "Opposite rectangle sides must be equal."

    normalized = [
        {"x": p0[0], "y": p0[1]},
        {"x": p1[0], "y": p1[1]},
        {"x": p2[0], "y": p2[1]},
        {"x": p3[0], "y": p3[1]},
    ]
    return normalized, pts, width, height


# Returns (instance_id, quant_scale), creating the row if needed
def get_or_create_fit_instance(domain=SQUARE_DOMAIN, container_type=SQUARE_CONTAINER):
    with get_cursor() as (conn, cur):
        cur.execute(
            """
            SELECT id, quant_scale
            FROM problem_instances
            WHERE domain = %s
              AND container_type = %s
            LIMIT 1
                        """,
            (domain, container_type),
        )
        row = cur.fetchone()
        if row:
            return row["id"], row["quant_scale"]
        cur.execute(
            """
            INSERT INTO problem_instances
                (domain, n, square_size, container_type, allow_rotation, quant_scale)
            VALUES (%s, 0, 56, %s, true, 1000000000)
            RETURNING id, quant_scale
            """,
            (domain, container_type),
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


def _create_fit_submission_for_variant(
    user_id,
    squares_payload,
    *,
    domain,
    container_type,
    squares_table,
):
    if not squares_payload:
        return None, "No squares to submit."
    instance_id, quant_scale = get_or_create_fit_instance(
        domain=domain,
        container_type=container_type,
    )
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
    duplicate_count_sql = f"""
        SELECT COUNT(*) AS cnt
        FROM submissions s
        LEFT JOIN {squares_table} ss ON s.id = ss.submission_id
        WHERE s.instance_id = %s
          AND s.objective_value = %s
        GROUP BY s.id
        HAVING COUNT(ss.idx) = %s
    """
    mark_first_duplicate_sql = f"""
        UPDATE submissions SET is_duplicate = true, duplicate_number = 1
        WHERE id = (
            SELECT s.id FROM submissions s
            LEFT JOIN {squares_table} ss ON s.id = ss.submission_id
            WHERE s.instance_id = %s
              AND s.objective_value = %s
              AND s.is_duplicate = false
              AND s.id != %s
            GROUP BY s.id
            HAVING COUNT(ss.idx) = %s
            ORDER BY s.created_at ASC
            LIMIT 1
        )
    """
    insert_shapes_sql = f"""
        INSERT INTO {squares_table}
        (submission_id, idx, cx, cy, ux, uy, cx_q, cy_q, ux_q, uy_q, pinned)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, false)
    """
    try:
        with get_cursor() as (conn, cur):
            cur.execute(
                "SELECT id FROM submissions "
                "WHERE instance_id = %s AND solution_hash = %s LIMIT 1",
                (instance_id, psycopg2.Binary(solution_hash)),
            )
            if cur.fetchone():
                return None, "An identical solution has already been submitted."

            cur.execute(duplicate_count_sql, (instance_id, objective_value, n_squares))
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
                    mark_first_duplicate_sql,
                    (instance_id, objective_value, submission_id, n_squares),
                )

            for sd in square_data_list:
                cur.execute(
                    insert_shapes_sql,
                    (submission_id, sd["idx"], sd["cx"], sd["cy"],
                     sd["ux"], sd["uy"], sd["cx_q"], sd["cy_q"],
                     sd["ux_q"], sd["uy_q"]),
                )
            return submission_id, None
    except psycopg2.Error as e:
        return None, str(e)


# Returns (submission_id, None) or (None, error)
def create_fit_submission(user_id, squares_payload):
    return _create_fit_submission_for_variant(
        user_id,
        squares_payload,
        domain=SQUARE_DOMAIN,
        container_type=SQUARE_CONTAINER,
        squares_table=SQUARES_TABLE,
    )


def create_submission(user_id, shapes_payload):
    return create_fit_submission(user_id, shapes_payload)


def _resolve_variant_tables(variant):
    if variant == "rectangle":
        ensure_rectangle_submission_table()
        return RECTANGLE_CONTAINER, RECTANGLE_SQUARES_TABLE
    return SQUARE_CONTAINER, SQUARES_TABLE


def get_available_square_counts(variant="square"):
    container_type, squares_table = _resolve_variant_tables(variant)
    with get_cursor() as (conn, cur):
        cur.execute(
            f"""
            SELECT COUNT(ss.idx) AS square_count,
                   COUNT(DISTINCT s.id) AS submission_count
            FROM submissions s
            JOIN problem_instances pi ON s.instance_id = pi.id
            LEFT JOIN {squares_table} ss ON s.id = ss.submission_id
            WHERE pi.domain = 'square_packing_rotatable'
              AND pi.container_type = %s
              AND s.status = 'valid'
            GROUP BY s.id
            """,
            (container_type,),
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


def get_best_submissions(square_count, page=1, per_page=50, hide_duplicates=False, variant="square"):
    container_type, squares_table = _resolve_variant_tables(variant)
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
                                LEFT JOIN {squares_table} ss ON s.id = ss.submission_id
                WHERE pi.domain = 'square_packing_rotatable'
                                    AND pi.container_type = %s
                  AND s.status = 'valid'
                  {dup_filter}
                GROUP BY s.id
                HAVING COUNT(ss.idx) = %s
            ) sub
            """,
                        (container_type, square_count),
        )
        total = cur.fetchone()["cnt"]

        cur.execute(
            f"""
            SELECT s.id, s.user_id, s.status, s.objective_value, s.min_slack,
                   s.created_at, s.is_duplicate, s.duplicate_number,
                   COUNT(ss.idx) AS square_count
            FROM submissions s
            JOIN problem_instances pi ON s.instance_id = pi.id
                        LEFT JOIN {squares_table} ss ON s.id = ss.submission_id
            WHERE pi.domain = 'square_packing_rotatable'
                            AND pi.container_type = %s
              AND s.status = 'valid'
              {dup_filter}
            GROUP BY s.id, s.user_id, s.status, s.objective_value, s.min_slack,
                     s.created_at, s.is_duplicate, s.duplicate_number
            HAVING COUNT(ss.idx) = %s
            ORDER BY s.objective_value ASC NULLS LAST, s.created_at ASC
            LIMIT %s OFFSET %s
            """,
                        (container_type, square_count, per_page, offset),
        )
        return cur.fetchall(), total


# IDs of top N valid submissions with distinct bounds (for medals)
def get_top_valid_ids(square_count, limit=3, variant="square"):
    container_type, squares_table = _resolve_variant_tables(variant)
    with get_cursor() as (conn, cur):
        cur.execute(
            f"""
            SELECT DISTINCT ON (s.objective_value) s.id
            FROM submissions s
            JOIN problem_instances pi ON s.instance_id = pi.id
            LEFT JOIN {squares_table} ss ON s.id = ss.submission_id
            WHERE pi.domain = 'square_packing_rotatable'
              AND pi.container_type = %s
              AND s.status = 'valid'
              AND (s.is_duplicate = false OR s.duplicate_number = 1)
            GROUP BY s.id, s.objective_value, s.created_at
            HAVING COUNT(ss.idx) = %s
            ORDER BY s.objective_value ASC NULLS LAST, s.created_at ASC
            LIMIT %s
            """,
            (container_type, square_count, limit),
        )
        return [row["id"] for row in cur.fetchall()]


def get_submission_squares(submission_id):
    with get_cursor() as (conn, cur):
        cur.execute(
            """
            SELECT idx, cx, cy, ux, uy,
                   NULL::double precision AS width,
                   NULL::double precision AS height
            FROM submission_squares
            WHERE submission_id = %s
            ORDER BY idx
            """,
            (submission_id,),
        )
        rows = cur.fetchall()
        if rows:
            return rows

        ensure_rectangle_submission_table()
        cur.execute(
            """
            SELECT idx, cx, cy, ux, uy, width, height
            FROM submission_rectangle_squares
            WHERE submission_id = %s
            ORDER BY idx
            """,
            (submission_id,),
        )
        return cur.fetchall()


def create_rectangle_submission(user_id, squares_payload):
    ensure_rectangle_submission_table()
    if not squares_payload:
        return None, "No rectangles to submit."

    instance_id, quant_scale = get_or_create_fit_instance(
        domain=SQUARE_DOMAIN,
        container_type=RECTANGLE_CONTAINER,
    )
    if not instance_id:
        return None, "Could not get problem instance."

    rectangle_data_list = []
    canonical_payload = []
    float_corners_list = []

    for idx, shape_payload in enumerate(squares_payload):
        normalized, float_pts, width, height = _normalize_rectangle_payload(shape_payload)
        if normalized is None:
            return None, height

        cx, cy, ux, uy, cx_q, cy_q, ux_q, uy_q = _corners_to_cx_cy_ux_uy(
            normalized,
            quant_scale,
        )
        rectangle_data_list.append(
            {
                "idx": idx,
                "cx": cx,
                "cy": cy,
                "ux": ux,
                "uy": uy,
                "cx_q": cx_q,
                "cy_q": cy_q,
                "ux_q": ux_q,
                "uy_q": uy_q,
                "width": width,
                "height": height,
            }
        )
        canonical_payload.append(normalized)
        float_corners_list.append(float_pts)

    for i in range(len(float_corners_list)):
        for j in range(i + 1, len(float_corners_list)):
            if _sat_overlap_float(float_corners_list[i], float_corners_list[j]):
                return None, f"Rectangles {i} and {j} overlap."

    objective_value = _compute_objective_value(canonical_payload)
    n_shapes = len(rectangle_data_list)
    solution_hash = hashlib.sha256(
        json.dumps(canonical_payload, sort_keys=True).encode()
    ).digest()

    duplicate_count_sql = f"""
        SELECT COUNT(*) AS cnt
        FROM submissions s
        LEFT JOIN {RECTANGLE_SQUARES_TABLE} ss ON s.id = ss.submission_id
        WHERE s.instance_id = %s
          AND s.objective_value = %s
        GROUP BY s.id
        HAVING COUNT(ss.idx) = %s
    """
    mark_first_duplicate_sql = f"""
        UPDATE submissions SET is_duplicate = true, duplicate_number = 1
        WHERE id = (
            SELECT s.id FROM submissions s
            LEFT JOIN {RECTANGLE_SQUARES_TABLE} ss ON s.id = ss.submission_id
            WHERE s.instance_id = %s
              AND s.objective_value = %s
              AND s.is_duplicate = false
              AND s.id != %s
            GROUP BY s.id
            HAVING COUNT(ss.idx) = %s
            ORDER BY s.created_at ASC
            LIMIT 1
        )
    """

    try:
        with get_cursor() as (conn, cur):
            cur.execute(
                "SELECT id FROM submissions "
                "WHERE instance_id = %s AND solution_hash = %s LIMIT 1",
                (instance_id, psycopg2.Binary(solution_hash)),
            )
            if cur.fetchone():
                return None, "An identical solution has already been submitted."

            cur.execute(duplicate_count_sql, (instance_id, objective_value, n_shapes))
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
                (
                    instance_id,
                    user_id,
                    objective_value,
                    psycopg2.Binary(solution_hash),
                    is_duplicate,
                    duplicate_number,
                ),
            )
            row = cur.fetchone()
            if not row:
                return None, "Failed to create submission."
            submission_id = row["id"]

            if is_duplicate and existing_count == 1:
                cur.execute(
                    mark_first_duplicate_sql,
                    (instance_id, objective_value, submission_id, n_shapes),
                )

            for sd in rectangle_data_list:
                cur.execute(
                    """
                    INSERT INTO submission_rectangle_squares
                    (submission_id, idx, cx, cy, ux, uy, cx_q, cy_q, ux_q, uy_q, width, height, pinned)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, false)
                    """,
                    (
                        submission_id,
                        sd["idx"],
                        sd["cx"],
                        sd["cy"],
                        sd["ux"],
                        sd["uy"],
                        sd["cx_q"],
                        sd["cy_q"],
                        sd["ux_q"],
                        sd["uy_q"],
                        sd["width"],
                        sd["height"],
                    ),
                )
            return submission_id, None
    except psycopg2.Error as e:
        return None, str(e)
