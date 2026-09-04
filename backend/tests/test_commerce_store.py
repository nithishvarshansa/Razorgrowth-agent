import sqlite3
import pytest
from backend.services.analytics_store import AnalyticsStore

def test_action_creation_and_retrieval(tmp_path):
    store=AnalyticsStore(f"sqlite:///./{tmp_path / 'actions.db'}")
    store.create_commerce_action("demo-1","action-1",{"environment":"TEST MODE","demo_data":True,"amount":50000,"currency":"INR"})
    action=store.get_commerce_action("demo-1")
    assert action["action_id"]=="action-1" and action["status"]=="executing"

def test_duplicate_action_is_rejected(tmp_path):
    store=AnalyticsStore(f"sqlite:///./{tmp_path / 'actions.db'}")
    store.create_commerce_action("demo-1","action-1",{})
    with pytest.raises(sqlite3.IntegrityError): store.create_commerce_action("demo-1","action-2",{})
