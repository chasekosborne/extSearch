from importlib import import_module


SQUARE = "square"
RECTANGLE = "rectangle"

SQUARE_HANDLER_MODULE = "../../clients/fit/db/submissions.py"


def _load_handler(module_path):
    module = import_module(module_path)
    required = ("get_submission_squares",)
    for name in required:
        if not hasattr(module, name):
            raise AttributeError(
                f"Handler module '{module_path}' is missing required function '{name}'."
            )
    return module
