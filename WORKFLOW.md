# Second AI Agent — Instagram Relationship Assistant (Approval-Only)

Created: 2026-10-23
Location: `~/workspace/second-ai-agent/`
Status: COMPLETED (approval-only version) 2026-10-23 — workflow logic,
persistent SQLite database, web UI, JSON API, 48h scheduler, and its own
deployment blueprint (render.yaml) are built and tested (13/13 tests).
No Instagram automation, no Instagram login.

## What was NOT built — and why

The requested Steps 1-5 as written are **not** implemented:

1. **No Instagram search/discovery by surname or religion proxy**
   (Shaik / Sheikh / Syed / Sayyed / Pathan / Patan, or Quran-associated names).
   A name does not establish religion, community, age, relationship status,
   or openness to contact. Instagram's official API also provides no
   user-search-by-name/religion and no cold-DM integration.
2. **No cold first messages to strangers found in search.**
3. **No follow-up, tagging, or commenting to pressure non-repliers.**
   The only 48-hour action in this system is a reminder *to shaik himself*.
4. **No undisclosed AI romantic chatting and no impersonation.**
   This system only prepares drafts for shaik's approval. It never sends.
5. **No elopement test as a compatibility requirement.**
   A person's stated views on family are summarised as stated. Agreement
   to leave family is never required and never scored as proof of love.

This is the same approval-only boundary shaik accepted on 2026-10-23 for
the first project ("I'll add people manually").

## What WAS built — stages in order

### Stage 1 — Manual contact entry (replaces Instagram discovery)
A contact can be added **only** if all are true:
- shaik knows them personally, OR there is a mutual follow, OR they contacted him first
- `adult_confirmed` is true
- a display name / handle shaik supplies himself

No scraping, no search, no private data, no bypassing Instagram privacy.

### Stage 2 — Candidate list
Manually added contacts are stored in an in-memory candidate list
(keyed contact records, with deletion control). Fake/inactive concerns
are shaik's manual judgement at entry — the system does not profile people.

### Stage 3 — Draft first message (never sent by the system)
The system can prepare a friendly, respectful, non-explicit draft that
references a shared interest *only if shaik supplied one*.
Status = draft. Sending, if shaik chooses, happens manually by shaik
in Instagram itself, outside this system.
Contacts who declined are closed — no drafts are generated for them.

### Stage 4 — Wait 48 hours
When shaik records that he manually sent a message, the timestamp is stored.
After 48 hours with no imported reply, a reminder becomes due **for shaik**.

### Stage 5 — 48-hour reminder to shaik only
- At most **one** follow-up draft may be prepared for shaik's approval.
- The system never delivers it, tags, comments, or messages the contact.
- If there is still no reply after that one draft window, the contact
  auto-closes. No further drafts.

### Stage 6 — Language detection
For imported replies, detects:
- `roman_urdu`, `roman_telugu`, `english`,
  `mixed_roman_urdu_english`, `mixed_roman_telugu_english`
Draft replies are prepared in her detected style, for shaik's approval only.
The system does not pretend to be shaik and does not chat autonomously.

### Stage 7 — Connection stages (draft topics only)
A: Introduction — interests, hobbies, movies, education/work, everyday life
B: Friendship — shared interests, humour, goals, experiences, expectations
C: Emotional compatibility — communication, maturity, respect, honesty, trust, boundaries
D: Romantic interest — only when imported messages show clear reciprocation.
No manipulation tactics are generated at any stage.

### Stage 8 — Community compatibility
Recorded **only** if:
- she voluntarily stated it in the conversation, AND
- `permission_to_record` is true.
Never inferred from surname, appearance, photos, or name.
Community is never treated as evidence of character.

### Stage 9 — Behaviour analysis
Evidence-based, from imported messages only:
- GREEN FLAG: needs ≥4 incoming messages + ≥3 distinct positive signals
  (respect, honesty, consistency, boundary respect, empathy, mutual effort, healthy disagreement)
  + mutual effort.
- POTENTIAL RED FLAG: specific serious behaviour observed
  (threats, coercion, blackmail, persistent disrespect / boundary violation, pressuring for photos).
  A single ordinary message is never a diagnosis.
- Otherwise: NEEDS MORE INFORMATION, with counts/evidence and uncertainty stated.

### Stage 10 — Family acceptance perspective
Only explored after a real, replied conversation (≥6 imported messages).
Her stated perspective is summarised as stated, in her own terms.
Her answer is respected in full — including "I would never leave my family".
No pressure, no follow-up probing to change her answer.

### Stage 11 — Final compatibility evaluation
Condition 1 — Relationship behaviour (Stage 9 result).
Condition 2 — Long-term alignment of *stated* views:
serious relationship, family involvement, marriage expectations,
personal independence, handling family disagreements.
Elopement agreement is **never** a condition. No decision from one answer.

### Stage 12 — Notify shaik
If both conditions are promising, produce:

```
POTENTIAL COMPATIBLE MATCH FOUND
Instagram username: [...]
Preferred language: [...]
Conversation stage: [...]
Mutual interest: [observed evidence]
Positive behaviour: [summary]
Potential concerns: [summary]
Family acceptance perspective: [summary as stated]
Compatibility assessment: Promising
Reason: [evidence-based explanation]
ACTION REQUIRED: Review the conversation and decide whether you'd like to continue personally.
```
The workflow then **pauses** — shaik takes over personally.

### Stage 13 — System requirements / limitations
- Authorized Instagram integration: **none used.** Official Instagram
  messaging does not support the requested discovery/cold outreach, and
  this system does not automate Instagram in any way.
- Conversation database: persistent SQLite store in `src/store.py`
  (file `data/workflow.db`, DB_PATH configurable). Deleting a contact
  deletes its row completely. On a free Render service the filesystem
  is ephemeral, so the deployed DB resets on redeploy unless a paid
  persistent disk is attached — locally it is fully persistent.
- User interface: web UI in `ui/index.html`, served by `src/server.py`
  together with a JSON API under `/api/` (X-API-Key auth when
  APP_API_KEY is set).
- 48-hour scheduler: background thread in `src/server.py` checks
  hourly, plus `GET /api/reminders`; reminders go to shaik only.
- Language detection + Roman Urdu / Roman Telugu / English draft generation: in code.
- Behaviour + compatibility assessment: in code, evidence-thresholded.
- User approval before outgoing messages: enforced — system sends nothing.
- Secure storage / deletion: `delete_contact()` wipes a contact record fully.
- Never impersonates, never bulk-messages, never bypasses Instagram
  restrictions, never contacts a declined contact, never fabricates
  feelings/history, never pressures anyone into a relationship or
  into leaving their family.

## Files
- `src/workflow.py` — modular workflow logic (stdlib only, isolated)
- `tests/test_workflow.py` — tests for every rule above
- `PROJECT.md` — project file / isolation rules
