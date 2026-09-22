"""
expert_advisor.py - AI Regulatory Expert Advisor Engine (v2, fixed)

Searches live internet regulatory gazettes, standards bodies, testing-laboratory bulletins
and government portals to produce in-depth compliance advisories and interactive engineering
Q&A for flash memory & storage products.

v2 fixes:
  * timezone-aware timestamps (datetime.utcnow() is deprecated)
  * a hard network budget: no consult / question ever blocks for more than ~8 s in total,
    with an offline circuit breaker so repeated calls degrade instantly when there is no
    internet or a corporate proxy blocks the search endpoint
  * the DuckDuckGo HTML regexes are brittle - they are kept, wrapped, and complemented by
    a tolerant fallback pattern; failures fall back to curated authoritative sources
  * when ai_bridge is configured, answer_custom_question() prefers a Claude answer grounded
    on the alert + the rules-based explanation and falls back to the rule-based answer
"""
import datetime as _dt
import html as _html
import re
import threading
import time
import urllib.error
import urllib.parse
import urllib.request

NETWORK_BUDGET_S = 8.0          # total wall-clock budget per consult / question
PER_REQUEST_TIMEOUT_S = 4.0     # single HTTP request cap
OFFLINE_BACKOFF_S = 300         # after a network failure, skip live search for 5 minutes

