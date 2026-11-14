"""Shared bootstrap for operational scripts.

Adds the backend package to sys.path and builds the Flask app so scripts can
reuse the exact same configuration, database mode and seeding logic as the
running server.
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))


def build_app(overrides=None):
    from app import create_app

    return create_app(overrides)
