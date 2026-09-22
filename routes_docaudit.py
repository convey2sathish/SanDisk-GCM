"""
routes_docaudit.py - /api/documents/* (Document Impact Audit v2).

Endpoints (see docs/ARCHITECTURE_CONTRACT.md §4 "Documents"):
  POST /api/documents/scan-folder      {folder_path, recursive}     -> Audit report v2
  POST /api/documents/upload-scan      multipart files[]            -> Audit report v2 (temp dir, cleaned up)
  GET  /api/documents/last-report                                   -> last report or {documents: []}
  GET  /api/documents/export-audit                                  -> xlsx (4 sheets) of the last report
  POST /api/documents/generate-samples {target_dir?}                -> {success, message, files[], report}
  GET  /api/documents/browse-dialog                                 -> {success, folder_path} (tkinter)
  POST /api/documents/explain          {index}                      -> plain-language explanation of one document
"""
import datetime as _dt
import logging
import os
import re
import shutil
import tempfile
import threading

from flask import jsonify, request, send_file

import doc_audit_engine as engine

log = logging.getLogger("gcm.docaudit")
XLSX = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
DEFAULT_SAMPLE_DIR = os.path.join(os.path.expanduser("~"), "GCM_Example_Documents")
_scan_lock = threading.Lock()
_SAFE_SEGMENT = re.compile(r"[^A-Za-z0-9._ \-()\[\]&+,]+")


def _validate_folder(raw):
    """Return (abs_path, error). Rejects empty / relative / UNC-less weirdness with a clear message."""
    p = str(raw or "").strip().strip('"').strip("'")
    if not p:
        return None, "Enter a folder path (for example C:\\Compliance_Docs)."
    if any(ch in p for ch in "\x00\n\r\t"):
        return None, "The folder path contains control characters."
    if p.startswith("\\\\?\\"):
        p = p[4:]
    if not os.path.isabs(p):
        return None, f"'{p}' is a relative path. Please enter a full path such as C:\\Folder\\Compliance_Docs."
    p = os.path.normpath(p)
    if not os.path.exists(p):
        return None, f"Folder not found: {p}. Check the drive letter and spelling, or use Browse."
    if not os.path.isdir(p):
        return None, f"{p} is a file, not a folder. Point the scanner at the folder that contains your documents."
    try:
        os.listdir(p)
    except PermissionError:
        return None, f"Access denied to {p}. Run the platform with an account that can read this folder."
    except OSError as e:
        return None, f"Cannot open {p}: {e.strerror or e}"
    return p, None


def _safe_relpath(name):
    """Turn a browser-supplied filename / webkitRelativePath into a safe relative path under the temp dir."""
    parts = re.split(r"[\\/]+", str(name or ""))
    clean = []
    for seg in parts:
        seg = seg.strip()
        if not seg or seg in (".", "..") or seg.startswith("~$"):
            continue
        seg = _SAFE_SEGMENT.sub("_", seg)[:150]
        if seg:
            clean.append(seg)
    if not clean:
        return None
    return os.path.join(*clean)


