"""
reg_surveillance.py - Autonomous Regulatory Surveillance Engine (v2)

Watches global / regional regulatory gateways (WTO TBT ePing, US Federal Register,
EUR-Lex, BIS, RRA, BSMI, SAMR, GSO, ARSO, ...) for storage-relevant notices,
turns them into structured events, records them in a tamper-evident ledger and
applies them to the working copy of the country knowledge base as *transitions*
(the current mandatory standard stays valid until the notice's deadline; the
incoming standard is recorded alongside it). Every applied event also produces
a fully enriched regulation alert with resolved product impacts.

v2 fixes versus v1:
  * never writes into the read-only bundle directory (uses config.DATA_DIR)
  * does not overwrite a country's current standard with free text - records a
    transition (from -> to, deadline, source) instead
  * deterministic event ids (content hash) so re-scans never duplicate events
  * SHA-256 hash-chained ledger entries (verify with store.verify_ledger)
  * pillar detection understands Cyber / Environmental / EMC / Safety properly
  * real parsers for JSON (Federal Register) and RSS/Atom (EUR-Lex) feeds
  * thread-safe file access and atomic writes
"""
import datetime as _dt
import hashlib
import json
import os
import re
import threading
import time
import urllib.error
import urllib.request
import xml.etree.ElementTree as ET

import config
import store as store_module
from surveillance_data import STORAGE_RELEVANCE_KEYWORDS, GLOBAL_MONITORED_SOURCES, AUTO_SIMULATED_SCENARIOS

EU_COUNTRIES = {"AT", "BE", "BG", "HR", "CY", "CZ", "DK", "EE", "FI", "FR", "DE", "GR", "HU", "IE", "IT", "LV", "LT",
                "LU", "MT", "NL", "PL", "PT", "RO", "SK", "SI", "ES", "SE"}
EEA_EXTRA = {"IS", "NO", "LI", "CH", "GB"}
REGION_MARKETS = {
    "AMERICAS": {"US", "CA", "MX", "BR", "AR", "CL", "CO", "PE"},
    "ASIA": {"JP", "KR", "TW", "CN", "IN", "AU", "SG", "MY", "TH", "VN", "ID", "NZ", "PH", "HK"},
    "APAC": {"JP", "KR", "TW", "CN", "IN", "AU", "SG", "MY", "TH", "VN", "ID", "NZ", "PH", "HK"},
    "MIDDLE EAST": {"SA", "AE", "IL", "EG", "QA", "KW", "OM", "BH", "TR"},
    "MENA": {"SA", "AE", "IL", "EG", "QA", "KW", "OM", "BH", "TR", "MA", "DZ", "TN"},
    "AFRICA": {"ZA", "NG", "KE", "EG", "GH", "MA", "TZ"},
    "EUROPE": EU_COUNTRIES | EEA_EXTRA,
    "EURASIA": EU_COUNTRIES | EEA_EXTRA | {"RU", "BY", "KZ", "AM", "KG", "UA", "TR", "RS"},
}
PILLARS = ("Safety", "EMC", "Environmental", "Cyber", "All")
PILLAR_FIELD = {"Safety": "safety_std", "EMC": "emc_std", "Environmental": "env_std", "Cyber": "cyber_std"}

_now = lambda: _dt.datetime.now(_dt.timezone.utc)


def utc_iso():
    return _now().strftime("%Y-%m-%dT%H:%M:%SZ")


def today_iso():
    return _dt.date.today().isoformat()


# ---------------------------------------------------------------------------- shared helpers
def infer_pillar(alert_or_text):
    """Classify an alert/text into Safety | EMC | Environmental | Cyber | All."""
    if isinstance(alert_or_text, dict):
        if alert_or_text.get("pillar") in PILLARS:
            return alert_or_text["pillar"]
        text = " ".join(str(alert_or_text.get(k, "")) for k in ("title", "standard", "summary", "technical_impact"))
    else:
        text = str(alert_or_text or "")
    t = text.lower()
    scores = {
        "Cyber": sum(w in t for w in ("cyber", "resilience act", "2024/2847", "psti", "sbom", "firmware", "vulnerab", "en 18031", "encryption", "fips")),
        "Environmental": sum(w in t for w in ("rohs", "reach svhc", "reach regulation", "1907/2006", "under reach", "pfas", "tsca", "packaging", "weee", "e-waste", "prop 65", "recycl", "substance", "chemical", "triman", "epr", "ppwr", "plastic", "116/2020", "phthalate")),
        "EMC": sum(w in t for w in ("emc", "cispr", "part 15", "kn 32", "kn 35", "vcci", "cns 15936", "emission", "immunity", "radiated", "radio", "esd", "55032", "9254")),
        "Safety": sum(w in t for w in ("safety", "62368", "60950", "lvd", "electric", "power adapter", "selv", "thermal", "shock", "fire", "13252", "gb 4943", "pse", "ccc", "touch temperature")),
    }
    best = max(scores, key=scores.get)
    if scores[best] == 0:
        return "Safety"
    top = sorted(scores.values(), reverse=True)
    if top[0] > 0 and top[1] > 0 and top[0] - top[1] <= 1 and scores["Cyber"] != top[0]:
        # genuinely multi-pillar notice
        if sum(1 for v in scores.values() if v > 0) >= 3:
            return "All"
    return best


