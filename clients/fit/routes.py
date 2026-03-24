from flask import render_template, request

from clients.fit import fit_bp
from clients.fit.db.fit_cases import build_explore_groups, get_optimal_n
from clients.fit.db.submissions import (
    get_available_square_counts,
    get_best_submissions,
    get_top_valid_ids,
)
from shared.users import enrich_submissions_with_usernames

CHIP_BATCH = 50


@fit_bp.route("/fit")
def game():
    return render_template("fit/game.html", optimal_n=list(get_optimal_n()))


@fit_bp.route("/fit/api")
def fit_api():
    return render_template("fit/api.html")


@fit_bp.route("/solution")
def solution():
    return render_template("fit/solution.html")


@fit_bp.route("/what-is-fit")
def what_is_fit():
    return render_template("fit/what-is-fit.html")


@fit_bp.route("/fit/explore")
def explore_solutions():
    from_db = get_available_square_counts()
    db_by_n = {r["square_count"]: r["submission_count"] for r in from_db}
    optimal_counts, found_counts = build_explore_groups(db_by_n)
    n = request.args.get("n", type=int)
    page = request.args.get("page", 1, type=int)
    hide_duplicates = request.args.get("hide_duplicates", "1") == "1"
    per_page = 50
    submissions_list = []
    total = 0
    total_pages = 1
    medal_ids = []
    if n is not None:
        submissions_list, total = get_best_submissions(
            n, page=page, per_page=per_page, hide_duplicates=hide_duplicates,
        )
        enrich_submissions_with_usernames(submissions_list)
        total_pages = max(1, (total + per_page - 1) // per_page)
        medal_ids = get_top_valid_ids(n, limit=3)
    return render_template(
        "fit/explore.html",
        optimal_counts=optimal_counts[:CHIP_BATCH],
        found_counts=found_counts[:CHIP_BATCH],
        optimal_has_more=len(optimal_counts) > CHIP_BATCH,
        found_has_more=len(found_counts) > CHIP_BATCH,
        selected_n=n,
        submissions=submissions_list,
        page=page,
        total_pages=total_pages,
        total=total,
        hide_duplicates=hide_duplicates,
        medal_ids=medal_ids,
    )
