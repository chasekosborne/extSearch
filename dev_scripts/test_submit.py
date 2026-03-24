import requests

BASE = "http://localhost:5000"
USERNAME = "chasekosborne"
PASSWORD = "surfdracula"
SQ = 56


def make_square(px, py, rotation_deg=0):
    import math

    cx, cy = px + SQ / 2, py + SQ / 2
    rad = math.radians(rotation_deg)
    cos_r, sin_r = math.cos(rad), math.sin(rad)

    raw = [
        (-SQ / 2, -SQ / 2),
        (SQ / 2, -SQ / 2),
        (SQ / 2, SQ / 2),
        (-SQ / 2, SQ / 2),
    ]
    corners = []
    for dx, dy in raw:
        rx = dx * cos_r - dy * sin_r
        ry = dx * sin_r + dy * cos_r
        corners.append({"x": round(cx + rx, 6), "y": round(cy + ry, 6)})
    return corners


def get_token():
    r = requests.post(
        f"{BASE}/api/fit/token",
        json={"username": USERNAME, "password": PASSWORD},
    )
    r.raise_for_status()
    token = r.json()["token"]
    print(f"[+] Got JWT token: {token[:40]}...")
    return token


def submit(token, squares, label):
    print(f"\n{'='*60}")
    print(f"  {label}  ({len(squares)} squares)")
    print(f"{'='*60}")
    r = requests.post(
        f"{BASE}/api/fit/submit",
        json={"squares": squares},
        headers={"Authorization": f"Bearer {token}"},
    )
    print(f"  Status : {r.status_code}")
    body = r.json()
    for k, v in body.items():
        print(f"  {k:20s}: {v}")
    rl = r.headers.get("X-RateLimit-Remaining")
    if rl is not None:
        print(f"  Rate-Limit-Remaining: {rl}")
    return r.status_code


def main():
    token = get_token()

    # --- Valid solution: 11 non-overlapping squares in a unique layout ---
    # Uses an offset on the last row to avoid matching earlier submissions.
    import random
    offset = random.randint(1, 500) * 56
    valid_squares = []
    positions = [
        (0, 0), (56, 0), (112, 0), (168, 0),
        (0, 56), (56, 56), (112, 56), (168, 56),
        (0, 112), (56, 112), (0, 112 + 56 + offset),
    ]
    for px, py in positions:
        valid_squares.append(make_square(px, py))

    code = submit(token, valid_squares, "TEST 1: Valid 11-square grid (no overlaps)")
    assert code == 200, f"Expected 200, got {code}"
    print("  >>> PASS: accepted as expected")

    # --- Invalid solution: 11 squares where two overlap ---
    invalid_squares = []
    bad_positions = [
        (0, 0), (56, 0), (112, 0), (168, 0),
        (0, 56), (56, 56), (112, 56), (168, 56),
        (0, 112), (56, 112),
        (80, 112),  # overlaps with the square at (56, 112)
    ]
    for px, py in bad_positions:
        invalid_squares.append(make_square(px, py))

    code = submit(token, invalid_squares, "TEST 2: Invalid 11-square grid (squares overlap)")
    assert code == 422, f"Expected 422, got {code}"
    print("  >>> PASS: rejected as expected")

    print("\n[+] All tests passed.")


if __name__ == "__main__":
    main()
