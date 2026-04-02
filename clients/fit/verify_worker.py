#!/usr/bin/env python3
import argparse
import json
import math
import os
import sys
import time

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

try:
    from dotenv import load_dotenv
    load_dotenv(os.path.join(ROOT, ".env"))
except ImportError:
    pass

from shared.db import get_cursor

VALIDATOR_VERSION = "fit-v2.0"
SQUARE_SIZE = 56
HALF = SQUARE_SIZE / 2
QUANT_SCALE = 1_000_000_000

SIDE_TOL = 0.05
ORTHO_TOL = 1e-4
UNIT_VEC_TOL = 1e-4
OBJ_TOL = 0.0001
DIAGONAL_TOL = 0.05


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


def _rectangle_corners_from_row(sq):
    cx = float(sq["cx"])
    cy = float(sq["cy"])
    ux = float(sq["ux"])
    uy = float(sq["uy"])
    width = float(sq["width"])
    height = float(sq["height"])

    corner_angle = math.atan2(uy, ux)
    offset_angle = math.atan2(height, width)
    rotation = corner_angle + offset_angle
    cos_r = math.cos(rotation)
    sin_r = math.sin(rotation)
    hw = width / 2
    hh = height / 2

    return [
        (cx + (-hw) * cos_r - (-hh) * sin_r, cy + (-hw) * sin_r + (-hh) * cos_r),
        (cx + hw * cos_r - (-hh) * sin_r, cy + hw * sin_r + (-hh) * cos_r),
        (cx + hw * cos_r - hh * sin_r, cy + hw * sin_r + hh * cos_r),
        (cx + (-hw) * cos_r - hh * sin_r, cy + (-hw) * sin_r + hh * cos_r),
    ]


def corners_from_square_q(cx_q, cy_q, ux_q, uy_q):
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
def sat_overlap_int(corners_a, corners_b):
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


def corners_from_square_f(cx, cy, ux, uy):
    d = HALF * math.sqrt(2)
    return [
        (cx + d * ux, cy + d * uy),
        (cx - d * uy, cy + d * ux),
        (cx - d * ux, cy - d * uy),
        (cx + d * uy, cy - d * ux),
    ]


