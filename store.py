"""
store.py - Thread-safe, JSON-persisted application state.

Seed data (from compliance_db) is read-only and always reflects the shipped
knowledge base. Everything the user (or the surveillance engine) creates at
runtime is persisted separately in DATA_DIR and merged on read, so upgrades
never lose user data and shipped data can still be refreshed.

Files in DATA_DIR:
  alerts_user.json          alerts created by the user / surveillance engine
  alert_state.json          triage state per alert id (status, owner, notes...)
  products_user.json        products added at runtime
  certificates_user.json    certificates added at runtime
  actions.json              action items (tasks) linked to alerts / documents
  last_audit.json           last document-audit report (for Excel export)
  countries_data.json       working copy of the country knowledge base
  surveillance_log.json     tamper-evident surveillance ledger
"""
import datetime as _dt
import hashlib
import json
import threading
import uuid

import config
import compliance_db as db

ALERT_STATUSES = ("New", "Acknowledged", "In Progress", "Closed")
ACTION_STATUSES = ("Open", "In Progress", "Blocked", "Done")


def utc_now_iso():
    return _dt.datetime.now(_dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def today_iso():
    return _dt.date.today().isoformat()


class Store:
    def __init__(self):
        self._lock = threading.RLock()
        config.ensure_data_dir()
        self._alerts_user = config.read_json(config.data_path("alerts_user.json"), []) or []
        self._alert_state = config.read_json(config.data_path("alert_state.json"), {}) or {}
        self._products_user = config.read_json(config.data_path("products_user.json"), []) or []
        self._certs_user = config.read_json(config.data_path("certificates_user.json"), []) or []
        self._actions = config.read_json(config.data_path("actions.json"), []) or []
        self._last_audit = config.read_json(config.data_path("last_audit.json"), {}) or {}
        # Working copy of countries replaces the seed copy loaded by compliance_db
        working = config.read_json(config.data_path("countries_data.json"), None)
        if isinstance(working, dict) and working:
            db.COUNTRIES_DB.clear()
            db.COUNTRIES_DB.update(working)

    # ------------------------------------------------------------------ persistence
    def _save(self, name, payload):
        config.atomic_write_json(config.data_path(name), payload)

    def save_countries(self):
        with self._lock:
            self._save("countries_data.json", db.COUNTRIES_DB)

    # ------------------------------------------------------------------ alerts
    def alerts(self):
        """Merged alert list, newest user/surveillance alerts first, then seed alerts."""
        with self._lock:
            seen = set()
            merged = []
            for a in list(self._alerts_user) + list(db.REGULATION_ALERTS):
                if a.get("id") in seen:
                    continue
                seen.add(a.get("id"))
                merged.append(a)
            return merged

    def get_alert(self, alert_id):
        for a in self.alerts():
            if a.get("id") == alert_id:
                return a
        return None

    def add_alert(self, alert):
        with self._lock:
            if not alert.get("id"):
                alert["id"] = f"ALERT-USR-{uuid.uuid4().hex[:8].upper()}"
            alert.setdefault("created_at", utc_now_iso())
            self._alerts_user = [a for a in self._alerts_user if a.get("id") != alert["id"]]
            self._alerts_user.insert(0, alert)
            self._save("alerts_user.json", self._alerts_user)
            return alert

    def delete_alert(self, alert_id):
        with self._lock:
            before = len(self._alerts_user)
            self._alerts_user = [a for a in self._alerts_user if a.get("id") != alert_id]
            if len(self._alerts_user) != before:
                self._save("alerts_user.json", self._alerts_user)
                return True
            return False

    def alert_state(self, alert_id):
        with self._lock:
            return dict(self._alert_state.get(alert_id, {"status": "New"}))

    def set_alert_state(self, alert_id, **fields):
        with self._lock:
            st = self._alert_state.get(alert_id, {"status": "New"})
            for k, v in fields.items():
                if v is not None:
                    st[k] = v
            if st.get("status") not in ALERT_STATUSES:
                st["status"] = "New"
            st["updated_at"] = utc_now_iso()
            self._alert_state[alert_id] = st
            self._save("alert_state.json", self._alert_state)
            return dict(st)

    def all_alert_states(self):
        with self._lock:
            return dict(self._alert_state)

    # ------------------------------------------------------------------ products / certificates
    def products(self):
        with self._lock:
            return list(db.SAMPLE_PRODUCTS) + list(self._products_user)

    def add_product(self, product):
        with self._lock:
            if not product.get("id"):
                product["id"] = f"PROD-{len(self.products()) + 1:03d}"
            self._products_user.append(product)
            self._save("products_user.json", self._products_user)
            return product

    def certificates(self):
        with self._lock:
            return list(db.SAMPLE_CERTIFICATES) + list(self._certs_user)

    def add_certificate(self, cert):
        with self._lock:
            if not cert.get("id"):
                cert["id"] = f"CERT-{len(self.certificates()) + 1:03d}"
            self._certs_user.append(cert)
            self._save("certificates_user.json", self._certs_user)
            return cert

    # ------------------------------------------------------------------ actions (tasks)
    def actions(self):
        with self._lock:
            return list(self._actions)

    def add_action(self, action):
        with self._lock:
            action["id"] = action.get("id") or f"ACT-{uuid.uuid4().hex[:8].upper()}"
            action.setdefault("status", "Open")
            action.setdefault("created_at", utc_now_iso())
            if action["status"] not in ACTION_STATUSES:
                action["status"] = "Open"
            self._actions.insert(0, action)
            self._save("actions.json", self._actions)
            return action

    def update_action(self, action_id, **fields):
        with self._lock:
            for a in self._actions:
                if a.get("id") == action_id:
                    for k, v in fields.items():
                        if v is not None:
                            a[k] = v
                    if a.get("status") not in ACTION_STATUSES:
                        a["status"] = "Open"
                    a["updated_at"] = utc_now_iso()
                    self._save("actions.json", self._actions)
                    return dict(a)
            return None

    def delete_action(self, action_id):
        with self._lock:
            before = len(self._actions)
            self._actions = [a for a in self._actions if a.get("id") != action_id]
            if len(self._actions) != before:
                self._save("actions.json", self._actions)
                return True
            return False

    # ------------------------------------------------------------------ document audit cache
    def last_audit(self):
        with self._lock:
            return self._last_audit

    def set_last_audit(self, report):
        with self._lock:
            self._last_audit = report or {}
            self._save("last_audit.json", self._last_audit)


# ---------------------------------------------------------------------- tamper-evident ledger
def ledger_hash(entry, prev_hash):
    """SHA-256 over the canonical JSON of an entry (minus its own hash fields) chained to prev_hash."""
    body = {k: v for k, v in entry.items() if k not in ("hash", "prev_hash")}
    raw = json.dumps(body, sort_keys=True, ensure_ascii=False, default=str) + (prev_hash or "GENESIS")
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def verify_ledger(entries):
    """Entries are newest-first. Returns (ok, first_bad_index or None). Legacy entries without hashes are skipped."""
    chain = [e for e in reversed(entries) if e.get("hash")]
    prev = None
    for idx, e in enumerate(chain):
        if e.get("prev_hash") != prev:
            return False, idx
        if ledger_hash(e, e.get("prev_hash")) != e.get("hash"):
            return False, idx
        prev = e["hash"]
    return True, None


_store = None
_store_lock = threading.Lock()


def get_store():
    global _store
    with _store_lock:
        if _store is None:
            _store = Store()
        return _store
