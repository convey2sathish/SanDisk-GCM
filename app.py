"""
GCM Platform 2.0 - Flask entry point.

Thin composition root: builds the Flask app, wires shared context (store,
surveillance engine, knowledge base) and registers every routes_*.py module.
Run:  python app.py            (developer mode, http://localhost:5000)
Build: pyinstaller GCM_Platform.spec --clean -y
"""
import logging
import os
import sys
import threading
import time
import webbrowser

from flask import Flask, jsonify, render_template

import config
import compliance_db as db
import store as store_module
import reg_surveillance

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
log = logging.getLogger("gcm")

STARTED_AT = time.time()


def create_app():
    config.ensure_data_dir()
    the_store = store_module.get_store()
    surveillance = reg_surveillance.get_surveillance_engine(db, store=the_store)
    import kb_review
    kb_review.init(db)  # apply human-approved overrides on top of the read-only seed

    app = Flask(
        __name__,
        template_folder=config.bundle_path("templates"),
        static_folder=config.bundle_path("static"),
    )
    app.config["JSON_SORT_KEYS"] = False
    app.config["MAX_CONTENT_LENGTH"] = 512 * 1024 * 1024  # document uploads
    app.json.sort_keys = False
    if not config.IS_FROZEN:
        app.config["SEND_FILE_MAX_AGE_DEFAULT"] = 0  # developer mode: never cache static assets

    ctx = {"store": the_store, "surveillance": surveillance, "db": db, "started_at": STARTED_AT}

    @app.route("/")
    def index():
        settings = config.load_settings()
        return render_template(
            "index.html",
            company=settings.get("company_name") or "SanDisk",
            version=config.APP_VERSION,
            codename=config.APP_CODENAME,
        )

    @app.route("/favicon.ico")
    def favicon():
        return app.send_static_file("img/favicon.svg")

    @app.errorhandler(404)
    def not_found(_e):
        return jsonify({"error": "Not found"}), 404

    @app.errorhandler(405)
    def not_allowed(_e):
        return jsonify({"error": "Method not allowed"}), 405

    @app.errorhandler(413)
    def too_large(_e):
        return jsonify({"error": "Upload too large (limit 512 MB)"}), 413

    @app.errorhandler(Exception)
    def unhandled(e):
        log.exception("Unhandled error: %s", e)
        return jsonify({"error": f"Internal error: {type(e).__name__}: {e}"}), 500

    @app.after_request
    def security_headers(resp):
        resp.headers.setdefault("X-Content-Type-Options", "nosniff")
        resp.headers.setdefault("X-Frame-Options", "SAMEORIGIN")
        resp.headers.setdefault("Referrer-Policy", "no-referrer")
        if resp.mimetype == "application/json" or "spreadsheetml" in (resp.mimetype or "") or resp.mimetype == "application/zip":
            resp.headers["Cache-Control"] = "no-store"
        return resp

    import routes_core
    import routes_alerts
    import routes_docaudit
    import routes_risk
    import routes_review

    for mod in (routes_core, routes_alerts, routes_docaudit, routes_risk, routes_review):
        mod.register(app, ctx)
        log.info("Registered %s", mod.__name__)

    _start_auto_scan(surveillance)
    return app


def _start_auto_scan(surveillance):
    """Optional periodic feed scan (settings.surveillance_auto_scan_hours > 0)."""
    def loop():
        while True:
            hours = 0
            try:
                hours = float(config.load_settings().get("surveillance_auto_scan_hours") or 0)
            except (TypeError, ValueError):
                hours = 0
            if hours <= 0:
                time.sleep(300)
                continue
            try:
                surveillance.scan_all_sources()
            except Exception as e:  # pragma: no cover - background safety net
                log.warning("Auto-scan failed: %s", e)
            time.sleep(max(hours, 0.25) * 3600)

    t = threading.Thread(target=loop, name="gcm-autoscan", daemon=True)
    t.start()


app = create_app()


def _open_browser(url):
    try:
        webbrowser.open(url)
    except Exception:
        pass


if __name__ == "__main__":
    settings = config.load_settings()
    port = int(os.environ.get("GCM_PORT") or settings.get("port") or 5000)
    host = os.environ.get("GCM_HOST", "127.0.0.1")
    url = f"http://localhost:{port}"
    print("=" * 72)
    print(f"  {config.APP_NAME} v{config.APP_VERSION} '{config.APP_CODENAME}'")
    print(f"  URL:        {url}")
    print(f"  Data dir:   {config.DATA_DIR}")
    print(f"  Mode:       {'standalone executable' if config.IS_FROZEN else 'developer'}")
    print("=" * 72)
    if settings.get("open_browser", True) and os.environ.get("GCM_NO_BROWSER") != "1":
        threading.Timer(1.2, _open_browser, args=(url,)).start()
    app.run(host=host, port=port, debug=False, threaded=True, use_reloader=False)
