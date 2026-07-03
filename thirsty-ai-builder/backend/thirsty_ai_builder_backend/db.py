"""MongoDB wrapper for the ThirstyAi Builder.

Production: connects to a real MongoDB via pymongo. Dev / tests: an
in-memory dict-backed stub with a Mongo-compatible surface (`insert_one`,
`find`, `find_one`, `update_one`, `delete_one`, `count`).

The Mongo path is exercised on first call by pinging the server. By
default, an unreachable or missing Mongo falls back to the in-memory
stub so local tests remain self-contained. In production, set
`THIRSTY_AI_REQUIRE_MONGO=1`; that mode fails closed instead of using
volatile in-memory storage.
"""
from __future__ import annotations

import logging
import os
import threading
from typing import Any

LOG = logging.getLogger("thirsty_ai_builder.db")


# ----- in-memory implementation -------------------------------------------


class _InMemoryCollection:
    def __init__(self) -> None:
        self._docs: list[dict[str, Any]] = []
        self._lock = threading.Lock()

    def insert_one(self, doc: dict[str, Any]) -> str:
        with self._lock:
            self._docs.append(dict(doc))
            return str(len(self._docs))

    def find(self, query: dict[str, Any] | None = None) -> list[dict[str, Any]]:
        with self._lock:
            q = query or {}
            return [doc for doc in self._docs if all(doc.get(k) == v for k, v in q.items())]

    def find_one(self, query: dict[str, Any]) -> dict[str, Any] | None:
        for doc in self.find(query):
            return doc
        return None

    def update_one(self, query: dict[str, Any], update: dict[str, Any]) -> bool:
        with self._lock:
            for doc in self._docs:
                if all(doc.get(k) == v for k, v in query.items()):
                    if "$set" in update:
                        doc.update(update["$set"])
                    return True
        return False

    def delete_one(self, query: dict[str, Any]) -> bool:
        with self._lock:
            for index, doc in enumerate(self._docs):
                if all(doc.get(k) == v for k, v in query.items()):
                    del self._docs[index]
                    return True
        return False

    def count(self) -> int:
        with self._lock:
            return len(self._docs)


class _InMemoryDatabase:
    def __init__(self) -> None:
        self._collections: dict[str, _InMemoryCollection] = {}

    def __getitem__(self, name: str) -> _InMemoryCollection:
        if name not in self._collections:
            self._collections[name] = _InMemoryCollection()
        return self._collections[name]


class _InMemoryClient:
    def __init__(self) -> None:
        self._databases: dict[str, _InMemoryDatabase] = {}

    def __getitem__(self, name: str) -> _InMemoryDatabase:
        if name not in self._databases:
            self._databases[name] = _InMemoryDatabase()
        return self._databases[name]


# ----- backend selection -------------------------------------------------


class _Backend:
    """Records which backend was selected for the process."""

    def __init__(self) -> None:
        self.kind: str = "in-memory"
        self.mongo_url: str | None = None


_BACKEND_STATE = _Backend()
_BACKEND_LOCK = threading.Lock()
_RESOLVED = False

TRUE_VALUES = {"1", "true", "yes", "on"}


def backend_kind() -> str:
    """Return the active backend: `"mongo"` or `"in-memory"`."""
    return _BACKEND_STATE.kind


def mongo_url() -> str | None:
    """Return the configured `MONGO_URL` if any."""
    return os.environ.get("MONGO_URL")


def require_mongo() -> bool:
    """Return whether startup must fail unless a real MongoDB is available."""
    return os.environ.get("THIRSTY_AI_REQUIRE_MONGO", "").strip().lower() in TRUE_VALUES


def _try_mongo(url: str) -> Any | None:
    """Attempt a real Mongo connection; return the client on success, None on failure."""
    try:
        from pymongo import MongoClient  # type: ignore[import-untyped]
        from pymongo.errors import PyMongoError  # type: ignore[import-untyped]
    except ImportError:
        LOG.warning("MONGO_URL is set but pymongo is not installed; falling back to in-memory stub")
        return None
    try:
        client = MongoClient(url, serverSelectionTimeoutMS=2000)
        # Force a round-trip; pymongo is lazy.
        client.admin.command("ping")
        return client
    except PyMongoError as exc:
        LOG.warning("MongoDB at %s is unreachable (%s); falling back to in-memory stub", url, exc)
        return None
    except Exception as exc:  # noqa: BLE001
        LOG.warning("MongoDB connection error (%s); falling back to in-memory stub", exc)
        return None


def _resolve_client() -> Any:
    """Return the active client. Idempotent across the process lifetime."""
    global _RESOLVED
    with _BACKEND_LOCK:
        if _RESOLVED:
            url = os.environ.get("MONGO_URL")
            if url and _BACKEND_STATE.kind == "mongo":
                # Caller may have changed MONGO_URL between calls; re-pick.
                pass
            return _current_client()
        url = os.environ.get("MONGO_URL")
        must_use_mongo = require_mongo()
        if must_use_mongo and not url:
            raise RuntimeError("THIRSTY_AI_REQUIRE_MONGO=1 requires MONGO_URL")
        if url:
            client = _try_mongo(url)
            if client is not None:
                _BACKEND_STATE.kind = "mongo"
                _BACKEND_STATE.mongo_url = url
                _set_client(client)
                LOG.info("db: using MongoDB at %s", url)
                _RESOLVED = True
                return client
            if must_use_mongo:
                raise RuntimeError("THIRSTY_AI_REQUIRE_MONGO=1 requires a reachable MongoDB")
            LOG.warning("db: MONGO_URL=%s unreachable; using in-memory stub", url)
        _BACKEND_STATE.kind = "in-memory"
        client = _InMemoryClient()
        _set_client(client)
        LOG.info("db: using in-memory stub (no MONGO_URL set, or Mongo unreachable)")
        _RESOLVED = True
        return client


# Single mutable holder so tests can reset between cases.
_CURRENT_CLIENT: Any | None = None


def _set_client(c: Any) -> None:
    global _CURRENT_CLIENT
    _CURRENT_CLIENT = c


def _current_client() -> Any:
    return _CURRENT_CLIENT


def reset_for_test() -> None:
    """Reset the cached client. Test-only."""
    global _RESOLVED
    with _BACKEND_LOCK:
        _RESOLVED = False
        _BACKEND_STATE.kind = "in-memory"
        _BACKEND_STATE.mongo_url = None
        _set_client(None)


def get_client() -> Any:
    """Return a Mongo-compatible client.

    Tries `MONGO_URL` env var. If set AND pymongo is installed AND the
    server responds to `ping`, returns a real `MongoClient`. Otherwise
    returns the in-memory stub. The choice is logged once at INFO.
    """
    return _resolve_client()


def get_database(client: Any) -> Any:
    """Return the named database from the client.

    `client` is accepted as an arg to keep the call signature flexible
    for tests that inject their own client. The default name is
    `thirsty_ai_builder`; override with the `DB_NAME` env var.
    """
    db_name = os.environ.get("DB_NAME", "thirsty_ai_builder")
    return client[db_name]
