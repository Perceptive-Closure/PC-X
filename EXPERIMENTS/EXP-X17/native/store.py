"""Durable, content-addressed evidence for local X17 attempts."""

import hashlib
import json
import sqlite3
import zlib
from pathlib import Path


def canonical_json(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode()


class NativeStore:
    """SQLite writer with bounded transactions and independently readable raw artifacts."""

    def __init__(self, path, batch_size=256):
        if type(batch_size) is not int or batch_size < 1:
            raise ValueError("batch_size must be a positive integer")
        self.path = Path(path)
        self.batch_size = batch_size
        self._pending = 0
        self._db = sqlite3.connect(self.path)
        self._db.execute("PRAGMA foreign_keys = ON")
        self._db.execute("PRAGMA journal_mode = WAL")
        self._db.execute("PRAGMA synchronous = FULL")
        self._db.executescript(
            """
            CREATE TABLE IF NOT EXISTS artifacts (
                digest TEXT PRIMARY KEY,
                body BLOB NOT NULL
            ) WITHOUT ROWID;
            CREATE TABLE IF NOT EXISTS attempts (
                attempt_id TEXT PRIMARY KEY,
                mechanism TEXT NOT NULL CHECK(mechanism IN ('actual','nominal','ordinary')),
                source_digest TEXT NOT NULL REFERENCES artifacts(digest),
                intake_digest TEXT REFERENCES artifacts(digest),
                final_digest TEXT REFERENCES artifacts(digest),
                trace BLOB NOT NULL
            ) WITHOUT ROWID;
            """
        )
        self._artifact_cache = {}

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, traceback):
        try:
            if exc_type is None:
                self.flush()
            else:
                self._db.rollback()
        finally:
            self._db.close()

    def put_artifact(self, body):
        if not isinstance(body, bytes):
            raise TypeError("artifact body must be bytes")
        digest = hashlib.sha256(body).hexdigest()
        if digest not in self._artifact_cache:
            self._db.execute("INSERT OR IGNORE INTO artifacts VALUES (?, ?)", (digest, body))
            if len(self._artifact_cache) == 128:
                self._artifact_cache.clear()
            self._artifact_cache[digest] = body
        return digest

    def write_attempt(self, attempt_id, mechanism, source_digest, intake_digest, final_digest, trace):
        encoded = zlib.compress(canonical_json(trace), level=1)
        self._db.execute(
            "INSERT INTO attempts VALUES (?, ?, ?, ?, ?, ?)",
            (attempt_id, mechanism, source_digest, intake_digest, final_digest, encoded),
        )
        self._pending += 1
        if self._pending >= self.batch_size:
            self.flush()

    def flush(self):
        self._db.commit()
        self._pending = 0

    def read_artifact(self, digest):
        row = self._db.execute("SELECT body FROM artifacts WHERE digest = ?", (digest,)).fetchone()
        if row is None:
            raise KeyError(digest)
        body = row[0]
        if hashlib.sha256(body).hexdigest() != digest:
            raise ValueError("inventory artifact digest mismatch")
        return body

    @staticmethod
    def _decode(row):
        attempt_id, mechanism, source_digest, intake_digest, final_digest, trace = row
        return {
            "attempt_id": attempt_id,
            "mechanism": mechanism,
            "source_digest": source_digest,
            "intake_digest": intake_digest,
            "final_digest": final_digest,
            "trace": json.loads(zlib.decompress(trace)),
        }

    def read_attempt(self, attempt_id):
        row = self._db.execute("SELECT * FROM attempts WHERE attempt_id = ?", (attempt_id,)).fetchone()
        if row is None:
            raise KeyError(attempt_id)
        return self._decode(row)

    def iter_attempts(self):
        for row in self._db.execute("SELECT * FROM attempts ORDER BY attempt_id"):
            yield self._decode(row)
