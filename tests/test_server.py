import json, os, sys, threading, urllib.request, urllib.error
sys.path.insert(0, "src")

os.environ["DB_PATH"] = ":memory:"
os.environ["APP_API_KEY"] = "test-key-123"

import server
from http.server import ThreadingHTTPServer

def _req(method, path, body=None, key="test-key-123"):
    req = urllib.request.Request("http://127.0.0.1:8765" + path,
        method=method, data=json.dumps(body).encode() if body is not None else None,
        headers={"Content-Type": "application/json", "X-API-Key": key})
    try:
        with urllib.request.urlopen(req) as r:
            return r.status, json.loads(r.read() or b"{}")
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read() or b"{}")

def test_server_api_and_ui():
    srv = ThreadingHTTPServer(("127.0.0.1", 8765), server.Handler)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    try:
        # health is public and states there is no Instagram integration
        with urllib.request.urlopen("http://127.0.0.1:8765/health") as r:
            h = json.loads(r.read())
        assert h["status"] == "ok" and h["instagram_integration"] is False
        # UI loads and says no Instagram login
        with urllib.request.urlopen("http://127.0.0.1:8765/") as r:
            html = r.read().decode()
        assert "No Instagram login" in html
        # auth enforced
        code, _ = _req("GET", "/api/contacts", key="wrong")
        assert code == 401
        # full flow through the API
        code, c = _req("POST", "/api/contacts",
                       {"handle": "api_person", "basis": "known_personally", "adult_confirmed": True})
        assert code == 201
        cid = c["contact_id"]
        code, d = _req("POST", f"/api/contacts/{cid}/draft", {"kind": "intro"})
        assert code == 200 and d["sent"] is False
        msgs = [{"sender": "me", "text": "hi, how was your day?"},
                {"sender": "them", "text": "thank you, please tell me about your day too"},
                {"sender": "them", "text": "honestly I will be honest, the truth matters"},
                {"sender": "them", "text": "no pressure, whenever you're comfortable, your choice"},
                {"sender": "them", "text": "i understand how that feels, how was your day?"},
                {"sender": "them", "text": "i see your point, let's talk about it"}]
        code, _ = _req("POST", f"/api/contacts/{cid}/import", {"messages": msgs})
        assert code == 200
        code, b = _req("GET", f"/api/contacts/{cid}/behaviour")
        assert code == 200 and b["verdict"] == "green_flag"
        code, _ = _req("POST", f"/api/contacts/{cid}/family",
                       {"perspective": "Family should be convinced first."})
        assert code == 200
        code, r = _req("POST", f"/api/contacts/{cid}/evaluate",
                       {"alignment": {"serious_relationship": True, "family_involvement": True,
                                      "marriage_expectations": True, "personal_independence": True,
                                      "handling_disagreements": False}})
        assert code == 200 and r["assessment"] == "promising"
        assert r["notification"]["title"] == "POTENTIAL COMPATIBLE MATCH FOUND"
        code, d2 = _req("DELETE", f"/api/contacts/{cid}")
        assert code == 200 and d2["deleted"] is True
    finally:
        srv.shutdown()
