"""Index Server blueprint – main site pages, authentication, and account management."""

from flask import Blueprint

index_bp = Blueprint(
    "index",
    __name__,
    template_folder="templates",
    static_folder="static",
    static_url_path="/static/index",
)

from index_server import routes  # noqa: E402, F401