# Returns (valid, reason, metrics)
def validate_submission(squares):
    if not squares:
        return False, "No squares in submission.", {}

    n = len(squares)
    float_corners_list = []
    int_corners_list = []

    for sq in squares:
        ux, uy = float(sq["ux"]), float(sq["uy"])
        cx, cy = float(sq["cx"]), float(sq["cy"])
        cx_q = int(sq["cx_q"])
        cy_q = int(sq["cy_q"])
        ux_q = int(sq["ux_q"])
        uy_q = int(sq["uy_q"])
        idx = sq["idx"]

        unit_len = math.hypot(ux, uy)
        if abs(unit_len - 1.0) > UNIT_VEC_TOL:
            return False, f"Square {idx}: unit vector length {unit_len:.8f} != 1", {}

        unit_len_q = math.hypot(ux_q, uy_q)
        expected_q = float(QUANT_SCALE)
        if abs(unit_len_q - expected_q) / expected_q > UNIT_VEC_TOL:
            return False, f"Square {idx}: quantized unit vector length mismatch", {}

        corners_f = corners_from_square_f(cx, cy, ux, uy)
        float_corners_list.append(corners_f)

        for i in range(4):
            x1, y1 = corners_f[i]
            x2, y2 = corners_f[(i + 1) % 4]
            side = math.hypot(x2 - x1, y2 - y1)
            if abs(side - SQUARE_SIZE) > SIDE_TOL:
                return (
                    False,
                    f"Square {idx}: side {i} length {side:.6f}, "
                    f"expected {SQUARE_SIZE} (tol={SIDE_TOL})",
                    {},
                )

        for i in range(4):
            x1, y1 = corners_f[i]
            x2, y2 = corners_f[(i + 1) % 4]
            x3, y3 = corners_f[(i + 2) % 4]
            e1x, e1y = x2 - x1, y2 - y1
            e2x, e2y = x3 - x2, y3 - y2
            dot = e1x * e2x + e1y * e2y
            if abs(dot) > ORTHO_TOL * SQUARE_SIZE * SQUARE_SIZE:
                return (
                    False,
                    f"Square {idx}: edges {i},{(i+1)%4} not perpendicular "
                    f"(dot={dot:.6f}, max={ORTHO_TOL * SQUARE_SIZE * SQUARE_SIZE:.6f})",
                    {},
                )

        diag1 = math.hypot(
            corners_f[2][0] - corners_f[0][0],
            corners_f[2][1] - corners_f[0][1],
        )
        diag2 = math.hypot(
            corners_f[3][0] - corners_f[1][0],
            corners_f[3][1] - corners_f[1][1],
        )
        expected_diag = SQUARE_SIZE * math.sqrt(2)
        if abs(diag1 - expected_diag) > DIAGONAL_TOL:
            return False, f"Square {idx}: diagonal 1 length {diag1:.6f}, expected {expected_diag:.6f}", {}
        if abs(diag2 - expected_diag) > DIAGONAL_TOL:
            return False, f"Square {idx}: diagonal 2 length {diag2:.6f}, expected {expected_diag:.6f}", {}
        if abs(diag1 - diag2) > DIAGONAL_TOL:
            return False, f"Square {idx}: diagonals not equal ({diag1:.6f} vs {diag2:.6f})", {}

        int_corners_list.append(corners_from_square_q(cx_q, cy_q, ux_q, uy_q))

    for i in range(n):
        for j in range(i + 1, n):
            if sat_overlap_int(int_corners_list[i], int_corners_list[j]):
                return (
                    False,
                    f"Squares {squares[i]['idx']} and {squares[j]['idx']} overlap "
                    f"(exact integer SAT).",
                    {},
                )

    all_corners_f = [c for corners in float_corners_list for c in corners]
    min_x = min(x for x, y in all_corners_f)
    min_y = min(y for x, y in all_corners_f)
    max_x = max(x for x, y in all_corners_f)
    max_y = max(y for x, y in all_corners_f)
    width = (max_x - min_x) / SQUARE_SIZE
    height = (max_y - min_y) / SQUARE_SIZE
    computed_obj = round(max(width, height), 5)

    metrics = {
        "n_squares": n,
        "computed_objective": computed_obj,
        "bounding_box": {
            "width": round(width, 5),
            "height": round(height, 5),
        },
        "validator": VALIDATOR_VERSION,
    }

    return True, "All checks passed.", metrics


def validate_rectangle_submission(squares):
    if not squares:
        return False, "No rectangles in submission.", {}

    corners_list = []
    for sq in squares:
        width = float(sq.get("width") or 0)
        height = float(sq.get("height") or 0)
        if width <= 0 or height <= 0:
            return False, f"Rectangle {sq.get('idx')}: width/height must be positive.", {}

        ux, uy = float(sq["ux"]), float(sq["uy"])
        unit_len = math.hypot(ux, uy)
        if abs(unit_len - 1.0) > UNIT_VEC_TOL:
            return False, f"Rectangle {sq.get('idx')}: unit vector length mismatch.", {}

        corners_list.append(_rectangle_corners_from_row(sq))

    for i in range(len(corners_list)):
        for j in range(i + 1, len(corners_list)):
            if _sat_overlap_float(corners_list[i], corners_list[j]):
                return False, f"Rectangles {squares[i]['idx']} and {squares[j]['idx']} overlap.", {}

    all_corners = [c for corners in corners_list for c in corners]
    min_x = min(x for x, y in all_corners)
    min_y = min(y for x, y in all_corners)
    max_x = max(x for x, y in all_corners)
    max_y = max(y for x, y in all_corners)
    width = (max_x - min_x) / SQUARE_SIZE
    height = (max_y - min_y) / SQUARE_SIZE
    computed_obj = round(max(width, height), 5)

    metrics = {
        "n_squares": len(squares),
        "computed_objective": computed_obj,
        "bounding_box": {
            "width": round(width, 5),
            "height": round(height, 5),
        },
        "validator": VALIDATOR_VERSION,
        "container_type": "rectangle",
    }
    return True, "All checks passed.", metrics


