"""Fit client blueprint – square packing game, solution explorer, and API."""

from flask import Blueprint

fit_bp = Blueprint(
    "fit",
    __name__,
    template_folder="templates",
    static_folder="static",
    static_url_path="/static/fit",
)

from clients.fit import routes, api  # noqa: E402, F401
