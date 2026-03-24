import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from dotenv import load_dotenv

load_dotenv(os.path.join(ROOT, ".env"))

from flask import Flask, jsonify, request
from auth_server.db.users import (
    create_user,
    get_user_by_id,
    update_user_email,
    update_user_password,
    verify_user,
)
from shared.auth import generate_token, verify_token


app = Flask(__name__)


@app.route("/auth/login", methods=["POST"])
def login():
    data = request.get_json(silent=True) or {}
    identifier = (data.get("username") or "").strip()
    password = data.get("password") or ""
    if not identifier or not password:
        return jsonify(error="Username and password are required."), 400

    user = verify_user(identifier, password)
    if not user:
        return jsonify(error="Invalid username or password."), 401

    token = generate_token(user["id"], user["username"])
    return jsonify(
        token=token,
        user={
            "id": user["id"],
            "username": user["username"],
            "email": user.get("email"),
        },
    )


@app.route("/auth/register", methods=["POST"])
def register():
    data = request.get_json(silent=True) or {}
    username = (data.get("username") or "").strip()
    email = (data.get("email") or "").strip()
    password = data.get("password") or ""

    user_id, err = create_user(username, email, password)
    if err:
        return jsonify(error=err), 400

    token = generate_token(user_id, username.lower())
    return jsonify(
        token=token,
        user={"id": user_id, "username": username.lower(), "email": email.lower()},
    )


@app.route("/auth/verify", methods=["POST"])
def verify():
    data = request.get_json(silent=True) or {}
    token = data.get("token") or ""
    payload = verify_token(token)
    if not payload:
        return jsonify(valid=False, error="Invalid or expired token."), 401
    return jsonify(
        valid=True,
        user={"id": payload["sub"], "username": payload["username"]},
    )


@app.route("/auth/users/batch", methods=["POST"])
def users_batch():
    data = request.get_json(silent=True) or {}
    user_ids = data.get("user_ids", [])
    if not user_ids or not isinstance(user_ids, list):
        return jsonify(users={})

    user_ids = [int(uid) for uid in user_ids[:500]]
    from auth_server.db.connection import get_auth_cursor
    with get_auth_cursor(commit=False) as (conn, cur):
        cur.execute(
            "SELECT id, username, display_name FROM users WHERE id = ANY(%s)",
            (user_ids,),
        )
        rows = cur.fetchall()
    result = {}
    for row in rows:
        result[str(row["id"])] = {
            "username": row["username"],
            "display_name": row.get("display_name"),
        }
    return jsonify(users=result)


@app.route("/auth/user/<int:user_id>", methods=["GET"])
def user_info(user_id):
    payload = _require_token()
    if payload is None:
        return jsonify(error="Authentication required."), 401

    user = get_user_by_id(user_id)
    if not user:
        return jsonify(error="User not found."), 404
    return jsonify(
        user={
            "id": user["id"],
            "username": user["username"],
            "email": user.get("email"),
            "display_name": user.get("display_name"),
            "created_at": str(user["created_at"]) if user.get("created_at") else None,
        }
    )


@app.route("/auth/user/<int:user_id>/email", methods=["PUT"])
def update_email(user_id):
    payload = _require_token()
    if payload is None or payload["sub"] != user_id:
        return jsonify(error="Forbidden."), 403

    data = request.get_json(silent=True) or {}
    ok, err = update_user_email(user_id, data.get("email", ""))
    if not ok:
        return jsonify(error=err), 400
    return jsonify(success=True)


@app.route("/auth/user/<int:user_id>/password", methods=["PUT"])
def update_password(user_id):
    payload = _require_token()
    if payload is None or payload["sub"] != user_id:
        return jsonify(error="Forbidden."), 403

    data = request.get_json(silent=True) or {}
    ok, err = update_user_password(
        user_id, data.get("current_password", ""), data.get("new_password", "")
    )
    if not ok:
        return jsonify(error=err), 400
    return jsonify(success=True)


@app.route("/auth/health")
def health():
    return jsonify(status="ok")


def _require_token():
    auth = request.headers.get("Authorization", "")
    if auth.startswith("Bearer "):
        return verify_token(auth[7:])
    return None


if __name__ == "__main__":
    port = int(os.environ.get("AUTH_PORT", 5001))
    debug = os.environ.get("FLASK_DEBUG", "0") == "1"
    print(f"Auth server starting on port {port}")
    app.run(host="0.0.0.0", port=port, debug=debug)
