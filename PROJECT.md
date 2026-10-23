# Second AI Agent — Project File

- **Owner:** shaik
- **Created:** 2026-10-23
- **Status:** Approval-only version completed 2026-10-23 — UI, persistent
  SQLite database, JSON API, 48h scheduler, and deployment blueprint
  built and tested (13/13 tests). GitHub repo live; its own Render
  service is the remaining deployment step.
- **Location:** `~/workspace/second-ai-agent/`
- **GitHub:** https://github.com/siraaj2004/SecondAIAgent
- **Isolation:** Logically isolated project. Separate folder, separate code, separate `.env`, separate Git repo and separate deployment for this project only.

## Purpose
Approval-only Instagram relationship assistant (see WORKFLOW.md):
manual contacts only, drafts for shaik's approval only, language
detection (Roman Urdu / Roman Telugu / English), behaviour and
compatibility analysis, and a POTENTIAL COMPATIBLE MATCH FOUND
notification. No Instagram login, no Instagram automation, nothing
is ever sent by the system.

## Not part of this project
- First agent: Relationship AI Keyboard
  - Code: `~/workspace/relationship-ai-keyboard/` — do not edit from this project
  - Repo: `siraaj2004/RelationshipChartSuggestor2`
  - Deployment: `relationship-ai-backend-kozw.onrender.com` — do not reuse for this project

## Rules for this project
1. All new code goes only in `~/workspace/second-ai-agent/`
2. Use its own `.env` (see `.env.example`) — never copy secrets from the first project
3. Use its own ports, GitHub repo, and hosting service
4. Nothing in this folder should import from or depend on the first project

## Next steps
- [x] Define what the agent does — approval-only workflow (WORKFLOW.md)
- [x] Choose stack — Python stdlib only (server, SQLite, no dependencies)
- [x] Web UI + JSON API + persistent database + 48h scheduler
- [x] Create its own GitHub repo — siraaj2004/SecondAIAgent
- [ ] Create its own deployment service — render.yaml blueprint is
      ready in the repo; create the `second-ai-agent` service on Render
      from it and set its own APP_API_KEY
