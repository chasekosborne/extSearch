import time
import threading

from flask import jsonify, request, session

from clients.fit import fit_bp
from clients.fit.db.fit_cases import build_explore_groups, get_optimal_n
from clients.fit.db.submissions import (
    create_fit_submission,
    get_available_square_counts,
    get_submission_squares,
)
from shared.auth import verify_token
from shared.rate_limit import check_rate_limit
from index_server.db.users import login_user

CHIP_BATCH = 50

_ip_lock = threading.Lock()
_ip_hits: dict[str, list[float]] = {}

IP_WINDOW = 3600
IP_MAX_ANON = 10
IP_MAX_AUTH = 120


# Per-IP sliding-window rate check, returns (allowed, retry_after_seconds)
def _check_ip_rate(ip: str, is_authenticated: bool) -> tuple[bool, int]:
    now = time.time()
    cutoff = now - IP_WINDOW
    limit = IP_MAX_AUTH if is_authenticated else IP_MAX_ANON

    with _ip_lock:
        hits = _ip_hits.get(ip, [])
        hits = [t for t in hits if t > cutoff]
        if len(hits) >= limit:
            retry = int(hits[0] - cutoff) + 1
            _ip_hits[ip] = hits
            return False, retry
        hits.append(now)
        _ip_hits[ip] = hits
        return True, 0



# Returns (user_id, username) or (None, None)
def _get_authenticated_user():
    uid = session.get("user_id")
    if uid:
        return uid, session.get("username")

    auth = request.headers.get("Authorization", "")
    if auth.startswith("Bearer "):
        payload = verify_token(auth[7:])
        if payload:
            return payload["sub"], payload.get("username")

    return None, None


@fit_bp.route("/api/fit/token", methods=["POST"])
def api_token():
    if not request.is_json:
        return jsonify(error="Content-Type must be application/json"), 400
    data = request.get_json() or {}
    username = (data.get("username") or "").strip()
    password = data.get("password") or ""
    if not username or not password:
        return jsonify(error="username and password are required."), 400

    token, result = login_user(username, password)
    if not token:
        error = result if isinstance(result, str) else "Invalid credentials."
        return jsonify(error=error), 401

    return jsonify(token=token)


@fit_bp.route("/api/fit/explore/square-counts")
def api_explore_square_counts():
    group = request.args.get("group")
    if group not in ("optimal", "found"):
        return jsonify(error="group must be optimal or found"), 400
    try:
        offset = max(0, request.args.get("offset", 0, type=int))
        limit = min(100, max(1, request.args.get("limit", CHIP_BATCH, type=int)))
    except TypeError:
        offset, limit = 0, CHIP_BATCH
    from_db = get_available_square_counts()
    db_by_n = {r["square_count"]: r["submission_count"] for r in from_db}
    optimal_counts, found_counts = build_explore_groups(db_by_n)
    if group == "optimal":
        items = optimal_counts[offset : offset + limit]
        has_more = len(optimal_counts) > offset + limit
    else:
        items = found_counts[offset : offset + limit]
        has_more = len(found_counts) > offset + limit
    return jsonify(items=items, has_more=has_more)


@fit_bp.route("/api/submission/<int:submission_id>/squares")
def api_submission_squares(submission_id):
    rows = get_submission_squares(submission_id)
    squares = [
        {"cx": float(r["cx"]), "cy": float(r["cy"]),
         "ux": float(r["ux"]), "uy": float(r["uy"])}
        for r in rows
    ]
    return jsonify(squares=squares)


@fit_bp.route("/api/fit/submit", methods=["POST"])
def api_submit():
    if not request.is_json:
        return jsonify(error="Content-Type must be application/json"), 400

    user_id, _username = _get_authenticated_user()

    has_bearer = request.headers.get("Authorization", "").startswith("Bearer ")
    if has_bearer and user_id is None:
        return jsonify(error="Invalid or expired token."), 401

    client_ip = request.headers.get("X-Forwarded-For", request.remote_addr or "")
    ip_ok, ip_retry = _check_ip_rate(client_ip, is_authenticated=user_id is not None)
    if not ip_ok:
        resp = jsonify(
            error="Too many submissions from this IP. Try again in %d seconds." % ip_retry,
        )
        resp.status_code = 429
        resp.headers["Retry-After"] = str(ip_retry)
        return resp

    rate_info = None
    if user_id is not None:
        allowed, rate_info = check_rate_limit(user_id)
        if not allowed:
            resp = jsonify(
                error="Rate limit exceeded. Try again in %d seconds." % rate_info.get("retry_after", 60),
                rate_limit=rate_info,
            )
            resp.status_code = 429
            resp.headers["Retry-After"] = str(rate_info.get("retry_after", 60))
            _add_rate_headers(resp, rate_info)
            return resp

    data = request.get_json() or {}
    squares_payload = data.get("squares")
    if not isinstance(squares_payload, list):
        return jsonify(error='Missing or invalid "squares" array.'), 400
    n = len(squares_payload)
    if n < 11:
        return jsonify(
            error="At least 11 squares are required. You submitted %d." % n
        ), 422
    if n in get_optimal_n():
        return jsonify(
            error="Solutions for %d squares are already known optimal; "
                  "submission not accepted." % n
        ), 422
    submission_id, err = create_fit_submission(user_id, squares_payload)
    if err:
        return jsonify(error=err), 422

    resp = jsonify(submission_id=submission_id, message="Solution submitted.")
    if rate_info is not None:
        rate_info["remaining"] = max(0, rate_info["remaining"] - 1)
        _add_rate_headers(resp, rate_info)
    return resp


def _add_rate_headers(resp, rate_info):
    resp.headers["X-RateLimit-Limit"] = str(rate_info["limit"])
    resp.headers["X-RateLimit-Remaining"] = str(rate_info["remaining"])
    resp.headers["X-RateLimit-Window"] = str(rate_info["window_seconds"])
