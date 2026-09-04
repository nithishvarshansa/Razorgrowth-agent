import sqlite3
from datetime import UTC, datetime, timedelta
from pathlib import Path
from uuid import uuid4

from ..models.analytics import NormalizedOrder, NormalizedPayment
from ..config import get_settings

# How recent an unresolved demo run must be to count as "the demo currently in
# progress" and therefore be reused instead of creating a duplicate entry.
# Long enough to cover repeated clicks in a live demo session, short enough that
# a run abandoned in an earlier session never replaces a new one.
DEMO_REUSE_WINDOW = timedelta(minutes=30)


class AnalyticsStore:
    VALID_MEASUREMENT_EVENTS = {
        "recommendation_created",
        "guardrail_evaluated",
        "merchant_approved",
        "merchant_rejected",
        "test_order_created",
        "checkout_started",
        "payment_attempted",
        "payment_verified",
        "payment_failed",
        "payment_cancelled",
    }
    def __init__(self, database_url: str | None = None) -> None:
        value = database_url or get_settings().database_url
        self.path = Path(value.removeprefix("sqlite:///./"))

    def _connection(self) -> sqlite3.Connection:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        connection = sqlite3.connect(self.path)
        connection.row_factory = sqlite3.Row
        connection.executescript("""
            CREATE TABLE IF NOT EXISTS normalized_orders (id TEXT PRIMARY KEY, status TEXT, amount INTEGER, currency TEXT, customer_id TEXT, product_id TEXT, product_name TEXT, created_at INTEGER);
            CREATE TABLE IF NOT EXISTS normalized_payments (id TEXT PRIMARY KEY, order_id TEXT, status TEXT, amount INTEGER, currency TEXT, customer_id TEXT, created_at INTEGER, success INTEGER NOT NULL, failed INTEGER NOT NULL);
            CREATE TABLE IF NOT EXISTS agent_runs (id TEXT PRIMARY KEY, status TEXT NOT NULL, mode TEXT NOT NULL, started_at TEXT NOT NULL, ended_at TEXT NOT NULL, decision TEXT, recommendation_json TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS approval_states (recommendation_id TEXT PRIMARY KEY, status TEXT NOT NULL, decision_json TEXT NOT NULL, updated_at TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS policy_events (id INTEGER PRIMARY KEY AUTOINCREMENT, event_type TEXT NOT NULL, timestamp TEXT NOT NULL, agent_run_id TEXT, recommendation_id TEXT NOT NULL, decision TEXT NOT NULL, reason TEXT);
            CREATE TABLE IF NOT EXISTS commerce_actions (recommendation_id TEXT PRIMARY KEY, action_id TEXT NOT NULL, status TEXT NOT NULL, razorpay_order_id TEXT, payload_json TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS measurement_events (id INTEGER PRIMARY KEY AUTOINCREMENT, event_id TEXT NOT NULL UNIQUE, recommendation_id TEXT NOT NULL, event_type TEXT NOT NULL, timestamp TEXT NOT NULL, mode TEXT NOT NULL, metadata_json TEXT NOT NULL DEFAULT '{}');
        """)
        return connection

    def save(self, orders: list[NormalizedOrder], payments: list[NormalizedPayment]) -> None:
        with self._connection() as connection:
            connection.executemany("INSERT OR REPLACE INTO normalized_orders VALUES (:id,:status,:amount,:currency,:customer_id,:product_id,:product_name,:created_at)", [o.to_dict() for o in orders])
            connection.executemany("INSERT OR REPLACE INTO normalized_payments VALUES (:id,:order_id,:status,:amount,:currency,:customer_id,:created_at,:success,:failed)", [{**p.to_dict(), "success": int(p.success), "failed": int(p.failed)} for p in payments])

    def load(self) -> tuple[list[NormalizedOrder], list[NormalizedPayment]]:
        with self._connection() as connection:
            orders = [NormalizedOrder(**dict(row)) for row in connection.execute("SELECT * FROM normalized_orders")]
            payments = [NormalizedPayment(**{**dict(row), "success": bool(row["success"]), "failed": bool(row["failed"])}) for row in connection.execute("SELECT * FROM normalized_payments")]
        return orders, payments

    def save_agent_run(self, result) -> None:
        import json
        with self._connection() as connection:
            connection.execute("INSERT OR REPLACE INTO agent_runs VALUES (?, ?, ?, ?, ?, ?, ?)", (result.agent_run_id, result.status, result.mode, result.started_at.isoformat(), result.ended_at.isoformat(), result.opportunity_type, json.dumps(result.model_dump(mode="json"))))
        self.record_measurement_event(
            result.agent_run_id,
            "recommendation_created",
            {
                "status": result.status,
                "opportunity_type": result.opportunity_type,
                "recommended_product": result.recommended_product,
                "mode": result.mode,
            },
            mode="demo/test" if str(result.agent_run_id).startswith("demo-") else result.mode,
        )

    def load_agent_runs(self) -> list[dict]:
        import json
        with self._connection() as connection:
            rows = connection.execute("SELECT recommendation_json FROM agent_runs ORDER BY started_at DESC LIMIT 20").fetchall()
        return [json.loads(row["recommendation_json"]) for row in rows]

    def find_agent_run(self, run_id: str) -> dict | None:
        import json
        with self._connection() as connection:
            row = connection.execute("SELECT recommendation_json FROM agent_runs WHERE id=?", (run_id,)).fetchone()
        return json.loads(row["recommendation_json"]) if row else None

    def save_approval_state(self, decision, event_type: str, reason: str | None = None) -> None:
        import json
        now = datetime.now(UTC).isoformat()
        with self._connection() as connection:
            connection.execute("INSERT OR REPLACE INTO approval_states VALUES (?, ?, ?, ?)", (decision.recommendation_id, decision.status, json.dumps(decision.model_dump(mode="json")), now))
            connection.execute("INSERT INTO policy_events (event_type,timestamp,agent_run_id,recommendation_id,decision,reason) VALUES (?,?,?,?,?,?)", (event_type, now, decision.recommendation_id, decision.recommendation_id, decision.decision, reason))
        if event_type in self.VALID_MEASUREMENT_EVENTS:
            self.record_measurement_event(decision.recommendation_id, event_type, {"decision": decision.decision, "status": decision.status, "reason": reason}, mode="demo/test")

    def load_approval_state(self, recommendation_id: str) -> dict | None:
        import json
        with self._connection() as connection:
            row = connection.execute("SELECT decision_json FROM approval_states WHERE recommendation_id=?", (recommendation_id,)).fetchone()
        return json.loads(row["decision_json"]) if row else None

    def create_commerce_action(self, recommendation_id, action_id, payload):
        import json
        with self._connection() as connection:
            connection.execute("INSERT INTO commerce_actions VALUES (?,?,?,?,?)", (recommendation_id, action_id, "executing", None, json.dumps(payload)))

    def record_measurement_event(self, recommendation_id: str, event_type: str, metadata: dict | None = None, mode: str = "demo/test") -> dict:
        if event_type not in self.VALID_MEASUREMENT_EVENTS:
            raise ValueError(f"Unsupported measurement event type: {event_type}")
        normalized_metadata = dict(metadata or {})
        normalized_metadata.setdefault("mode", mode)
        event_id = str(uuid4())
        timestamp = datetime.now(UTC).isoformat()
        with self._connection() as connection:
            connection.execute(
                "INSERT INTO measurement_events (event_id,recommendation_id,event_type,timestamp,mode,metadata_json) VALUES (?,?,?,?,?,?)",
                (event_id, recommendation_id, event_type, timestamp, mode, __import__("json").dumps(normalized_metadata)),
            )
        return {"event_id": event_id, "recommendation_id": recommendation_id, "event_type": event_type, "timestamp": timestamp, "mode": mode, "metadata": normalized_metadata}

    def get_measurement_events(self, recommendation_id: str) -> list[dict]:
        import json
        with self._connection() as connection:
            rows = connection.execute(
                "SELECT event_id, recommendation_id, event_type, timestamp, mode, metadata_json FROM measurement_events WHERE recommendation_id=? ORDER BY timestamp ASC, id ASC",
                (recommendation_id,),
            ).fetchall()
        return [{
            "event_id": row["event_id"],
            "recommendation_id": row["recommendation_id"],
            "event_type": row["event_type"],
            "timestamp": row["timestamp"],
            "mode": row["mode"],
            "metadata": json.loads(row["metadata_json"]),
        } for row in rows]

    def get_measurement_state(self, recommendation_id: str) -> dict:
        events = self.get_measurement_events(recommendation_id)
        status = events[-1]["event_type"] if events else None
        return {
            "recommendation_id": recommendation_id,
            "status": status,
            "mode": events[0]["mode"] if events else "demo/test",
            "events": events,
        }

    def update_commerce_action(self, recommendation_id, status, order_id, payload):
        import json
        with self._connection() as connection:
            connection.execute("UPDATE commerce_actions SET status=?, razorpay_order_id=?, payload_json=? WHERE recommendation_id=?", (status, order_id, json.dumps(payload), recommendation_id))
        if status == "order_created":
            self.record_measurement_event(recommendation_id, "test_order_created", {"razorpay_order_id": order_id, "status": status, "environment": "TEST MODE"}, mode="demo/test")
        elif status == "failed":
            self.record_measurement_event(recommendation_id, "payment_failed", {"razorpay_order_id": order_id, "status": status}, mode="demo/test")
        elif status == "payment_verified":
            self.record_measurement_event(recommendation_id, "payment_verified", {"razorpay_order_id": order_id, "status": status}, mode="demo/test")

    def get_commerce_action(self, recommendation_id):
        import json
        with self._connection() as connection:
            row = connection.execute("SELECT * FROM commerce_actions WHERE recommendation_id=?", (recommendation_id,)).fetchone()
        if not row: return None
        payload = json.loads(row["payload_json"])
        return {**payload, "action_id": row["action_id"], "recommendation_id": row["recommendation_id"], "status": row["status"], "razorpay_order_id": row["razorpay_order_id"]}

    def find_unresolved_demo_run(self) -> dict | None:
        """Most recent *still-current* demo-fixture agent run with no merchant
        decision yet (no approval state, or still 'pending_approval').

        Used only to avoid creating a new, identical Experiment History entry
        every time the demo fixture is re-run while the previous one is still
        awaiting a merchant decision. A run that has been approved, rejected,
        or blocked is resolved and is never returned here.

        The freshness window matters: an unresolved run that was abandoned in an
        earlier session is history, not "the experiment currently in progress",
        so reusing it would silently replace a new demo run with a stale record.
        Only a run from the active demo session is reused.
        """
        import json
        cutoff = (datetime.now(UTC) - DEMO_REUSE_WINDOW).isoformat()
        with self._connection() as connection:
            row = connection.execute(
                "SELECT ar.recommendation_json FROM agent_runs ar "
                "LEFT JOIN approval_states aps ON aps.recommendation_id = ar.id "
                "WHERE ar.id LIKE 'demo-%' AND (aps.status IS NULL OR aps.status = 'pending_approval') "
                "AND ar.started_at >= ? "
                "ORDER BY ar.started_at DESC LIMIT 1",
                (cutoff,),
            ).fetchone()
        return json.loads(row["recommendation_json"]) if row else None

    def get_actioned_opportunities(self) -> set[tuple[str, str, str]]:
        """Opportunities the merchant has already decided on (approved or rejected).

        Used so the next agent run does not recommend the same opportunity again.
        """
        import json
        with self._connection() as connection:
            rows = connection.execute(
                "SELECT ar.recommendation_json FROM agent_runs ar "
                "JOIN approval_states aps ON aps.recommendation_id = ar.id "
                "WHERE aps.status IN ('approved','rejected')"
            ).fetchall()
        actioned = set()
        for row in rows:
            recommendation = json.loads(row["recommendation_json"])
            key = (recommendation.get("customer_id"), recommendation.get("recommended_product"), recommendation.get("opportunity_type"))
            if all(key):
                actioned.add(key)
        return actioned

    def find_commerce_action_by_order(self, order_id):
        import json
        with self._connection() as connection:
            row=connection.execute("SELECT * FROM commerce_actions WHERE razorpay_order_id=?",(order_id,)).fetchone()
        return ({**json.loads(row["payload_json"]),"action_id":row["action_id"],"recommendation_id":row["recommendation_id"],"status":row["status"],"razorpay_order_id":row["razorpay_order_id"]} if row else None)
