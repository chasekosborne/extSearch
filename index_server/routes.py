from flask import redirect, render_template, request, session, url_for

from index_server import index_bp
from index_server.db.users import (
    get_user_by_id,
    get_user_submissions,
    login_user,
    register_user,
    update_user_email,
    update_user_password,
)


@index_bp.route("/")
def home():
    return render_template("index/home.html")


@index_bp.route("/about")
def about():
    return render_template("index/about.html")


@index_bp.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        identifier = request.form.get("username", "").strip()
        password = request.form.get("password", "")

        token, result = login_user(identifier, password)
        if token and isinstance(result, dict):
            session.clear()
            session["user_id"] = result["id"]
            session["username"] = result["username"]
            session["is_guest"] = False
            session["token"] = token
            return redirect(url_for("fit.game"))

        error = result if isinstance(result, str) else "Invalid username or password."
        return render_template("index/login.html", error=error)
    return render_template("index/login.html")


@index_bp.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        email = request.form.get("email", "").strip()
        password = request.form.get("password", "")

        token, result = register_user(username, email, password)
        if token and isinstance(result, dict):
            session.clear()
            session["user_id"] = result["id"]
            session["username"] = result["username"]
            session["is_guest"] = False
            session["token"] = token
            return redirect(url_for("fit.game"))

        error = result if isinstance(result, str) else "Registration failed."
        return render_template("index/register.html", error=error)

    return render_template("index/register.html")


@index_bp.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("index.home"))


@index_bp.route("/submissions")
def submissions():
    user_id = session.get("user_id")
    is_guest = session.get("is_guest", False)
    if not user_id or is_guest:
        return redirect(url_for("index.login"))
    page = request.args.get("page", 1, type=int)
    per_page = 50
    submissions_list, total = get_user_submissions(user_id, page=page, per_page=per_page)
    total_pages = max(1, (total + per_page - 1) // per_page)
    return render_template(
        "index/submissions.html",
        submissions=submissions_list,
        page=page,
        total_pages=total_pages,
        total=total,
    )


@index_bp.route("/account/settings", methods=["GET", "POST"])
def account_settings():
    user_id = session.get("user_id")
    is_guest = session.get("is_guest", False)
    token = session.get("token")
    if not user_id or is_guest:
        return redirect(url_for("index.login"))

    user = get_user_by_id(user_id, token=token)
    if not user:
        return redirect(url_for("index.login"))

    error = None
    success = None

    if request.method == "POST":
        action = request.form.get("action")

        if action == "update_email":
            new_email = request.form.get("email", "").strip()
            success_flag, err = update_user_email(user_id, new_email, token=token)
            if success_flag:
                success = "Email updated successfully."
                user["email"] = new_email
            else:
                error = err or "Failed to update email."

        elif action == "update_password":
            current_password = request.form.get("current_password", "")
            new_password = request.form.get("new_password", "")
            confirm_password = request.form.get("confirm_password", "")

            if new_password != confirm_password:
                error = "New passwords do not match."
            else:
                success_flag, err = update_user_password(
                    user_id, current_password, new_password, token=token
                )
                if success_flag:
                    success = "Password updated successfully."
                else:
                    error = err or "Failed to update password."

    return render_template(
        "index/account-settings.html", user=user, error=error, success=success
    )