def register(app, ctx):
    store = ctx["store"]

    def _live():
        try:
            return store.alerts(), store.products()
        except Exception as e:  # pragma: no cover - store failure must not block a scan
            log.warning("store unavailable, using seed knowledge: %s", e)
            return None, None

    def _persist(report):
        try:
            store.set_last_audit(report)
        except Exception as e:  # pragma: no cover
            log.warning("could not persist audit report: %s", e)

    # ------------------------------------------------------------------ scan a local folder
    @app.post("/api/documents/scan-folder")
    def docaudit_scan_folder():
        data = request.get_json(silent=True) or {}
        folder, err = _validate_folder(data.get("folder_path"))
        if err:
            return jsonify({"error": err}), 400
        recursive = data.get("recursive", True)
        if isinstance(recursive, str):
            recursive = recursive.strip().lower() not in ("0", "false", "no", "off")
        alerts, products = _live()
        with _scan_lock:
            report = engine.scan_directory(folder, recursive=bool(recursive), alerts=alerts, products=products)
        if report.get("error"):
            return jsonify({"error": report["error"]}), 400
        _persist(report)
        return jsonify(report)

    # ------------------------------------------------------------------ browser upload
    @app.post("/api/documents/upload-scan")
    def docaudit_upload_scan():
        files = request.files.getlist("files") or request.files.getlist("files[]")
        if not files:
            return jsonify({"error": "No files received. Select a folder (or drop files) and try again."}), 400
        tmp = tempfile.mkdtemp(prefix="gcm_docaudit_")
        saved = []
        try:
            for f in files:
                rel = _safe_relpath(f.filename)
                if not rel:
                    continue
                dest = os.path.join(tmp, rel)
                if not os.path.abspath(dest).startswith(os.path.abspath(tmp)):
                    continue
                os.makedirs(os.path.dirname(dest), exist_ok=True)
                f.save(dest)
                saved.append(dest)
            if not saved:
                return jsonify({"error": "None of the uploaded files could be saved."}), 400
            alerts, products = _live()
            supported = [p for p in saved if os.path.splitext(p)[1].lower() in engine.SUPPORTED_EXTS]
            with _scan_lock:
                report = engine.scan_files(saved, alerts=alerts, products=products, display_root=tmp,
                                           folder_label=f"Browser upload ({len(supported)} files)")
            report["upload"] = {"received": len(files), "saved": len(saved), "supported": len(supported)}
            _persist(report)
            return jsonify(report)
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    # ------------------------------------------------------------------ last report / export
    @app.get("/api/documents/last-report")
    def docaudit_last_report():
        report = store.last_audit() or {}
        if not report or not isinstance(report, dict) or "documents" not in report:
            return jsonify({"documents": [], "total_documents": 0, "impacted_documents": 0})
        return jsonify(report)

    @app.get("/api/documents/export-audit")
    def docaudit_export_audit():
        report = store.last_audit() or {}
        if not report or not report.get("documents"):
            return jsonify({"error": "No audit report available yet. Scan a folder first, then export."}), 404
        buf = engine.export_audit_to_excel(report)
        stamp = _dt.datetime.now().strftime("%Y%m%d_%H%M")
        return send_file(buf, as_attachment=True, download_name=f"GCM_Document_Revision_Directive_{stamp}.xlsx", mimetype=XLSX)

    # ------------------------------------------------------------------ samples
    @app.post("/api/documents/generate-samples")
    def docaudit_generate_samples():
        data = request.get_json(silent=True) or {}
        target = str(data.get("target_dir") or DEFAULT_SAMPLE_DIR).strip().strip('"')
        if not os.path.isabs(target):
            return jsonify({"error": f"target_dir must be an absolute path (got '{target}')."}), 400
        target = os.path.normpath(target)
        try:
            os.makedirs(target, exist_ok=True)
            files = engine.generate_sample_compliance_docs(target)
        except PermissionError:
            return jsonify({"error": f"Cannot write to {target}. Choose a folder you have write access to (target_dir)."}), 400
        except OSError as e:
            return jsonify({"error": f"Could not create example documents in {target}: {e.strerror or e}"}), 400
        alerts, products = _live()
        with _scan_lock:
            report = engine.scan_directory(target, recursive=False, alerts=alerts, products=products)
        _persist(report)
        return jsonify({"success": True, "message": f"Created {len(files)} generic example documents in {target} and audited them.",
                        "target_dir": target, "files": [os.path.basename(f) for f in files], "report": report})

    # ------------------------------------------------------------------ native folder picker
    @app.get("/api/documents/browse-dialog")
    def docaudit_browse_dialog():
        result = {"success": False, "error": "Folder picker unavailable"}

        def _pick():
            try:
                import tkinter as tk
                from tkinter import filedialog
                root = tk.Tk()
                root.withdraw()
                root.attributes("-topmost", True)
                initial = request.args.get("initial") or DEFAULT_SAMPLE_DIR
                path = filedialog.askdirectory(title="Select the compliance documents folder", initialdir=initial if os.path.isdir(initial) else None, mustexist=True)
                root.destroy()
                if path:
                    result.update({"success": True, "folder_path": os.path.normpath(path)})
                else:
                    result.update({"success": False, "error": "No folder selected."})
            except Exception as e:  # no display / tkinter missing
                result.update({"success": False, "error": f"The native folder picker could not open ({type(e).__name__}). Type the path or use the browser folder upload instead."})

        t = threading.Thread(target=_pick, daemon=True)
        t.start()
        t.join(timeout=300)
        if t.is_alive():
            return jsonify({"success": False, "error": "Folder picker timed out."})
        return jsonify(result)

    # ------------------------------------------------------------------ explain one document
    @app.post("/api/documents/explain")
    def docaudit_explain():
        data = request.get_json(silent=True) or {}
        report = store.last_audit() or {}
        docs = report.get("documents") or []
        try:
            idx = int(data.get("index"))
        except (TypeError, ValueError):
            return jsonify({"error": "index must be an integer position in the last report's documents list"}), 400
        if idx < 0 or idx >= len(docs):
            return jsonify({"error": f"No document at index {idx} (last report has {len(docs)} documents). Re-run the scan."}), 404
        alerts, _ = _live()
        explanation = engine.explain_document(docs[idx], alerts=alerts)
        explanation["index"] = idx
        explanation["filename"] = docs[idx].get("metadata", {}).get("filename")
        return jsonify(explanation)
