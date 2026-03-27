from importlib import import_module


SQUARE = "square"
RECTANGLE = "rectangle"

SQUARE_HANDLER_MODULE = "clients.fit.db.submissions"


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
        return _load_handler(RECTANGLE_HANDLER_MODULE)
    raise ValueError(
        "Could not determine submission variant. Provide payload.variant or payload.size {width,height}."
    )
def _normalize_variant(payload):
    if not payload:
        return None
        
    element = payload[0]
    return "SQUARE" if all(x == element[0] for x in element) else "RECTANGLE"