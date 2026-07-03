"""Tests for the DB layer: in-memory + the Mongo selection logic."""
from __future__ import annotations

import os
import sys
import unittest
from pathlib import Path
from unittest import mock

# Make the backend package importable.
_BACKEND = Path(__file__).resolve().parents[1]
if str(_BACKEND) not in sys.path:
    sys.path.insert(0, str(_BACKEND))

from thirsty_ai_builder_backend import db  # noqa: E402


class InMemoryBackend(unittest.TestCase):
    def setUp(self):
        db.reset_for_test()

    def test_default_backend_is_in_memory(self):
        c = db.get_client()
        self.assertEqual(db.backend_kind(), "in-memory")
        d = db.get_database(c)
        coll = d["smoke"]
        coll.insert_one({"id": "1", "value": "a"})
        coll.insert_one({"id": "2", "value": "b"})
        self.assertEqual(coll.count(), 2)
        self.assertEqual(coll.find_one({"id": "1"})["value"], "a")
        self.assertEqual(coll.find({}), [{"id": "1", "value": "a"}, {"id": "2", "value": "b"}])
        coll.update_one({"id": "1"}, {"$set": {"value": "A"}})
        self.assertEqual(coll.find_one({"id": "1"})["value"], "A")
        self.assertTrue(coll.delete_one({"id": "2"}))
        self.assertEqual(coll.count(), 1)
        self.assertIsNone(coll.find_one({"id": "2"}))


class MongoSelection(unittest.TestCase):
    def setUp(self):
        db.reset_for_test()

    def test_mongo_url_with_pymongo_success(self):
        """When MONGO_URL is set and pymongo's ping succeeds, return a real client."""
        class _FakeCollection:
            def __init__(self): self.docs = []
            def insert_one(self, doc): self.docs.append(dict(doc)); return str(len(self.docs))
        class _FakeDB:
            def __init__(self): self.c = _FakeCollection()
            def __getitem__(self, name): return self.c
        class _FakeAdmin:
            def command(self, name): return {"ok": 1.0}
        class _FakeClient:
            def __init__(self, url, **kwargs):
                self.url = url
                self.kwargs = kwargs
                self.admin = _FakeAdmin()
            def __getitem__(self, name): return _FakeDB()

        class _PyMongoError(Exception):
            pass

        fake_pymongo = mock.MagicMock()
        fake_pymongo.MongoClient = _FakeClient
        fake_pymongo.errors.PyMongoError = _PyMongoError

        with mock.patch.dict(os.environ, {"MONGO_URL": "mongodb://fake-host:27017"}):
            with mock.patch.dict(
                sys.modules,
                {"pymongo": fake_pymongo, "pymongo.errors": fake_pymongo.errors},
            ):
                db.reset_for_test()
                c = db.get_client()
                self.assertEqual(db.backend_kind(), "mongo")
                self.assertIsInstance(c, _FakeClient)
                self.assertEqual(c.url, "mongodb://fake-host:27017")

    def test_mongo_url_unreachable_falls_back_to_in_memory(self):
        """When MONGO_URL is set but ping fails, fall back to in-memory and log a warning."""
        class _PyMongoError(Exception):
            pass

        class _FakeClient:
            def __init__(self, url, **kwargs):
                self.url = url
            def __getitem__(self, name): return mock.MagicMock()
            @property
            def admin(self):
                raise _PyMongoError("connection refused")

        fake_pymongo = mock.MagicMock()
        fake_pymongo.MongoClient = _FakeClient
        fake_pymongo.errors.PyMongoError = _PyMongoError

        with mock.patch.dict(os.environ, {"MONGO_URL": "mongodb://nope:27017"}):
            with mock.patch.dict(
                sys.modules,
                {"pymongo": fake_pymongo, "pymongo.errors": fake_pymongo.errors},
            ):
                db.reset_for_test()
                c = db.get_client()
                self.assertEqual(db.backend_kind(), "in-memory")

    def test_mongo_url_set_but_pymongo_missing_falls_back(self):
        """If MONGO_URL is set but pymongo isn't installed, fall back gracefully."""
        with mock.patch.dict(os.environ, {"MONGO_URL": "mongodb://nope:27017"}):
            with mock.patch.dict(sys.modules, {"pymongo": None}):
                db.reset_for_test()
                c = db.get_client()
                self.assertEqual(db.backend_kind(), "in-memory")

    def test_idempotent_resolution(self):
        """Calling get_client() multiple times returns the same backend."""
        c1 = db.get_client()
        c2 = db.get_client()
        self.assertIs(c1, c2)
        self.assertEqual(db.backend_kind(), "in-memory")

    def test_reset_for_test_clears_cache(self):
        """reset_for_test() allows tests to switch backends mid-run."""
        c1 = db.get_client()
        self.assertIsInstance(c1, db._InMemoryClient)
        db.reset_for_test()
        c2 = db.get_client()
        self.assertIsNotNone(c2)


class DatabaseName(unittest.TestCase):
    def test_default_db_name(self):
        c = db.get_client()
        d = db.get_database(c)
        # The in-memory client exposes `client[name]` -> _InMemoryDatabase.
        self.assertIsInstance(d, db._InMemoryDatabase)

    def test_custom_db_name_via_env(self):
        with mock.patch.dict(os.environ, {"DB_NAME": "custom_test_db"}):
            c = db.get_client()
            d = db.get_database(c)
            # The custom name should work and be independent of the default.
            d["smoke"].insert_one({"id": "1"})
            self.assertEqual(d["smoke"].count(), 1)


if __name__ == "__main__":
    raise SystemExit(unittest.main())