def _alert_country_codes(alert, countries_db):
    """Resolve the set of ISO codes an alert applies to."""
    cc = str(alert.get("country_code") or "").upper().strip()
    country = str(alert.get("country") or "")
    region = str(alert.get("region") or "")
    cl = country.lower()
    if cc in ("ALL", "GLOBAL", "WORLDWIDE") or cl.startswith("all 205") or "global" in cl and "jurisdiction" in cl:
        return set(countries_db.keys())
    if cc and cc in countries_db:
        return {cc}
    if cc == "EU" or "european union" in cl or "eu 27" in cl:
        return set(c for c in EU_COUNTRIES if c in countries_db)
    if "iecee" in cl or "cb scheme" in cl:
        return {c for c, v in countries_db.items() if v.get("cb_scheme_accepted")}
    codes = set()
    for code, c in countries_db.items():
        name = c.get("name", "").lower()
        if name and (name == cl or cl.startswith(name + " ") or cl.startswith(name + "(") or f" {name}" in f" {cl}"):
            codes.add(code)
    if codes:
        return codes
    if region.lower() in ("global", "worldwide", "international", "all"):
        return set(countries_db.keys())
    rl = region.lower()
    if rl:
        return {code for code, c in countries_db.items() if c.get("region", "").lower() in rl or rl in c.get("region", "").lower()}
    return set()


def alert_matches_country(alert, country):
    import compliance_db as db
    return country.get("code") in _alert_country_codes(alert, db.COUNTRIES_DB)


def resolve_product_impacts(affected_categories, country_code="Global", region="Global", products=None):
    """Which portfolio products are hit by a notice (category x target-market intersection)."""
    if products is None:
        try:
            import compliance_db as cdb
            products = getattr(cdb, "SAMPLE_PRODUCTS", [])
        except Exception:
            products = []
    cats = affected_categories or []
    is_universal = any(c in ("all", "all_storage_categories", "all_categories") for c in cats)
    cc = (country_code or "GLOBAL").upper()
    reg = (region or "GLOBAL").upper()
    impacted = []
    for p in products:
        if not (is_universal or p.get("category_id") in cats):
            continue
        targets = {m.upper() for m in p.get("target_markets", [])}
        label = None
        if cc in ("GLOBAL", "ALL", "INTERNATIONAL", "WORLDWIDE"):
            label = "Global markets"
        elif cc in targets:
            label = f"Target market: {cc}"
        elif cc == "EU" and targets & EU_COUNTRIES:
            label = "European Union"
        else:
            for key, markets in REGION_MARKETS.items():
                if key in reg and targets & markets:
                    label = f"{key.title()} region"
                    break
            if label is None and reg not in ("GLOBAL", "") and any(reg in (m or "").upper() for m in targets):
                label = reg.title()
        if label:
            impacted.append({
                "id": p.get("id"), "sku": p.get("sku"), "name": p.get("name"), "category_id": p.get("category_id"),
                "category_name": p.get("category_name"), "hw_revision": p.get("hw_revision"), "controller": p.get("controller"),
                "power_source": p.get("power_source"), "market_label": label, "compliance_status": p.get("compliance_status", "Certified"),
            })
    return impacted


STRONG_TERMS = ("solid state", "ssd", "flash memory", "memory card", "microsd", "sd card", "usb drive", "flash drive",
                "storage device", "card reader", "nvme", "62368", "60950", "cispr 32", "part 15", "rohs", "pfas", "tsca",
                "per- and polyfluoroalkyl", "recognized testing laborator", "equipment authorization", "unintentional radiator",
                "information technology equipment", "hazardous substances", "e-waste", "weee", "reach svhc", "1907/2006", "cyber resilience",
                "product security", "declaration of conformity", "ecodesign", "packaging", "13252", "gb 4943", "cns 15")
