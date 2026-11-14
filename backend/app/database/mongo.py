"""MongoDB connection (Atlas when configured, in-memory demo store otherwise)."""
import logging

from flask import current_app

logger = logging.getLogger(__name__)


def init_database(app) -> None:
    uri = (app.config.get("MONGODB_URI") or "").strip()
    db_name = app.config.get("MONGODB_DB_NAME", "eip")
    mode = "memory"
    db = None

    if uri:
        try:
            from pymongo import MongoClient

            client = MongoClient(uri, serverSelectionTimeoutMS=5000, connectTimeoutMS=5000)
            client.admin.command("ping")
            db = client[db_name]
            mode = "mongodb"
        except Exception as exc:  # connection issues must not crash the demo
            logger.warning("MongoDB connection failed (%s). Using in-memory demo store.", exc)

    if db is None:
        import mongomock

        db = mongomock.MongoClient()[db_name]

    app.extensions["mongo_db"] = db
    app.extensions["db_mode"] = mode

    from app.database.indexes import ensure_indexes

    ensure_indexes(db)


def get_db():
    return current_app.extensions["mongo_db"]


def db_mode() -> str:
    return current_app.extensions.get("db_mode", "memory")