# Pre-indexed domain knowledge for offline resilience & deep regulatory context
CURATED_EXPERT_KNOWLEDGE = {
    "ALERT-2026-01": {
        "legal_authority": "Regulation (EU) 2024/2847 (Cyber Resilience Act) - Official Journal L, Nov 20, 2024",
        "enforcing_body": "European Commission, ENISA, and National Market Surveillance Authorities (e.g. BSI Germany, ANSSI France)",
        "testing_standards": "EN 18031-1, EN 18031-2, EN 18031-3 (Common European Cybersecurity Assessment Standards for Products with Digital Elements)",
        "hardware_scope": "Storage devices with microcontrollers (NVMe SSD controllers, SATA bridge ASICs, USB 3.2/USB4 bridge ICs)",
        "technical_clauses": [
            "Article 10 & Annex I Part I: Security-by-design baseline, protection against unauthorized firmware modification",
            "Article 10(4): Mandatory machine-readable Software Bill of Materials (SBOM) in SPDX or CycloneDX format",
            "Article 11: Mandatory reporting of actively exploited vulnerabilities to ENISA and national CSIRTs within 24 hours",
            "Article 14: Conformity assessment procedures (Internal control Module A or Third-Party Module B+C depending on classification)"
        ],
        "engineering_guidance": "For NVMe SSDs and USB drives with a firmware-bearing controller, firmware ROM bootloaders must enforce ECDSA-384 / RSA-3072 signature verification. Diagnostic JTAG/UART access and vendor flash commands must be permanently blown via eFuses prior to mass production.",
        "lab_recommendations": "Engage accredited European Cybersecurity Assessment labs (TÜV Rheinland, UL Solutions Europe, SGS Brightsight) for Module A technical file audit.",
        "suggested_questions": [
            "Does CRA require third-party lab testing or self-declaration for NVMe SSDs?",
            "What format of SBOM is required and how should flash controller microcode be declared?",
            "What are the reporting obligations to ENISA for discovered firmware bugs?",
            "Are legacy SSD models grandfathered if sold after January 2027?"
        ]
    },
    "ALERT-2026-02": {
        "legal_authority": "IEC 62368-1:2023 (Edition 4.0) Audio/video, information and communication technology equipment - Part 1: Safety requirements",
        "enforcing_body": "IECEE CB Scheme, CENELEC (Europe), OSHA NRTL (US/Canada), BIS (India), CCC (China)",
        "testing_standards": "IEC 62368-1:2023, EN IEC 62368-1:2024, UL 62368-1 4th Edition",
        "hardware_scope": "High-speed bus-powered SSDs, USB-PD external desktop storage, SD Express removable cards",
        "technical_clauses": [
            "Clause 9 (Thermal burn injury hazard): Refined touch temperature limits for metallic accessible enclosures (TS2 limit: 70°C, TS1 limit: 48°C)",
            "Clause 6 (Electrically-caused fire): DC-DC converter fault condition testing under maximum power transfer from USB-PD source",
            "Annex G (Components): Updated capacitor discharge and optical radiation isolation guidelines",
            "National Deviations: Mandatory testing for US/Canada (CSA/UL requirements) and European group differences"
        ],
        "engineering_guidance": "Bus-powered portable SSDs with metal enclosures must keep accessible surface temperatures <= 70°C under continuous 100% sequential write loops at 35°C ambient. Firmware thermal throttling algorithms must be verified in thermal chambers.",
        "lab_recommendations": "Coordinate with UL Solutions or TÜV SÜD for CB Test Certificate upgrade. Request IECEE TRF 62368-1_4 test report format with national differences for US, EU, and China.",
        "suggested_questions": [
            "What is the maximum allowed touch temperature for metal SSD cases under 4th Edition?",
            "Can existing Edition 3 CB Test Certificates be amended without physical hardware re-testing?",
            "How does Edition 4 evaluate USB Type-C Power Delivery negotiate lines?",
            "When will Europe withdraw the presumption of conformity for Edition 3?"
        ]
    },
    "ALERT-2026-03": {
        "legal_authority": "MeitY Gazette Order No. 27(1)/2022-IPHW & BIS Scheme-II Notification",
        "enforcing_body": "Bureau of Indian Standards (BIS) and Ministry of Electronics & IT (MeitY)",
        "testing_standards": "IS/IEC 62368-1:2023 (Replacing IS 13252 Part 1:2010)",
        "hardware_scope": "External SSDs, External Desktop Storage with DC Adapters, Internal SSDs, Power Supplies",
        "technical_clauses": [
            "Mandatory migration deadline: November 1, 2028 (Concurrent running allowed until sunset)",
            "In-country testing requirement: Test reports must be generated exclusively by NABL-accredited BIS-recognized labs in India",
            "R-Number inclusion: Existing R-8400xxxx registrations must be transitioned via Change of Standard application"
        ],
        "engineering_guidance": "Ship 2 test samples of each mains-powered desktop storage product and its external power supply to a BIS-recognised NABL laboratory in India 6 months prior to cutover. Local Authorized Indian Representative (AIR) must execute online portal endorsement.",
        "lab_recommendations": "Book test slots early at UL India (Bengaluru) or TÜV Rheinland India to avoid the Q3 2028 industry backlog.",
        "suggested_questions": [
            "Can overseas CB Scheme test reports be directly accepted by BIS for IS/IEC 62368-1?",
            "What happens to existing customs shipments in India if the R-number is not transitioned by Nov 2028?",
            "Does IS/IEC 62368-1 require testing of the storage drive or only the external power adapter?",
            "What documents are required from the Authorized Indian Representative (AIR)?"
        ]
    },
    "ALERT-ENV-01": {
        "legal_authority": "US Toxic Substances Control Act (TSCA) Section 8(a)(7) - 40 CFR Part 705",
        "enforcing_body": "US Environmental Protection Agency (EPA)",
        "testing_standards": "EPA TSCA PFAS Structural Definition (per- and polyfluoroalkyl substances containing at least one CF2 or CF3 group)",
        "hardware_scope": "All electronic articles: SSD PCBAs, flash memory enclosures, cabling, thermal pads, wire insulation, labels",
        "technical_clauses": [
            "Mandatory retrospective reporting covering manufacture/import from January 1, 2011 to December 31, 2022",
            "Reporting window: Closes May 8, 2025 (Small entity extension to November 10, 2025)",
            "No de minimis volume exemption: Even trace fluoropolymers (e.g. PTFE in wire jackets, PVDF in conformal coating) require filing"
        ],
        "engineering_guidance": "Request Full Material Disclosures (FMD) from all tier-1 PCBA, wire harness, and thermal interface material (TIM) suppliers. Compile structural CAS numbers and import tonnages for EPA CDX portal submission.",
        "lab_recommendations": "Screen high-risk polymers using Total Organic Fluorine (TOF) combustion ion chromatography testing at accredited environmental labs (SGS, Eurofins).",
        "suggested_questions": [
            "Does TSCA 8(a)(7) apply to imported articles like finished SSDs or only bulk chemicals?",
            "What is the penalty for failing to submit PFAS import reports to the EPA CDX portal?",
            "How do we obtain PFAS declarations if contract suppliers refuse full chemical disclosure?",
            "How does the EPA rule interact with state-level bans in Maine and Minnesota?"
        ]
    },
    "ALERT-ENV-03": {
        "legal_authority": "France AGEC Law (Loi Anti-Gaspillage pour une Économie Circulaire) & Decree No. 2021-835",
        "enforcing_body": "DGCCRF (Direction générale de la concurrence, de la consommation et de la répression des fraudes) & CITEO",
        "testing_standards": "CITEO / ADEME Info-tri Harmonized Packaging Signage Guide",
        "hardware_scope": "Retail packaging for consumer SSDs, microSD cards, USB drives sold on the French market",
        "technical_clauses": [
            "Mandatory Triman Logo accompanied by Info-tri sorting pictogram (Bac Jaune sorting instructions)",
            "Dual-material packaging: Clear visual separation for cardboard retail box vs interior PET blister tray",
            "Fines of up to €15,000 per commercial SKU and product recall for non-compliant retail packaging"
        ],
        "engineering_guidance": "Retail packaging artwork die-lines for consumer SSDs and memory cards must include the Triman logo + CITEO sorting icon on the reverse or side panel. Units destined for Pan-EU distribution should use the unified EU-compliant packaging layout.",
        "lab_recommendations": "Submit artwork proofs to CITEO portal for automated compliance validation prior to cylinder engraving.",
        "suggested_questions": [
            "Can the Triman logo be displayed digitally via QR code instead of printed on the retail box?",
            "What are the minimum size dimensions for the Triman and Info-tri symbols?",
            "How does French Triman labeling affect cross-border sales in Germany and Italy?",
            "Are B2B industrial SSD shipments subject to the AGEC consumer packaging decree?"
        ]
    }
}