def fetch_pending(limit=10):
    with get_cursor(commit=False) as (conn, cur):
        cur.execute(
            """
                        SELECT s.id, s.objective_value, pi.container_type
            FROM submissions s
            JOIN problem_instances pi ON s.instance_id = pi.id
            WHERE pi.domain = 'square_packing_rotatable'
              AND s.status = 'pending'
            ORDER BY s.created_at ASC
            LIMIT %s
            """,
            (limit,),
        )
        return cur.fetchall()


def fetch_squares(submission_id, container_type):
    table = "submission_squares" if container_type == "square" else "submission_rectangle_squares"
    width_select = "NULL::double precision AS width, NULL::double precision AS height" if container_type == "square" else "width, height"
    with get_cursor(commit=False) as (conn, cur):
        cur.execute(
            f"""
            SELECT idx, cx, cy, ux, uy, cx_q, cy_q, ux_q, uy_q, {width_select}
            FROM {table}
            WHERE submission_id = %s
            ORDER BY idx
            """,
            (submission_id,),
        )
        return cur.fetchall()


def record_result(submission_id, valid, reason, metrics, obj_from_db):
    with get_cursor() as (conn, cur):
        status = "valid" if valid else "invalid"
        cur.execute(
            """
            INSERT INTO validation_runs
                (submission_id, validator_ver, valid, reason, metrics)
            VALUES (%s, %s, %s, %s, %s)
            """,
            (
                submission_id,
                VALIDATOR_VERSION,
                valid,
                reason,
                json.dumps(metrics),
            ),
        )

        update_fields = ["status = %s"]
        update_vals = [status]

        if valid and metrics.get("computed_objective") is not None:
            computed = metrics["computed_objective"]
            if obj_from_db is None or abs(computed - obj_from_db) > OBJ_TOL:
                update_fields.append("objective_value = %s")
                update_vals.append(computed)

        update_vals.append(submission_id)
        cur.execute(
            f"UPDATE submissions SET {', '.join(update_fields)} WHERE id = %s",
            update_vals,
        )


def process_batch(limit=10):
    pending = fetch_pending(limit)
    if not pending:
        return 0

    for sub in pending:
        sid = sub["id"]
        obj_from_db = sub.get("objective_value")
        container_type = sub.get("container_type") or "square"
        squares = fetch_squares(sid, container_type)
        if container_type == "rectangle":
            valid, reason, metrics = validate_rectangle_submission(squares)
        else:
            valid, reason, metrics = validate_submission(squares)
        record_result(sid, valid, reason, metrics, obj_from_db)
        status = "VALID" if valid else "INVALID"
        print(f"  [{status}] submission {sid}: {reason}")

    return len(pending)


def main():
    parser = argparse.ArgumentParser(description="Fit solution verification worker")
    parser.add_argument("--loop", action="store_true", help="Poll continuously")
    parser.add_argument(
        "--interval", type=int, default=5, help="Seconds between polls (with --loop)"
    )
    parser.add_argument(
        "--batch", type=int, default=10, help="Submissions per batch"
    )
    args = parser.parse_args()

    print(f"Fit verification worker ({VALIDATOR_VERSION})")
    print(f"  Database: {os.environ.get('DATABASE_URL', '(default)')}")
    print(f"  Policy: conservative (reject if uncertain)")
    print(f"  Overlap: exact integer SAT (quant_scale={QUANT_SCALE})")

    if args.loop:
        print(f"  Mode: continuous (interval={args.interval}s, batch={args.batch})")
        while True:
            n = process_batch(args.batch)
            if n > 0:
                print(f"  Processed {n} submission(s)")
            time.sleep(args.interval)
    else:
        print("  Mode: one-shot")
        n = process_batch(args.batch)
        print(f"Done. Processed {n} submission(s).")


if __name__ == "__main__":
    main()
