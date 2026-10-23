"""
Second AI Agent — approval-only relationship workflow.

Isolated module: stdlib only, no imports from the first project,
no Instagram automation, no sending of any kind.

Rules enforced here (see WORKFLOW.md):
- Manual contacts only: known personally / mutual follow / contacted him
  first, AND adult confirmed.
- Drafts only. This module never sends a message to anyone.
- Declined = closed immediately, no further drafts.
- 48h reminder goes to the user only, at most one follow-up draft,
  then auto-close if still no reply.
- Community recorded only if volunteered + permission_to_record.
- Behaviour: green flag needs >=4 incoming messages + >=3 positive
  signals + mutual effort; serious patterns flagged; else
  needs-more-information.
- Family perspective summarised as stated; elopement agreement is
  never required or scored.
- Promising compatibility -> notification dict + workflow pauses.
"""

from __future__ import annotations

import re
import time
from dataclasses import dataclass, field

VALID_BASIS = {"known_personally", "mutual_follow", "contacted_me_first"}
FOLLOW_UP_DELAY_SECONDS = 48 * 3600

ROMAN_URDU_WORDS = {
    "aap", "tum", "kya", "hai", "hain", "nahi", "kyun", "kaisa", "kaisi",
    "maine", "mujhe", "tumhe", "aapko", "bohat", "bahut", "acha", "accha",
    "theek", "shukriya", "mein", "mera", "meri", "tumhara", "kahan",
    "kab", "aur", "bhi", "toh", "agar", "lekin", "ghar", "wale",
}
ROMAN_TELUGU_WORDS = {
    "nenu", "nuvvu", "meeru", "enti", "ela", "ekkada", "eppudu", "enduku",
    "naaku", "neeku", "chaala", "bagunna", "bagunnara", "unnava", "chesanu",
    "cheyyali", "intlo", "vallu", "oka", "kani", "leda", "avuthava",
    "ishtam", "prem", "manchi", "rojulu",
}
ENGLISH_WORDS = {
    "the", "you", "are", "how", "what", "when", "where", "why", "hello",
    "hi", "thanks", "thank", "please", "would", "could", "family",
    "think", "feel", "really", "good", "nice", "love",
}

POSITIVE_PATTERNS = {
    "respect": [r"\bthank", r"\bplease\b", r"\brespect\b", r"\bi understand\b"],
    "honesty": [r"\bhonestly\b", r"\btruth\b", r"\bi'?ll be honest\b"],
    "consistency": [r"\bevery day\b", r"\balways reply", r"\bas promised\b"],
    "boundary_respect": [r"\byour choice\b", r"\bno pressure\b", r"\bwhenever you'?re comfortable\b", r"\bi understand if\b"],
    "empathy": [r"\bi understand how\b", r"\bthat must be\b", r"\bi'?m here\b", r"\bsorry to hear\b"],
    "mutual_effort": [r"\bhow was your\b", r"\btell me about\b", r"\bwhat about you\b", r"\byour day\b"],
    "healthy_disagreement": [r"\bi see your point\b", r"\blet'?s talk\b", r"\bi disagree but\b"],
}
SERIOUS_PATTERNS = [
    r"\bi'?ll hurt\b", r"\bthreaten", r"\bblackmail", r"\byou must\b.*\bor else\b",
    r"\bsend (me )?(your )?photo", r"\bsend pics\b", r"\byou have to obey\b",
    r"\bstupid\b.*\byou\b", r"\bshut up\b",
]


def detect_language(text: str) -> str:
    words = re.findall(r"[a-z']+", text.lower())
    if not words:
        return "english"
    urdu = sum(1 for w in words if w in ROMAN_URDU_WORDS)
    telugu = sum(1 for w in words if w in ROMAN_TELUGU_WORDS)
    english = sum(1 for w in words if w in ENGLISH_WORDS)
    if urdu and english and urdu >= 2:
        return "mixed_roman_urdu_english"
    if telugu and english and telugu >= 2:
        return "mixed_roman_telugu_english"
    if urdu >= 2 and urdu >= telugu:
        return "roman_urdu"
    if telugu >= 2:
        return "roman_telugu"
    return "english"


