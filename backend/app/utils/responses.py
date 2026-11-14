"""Uniform API responses and application errors."""
from flask import jsonify


class AppError(Exception):
    """Expected application error that maps to a clean API response."""

    def __init__(self, message: str, code: str = "REQUEST_FAILED", status: int = 400, details=None):
        super().__init__(message)
        self.message = message
        self.code = code
        self.status = status
        self.details = details


def ok(data=None, message: str = "Operation completed successfully", status: int = 200):
    return jsonify({"success": True, "message": message, "data": data if data is not None else {}}), status


def fail(message: str, code: str = "REQUEST_FAILED", status: int = 400, details=None):
    payload = {"success": False, "message": message, "error_code": code}
    if details is not None:
        payload["details"] = details
    return jsonify(payload), status