WEAK_TERMS = ("electronic", "electrical", "electromagnetic", "radio frequency device", "low voltage", "safety standard",
              "consumer product", "chemical", "substance", "recycl", "import", "conformity", "certification", "labelling", "labeling")
NOISE_TERMS = ("emergency alert", "spectrum", "band)", "ghz band", "broadcast", "satellite", "licens", "auction", "telephone",
               "robocall", "911", "patent", "pesticide", "drinking water", "fuel", "vehicle", "aircraft", "medical device",
               "tobacco", "food", "drug", "toy", "battery", "batteries")


def relevance_score(text):
    """Storage/ITE relevance: strong terms count 2, weak terms 1, obvious off-topic notices are penalised."""
    t = (text or "").lower()
    score = sum(2 for k in STRONG_TERMS if k in t) + sum(1 for k in WEAK_TERMS if k in t)
    if any(n in t for n in NOISE_TERMS) and not any(k in t for k in STRONG_TERMS[:14]):
        score -= 4
    return score


def _slug(s):
    return re.sub(r"[^a-z0-9]+", "-", str(s).lower()).strip("-")[:40]


def _event_id(prefix, *parts):
    h = hashlib.sha1("|".join(str(p) for p in parts).encode("utf-8", "ignore")).hexdigest()[:10].upper()
    return f"{prefix}-{h}"