@dataclass
class Contact:
    contact_id: str
    handle: str
    basis: str
    adult_confirmed: bool
    status: str = "active"  # active | declined | closed | paused
    shared_interest: str | None = None
    community_volunteered: str | None = None
    community_permission: bool = False
    messages: list = field(default_factory=list)  # {sender: me|them, text, ts}
    last_outbound_ts: float | None = None
    follow_up_draft_used: bool = False
    family_perspective: str | None = None
    stage: str = "A"

    def incoming(self):
        return [m for m in self.messages if m["sender"] == "them"]

    def outgoing(self):
        return [m for m in self.messages if m["sender"] == "me"]


class Workflow:
    """In-memory, approval-only workflow store. Sends nothing, ever."""

    def __init__(self):
        self.contacts: dict[str, Contact] = {}
        self._seq = 0

    # Stage 1-2: manual entry + candidate list
    def add_contact(self, handle, basis, adult_confirmed, shared_interest=None):
        if basis not in VALID_BASIS:
            raise ValueError(
                "Contact must be known personally, a mutual follow, "
                "or someone who contacted you first. Discovery by "
                "search/surname is not supported."
            )
        if not adult_confirmed:
            raise ValueError("Adult must be confirmed before adding a contact.")
        self._seq += 1
        cid = f"c{self._seq}"
        self.contacts[cid] = Contact(cid, handle, basis, True,
                                     shared_interest=shared_interest)
        return self.contacts[cid]

    def list_contacts(self):
        return list(self.contacts.values())

    def delete_contact(self, contact_id):
        """Full deletion control."""
        return self.contacts.pop(contact_id, None) is not None

    def mark_declined(self, contact_id):
        c = self.contacts[contact_id]
        c.status = "declined"  # closed immediately, no further drafts
        return c

    # Stage 3: draft only
    def draft_message(self, contact_id, kind="intro"):
        c = self.contacts[contact_id]
        if c.status in {"declined", "closed"}:
            raise ValueError("Contact is closed — no drafts may be prepared.")
        if kind == "follow_up" and c.follow_up_draft_used:
            raise ValueError("Only one follow-up draft is allowed.")
        interest = f" I noticed we both like {c.shared_interest}." if c.shared_interest else ""
        draft = f"Hi, hope you're doing well.{interest} Happy to chat if you're comfortable."
        return {"status": "draft_for_user_approval", "text": draft, "sent": False}

    def record_manual_send(self, contact_id, ts=None):
        """User records that THEY sent manually in Instagram. System sends nothing."""
        c = self.contacts[contact_id]
        c.last_outbound_ts = ts if ts is not None else time.time()
        return c

    # Stage 4-5: 48h reminder to the USER only
    def due_reminders(self, now=None):
        now = now if now is not None else time.time()
        due = []
        for c in self.contacts.values():
            if c.status != "active" or c.last_outbound_ts is None:
                continue
            if c.incoming():
                continue
            if now - c.last_outbound_ts >= FOLLOW_UP_DELAY_SECONDS:
                if not c.follow_up_draft_used:
                    due.append({"contact_id": c.contact_id, "handle": c.handle,
                                "reminder_for": "user_only",
                                "follow_up_draft": self.draft_message(c.contact_id, "follow_up")})
                    c.follow_up_draft_used = True
                else:
                    c.status = "closed"  # one follow-up draft, still no reply -> stop
        return due

    # Stage 6-7: import + language
    def import_messages(self, contact_id, messages):
        c = self.contacts[contact_id]
        if c.status == "declined":
            raise ValueError("Contact declined — workflow is closed.")
        c.messages.extend(messages)
        langs = [detect_language(m["text"]) for m in c.incoming()] or ["english"]
        return {"preferred_language": langs[-1], "count": len(c.messages)}

    # Stage 8: community, only volunteered + permission
    def record_community(self, contact_id, community, volunteered, permission_to_record):
        c = self.contacts[contact_id]
        if not (volunteered and permission_to_record):
            return {"recorded": False,
                    "reason": "Community is recorded only if volunteered by her with permission."}
        c.community_volunteered = community
        c.community_permission = True
        return {"recorded": True, "community": community}

    # Stage 9: behaviour analysis
    def analyse_behaviour(self, contact_id):
        c = self.contacts[contact_id]
        incoming = c.incoming()
        texts = " \n".join(m["text"].lower() for m in incoming)
        serious = [p for p in SERIOUS_PATTERNS if re.search(p, texts)]
        signals = {name: any(re.search(p, texts) for p in pats)
                   for name, pats in POSITIVE_PATTERNS.items()}
        found = [k for k, v in signals.items() if v]
        mutual_effort = bool(incoming) and bool(c.outgoing()) and signals.get("mutual_effort", False)
        if serious:
            verdict = "potential_red_flag"
        elif len(incoming) >= 4 and len(found) >= 3 and mutual_effort:
            verdict = "green_flag"
        else:
            verdict = "needs_more_information"
        return {"verdict": verdict, "incoming_count": len(incoming),
                "positive_signals": found, "serious_patterns_found": len(serious),
                "mutual_effort": mutual_effort,
                "note": "Evidence-based only; a single message is never a diagnosis."}

    # Stage 10: family perspective, as stated
    def record_family_perspective(self, contact_id, perspective_text):
        c = self.contacts[contact_id]
        if len(c.messages) < 6:
            raise ValueError("Family perspective is explored only after a real replied conversation (>=6 imported messages).")
        c.family_perspective = perspective_text  # summarised as stated, never scored for elopement
        return {"recorded": True, "perspective_as_stated": perspective_text}

    # Stage 11-12: compatibility + notification + pause
    def evaluate_compatibility(self, contact_id, alignment):
        """
        alignment: dict of stated-view alignment booleans, e.g.
        {serious_relationship, family_involvement, marriage_expectations,
         personal_independence, handling_disagreements}
        Elopement agreement is NOT an accepted key and never required.
        """
        if "elopement" in alignment or "willing_to_leave_family" in alignment:
            raise ValueError("Elopement agreement must not be used as a compatibility condition.")
        c = self.contacts[contact_id]
        behaviour = self.analyse_behaviour(contact_id)
        aligned = sum(1 for v in alignment.values() if v)
        if behaviour["verdict"] == "green_flag" and aligned >= 4:
            assessment = "promising"
        elif behaviour["verdict"] == "potential_red_flag":
            assessment = "not_compatible"
        else:
            assessment = "uncertain"
        result = {"assessment": assessment, "behaviour": behaviour,
                  "aligned_views": aligned}
        if assessment == "promising":
            lang = detect_language(c.incoming()[-1]["text"]) if c.incoming() else "english"
            result["notification"] = {
                "title": "POTENTIAL COMPATIBLE MATCH FOUND",
                "instagram_username": c.handle,
                "preferred_language": lang,
                "conversation_stage": c.stage,
                "mutual_interest": f"{len(c.incoming())} incoming messages, mutual effort: {behaviour['mutual_effort']}",
                "positive_behaviour": ", ".join(behaviour["positive_signals"]),
                "potential_concerns": "none observed" if not behaviour["serious_patterns_found"] else "see behaviour analysis",
                "family_acceptance_perspective": c.family_perspective or "not yet discussed",
                "compatibility_assessment": "Promising",
                "action_required": "A promising connection has developed. Review the conversation and decide whether you'd like to continue personally.",
            }
            c.status = "paused"  # user takes over personally
        return result
