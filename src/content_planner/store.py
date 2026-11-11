"""Only three tables. Every write uses a fresh snapshot within a short transaction."""
from contextlib import contextmanager
from copy import deepcopy
import json
from pathlib import Path
import sqlite3
import uuid

from .accounting import canonical


def new_id(prefix):
    return f"{prefix}_{uuid.uuid4().hex[:16]}"


def event(snapshot, kind, **data):
    value = {"event_id": f"e{len(snapshot['events']) + 1:04d}", "kind": kind, **data}
    snapshot["events"].append(value)
    return value


class Store:
    def __init__(self, path, timeout=3):
        self.path = str(path)
        if self.path != ":memory:":
            Path(path).parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(self.path, timeout=timeout, isolation_level=None)
        self.conn.row_factory = sqlite3.Row
        self.conn.execute("PRAGMA foreign_keys=ON")
        self.conn.executescript("""
        CREATE TABLE IF NOT EXISTS requests (
          request_id TEXT PRIMARY KEY, request_key TEXT NOT NULL UNIQUE,
          input_hash TEXT NOT NULL, snapshot_json TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS operations (
          operation_key TEXT PRIMARY KEY, request_id TEXT NOT NULL REFERENCES requests(request_id),
          tool TEXT NOT NULL, effective_args_hash TEXT NOT NULL, status TEXT NOT NULL,
          execution_attempt_count INTEGER NOT NULL DEFAULT 0,
          confirmed_result_json TEXT);
        CREATE TABLE IF NOT EXISTS ledger_entries (
          entry_id TEXT PRIMARY KEY, request_id TEXT NOT NULL REFERENCES requests(request_id),
          operation_key TEXT NOT NULL UNIQUE REFERENCES operations(operation_key),
          attempt_id TEXT NOT NULL, tool TEXT NOT NULL, amount_units INTEGER NOT NULL CHECK(amount_units>=0),
          catalog_version TEXT NOT NULL, committed_at TEXT NOT NULL);
        """)

    def close(self):
        self.conn.close()

    @contextmanager
    def transaction(self):
        self.conn.execute("BEGIN IMMEDIATE")
        try:
            yield
            self.conn.execute("COMMIT")
        except BaseException:
            if self.conn.in_transaction:
                self.conn.execute("ROLLBACK")
            raise

    def get(self, request_id):
        row = self.conn.execute("SELECT snapshot_json FROM requests WHERE request_id=?", (request_id,)).fetchone()
        return json.loads(row[0]) if row else None

    def by_key(self, key):
        row = self.conn.execute("SELECT * FROM requests WHERE request_key=?", (key,)).fetchone()
        if not row:
            return None
        return {"input_hash": row["input_hash"], "snapshot": json.loads(row["snapshot_json"])}

    def bind(self, key, input_hash, snapshot):
        # Existing requests are a read path: do not acquire a write transaction.
        existing = self.by_key(key)
        if existing:
            return existing, False
        with self.transaction():
            existing = self.by_key(key)
            if existing:
                return existing, False
            self.conn.execute("INSERT INTO requests VALUES (?,?,?,?)",
                              (snapshot["request_id"], key, input_hash, canonical(snapshot)))
        return {"input_hash": input_hash, "snapshot": deepcopy(snapshot)}, True

    def read_record(self, request_id):
        """Read request + pending-operation identities in one consistent SELECT.

        This does not look up receipts or decide whether an operation committed.
        Keeping STARTED/UNKNOWN unresolved is the purpose of this ordinary read.
        """
        rows = self.conn.execute("""
            SELECT r.snapshot_json, o.operation_key, o.tool, o.status AS operation_status
            FROM requests AS r
            LEFT JOIN operations AS o
              ON o.request_id=r.request_id AND o.status IN ('STARTED','UNKNOWN')
            WHERE r.request_id=?
            ORDER BY o.rowid
        """, (request_id,)).fetchall()
        if not rows:
            return None
        return {"snapshot": json.loads(rows[0]["snapshot_json"]),
                "unconfirmed_operations": [
                    {"operation_key": row["operation_key"], "tool": row["tool"],
                     "status": row["operation_status"]}
                    for row in rows if row["operation_key"] is not None]}

    def put(self, snapshot):
        if not self.conn.in_transaction:
            raise RuntimeError("snapshot writes require a transaction")
        self.conn.execute("UPDATE requests SET snapshot_json=? WHERE request_id=?",
                          (canonical(snapshot), snapshot["request_id"]))

    def update(self, request_id, callback):
        with self.transaction():
            snapshot = self.get(request_id)
            callback(snapshot)
            self.put(snapshot)
        return snapshot

    def operation(self, key):
        row = self.conn.execute("SELECT * FROM operations WHERE operation_key=?", (key,)).fetchone()
        if not row:
            return None
        result = dict(row)
        result["result"] = json.loads(row["confirmed_result_json"]) if row["confirmed_result_json"] else None
        return result

    def ledger(self, request_id):
        return [dict(row) for row in self.conn.execute(
            "SELECT * FROM ledger_entries WHERE request_id=? ORDER BY rowid", (request_id,))]

    def incurred(self, request_id):
        return self.conn.execute("SELECT COALESCE(SUM(amount_units),0) FROM ledger_entries WHERE request_id=?",
                                 (request_id,)).fetchone()[0]

    def unresolved(self, request_id):
        return bool(self.conn.execute(
            "SELECT 1 FROM operations WHERE request_id=? AND status IN ('STARTED','UNKNOWN') LIMIT 1",
            (request_id,)).fetchone())

    def find_plan(self, plan_id):
        # Ordinary explicit read/export, never UNKNOWN reconciliation or resume.
        for row in self.conn.execute("SELECT snapshot_json FROM requests"):
            s = json.loads(row[0])
            if s.get("save_receipt") and s["save_receipt"]["plan_id"] == plan_id:
                return s
        return None

