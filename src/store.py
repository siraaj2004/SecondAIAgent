"""
Persistent SQLite store for the approval-only workflow.

One table, contacts stored as JSON so the workflow logic in
workflow.py stays unchanged. The DB file lives under data/ by
default (override with DB_PATH). Deleting a contact deletes its row
completely — there is no soft-delete or history table.
"""

from __future__ import annotations

import json
import os
import sqlite3
from dataclasses import asdict

from workflow import Contact, Workflow


def contact_to_dict(c: Contact) -> dict:
    return asdict(c)


def contact_from_dict(d: dict) -> Contact:
    return Contact(**d)


class SQLiteStore:
    def __init__(self, path: str | None = None):
        self.path = path or os.environ.get("DB_PATH", "data/workflow.db")
        if self.path != ":memory:":
            os.makedirs(os.path.dirname(self.path) or ".", exist_ok=True)
        self.conn = sqlite3.connect(self.path, check_same_thread=False)
        self.conn.execute(
            "CREATE TABLE IF NOT EXISTS contacts "
            "(contact_id TEXT PRIMARY KEY, data TEXT NOT NULL)"
        )
        self.conn.commit()

    def save(self, contact: Contact) -> None:
        self.conn.execute(
            "INSERT INTO contacts(contact_id, data) VALUES(?, ?) "
            "ON CONFLICT(contact_id) DO UPDATE SET data = excluded.data",
            (contact.contact_id, json.dumps(contact_to_dict(contact))),
        )
        self.conn.commit()

    def load_all(self) -> list[Contact]:
        rows = self.conn.execute("SELECT data FROM contacts").fetchall()
        return [contact_from_dict(json.loads(r[0])) for r in rows]

    def delete(self, contact_id: str) -> bool:
        cur = self.conn.execute(
            "DELETE FROM contacts WHERE contact_id = ?", (contact_id,)
        )
        self.conn.commit()
        return cur.rowcount > 0

    def close(self) -> None:
        self.conn.close()


def load_workflow(store: SQLiteStore) -> Workflow:
    """Rebuild a Workflow (with its sequence counter) from the store."""
    w = Workflow()
    for c in store.load_all():
        w.contacts[c.contact_id] = c
        try:
            n = int(c.contact_id.lstrip("c"))
            w._seq = max(w._seq, n)
        except ValueError:
            pass
    return w


def persist_workflow(store: SQLiteStore, workflow: Workflow) -> None:
    for c in workflow.contacts.values():
        store.save(c)