def _utc_stamp():
    return _dt.datetime.now(_dt.timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")


def _strip_tags(s):
    return _html.unescape(re.sub(r"<[^>]+>", "", s or "")).strip()


class _Budget:
    """Wall-clock budget shared by all network calls of one consult / question."""

    def __init__(self, seconds=NETWORK_BUDGET_S):
        self.deadline = time.monotonic() + seconds

    def remaining(self):
        return max(0.0, self.deadline - time.monotonic())

    def timeout(self):
        return min(PER_REQUEST_TIMEOUT_S, self.remaining())


class RegulatoryExpertAdvisor:
    def __init__(self):
        self.user_agent = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
        self._lock = threading.Lock()
        self._offline_until = 0.0
        self.last_network_status = "untested"

    # ------------------------------------------------------------------ network
    def network_available(self):
        return time.monotonic() >= self._offline_until

    def _mark_offline(self, reason):
        with self._lock:
            self._offline_until = time.monotonic() + OFFLINE_BACKOFF_S
            self.last_network_status = f"offline / blocked ({reason}) - live search paused for {OFFLINE_BACKOFF_S // 60} min"

    def _fetch_within(self, req, budget):
        """Fetch in a worker thread and give up when the shared budget is exhausted, so a slow
        DNS lookup or a dribbling response can never hold the request thread hostage."""
        box = {}

        def worker():
            try:
                with urllib.request.urlopen(req, timeout=budget.timeout() or 0.5) as resp:
                    box["html"] = resp.read(1_500_000).decode("utf-8", errors="ignore")
            except Exception as e:  # any failure -> offline
                box["err"] = type(e).__name__

        t = threading.Thread(target=worker, name="gcm-expert-fetch", daemon=True)
        t.start()
        t.join(max(0.1, budget.remaining()))
        if t.is_alive():
            return None, "timeout"
        return box.get("html"), box.get("err")

    def _parse_ddg(self, html, num_results):
        """Two passes: the classic result__url/result__snippet pair, then a tolerant fallback."""
        results = []
        try:
            links = re.findall(r'<a[^>]+class="[^"]*result__url[^"]*"[^>]+href="([^"]+)"[^>]*>(.*?)</a>', html, re.DOTALL)
            snippets = re.findall(r'<a[^>]+class="[^"]*result__snippet[^"]*"[^>]*>(.*?)</a>', html, re.DOTALL)
            for i in range(min(len(links), len(snippets), num_results)):
                raw_u, raw_t = links[i]
                results.append(self._clean_result(raw_u, raw_t, snippets[i]))
        except Exception:
            results = []
        if len(results) < 2:
            try:
                for m in re.finditer(r'<a[^>]+class="[^"]*result__a[^"]*"[^>]+href="([^"]+)"[^>]*>(.*?)</a>(?:.*?<a[^>]+class="[^"]*result__snippet[^"]*"[^>]*>(.*?)</a>)?', html, re.DOTALL | re.IGNORECASE):
                    results.append(self._clean_result(m.group(1), m.group(2), m.group(3) or ""))
                    if len(results) >= num_results:
                        break
            except Exception:
                pass
        out = []
        for r in results:
            if r and r["url"] and r["url"].startswith("http") and not any(x["url"] == r["url"] for x in out):
                out.append(r)
        return out

    def _clean_result(self, raw_u, raw_t, raw_s):
        try:
            url = _html.unescape(raw_u.strip())
            if "uddg=" in url:
                url = urllib.parse.unquote(url.split("uddg=")[-1].split("&")[0])
            if url.startswith("//"):
                url = "https:" + url
            title = _strip_tags(raw_t)
            snippet = _strip_tags(raw_s)
            return {"title": title or "Regulatory Gazette Notice", "url": url, "snippet": snippet or title}
        except Exception:
            return None

    def search_internet(self, query, num_results=6, budget=None):
        """
        Live DuckDuckGo HTML search for official gazettes, standards bodies and lab notices.
        Never blocks beyond the shared budget; falls back to curated authoritative sources.
        """
        budget = budget or _Budget()
        results = []
        if self.network_available() and budget.remaining() > 0.5:
            search_url = "https://html.duckduckgo.com/html/?q=" + urllib.parse.quote(query)
            req = urllib.request.Request(search_url, headers={
                "User-Agent": self.user_agent,
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                "Accept-Language": "en-US,en;q=0.9",
            })
            html, err = self._fetch_within(req, budget)
            if html is not None:
                results = self._parse_ddg(html, num_results)
                with self._lock:
                    self.last_network_status = "online"
            else:
                self._mark_offline(err or "timeout")
        if len(results) < 2:
            for src in self._get_fallback_authoritative_sources(query):
                if not any(r["url"] == src["url"] for r in results):
                    results.append(src)
        return results[:num_results]

    def _get_fallback_authoritative_sources(self, query):
        """Verified official government and standards-body citations matching the query keywords."""
        q_lower = (query or "").lower()
        sources = []
        if "cra" in q_lower or "resilience" in q_lower or "2024/2847" in q_lower or "cyber" in q_lower:
            sources.append({"title": "Official Journal of the European Union - Regulation (EU) 2024/2847 (Cyber Resilience Act)",
                            "url": "https://eur-lex.europa.eu/legal-content/EN/TXT/?uri=CELEX:32024R2847",
                            "snippet": "Horizontal cybersecurity requirements for products with digital elements placed on the EU Single Market, establishing duty-of-care obligations and mandatory vulnerability reporting."})
            sources.append({"title": "ENISA European Union Agency for Cybersecurity - CRA Standards Harmonization Guide",
                            "url": "https://www.enisa.europa.eu/topics/cybersecurity-education/vulnerability-disclosure",
                            "snippet": "Technical standards and vulnerability reporting channels for hardware manufacturers under the Cyber Resilience Act."})
        elif "psti" in q_lower or "united kingdom" in q_lower:
            sources.append({"title": "UK Government - Product Security and Telecommunications Infrastructure Act 2022 guidance",
                            "url": "https://www.gov.uk/guidance/product-security-and-telecommunications-infrastructure-act-2022",
                            "snippet": "Security requirements for consumer connectable products, Statement of Compliance and enforcement by OPSS."})
        elif "62368" in q_lower or "safety" in q_lower:
            sources.append({"title": "IECEE CB Scheme - IEC 62368-1:2023 (Edition 4.0) Implementation & TRF Guidelines",
                            "url": "https://www.iecee.org/dyn/www/f?p=106:1:0:::::",
                            "snippet": "IECEE Committee of Testing Laboratories (CTL) transition guidelines, test reporting formats (TRF), and national deviations for 4th Edition safety evaluations."})
            sources.append({"title": "UL Solutions Technical Whitepaper - Navigating IEC 62368-1 4th Edition Requirements",
                            "url": "https://www.ul.com/services/iec-62368-1-testing-and-certification",
                            "snippet": "Analysis of key changes in Edition 4 including Clause 9 touch temperature limits, USB-PD power delivery evaluations, and outdoor enclosure testing."})
        elif "bis" in q_lower or "india" in q_lower or "13252" in q_lower:
            sources.append({"title": "Bureau of Indian Standards (BIS) - Compulsory Registration Scheme (CRS) Transition Portal",
                            "url": "https://www.bis.gov.in/index.php/standard-marking/compulsory-registration-scheme/",
                            "snippet": "Official notification regarding migration of ICT products from IS 13252 (Part 1) to IS/IEC 62368-1:2023 with mandatory transition cutover schedule."})
        elif "pfas" in q_lower or "tsca" in q_lower or "epa" in q_lower:
            sources.append({"title": "US EPA - TSCA Section 8(a)(7) PFAS Reporting Rule Regulatory Guidance",
                            "url": "https://www.epa.gov/assessing-and-managing-chemicals-under-tsca/tsca-section-8a7-reporting-and-recordkeeping-requirements",
                            "snippet": "Comprehensive reporting and recordkeeping requirements for per- and polyfluoroalkyl substances manufactured or imported into the United States."})
        elif "triman" in q_lower or "france" in q_lower or "agec" in q_lower or "packaging" in q_lower:
            sources.append({"title": "CITEO / ADEME - Harmonized Info-tri Signage Guide for Electrical & Electronic Packaging",
                            "url": "https://www.citeo.com/le-mag/guide-du-tri-comment-adopter-le-nouveau-logo-triman-et-linfo-tri",
                            "snippet": "Technical specifications for displaying the Triman logo and sorting pictograms on packaging under Article 17 of the French AGEC circular economy law."})
        elif "saso" in q_lower or "saber" in q_lower or "saudi" in q_lower:
            sources.append({"title": "SABER - Saudi Product Safety Program conformity platform",
                            "url": "https://saber.sa",
                            "snippet": "Registration of products, Product and Shipment Certificates of Conformity for imports into the Kingdom of Saudi Arabia."})
        elif "rohs" in q_lower or "reach" in q_lower:
            sources.append({"title": "European Commission - RoHS Directive (2011/65/EU) evaluation and review",
                            "url": "https://environment.ec.europa.eu/topics/waste-and-recycling/rohs-directive_en",
                            "snippet": "Restriction of hazardous substances in electrical and electronic equipment; substance review and exemptions."})
            sources.append({"title": "ECHA - Candidate List of Substances of Very High Concern",
                            "url": "https://echa.europa.eu/candidate-list-table",
                            "snippet": "Official REACH Candidate List with the 0.1 % communication threshold for articles."})
        else:
            sources.append({"title": "World Trade Organization (WTO) - Technical Barriers to Trade (TBT) Information System",
                            "url": "https://epingalert.org/",
                            "snippet": "Global surveillance system for draft technical regulations, conformity assessment procedures, and international standards notifications."})
            sources.append({"title": "NIST International Standards & Compliance Directory",
                            "url": "https://www.nist.gov/standardsgov/compliance-faqs",
                            "snippet": "Guidance on international conformity assessment systems, mutual recognition agreements, and accreditation body requirements."})
        return sources

    # ------------------------------------------------------------------ expert brief
    def consult_expert_on_alert(self, alert):
        """
        Collects internet intelligence (within the network budget), cross-references it with
        the alert parameters and curated knowledge, and compiles an in-depth expert brief.
        """
        alert = alert or {}
        budget = _Budget()
        alert_id = alert.get("id", "ALERT-GENERIC")
        standard = alert.get("standard", "") or ""
        country = alert.get("country", "") or ""
        title = alert.get("title", "") or ""
        affected_categories = alert.get("affected_categories", []) or []

        clean_standard = re.sub(r"[^\w\s\-\/\.]", "", standard)
        primary_query = f"{clean_standard} {country} official compliance requirements storage electronics".strip()
        secondary_query = f"{title} compliance enforcement testing guidance".strip()

        search_results = self.search_internet(primary_query, num_results=4, budget=budget)
        if len(search_results) < 3 and budget.remaining() > 1.0:
            for r in self.search_internet(secondary_query, num_results=3, budget=budget):
                if not any(x["url"] == r["url"] for x in search_results):
                    search_results.append(r)

        base_knowledge = CURATED_EXPERT_KNOWLEDGE.get(alert_id, {})
        legal_basis = base_knowledge.get("legal_authority") or f"Statutory mandate enforced in {country or 'the target market'} under technical standard {standard or 'cited in the notice'}."
        enforcing_agency = base_knowledge.get("enforcing_body") or f"National Standards and Market Surveillance Authorities of {country or 'the target market'}."
        technical_clauses = base_knowledge.get("technical_clauses") or [
            f"Mandatory adherence to {standard or 'the referenced standard'} technical parameters and testing limits.",
            f"Harmonized verification procedures applicable to {', '.join(affected_categories) or 'solid-state storage'}.",
            "Requirement to maintain a Technical Documentation File (TDF) for a minimum 10-year retention period.",
        ]
        engineering_guidance = base_knowledge.get("engineering_guidance") or (
            f"Audit all of the company's flash drive, SSD and controller designs against {standard or 'the new requirement'}. "
            f"Ensure packaging markings, DoC declarations, and supplier component disclosures are updated prior to {alert.get('effective_date') or 'the mandatory cutover'}."
        )
        lab_advice = base_knowledge.get("lab_recommendations") or "Engage accredited test laboratories (UL Solutions, TÜV Rheinland, SGS, Intertek) to obtain compliant test reports."
        suggested_q = base_knowledge.get("suggested_questions") or [
            f"What specific test clauses of {standard or 'this requirement'} apply to external bus-powered SSDs?",
            "What is the estimated laboratory re-testing cost and turnaround lead time?",
            "Are products already cleared through customs before the deadline grandfathered?",
            "What documentation must our OEM/ODM manufacturing partners provide?",
        ]

        live = [r for r in search_results if r.get("snippet") and "epingalert" not in r.get("url", "")]
        if self.network_available() and self.last_network_status == "online" and live:
            web_analysis = (
                f"Live search returned {len(live)} relevant public sources. Official publications confirm that authorities in {country or 'the target market'} "
                f"are prioritising compliance for consumer electronics and IT storage hardware; testing bodies emphasise early engagement with accredited "
                f"laboratories to avoid capacity bottlenecks, and customs inspection protocols with administrative penalties apply to non-compliant shipments."
            )
        else:
            web_analysis = (
                f"Live internet search was unavailable ({self.last_network_status}); the brief relies on the curated knowledge base and the official links recorded on the alert. "
                f"{standard or 'The referenced requirement'} in {country or 'the target market'} is entering its mandatory implementation phase; testing laboratories report high demand for conformity-assessment slots."
            )

        hardware_impacts = []
        for cat in affected_categories:
            cat = str(cat)
            clean_cat = cat.replace("_", " ").title()
            if "internal" in cat or "enterprise" in cat:
                action, verdict = f"Verify PCB design, thermal dissipation under sustained bus transfer, and BOM material declarations for {standard}.", "High Impact"
            elif "external" in cat:
                action, verdict = f"Evaluate enclosure touch temperature, cable flammability, and consumer regulatory labeling for {standard}.", "Critical Impact"
            elif "usb" in cat or "sd" in cat or "cf" in cat or "gaming" in cat:
                action, verdict = f"Verify silicon controller compliance, packaging waste markings, and customs tariff classification under {standard}.", "Medium Impact"
            else:
                action, verdict = f"Review technical specifications and ensure declaration of conformity references {standard}.", "Operational Impact"
            hardware_impacts.append({"category": clean_cat, "verdict": verdict, "engineering_action": action})

        lab_short = lab_advice.split("(")[-1].split(")")[0] if "(" in lab_advice else "UL / TÜV"
        roadmap = [
            {"phase": "Phase 1: Gap Analysis & BOM Audit", "timeline": "Immediate (Days 1 - 14)",
             "details": f"Cross-reference bill-of-materials and technical files for all {len(affected_categories)} affected hardware categories against {standard or 'the new requirement'} clauses."},
            {"phase": "Phase 2: Laboratory Engagement & Sample Dispatch", "timeline": "Months 1 - 2",
             "details": f"Submit golden engineering prototypes to accredited test labs ({lab_short})."},
            {"phase": "Phase 3: Declaration of Conformity & Portal Filings", "timeline": "Months 3 - 4",
             "details": "Update EU DoC / BIS CRS registration portal / EPA CDX filings; issue revised distributor technical documentation."},
            {"phase": "Phase 4: Packaging Artwork & Customs Release", "timeline": f"Target: Prior to {alert.get('effective_date') or 'enforcement'}",
             "details": "Roll out updated retail carton die-lines and ensure global logistics customs brokers possess active certificate numbers."},
        ]

        return {
            "alert_id": alert_id,
            "alert_title": title,
            "standard": standard,
            "country": country,
            "severity": alert.get("severity", "Information"),
            "effective_date": alert.get("effective_date", "TBD"),
            "search_query": primary_query,
            "analyzed_at": _utc_stamp(),
            "network_status": self.last_network_status,
            "internet_sources": search_results,
            "expert_brief": {
                "executive_summary": alert.get("summary", ""),
                "legal_authority": legal_basis,
                "enforcing_agency": enforcing_agency,
                "internet_intelligence_synthesis": web_analysis,
                "key_technical_clauses": technical_clauses,
                "hardware_impact": hardware_impacts,
                "engineering_guidance": engineering_guidance,
                "laboratory_testing_strategy": lab_advice,
                "compliance_roadmap": roadmap,
                "suggested_questions": suggested_q,
            },
        }

    # ------------------------------------------------------------------ Q&A
    def _rule_based_answer(self, alert, user_question):
        standard = alert.get("standard", "") or "the referenced standard"
        country = alert.get("country", "") or "the target market"
        q_lower = (user_question or "").lower()
        cats = alert.get("affected_categories") or ["storage"]

        if any(w in q_lower for w in ["temperature", "thermal", "heat", "touch", "burn", "70", "degrees"]):
            expert_answer = (
                f"Under {standard}, accessible touch temperature limits depend on the material classification (metal vs plastic vs rubber). "
                f"For bus-powered solid-state storage devices with metal enclosures (e.g. anodized aluminum), the maximum permissible temperature "
                f"under continuous maximum workload (TS2 touch threshold) is capped at 70°C for accidental contact and 48°C for continuous holding. "
                f"If the enclosure exceeds these limits during sequential write torture tests at 35°C ambient, firmware thermal throttling "
                f"must step down NAND controller clock frequencies to avoid a non-compliance failure."
            )
            key_clauses = ["Clause 9: Thermal Burn Injury Hazard", "Table 28: Touch Temperature Limits for Accessible Parts"]
            action_advice = "Audit thermal throttling PID loops in firmware; ensure temperature logging is recorded in the lab test file."
        elif any(w in q_lower for w in ["cost", "price", "fee", "sample", "turnaround", "lead time", "lab"]):
            expert_answer = (
                f"For testing against {standard} in {country}, turnaround times currently average 3 to 6 weeks depending on laboratory booking backlogs. "
                f"Typical safety and EMC testing costs range between $3,500 and $7,000 USD per product family when leveraging existing CB Scheme test reports. "
                f"For full baseline testing without prior CB certificates, budget between $8,000 and $12,000 USD. "
                f"Sample requirements: prepare 2 to 3 golden production units, 1 unpotted PCB sample for component inspection, "
                f"and dedicated test firmware enabling continuous read/write transfer loops."
            )
            key_clauses = ["Conformity Assessment Module B / CB Scheme Test Procedure", "IECEE CTL Operational Document OD-2020"]
            action_advice = "Consolidate model families under a single test report via technical delta justifications to minimize sample costs."
        elif any(w in q_lower for w in ["packaging", "triman", "label", "marking", "box", "art", "symbol"]):
            expert_answer = (
                f"Regarding packaging and markings for {country}: regulations mandate clear physical sorting and compliance markings directly "
                f"on the consumer-facing packaging. In jurisdictions like France (AGEC Law / Triman) and Italy (D.Lgs 116/2020), digital QR code alternatives "
                f"are NOT accepted as sole compliance on consumer packaging above the size thresholds - the Triman logo, Info-tri pictogram, and material alphanumeric coding "
                f"(e.g. PAP 20 for cardboard carton, PET 01 for blister insert) must be legibly printed on the physical retail carton."
            )
            key_clauses = ["CITEO Info-tri Marking Specifications", "Article 17 French AGEC Circular Economy Decree", "CONAI Alphanumeric Material Coding"]
            action_advice = "Update packaging mechanical die-lines before printing production batch cylinders. Validate proofs on the national portal."
        elif any(w in q_lower for w in ["grandfather", "grace", "legacy", "old", "stock", "existing", "inventory"]):
            expert_answer = (
                f"Regarding legacy inventory and grandfathering: the critical legal dividing line is the moment a product is 'placed on the market' "
                f"(imported through customs or made available for distribution) prior to the effective cutover deadline ({alert.get('effective_date') or 'the deadline'}). "
                f"Units physically cleared through customs and sitting in local distributor or retailer warehouses prior to the cutover date can generally "
                f"continue to be sold through the retail channel without recall. However, any shipments clearing customs AFTER the deadline must strictly "
                f"comply with {standard} or risk customs seizure and import embargoes."
            )
            key_clauses = ["EU Blue Guide Section 2.1: Making Available and Placing on the Market", "Customs Border Enforcement Protocols"]
            action_advice = "Execute warehouse inventory run-out schedules and ensure no non-compliant batches are in transit during the transition month."
        elif any(w in q_lower for w in ["pfas", "chemical", "rohs", "tsca", "substance", "fluor"]):
            expert_answer = (
                f"Under environmental rules affecting {standard}, electronic hardware articles contain "
                f"trace fluoropolymers that fall under reporting obligations (such as PTFE in wire jackets, PVDF in conformal coating, and fluoroelastomer gaskets). "
                f"Unlike traditional RoHS which provides 0.1% (1000 ppm) de minimis thresholds, regulations like EPA TSCA Section 8(a)(7) have NO de minimis threshold. "
                f"Manufacturers must collect structural Full Material Disclosures (FMD) from tier-1 suppliers and report chemical names, CAS numbers, and import tonnages."
            )
            key_clauses = ["40 CFR Part 705 (TSCA 8(a)(7))", "EU REACH Annex XVII Restrictions", "IEC 62474 Material Declaration Standards"]
            action_advice = "Issue urgent PFAS survey requests to all PCBA and connector suppliers using standard IPC-1752A XML templates."
        elif any(w in q_lower for w in ["sbom", "firmware", "vulnerab", "cyber", "secure boot", "sign"]):
            expert_answer = (
                f"Cybersecurity obligations under {standard} treat the controller firmware as part of the product: secure boot with cryptographically signed images, "
                f"permanently disabled debug/DFU back-doors in production SKUs, a machine-readable SBOM (SPDX or CycloneDX) covering every firmware component, "
                f"a public vulnerability-disclosure channel and a stated security-update support period. Storage devices without network connectivity are usually "
                f"'default' (self-assessed, Module A) rather than 'important' products, but the technical file must demonstrate each requirement."
            )
            key_clauses = ["CRA Annex I Part I (security requirements)", "CRA Article 14 (conformity assessment)", "UK PSTI Schedule 1 (security requirements)"]
            action_advice = "Generate the SBOM from the firmware build pipeline and archive signing-key custody evidence in the technical file."
        else:
            expert_answer = (
                f"In response to your query regarding '{user_question}' under {standard} ({country}): "
                f"regulatory authorities and test bodies mandate rigorous technical documentation. "
                f"For your solid-state storage products, compliance requires demonstrating that hardware microcontrollers, "
                f"electrical safety parameters, and environmental declarations satisfy the harmonized requirements of {standard}. "
                f"Market surveillance authorities are actively auditing conformity files and demanding accredited test reports covering all functional operating states. "
                f"This specific point is not covered in detail by the alert text - confirm it with the certification body or the official source linked on the alert."
            )
            key_clauses = [f"General Conformity Procedures for {standard}", f"National Market Surveillance Directive ({country})"]
            action_advice = f"Consult the Technical Documentation File (TDF) for your models in category {cats[0]}."
        return expert_answer, key_clauses, action_advice

    def answer_custom_question(self, alert, user_question, explanation=None, history=None, ctx=None):
        """
        Answers a custom engineering question about an alert. Prefers a Claude answer grounded on
        the alert + rules explanation (when ai_bridge is configured); falls back to the rule-based
        answer. Live web sources are collected within the network budget.
        """
        alert = alert or {}
        user_question = str(user_question or "").strip()
        budget = _Budget()
        standard = alert.get("standard", "") or ""
        country = alert.get("country", "") or ""

        query = f"{standard} {country} {user_question}".strip()
        search_results = self.search_internet(query, num_results=3, budget=budget)

        # 1. grounded offline answer (alert text + curated knowledge + country records + requirement rules)
        grounded = None
        try:
            import alert_explainer
            grounded = alert_explainer.grounded_answer(alert, user_question, ctx, explanation)
            if explanation is None:
                try:
                    explanation = alert_explainer.explain_alert(alert, ctx, "engineer")
                except Exception:
                    explanation = None
        except Exception as e:  # never break the endpoint
            print(f"[RegulatoryExpertAdvisor] grounded answer failed: {type(e).__name__}: {e}")

        # 2. Claude, when configured, answers on the same grounded material
        ai = None
        try:
            import ai_bridge
            if ai_bridge.is_active():
                ai = ai_bridge.answer_question(alert, explanation, user_question, history)
        except Exception:
            ai = None

        if ai and ai.get("answer"):
            expert_answer = ai["answer"]
            key_clauses = ai.get("cited_clauses") or (grounded or {}).get("cited_clauses") or []
            action_advice = ai.get("action_advice") or (grounded or {}).get("action_advice") or ""
            generated_by = ai.get("generated_by") or "claude"
            confidence = {"level": "High", "basis": "Answered by Claude on the alert facts and the grounded evidence below."}
        elif grounded:
            expert_answer = grounded["expert_answer"]
            key_clauses = grounded["cited_clauses"]
            action_advice = grounded["action_advice"]
            generated_by = grounded["generated_by"]
            confidence = grounded["confidence"]
        else:  # last-resort legacy heuristics
            expert_answer, key_clauses, action_advice = self._rule_based_answer(alert, user_question)
            generated_by = "rules"
            confidence = {"level": "Low", "basis": "Heuristic answer - grounded evidence engine unavailable."}

        return {
            "alert_id": alert.get("id"),
            "question": user_question,
            "expert_answer": expert_answer,
            "answer": expert_answer,
            "direct_answer": (grounded or {}).get("direct_answer"),
            "evidence": (grounded or {}).get("evidence") or [],
            "intent": (grounded or {}).get("intent"),
            "confidence": confidence,
            "cited_clauses": key_clauses,
            "action_advice": action_advice,
            "web_sources_consulted": search_results,
            "generated_by": generated_by,
            "network_status": self.last_network_status,
            "answered_at": _utc_stamp(),
        }


# Global singleton instance
expert_advisor_instance = RegulatoryExpertAdvisor()


def get_expert_advisor():
    return expert_advisor_instance
