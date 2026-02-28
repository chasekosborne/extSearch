import os
from dotenv import load_dotenv

from flask import Flask, jsonify, redirect, render_template, request, session, url_for

from db.connection import (
    create_fit_submission,
    create_user,
    get_available_square_counts,
    get_best_submissions,
    get_submission_squares,
    get_user_by_id,
    get_user_submissions,
    update_user_email,
    update_user_password,
    verify_user,
)
from db.fit_cases import build_explore_groups, get_optimal_n

load_dotenv()

app = Flask(__name__)
app.secret_key = os.environ.get("FLASK_SECRET_KEY", "dev-secret-change-in-production")


@app.route('/')
def home():
    return render_template('home.html')

@app.route('/what-is-fit')
def what_is_fit():
    return render_template('what-is-fit.html')

@app.route('/about')
def about():
    return render_template('about.html')

@app.route('/fit')
def fit():
    return render_template('fit.html', optimal_n=list(get_optimal_n()))


@app.route('/fit/api')
def fit_api():
    return render_template('fit-api.html')


@app.route('/solution')
def solution():
    return render_template('solution.html')


@app.route('/fit/explore')
def explore_solutions():
    """View the best submissions for a given number of squares."""
    from_db = get_available_square_counts()
    db_by_n = {r["square_count"]: r["submission_count"] for r in from_db}
    optimal_counts, found_counts = build_explore_groups(db_by_n)
    n = request.args.get('n', type=int)
    page = request.args.get('page', 1, type=int)
    per_page = 50
    submissions_list = []
    total = 0
    total_pages = 1
    if n is not None:
        submissions_list, total = get_best_submissions(n, page=page, per_page=per_page)
        total_pages = max(1, (total + per_page - 1) // per_page)
    return render_template(
        'explore-solutions.html',
        optimal_counts=optimal_counts[:CHIP_BATCH],
        found_counts=found_counts[:CHIP_BATCH],
        optimal_has_more=len(optimal_counts) > CHIP_BATCH,
        found_has_more=len(found_counts) > CHIP_BATCH,
        selected_n=n,
        submissions=submissions_list,
        page=page,
        total_pages=total_pages,
        total=total,
    )


CHIP_BATCH = 50


@app.route('/api/fit/explore/square-counts')
def api_fit_explore_square_counts():
    """Paginated square counts for explore chips. group=optimal|found, offset=0, limit=50."""
    group = request.args.get('group')
    if group not in ('optimal', 'found'):
        return jsonify(error='group must be optimal or found'), 400
    try:
        offset = max(0, request.args.get('offset', 0, type=int))
        limit = min(100, max(1, request.args.get('limit', CHIP_BATCH, type=int)))
    except TypeError:
        offset, limit = 0, CHIP_BATCH
    from_db = get_available_square_counts()
    db_by_n = {r["square_count"]: r["submission_count"] for r in from_db}
    optimal_counts, found_counts = build_explore_groups(db_by_n)
    if group == 'optimal':
        items = optimal_counts[offset : offset + limit]
        has_more = len(optimal_counts) > offset + limit
    else:
        items = found_counts[offset : offset + limit]
        has_more = len(found_counts) > offset + limit
    return jsonify(items=items, has_more=has_more)


@app.route('/api/submission/<int:submission_id>/squares')
def api_submission_squares(submission_id):
    """Return the squares of a submission as JSON for the visualiser."""
    rows = get_submission_squares(submission_id)
    squares = [
        {"cx": float(r["cx"]), "cy": float(r["cy"]),
         "ux": float(r["ux"]), "uy": float(r["uy"])}
        for r in rows
    ]
    return jsonify(squares=squares)


@app.route('/api/fit/submit', methods=['POST'])
def api_fit_submit():
    """Accept a Fit game solution (JSON body with 'squares') and store it."""
    if not request.is_json:
        return jsonify(error='Content-Type must be application/json'), 400
    data = request.get_json() or {}
    squares_payload = data.get('squares')
    if not isinstance(squares_payload, list):
        return jsonify(error='Missing or invalid "squares" array.'), 400
    n = len(squares_payload)
    if n in get_optimal_n():
        return jsonify(
            error='Solutions for %d squares are already known optimal; submission not accepted.' % n
        ), 422
    user_id = session.get('user_id')
    submission_id, err = create_fit_submission(user_id, squares_payload)
    if err:
        return jsonify(error=err), 422
    return jsonify(submission_id=submission_id, message='Solution submitted.')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        identifier = request.form.get('username', '').strip()
        password = request.form.get('password', '')
        user = verify_user(identifier, password)
        if user:
            session.clear()
            session['user_id'] = user['id']
            session['username'] = user['username']
            session['is_guest'] = False
            return redirect(url_for('fit'))
        return render_template('login.html', error='Invalid username or password.')
    return render_template('login.html')


@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        email = request.form.get('email', '').strip()
        password = request.form.get('password', '')

        user_id, err = create_user(username, email, password)
        if err:
            return render_template('register.html', error=err)

        session.clear()
        session['user_id'] = user_id
        session['username'] = username.lower()
        session['is_guest'] = False
        return redirect(url_for('fit'))

    return render_template('register.html')


@app.route('/logout')
def logout():
    """Clear session and redirect to home."""
    session.clear()
    return redirect(url_for("home"))


@app.route('/submissions')
def submissions():
    """View user's submitted solutions. Only for registered users."""
    user_id = session.get('user_id')
    is_guest = session.get('is_guest', False)
    if not user_id or is_guest:
        return redirect(url_for('login'))
    page = request.args.get('page', 1, type=int)
    per_page = 50
    submissions_list, total = get_user_submissions(user_id, page=page, per_page=per_page)
    total_pages = max(1, (total + per_page - 1) // per_page)
    return render_template(
        'submissions.html',
        submissions=submissions_list,
        page=page,
        total_pages=total_pages,
        total=total,
    )


@app.route('/account/settings', methods=['GET', 'POST'])
def account_settings():
    """Edit account information (email and password). Only for registered users."""
    user_id = session.get('user_id')
    is_guest = session.get('is_guest', False)
    if not user_id or is_guest:
        return redirect(url_for('login'))
    
    user = get_user_by_id(user_id)
    if not user:
        return redirect(url_for('login'))
    
    error = None
    success = None
    
    if request.method == 'POST':
        action = request.form.get('action')
        
        if action == 'update_email':
            new_email = request.form.get('email', '').strip()
            success_flag, err = update_user_email(user_id, new_email)
            if success_flag:
                success = "Email updated successfully."
                user['email'] = new_email
            else:
                error = err or "Failed to update email."
        
        elif action == 'update_password':
            current_password = request.form.get('current_password', '')
            new_password = request.form.get('new_password', '')
            confirm_password = request.form.get('confirm_password', '')
            
            if new_password != confirm_password:
                error = "New passwords do not match."
            else:
                success_flag, err = update_user_password(user_id, current_password, new_password)
                if success_flag:
                    success = "Password updated successfully."
                else:
                    error = err or "Failed to update password."
    
    return render_template('account-settings.html', user=user, error=error, success=success)


@app.context_processor
def inject_user():
    """Make current user info available in all templates."""
    return {
        "current_user_id": session.get("user_id"),
        "current_username": session.get("username"),
        "is_guest": session.get("is_guest", False),
    }
    
if __name__ == '__main__':
    app.run(debug=True)