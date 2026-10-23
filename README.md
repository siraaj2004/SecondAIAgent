# Second AI Agent

A completely separate project from the Relationship AI Keyboard.
Approval-only relationship assistant: manual contacts, drafts only,
nothing is ever sent, and there is **no Instagram login or integration**.

See `PROJECT.md` for project details and `WORKFLOW.md` for the full
workflow rules and limitations.

## Structure

```
second-ai-agent/
  PROJECT.md        # main project file
  README.md
  WORKFLOW.md       # approval-only workflow, stages and limitations
  render.yaml       # its OWN deployment blueprint (service: second-ai-agent)
  .env.example      # APP_API_KEY, PORT, DB_PATH — this project's own config
  .gitignore
  requirements.txt  # stdlib only — no dependencies
  src/
    main.py         # entry point — runs the server
    server.py       # UI + JSON API (stdlib http.server)
    workflow.py     # approval-only workflow logic
    store.py        # persistent SQLite store
  ui/
    index.html      # web UI
  data/             # SQLite DB lives here at runtime (gitignored)
  tests/            # workflow + store + server tests
```

## Run it

```bash
cd ~/workspace/second-ai-agent
APP_API_KEY=choose-your-own-key python3 src/main.py
# then open http://localhost:8001 — health check at /health
```

## Tests

```bash
cd ~/workspace/second-ai-agent
python3 -m pytest tests/ -q   # or run the test functions directly
```

## Deploy (its own service, separate from the first project)

This repo contains a Render blueprint (`render.yaml`) for a free web
service named `second-ai-agent`. On Render: New → Blueprint → pick the
`siraaj2004/SecondAIAgent` repo → set `APP_API_KEY` → Apply.
Note: free Render services have an ephemeral filesystem, so the SQLite
database resets on redeploy/restart of the service unless a paid
persistent disk is attached. Locally, the database is fully persistent.
