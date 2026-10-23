import sys, time
sys.path.insert(0, "src")
from workflow import Workflow, detect_language

def test_manual_only_and_adult_required():
    w = Workflow()
    for bad in [("x", "discovered_by_surname_search", True), ("x", "known_personally", False)]:
        try:
            w.add_contact(*bad); assert False, bad
        except ValueError:
            pass
    c = w.add_contact("someone_i_know", "known_personally", True)
    assert c.status == "active"

def test_language_detection():
    assert detect_language("aap kaisa hain, maine aapko message kiya tha") == "roman_urdu"
    assert detect_language("nuvvu ela unnava, neeku message chesanu") == "roman_telugu"
    assert detect_language("hello, how are you today?") == "english"

def test_declined_closes_no_drafts():
    w = Workflow(); c = w.add_contact("a", "mutual_follow", True)
    w.mark_declined(c.contact_id)
    try:
        w.draft_message(c.contact_id); assert False
    except ValueError:
        pass

def test_drafts_never_sent():
    w = Workflow(); c = w.add_contact("a", "contacted_me_first", True, shared_interest="movies")
    d = w.draft_message(c.contact_id)
    assert d["sent"] is False and d["status"] == "draft_for_user_approval"

def test_48h_reminder_is_user_only_and_one_follow_up_then_close():
    w = Workflow(); c = w.add_contact("a", "known_personally", True)
    t0 = time.time() - 49 * 3600
    w.record_manual_send(c.contact_id, ts=t0)
    due = w.due_reminders(now=time.time())
    assert len(due) == 1 and due[0]["reminder_for"] == "user_only"
    # second check: no more drafts, contact auto-closes
    w.due_reminders(now=time.time())
    assert w.contacts[c.contact_id].status == "closed"

def test_community_only_volunteered_with_permission():
    w = Workflow(); c = w.add_contact("a", "known_personally", True)
    assert w.record_community(c.contact_id, "X", volunteered=False, permission_to_record=True)["recorded"] is False
    assert w.record_community(c.contact_id, "X", volunteered=True, permission_to_record=False)["recorded"] is False
    assert w.record_community(c.contact_id, "X", volunteered=True, permission_to_record=True)["recorded"] is True

def _rich_convo(w):
    c = w.add_contact("a", "known_personally", True)
    w.import_messages(c.contact_id, [
        {"sender": "me", "text": "hi, how was your day?"},
        {"sender": "them", "text": "thank you, please tell me about your day too"},
        {"sender": "them", "text": "honestly I will be honest, the truth matters"},
        {"sender": "them", "text": "no pressure, whenever you're comfortable, your choice"},
        {"sender": "them", "text": "i understand how that feels, how was your day?"},
        {"sender": "them", "text": "i see your point, let's talk about it"},
    ])
    return c

def test_behaviour_needs_enough_evidence():
    w = Workflow(); c = w.add_contact("a", "known_personally", True)
    w.import_messages(c.contact_id, [{"sender": "them", "text": "hi"}])
    assert w.analyse_behaviour(c.contact_id)["verdict"] == "needs_more_information"

def test_behaviour_green_and_compatibility_notification_and_pause():
    w = Workflow(); c = _rich_convo(w)
    assert w.analyse_behaviour(c.contact_id)["verdict"] == "green_flag"
    w.record_family_perspective(c.contact_id, "She said family should be convinced first.")
    r = w.evaluate_compatibility(c.contact_id, {
        "serious_relationship": True, "family_involvement": True,
        "marriage_expectations": True, "personal_independence": True,
        "handling_disagreements": False})
    assert r["assessment"] == "promising"
    assert r["notification"]["title"] == "POTENTIAL COMPATIBLE MATCH FOUND"
    assert w.contacts[c.contact_id].status == "paused"

def test_elopement_never_a_condition():
    w = Workflow(); c = _rich_convo(w)
    try:
        w.evaluate_compatibility(c.contact_id, {"elopement": True}); assert False
    except ValueError:
        pass

def test_delete_wipes_contact():
    w = Workflow(); c = w.add_contact("a", "known_personally", True)
    assert w.delete_contact(c.contact_id) is True
    assert w.list_contacts() == []
