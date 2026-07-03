"""MongoDB wrapper for the ThirstyAi Builder.

Production: connects to a real MongoDB via pymongo / motor. Dev: an
in-memory dict-backed stub so the API surface is exercisable without a
Mongo instance. The stub persists for the process lifetime; tests
construct a fresh stub per test.
"""
from __future__ import annotations

import os
import threading
from typing import Any


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


def get_client() -> Any:
    """Return a Mongo-compatible client.

    Tries `MONGO_URL` env var; if set, attempts a real pymongo connection.
    Falls back to the in-memory client otherwise. The fallback ensures
    the API surface is exercisable in dev and CI without a Mongo instance.
    """
    mongo_url = os.environ.get("MONGO_URL")
    if mongo_url:
        try:
            import pymongo  # type: ignore[import-untyped]

            return pymongo.MongoClient(mongo_url)
        except ImportError:
            pass
    return _InMemoryClient()


def get_database(client: Any) -> Any:
    db_name = os.environ.get("DB_NAME", "thirsty_ai_builder")
    return client[db_name]
