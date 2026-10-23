"""
Second AI Agent — web server (stdlib only, no dependencies).

Serves:
- The web UI at /            (ui/index.html)
- A JSON API at /api/...     (approval-only workflow, drafts only)
- GET /health

There is NO Instagram integration and NO Instagram login anywhere
in this server. Nothing is ever sent to a contact.

Auth: if APP_API_KEY is set in the environment, every /api/ call
must send it as the X-API-Key header. If it is not set (local dev),
the API is open and /health reports auth_configured: false.

Persistence: contacts are stored in SQLite via store.py
(DB_PATH env var, default data/workflow.db) and survive restarts.

48-hour scheduler: a background thread checks hourly for contacts
whose 48h reminder is due and records them in an in-memory outbox
readable at GET /api/reminders. Reminders are for the user only.
"""

from __future__ import annotations

import json
import os
import threading
import time
from dataclasses import asdict
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from store import SQLiteStore, load_workflow, persist_workflow
from workflow import Workflow

ROOT = Path(__file__).resolve().parent.parent
UI_FILE = ROOT / "ui" / "index.html"
APP_API_KEY = os.environ.get("APP_API_KEY", "")

store = SQLiteStore()
workflow: Workflow = load_workflow(store)
reminders_outbox: list = []
_lock = threading.Lock()


def _save():
    persist_workflow(store, workflow)


def check_reminders_once(now=None):
    """48h scheduler step. Reminder goes to the user only."""
    with _lock:
        due = workflow.due_reminders(now=now)
        if due:
            reminders_outbox.extend(due)
            _save()
        return due


def _scheduler_loop():
    while True:
        time.sleep(3600)
        try:
            check_reminders_once()
        except Exception:
            pass


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *args):  # quiet
        pass

    def _json(self, code, obj):
        body = json.dumps(obj).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _auth_ok(self):
        return (not APP_API_KEY) or self.headers.get("X-API-Key") == APP_API_KEY

    def _body(self):
        length = int(self.headers.get("Content-Length") or 0)
        if not length:
            return {}
        try:
            return json.loads(self.rfile.read(length) or b"{}")
        except json.JSONDecodeError:
            return {}

    def _contact(self, cid):
        c = workflow.contacts.get(cid)
        if c is None:
            self._json(404, {"error": "contact not found"})
        return c

    def do_GET(self):
        if self.path == "/health":
            return self._json(200, {"status": "ok",
                                    "auth_configured": bool(APP_API_KEY),
                                    "instagram_integration": False,
                                    "contacts": len(workflow.contacts)})
        if self.path in ("/", "/index.html"):
            data = UI_FILE.read_bytes()
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            return self.wfile.write(data)
        if not self.path.startswith("/api/"):
            return self._json(404, {"error": "not found"})
        if not self._auth_ok():
            return self._json(401, {"error": "Invalid or missing X-API-Key"})
        if self.path == "/api/contacts":
            return self._json(200, [asdict(c) for c in workflow.list_contacts()])
        if self.path == "/api/reminders":
            due = check_reminders_once()
            return self._json(200, {"due_now": due,
                                    "outbox": reminders_outbox})
        if self.path.startswith("/api/contacts/"):
            cid = self.path.split("/")[3]
            parts = self.path.split("/")
            c = self._contact(cid)
            if c is None:
                return
            if len(parts) == 5 and parts[4] == "behaviour":
                return self._json(200, workflow.analyse_behaviour(cid))
            return self._json(200, asdict(c))
        return self._json(404, {"error": "not found"})

    def do_POST(self):
        if not self.path.startswith("/api/"):
            return self._json(404, {"error": "not found"})
        if not self._auth_ok():
            return self._json(401, {"error": "Invalid or missing X-API-Key"})
        data = self._body()
        try:
            with _lock:
                if self.path == "/api/contacts":
                    c = workflow.add_contact(
                        data.get("handle", ""), data.get("basis", ""),
                        bool(data.get("adult_confirmed")),
                        shared_interest=data.get("shared_interest") or None)
                    _save()
                    return self._json(201, asdict(c))
                parts = self.path.split("/")
                if len(parts) < 4:
                    return self._json(404, {"error": "not found"})
                cid = parts[3]
                if self._contact(cid) is None:
                    return
                action = parts[4] if len(parts) > 4 else ""
                if action == "decline":
                    workflow.mark_declined(cid); _save()
                    return self._json(200, asdict(workflow.contacts[cid]))
                if action == "draft":
                    return self._json(200, workflow.draft_message(
                        cid, kind=data.get("kind", "intro")))
                if action == "record-send":
                    workflow.record_manual_send(cid, ts=data.get("ts")); _save()
                    return self._json(200, {"recorded": True})
                if action == "import":
                    r = workflow.import_messages(cid, data.get("messages", []))
                    _save()
                    return self._json(200, r)
                if action == "community":
                    r = workflow.record_community(
                        cid, data.get("community", ""),
                        bool(data.get("volunteered")),
                        bool(data.get("permission_to_record")))
                    _save()
                    return self._json(200, r)
                if action == "family":
                    r = workflow.record_family_perspective(
                        cid, data.get("perspective", ""))
                    _save()
                    return self._json(200, r)
                if action == "evaluate":
                    r = workflow.evaluate_compatibility(
                        cid, data.get("alignment", {}))
                    _save()
                    return self._json(200, r)
                return self._json(404, {"error": "not found"})
        except (ValueError, KeyError) as e:
            return self._json(400, {"error": str(e)})

    def do_DELETE(self):
        if not self.path.startswith("/api/contacts/"):
            return self._json(404, {"error": "not found"})
        if not self._auth_ok():
            return self._json(401, {"error": "Invalid or missing X-API-Key"})
        cid = self.path.split("/")[3]
        with _lock:
            existed = workflow.delete_contact(cid)
            if existed:
                store.delete(cid)
            return self._json(200, {"deleted": existed})


def main():
    port = int(os.environ.get("PORT", "8001"))
    threading.Thread(target=_scheduler_loop, daemon=True).start()
    server = ThreadingHTTPServer(("0.0.0.0", port), Handler)
    print(f"Second AI Agent running on port {port} "
          f"(auth={'on' if APP_API_KEY else 'off'}, no Instagram integration)")
    server.serve_forever()


if __name__ == "__main__":
    main()