# ---------------------------------------------------------------------------- engine
class RegulatorySurveillanceEngine:
    def __init__(self, compliance_db_module=None, store=None):
        self.db = compliance_db_module
        self.store = store
        self.log_file = config.data_path("surveillance_log.json")
        self.last_scan_time = None
        self.last_scan_status = "Idle - no scan run in this session yet"
        self.last_scan_result = None
        self.active_sources = GLOBAL_MONITORED_SOURCES
        self.scenario_index = 0
        self._lock = threading.RLock()
        config.ensure_data_dir()
        self._ensure_log_initialized()

    # ------------------------------------------------------------------ ledger
    def _read_log(self):
        data = config.read_json(self.log_file, [])
        return data if isinstance(data, list) else []

    def _write_log(self, entries):
        config.atomic_write_json(self.log_file, entries)

    def _ensure_log_initialized(self):
        with self._lock:
            if os.path.exists(self.log_file) and self._read_log():
                return
            baseline = [
                {
                    "event_id": "SURV-BASE-0001", "timestamp": "2026-09-10T10:30:00Z", "country_code": "IN", "country_name": "India",
                    "authority": "Bureau of Indian Standards (BIS) / MeitY", "pillar": "Safety", "source_id": "SRC-IN-BIS",
                    "source_name": "India MeitY Gazette Circular No. 2026-11", "source_url": "https://www.crsbis.in/BIS/",
                    "old_standard": "IS 13252 (Part 1):2010 (IEC 60950-1)", "new_standard": "IS/IEC 62368-1:2023",
                    "effective_date": "2026-09-10", "withdrawal_deadline": "2028-11-01",
                    "affected_categories": ["external_ssd_powered", "internal_ssd", "external_ssd_bus"],
                    "event_type": "Safety Standard Transition", "severity": "Critical",
                    "summary": "BIS CRS migration from IS 13252 (IEC 60950-1) to IS/IEC 62368-1:2023 with in-country NABL testing; concurrent running until 1 Nov 2028.",
                    "status": "Recorded", "confidence_score": 0.98,
                },
                {
                    "event_id": "SURV-BASE-0002", "timestamp": "2026-09-05T14:15:00Z", "country_code": "KR", "country_name": "South Korea",
                    "authority": "National Radio Research Agency (RRA) / KATS", "pillar": "EMC", "source_id": "SRC-KR-RRA",
                    "source_name": "RRA Notification No. 2026-45", "source_url": "https://www.rra.go.kr/en/",
                    "old_standard": "KN 32/35 generic document", "new_standard": "KC Conformity Registration (KS C 9832/9835)",
                    "effective_date": "2026-01-01", "withdrawal_deadline": "Permanent",
                    "affected_categories": ["external_ssd_bus", "usb_drive", "card_reader", "sd_express"],
                    "event_type": "EMC Enforcement Clarification", "severity": "Warning",
                    "summary": "Clarification of the SELV Class III exemption for bus-powered flash drives and mandatory RRA KC Conformity Registration for high-speed ITE under KN 32/35.",
                    "status": "Recorded", "confidence_score": 0.98,
                },
                {
                    "event_id": "SURV-BASE-0003", "timestamp": "2026-09-08T09:00:00Z", "country_code": "EU", "country_name": "European Union",
                    "authority": "European Chemicals Agency (ECHA) / European Commission", "pillar": "Environmental", "source_id": "SRC-EU-EURLEX",
                    "source_name": "Official Journal of the European Union L series", "source_url": "https://eur-lex.europa.eu",
                    "old_standard": "EU RoHS 2011/65/EU", "new_standard": "EU RoHS 2011/65/EU + PFAS / phthalates restriction",
                    "effective_date": "2026-07-01", "withdrawal_deadline": "2027-06-30",
                    "affected_categories": ["all_storage_categories"], "event_type": "Environmental Hazardous Substances Restriction",
                    "severity": "Critical",
                    "summary": "Universal restriction on per- and polyfluoroalkyl substances (PFAS) in semiconductor packaging and packaging recyclability labelling.",
                    "status": "Recorded", "confidence_score": 0.97,
                },
            ]
            chained = []
            prev = None
            baseline.sort(key=lambda x: x["timestamp"])
            for e in baseline:  # oldest first for chaining
                e["prev_hash"] = prev
                e["hash"] = store_module.ledger_hash(e, prev)
                prev = e["hash"]
                chained.append(e)
            chained.reverse()  # newest first on disk
            self._write_log(chained)

    def _append_to_audit_log(self, event):
        with self._lock:
            log = self._read_log()
            if any(x.get("event_id") == event.get("event_id") for x in log):
                return False
            prev = log[0].get("hash") if log else None
            event["prev_hash"] = prev
            event["hash"] = store_module.ledger_hash(event, prev)
            log.insert(0, event)
            self._write_log(log)
            return True

    def get_audit_log(self, limit=50):
        """Newest first. File order *is* chain order (new entries are inserted at the front)."""
        with self._lock:
            log = self._read_log()
        return log[:limit]

    def verify(self):
        return store_module.verify_ledger(self.get_audit_log(limit=10 ** 6))

    # ------------------------------------------------------------------ status
    def get_status(self, light=False):
        log = self.get_audit_log(limit=10 ** 6)
        ok, _ = store_module.verify_ledger(log)
        status = {
            "engine_state": "ACTIVE_LISTENING",
            "last_scan_time": self.last_scan_time,
            "last_scan_status": self.last_scan_status,
            "monitored_sources_count": len(self.active_sources),
            "total_jurisdictions_covered": 205,
            "pillars_monitored": ["Electrical Safety", "EMC & Radio", "Environmental & Chemical", "Cybersecurity"],
            "auto_applied_events_count": len(log),
            "ledger_ok": ok,
            "latest_event": log[0] if log else None,
        }
        if not light:
            status["monitored_sources"] = self.active_sources
            status["last_scan_result"] = self.last_scan_result
        return status

    # ------------------------------------------------------------------ network
    def _fetch_url_safe(self, url, timeout=4):
        if not url:
            return None
        req = urllib.request.Request(url, headers={"User-Agent": "GCM-Platform-Surveillance/2.0 (+compliance intelligence)", "Accept": "*/*"})
        try:
            with urllib.request.urlopen(req, timeout=timeout) as response:
                return response.read(2_000_000).decode("utf-8", errors="ignore")
        except (urllib.error.URLError, urllib.error.HTTPError, OSError, ValueError):
            return None

    def scan_all_sources(self, max_new_events=3):
        started = time.time()
        scan_ts = utc_iso()
        detected, reachable, unreachable = [], [], []
        for source in self.active_sources:
            content = self._fetch_url_safe(source.get("endpoint") or source.get("url"))
            if content is None:
                unreachable.append(source["id"])
                continue
            reachable.append(source["id"])
            try:
                detected.extend(self._parse_source_content(source, content))
            except Exception as e:  # parser must never break a scan
                print(f"[Surveillance] parse error {source['id']}: {e}")

        existing = {e.get("event_id") for e in self.get_audit_log(limit=10 ** 6)}
        applied = []
        for ev in detected:
            if ev["event_id"] in existing or len(applied) >= max_new_events:
                continue
            self._apply_event(ev, create_alert=True)
            applied.append(ev)

        self.last_scan_time = scan_ts
        network = "online" if reachable else "offline / corporate proxy"
        self.last_scan_status = (f"Completed {scan_ts}: {len(reachable)}/{len(self.active_sources)} gateways reachable ({network}); "
                                 f"{len(detected)} storage-relevant notices found, {len(applied)} new event(s) ingested.")
        self.last_scan_result = {
            "scan_timestamp": scan_ts, "duration_s": round(time.time() - started, 1), "network_reachable": bool(reachable),
            "sources_reachable": reachable, "sources_unreachable": unreachable, "sources_scanned": len(self.active_sources),
            "notices_detected": len(detected), "newly_applied_count": len(applied),
            "new_events": [{"event_id": e["event_id"], "summary": e.get("summary"), "pillar": e.get("pillar"), "source_name": e.get("source_name")} for e in applied],
            "status": self.last_scan_status, "total_surveilled_events": len(self.get_audit_log(limit=10 ** 6)),
        }
        return self.last_scan_result

    # ------------------------------------------------------------------ parsing
    def _parse_source_content(self, source, content):
        items = []
        stripped = content.lstrip()
        if stripped.startswith("{") or stripped.startswith("["):
            try:
                data = json.loads(stripped)
            except ValueError:
                data = {}
            results = data.get("results") or data.get("data") or data.get("items") or (data if isinstance(data, list) else [])
            for it in results[:50]:
                if not isinstance(it, dict):
                    continue
                items.append({
                    "title": it.get("title") or it.get("subject") or it.get("name") or "",
                    "body": it.get("abstract") or it.get("body") or it.get("description") or it.get("summary") or "",
                    "url": it.get("html_url") or it.get("url") or it.get("link") or source.get("url"),
                    "date": (it.get("publication_date") or it.get("date") or it.get("published") or "")[:10],
                    "doc_type": it.get("type") or "",
                    "agencies": ", ".join(a.get("name", "") for a in it.get("agencies", []) if isinstance(a, dict))[:200],
                })
        elif "<rss" in stripped[:2000] or "<feed" in stripped[:2000] or stripped.startswith("<?xml"):
            try:
                root = ET.fromstring(stripped.encode("utf-8", "ignore"))
            except ET.ParseError:
                root = None
            if root is not None:
                ns = {"a": "http://www.w3.org/2005/Atom"}
                nodes = root.findall(".//item") or root.findall(".//a:entry", ns)
                for it in nodes[:50]:
                    def tx(tag):
                        el = it.find(tag) if not tag.startswith("a:") else it.find(tag, ns)
                        return (el.text or "").strip() if el is not None and el.text else ""
                    link = tx("link") or (it.find("a:link", ns).get("href") if it.find("a:link", ns) is not None else "")
                    items.append({"title": tx("title") or tx("a:title"), "body": tx("description") or tx("a:summary"),
                                  "url": link or source.get("url"), "date": (tx("pubDate") or tx("a:updated") or "")[:16]})
        else:
            # HTML gazette page: take headline-ish text snippets as candidates
            for m in re.finditer(r"<(?:h[1-3]|a)[^>]*>(.*?)</(?:h[1-3]|a)>", stripped, re.I | re.S):
                text = re.sub(r"<[^>]+>", " ", m.group(1))
                text = re.sub(r"\s+", " ", text).strip()
                if 25 <= len(text) <= 220:
                    items.append({"title": text, "body": "", "url": source.get("url"), "date": ""})
                if len(items) >= 60:
                    break
        scored = []
        for it in items:
            score = relevance_score(f"{it['title']} {it['body']}")
            if score >= 3:
                scored.append((score, it))
        scored.sort(key=lambda x: (-x[0], x[1].get("date") or ""))
        return [self._event_from_item(source, it, score) for score, it in scored]

    def _event_from_item(self, source, item, score=0):
        title = re.sub(r"\s+", " ", item.get("title") or "").strip()[:300]
        doc_type = str(item.get("doc_type") or "").lower()
        tl = title.lower()
        if "rule" in doc_type and "proposed" not in doc_type:
            severity = "Warning"
        elif "proposed" in doc_type or "recognition" in tl or "application" in tl or "receipt" in tl:
            severity = "Info"
        else:
            severity = "Warning" if any(w in tl for w in ("mandatory", "prohibit", "ban", "deadline", "reporting", "requirement")) else "Info"
        pillar = infer_pillar(f"{title} {item.get('body', '')}")
        blob = f"{title} {item.get('body', '')}"
        std_match = re.search(r"(IS/IEC\s*62368-1|IEC\s*62368-1(?::\d{4})?|EN\s*(?:IEC\s*)?62368-1|UL\s*62368-1|CISPR\s*32|EN\s*55032|"
                              r"FCC\s*Part\s*15\s*[A-Z]?|CNS\s*15598|CNS\s*15936|GB\s*4943(?:\.1)?|GB/T\s*9254|KC\s*62368|KS\s*C\s*9832|"
                              r"KN\s*32|2011/65/EU|2024/2847|EN\s*18031|IS\s*13252)", blob, re.I)             or re.search(r"(RoHS|REACH|PFAS|TSCA|WEEE)", blob)  # acronyms: case-sensitive to avoid matching plain words
        default_std = {"Safety": "IEC 62368-1 (national adoption)", "EMC": "CISPR 32 Class B", "Environmental": "RoHS / REACH restricted substances",
                       "Cyber": "Product cybersecurity baseline", "All": "Harmonised multi-pillar update"}[pillar]
        detected_std = std_match.group(0).upper().replace("  ", " ") if std_match else default_std
        sid = source["id"]
        cc, cname = "GLOBAL", "Global market access"
        if "US" in sid:
            cc, cname = "US", "United States"
        elif "EU" in sid:
            cc, cname = "EU", "European Union"
        elif "IN-" in sid:
            cc, cname = "IN", "India"
        elif "KR" in sid:
            cc, cname = "KR", "South Korea"
        elif "TW" in sid:
            cc, cname = "TW", "Taiwan"
        elif "CN" in sid:
            cc, cname = "CN", "China"
        pub = item.get("date") or today_iso()
        if not re.match(r"\d{4}-\d{2}-\d{2}", pub):
            pub = today_iso()
        return {
            "event_id": _event_id("SURV", sid, item.get("url") or title, title),
            "timestamp": utc_iso(), "country_code": cc, "country_name": cname, "authority": item.get("agencies") or source["name"], "pillar": pillar,
            "source_id": sid, "source_name": source["name"], "source_url": item.get("url") or source.get("url"),
            "old_standard": "Current national standard", "new_standard": detected_std, "effective_date": pub,
            "withdrawal_deadline": "See gazette bulletin", "affected_categories": ["external_ssd_powered", "external_ssd_bus", "usb_drive", "internal_ssd"],
            "event_type": f"{pillar} gazette notice" + (f" ({item.get('doc_type')})" if item.get("doc_type") else ""), "severity": severity, "summary": title,
            "detail": (item.get("body") or "")[:1200], "status": "Detected by live scan", "confidence_score": min(0.95, 0.6 + 0.05 * score), "relevance_score": score,
        }

    # ------------------------------------------------------------------ applying events
    def _target_codes(self, cc):
        cc = (cc or "ALL").upper().strip()
        cdb = self.db.COUNTRIES_DB if self.db else {}
        if cc in ("ALL", "GLOBAL", "WORLDWIDE", "ALL_COUNTRIES"):
            return list(cdb.keys())
        if cc == "EU":
            return [c for c in EU_COUNTRIES if c in cdb]
        return [cc] if cc in cdb else []

    def _apply_event(self, event, create_alert=True):
        """Record a transition on every target country, persist, create the enriched alert."""
        pillar = event.get("pillar", "Safety")
        new_std = event.get("new_standard")
        deadline = event.get("withdrawal_deadline")
        codes = self._target_codes(event.get("country_code"))
        applied_at = today_iso()
        pillars = ["Safety", "EMC", "Environmental"] if pillar == "All" else [pillar]
        has_deadline = bool(re.match(r"\d{4}-\d{2}-\d{2}", str(deadline or "")))
        event["no_deadline"] = not has_deadline
        # A detected notice without an explicit cutover date is informational: it is ledgered and
        # alerted but must not be recorded as a standard transition on the country records.
        records_transition = has_deadline or bool(event.get("simulated"))
        if self.db and records_transition:
            with self._lock:
                for code in codes:
                    c = self.db.COUNTRIES_DB[code]
                    transitions = [t for t in c.get("transitions", []) if t.get("event_id") != event["event_id"]]
                    for p in pillars:
                        field = PILLAR_FIELD.get(p)
                        transitions.append({
                            "event_id": event["event_id"], "pillar": p, "from": c.get(field) if field else None, "to": new_std,
                            "deadline": deadline, "effective_date": event.get("effective_date"), "source": event.get("source_name"),
                            "source_url": event.get("source_url"), "applied_at": applied_at,
                        })
                        if field:
                            c[f"{field}_next"] = new_std
                            c[f"{field}_transition_deadline"] = deadline
                    c["transitions"] = transitions[-12:]
                    c["last_surveilled_date"] = applied_at
                    c["last_surveilled_pillar"] = pillar
                    c["surveillance_source"] = event.get("source_name")
                if self.store and codes:
                    self.store.save_countries()
        event["affected_countries_count"] = len(codes) if records_transition else len(codes)
        event["transition_recorded"] = records_transition
        event["impacted_products"] = event.get("impacted_products") or resolve_product_impacts(
            event.get("affected_categories", []), country_code=event.get("country_code"), region=event.get("country_name"),
            products=self.store.products() if self.store else None)
        event["impacted_products_count"] = len(event["impacted_products"])
        if create_alert and self.store:
            event["alert"] = self._create_alert_from_event(event)
        self._append_to_audit_log({k: v for k, v in event.items() if k not in ("alert",)})
        return event

    def _create_alert_from_event(self, event):
        pillar = event.get("pillar", "Safety")
        new_std = event.get("new_standard")
        deadline = event.get("withdrawal_deadline")
        is_all = str(event.get("country_code", "")).upper() in ("ALL", "GLOBAL", "WORLDWIDE", "ALL_COUNTRIES")
        country_display = "All 205 global jurisdictions" if is_all else event.get("country_name")
        summary = event.get("summary", "")
        dl_txt = deadline if deadline and deadline not in ("Permanent", "See gazette bulletin") else "the enforcement date"
        detected = not event.get("simulated")
        if detected:
            title = f"{event.get('country_name')}: {summary}"[:200]
        elif is_all:
            title = f"Global harmonisation: {new_std} ({pillar}) mandated across all 205 jurisdictions"[:200]
        else:
            title = f"{event.get('country_name')} – {event.get('authority')}: {new_std} ({pillar}) gazette update"[:200]
        alert = {
            "id": f"ALERT-SURV-{event['event_id'].split('-')[-1]}",
            "title": title,
            "no_deadline": bool(event.get("no_deadline")),
            "detected_live": detected,
            "region": "Global" if is_all else (self.db.COUNTRIES_DB.get(event.get("country_code"), {}).get("region", event.get("country_name")) if self.db else event.get("country_name")),
            "country": country_display, "country_code": "ALL" if is_all else event.get("country_code"), "standard": new_std,
            "severity": event.get("severity") or ("Critical" if any(w in summary.lower() for w in ("mandatory", "deadline", "ban", "prohibit")) else "Warning"),
            "effective_date": deadline if deadline and re.match(r"\d{4}-\d{2}-\d{2}", str(deadline)) else event.get("effective_date"),
            "affected_categories": event.get("affected_categories", []), "pillar": pillar,
            "summary": f"[{event.get('source_name')}] {summary}",
            "action_required": event.get("action_required") or f"Review technical files, test reports and declarations for {pillar} compliance under {new_std}; complete gap assessment before {dl_txt}.",
            "status": "Auto-detected (surveillance)", "source": event.get("source_name"),
            "detailed_summary": event.get("detailed_summary") or (
                f"The surveillance engine recorded a regulatory notice from {event.get('authority')} ({country_display}). "
                f"It introduces or mandates {new_std} for the {pillar} pillar. The current national standard remains valid until {dl_txt}; "
                f"after that date products placed on the market must conform to the new requirement.\n\nNotice summary: {summary}"
                + (f"\n\nDetail: {event['detail']}" if event.get("detail") else "")),
            "technical_impact": event.get("technical_impact") or f"Pillar: {pillar}\nNew standard reference: {new_std}\nApplies to: {', '.join(event.get('affected_categories', []))}\nMandatory cutover: {deadline or 'as per gazette'}\nJurisdictions: {event.get('affected_countries_count', 1)}",
            "timeline_milestones": event.get("timeline_milestones") or [
                {"phase": "Gazette notice published & ingested", "date": event.get("effective_date", today_iso()), "status": "Active"},
                {"phase": "Recommended internal gap assessment complete", "date": event.get("effective_date", today_iso()), "status": "Recommended"},
                {"phase": "Mandatory cutover / enforcement", "date": deadline if deadline and re.match(r"\d{4}-\d{2}-\d{2}", str(deadline)) else "Immediate", "status": "Enforcement Deadline"},
            ],
            "official_links": event.get("official_links") or [{"label": f"{event.get('authority')} – official notice", "url": event.get("source_url") or "https://epingalert.org/"}],
            "compliance_checklist": event.get("compliance_checklist") or [
                f"Map every affected SKU to {new_std} clauses and identify test/documentation deltas",
                "Confirm with the certification body whether existing reports can be amended or need re-testing",
                f"Update declarations of conformity, labels and technical files before {dl_txt}",
                "Brief distributors / local representatives on the transition timeline",
            ],
            "impacted_products": event.get("impacted_products", []), "impacted_products_count": event.get("impacted_products_count", 0),
            "surveillance_event_id": event.get("event_id"),
        }
        return self.store.add_alert(alert)

    # ------------------------------------------------------------------ simulation (demo / what-if)
    def auto_simulate_next_event(self, products=None):
        scenario = AUTO_SIMULATED_SCENARIOS[self.scenario_index % len(AUTO_SIMULATED_SCENARIOS)]
        self.scenario_index += 1
        event = {
            "event_id": _event_id("SURV-AUTO", scenario.get("id_key"), int(time.time())),
            "timestamp": utc_iso(), "country_code": scenario["country_code"], "country_name": scenario["country_name"],
            "authority": scenario["authority"], "pillar": scenario["pillar"], "source_id": f"SRC-{scenario['country_code']}-{scenario.get('id_key')}",
            "source_name": scenario["source_name"], "source_url": scenario["source_url"], "old_standard": "Current national standard",
            "new_standard": scenario["new_standard"], "effective_date": today_iso(), "withdrawal_deadline": scenario["deadline"],
            "affected_categories": scenario["affected_categories"], "event_type": f"Simulated {scenario['pillar']} notice",
            "severity": scenario.get("severity", "Warning"), "summary": scenario["summary"], "action_required": scenario["action_required"],
            "detailed_summary": scenario.get("detailed_summary"), "technical_impact": scenario.get("technical_impact"),
            "timeline_milestones": scenario.get("timeline_milestones"), "official_links": scenario.get("official_links"),
            "compliance_checklist": scenario.get("compliance_checklist"), "status": "Simulated (what-if)", "confidence_score": 0.99,
            "simulated": True,
        }
        if products:
            event["impacted_products"] = resolve_product_impacts(scenario["affected_categories"], country_code=scenario["country_code"], region=scenario["country_name"], products=products)
        self._apply_event(event, create_alert=True)
        self.last_scan_time = utc_iso()
        self.last_scan_status = f"Simulated {scenario['pillar']} notice for {scenario['country_name']} ({scenario['new_standard']}) - {event['impacted_products_count']} portfolio products impacted."
        return event

    def simulate_gazette_update(self, country_code, authority, new_standard, deadline, summary, affected_categories, pillar="Safety", source_url=None):
        cc = (country_code or "ALL").upper().strip()
        is_all = cc in ("ALL", "GLOBAL", "WORLDWIDE", "ALL_COUNTRIES")
        if is_all:
            cc = "ALL"
            country_name = "All 205 global jurisdictions"
            source_name = "Global harmonisation bulletin (simulated)"
            source_url = source_url or "https://epingalert.org/"
        else:
            country_name = self.db.COUNTRIES_DB.get(cc, {}).get("name", cc) if self.db else cc
            source_name = f"{country_name} national gazette (simulated)"
            source_url = source_url or f"https://epingalert.org/en/Search?country={cc}"
        event = {
            "event_id": _event_id("SURV-SIM", cc, new_standard, pillar, int(time.time())),
            "timestamp": utc_iso(), "country_code": cc, "country_name": country_name, "authority": authority, "pillar": pillar,
            "source_id": f"SRC-{cc}-GAZETTE", "source_name": source_name, "source_url": source_url, "old_standard": "Current national standard",
            "new_standard": new_standard, "effective_date": today_iso(), "withdrawal_deadline": deadline, "affected_categories": affected_categories,
            "event_type": f"{'Global' if is_all else 'National'} {pillar} gazette notice (simulated)", "summary": summary,
            "severity": "Critical" if any(w in summary.lower() for w in ("mandatory", "deadline", "ban", "prohibit")) else "Warning",
            "status": "Simulated (what-if)", "confidence_score": 0.99, "simulated": True,
        }
        self._apply_event(event, create_alert=True)
        self.last_scan_time = utc_iso()
        self.last_scan_status = (f"Simulated {pillar} notice applied to {event['affected_countries_count']} jurisdiction(s) ({new_standard}); "
                                 f"{event['impacted_products_count']} portfolio products impacted.")
        return event

    # ------------------------------------------------------------------ maintenance
    def reset_to_seed(self):
        """Discard transitions/simulations: reload the shipped country knowledge base into the working copy."""
        seed = config.read_json(config.bundle_path("countries_data.json"), None)
        if not isinstance(seed, dict) or not seed or not self.db:
            return {"restored": 0}
        with self._lock:
            self.db.COUNTRIES_DB.clear()
            self.db.COUNTRIES_DB.update(seed)
            if self.store:
                self.store.save_countries()
        return {"restored": len(seed)}


_engine = None
_engine_lock = threading.Lock()


def get_surveillance_engine(compliance_db=None, store=None):
    global _engine
    with _engine_lock:
        if _engine is None:
            _engine = RegulatorySurveillanceEngine(compliance_db_module=compliance_db, store=store)
        else:
            if compliance_db is not None and _engine.db is None:
                _engine.db = compliance_db
            if store is not None and _engine.store is None:
                _engine.store = store
        return _engine
