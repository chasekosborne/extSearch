# Client Template

This directory contains a scaffold for creating a new problem/game client for
ExtSearch. Each client is a self-contained Flask Blueprint with its own pages,
API, database layer, static assets, and data.

## Quick Start

1. **Copy** this directory into `clients/<your_problem>/`.
2. **Rename** the blueprint in `__init__.py` (change `"_template"` to your
   problem's short name).
3. **Implement** the required components:
   - `routes.py` – page routes (game page, solution explorer, info page)
   - `api.py` – API endpoints (submit, retrieve, validate)
   - `db/submissions.py` – database functions for your problem's data
4. **Register** your blueprint in `main.py`:
   ```python
   from clients.your_problem import your_bp
   app.register_blueprint(your_bp)
   ```

## Directory Structure

```
your_problem/
├── __init__.py              # Blueprint factory
├── routes.py                # Page routes
├── api.py                   # API endpoints
├── db/
│   ├── __init__.py
│   └── submissions.py       # Problem-specific DB functions
├── templates/
│   └── your_problem/        # Namespaced Jinja2 templates
│       ├── game.html        # Main game / problem interaction page
│       ├── explore.html     # Solution explorer
│       └── api.html         # API documentation page
├── static/
│   ├── style/               # CSS files
│   ├── scripts/             # JavaScript files
│   └── img/                 # Images and icons
└── data/                    # Problem-specific data files
```

## Standard API Interface

Every client should provide at minimum:

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/<problem>/submit` | POST | Submit a solution |
| `/api/<problem>/retrieve/<id>` | GET | Retrieve solution data |
| `/api/<problem>/validate` | POST | Validate a solution |

See the Fit client (`clients/fit/`) for a complete reference implementation.
