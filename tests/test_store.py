import sys
sys.path.insert(0, "src")
from store import SQLiteStore, load_workflow, persist_workflow
from workflow import Workflow

def test_sqlite_persistence_roundtrip():
    store = SQLiteStore(":memory:")
    w = Workflow()
    c = w.add_contact("persisted_person", "known_personally", True, shared_interest="music")
    w.import_messages(c.contact_id, [{"sender": "them", "text": "hello, how are you?"}])
    persist_workflow(store, w)
    w2 = load_workflow(store)
    assert len(w2.list_contacts()) == 1
    c2 = w2.list_contacts()[0]
    assert c2.handle == "persisted_person"
    assert c2.messages[0]["text"] == "hello, how are you?"
    # sequence continues, no id collision after reload
    c3 = w2.add_contact("second_person", "mutual_follow", True)
    assert c3.contact_id != c.contact_id

def test_sqlite_delete_wipes():
    store = SQLiteStore(":memory:")
    w = Workflow()
    c = w.add_contact("to_delete", "contacted_me_first", True)
    persist_workflow(store, w)
    assert store.delete(c.contact_id) is True
    assert load_workflow(store).list_contacts() == []
