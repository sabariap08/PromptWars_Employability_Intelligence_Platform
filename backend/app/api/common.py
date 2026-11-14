"""Small request helpers shared by API blueprints."""
from flask import request


def json_body() -> dict:
    data = request.get_json(silent=True)
    return data if isinstance(data, dict) else {}


def pagination() -> dict:
    def _int(name: str, default: int, maximum: int) -> int:
        try:
            value = int(request.args.get(name, default))
        except (TypeError, ValueError):
            value = default
        return max(1, min(maximum, value))

    return {"page": _int("page", 1, 100000), "page_size": _int("page_size", 20, 100)}


def arg(name: str, default: str = "") -> str:
    return (request.args.get(name) or default).strip()
