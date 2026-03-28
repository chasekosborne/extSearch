from importlib import import_module
import math

SQUARE = "square"
RECTANGLE = "rectangle"

SQUARE_HANDLER_MODULE = "clients.fit.db.submissions"
RECTANGLE_HANDLER_MODULE = "clients.fit.db.rectangle_submissions"


def _load_handler(module_path,required = ()):
    module = import_module(module_path)
    for name in required:
        if not hasattr(module, name):
            raise AttributeError(
                f"Handler module '{module_path}' is missing required function '{name}'."
            )
    return module



def _get_handler(variant):
    if variant == SQUARE:
        return _load_handler(SQUARE_HANDLER_MODULE)
    if variant == RECTANGLE:
        if not RECTANGLE_HANDLER_MODULE:
            raise ValueError("Rectangle handler is not configured.")
        return _load_handler(RECTANGLE_HANDLER_MODULE)
    raise ValueError(
        "Could not determine submission variant. Provide payload.variant or payload.size {width,height}."
    )

def _normalize_variant(payload):
    if not isinstance(payload, dict):
        return None

    variant = payload.get("variant")
    if not isinstance(variant, str):
        return None

    normalized = variant.strip().lower()
    if normalized == SQUARE:
        return SQUARE
    if normalized == RECTANGLE:
        return RECTANGLE
    return None


def create_submission(user_id, shapes_payload, variant=None):
    resolved = (variant or "").strip().lower()
    handler = _get_handler(resolved)

    if hasattr(handler, "create_submission"):
        return handler.create_submission(user_id, shapes_payload)
    if hasattr(handler, "create_fit_submission"):
        return handler.create_fit_submission(user_id, shapes_payload)

    raise AttributeError(
        "Handler module is missing create_submission/create_fit_submission implementation."
    )


