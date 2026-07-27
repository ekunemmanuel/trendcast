"""
app.py — TrendCast Web Server

Endpoints:
  GET  /                              serve index.html
  POST /api/analyze                   upload CSV/Excel file → start analysis
  GET  /api/samples                   list built-in sample datasets
  POST /api/analyze_sample/<sample_id> start analysis on a sample dataset
  GET  /api/status/<job_id>           poll analysis progress & results

Usage:
    .venv\\Scripts\\python app.py
    Open http://localhost:5000
"""

import os
import threading
import uuid

from flask import Flask, jsonify, request, send_from_directory
from werkzeug.utils import secure_filename

# ── Config ─────────────────────────────────────────────────────────────────────

UPLOAD_DIR  = "uploads"
SAMPLES_DIR = "samples"
STATIC_DIR  = "static"
ALLOWED_EXTS = {".csv", ".xlsx", ".xls"}

SAMPLE_DATASETS = {
    "monthly_car_sales": {
        "filename": "monthly_car_sales.csv",
        "title": "🚗 Monthly Car Sales",
        "description": "108 months of car sales data (1960–1968)",
        "badge": "Monthly"
    },
    "coffee_shop_sales": {
        "filename": "coffee_shop_sales.csv",
        "title": "☕ Coffee Shop Sales",
        "description": "Daily revenue aggregated from 3,600+ transactions",
        "badge": "Daily"
    },
    "retailers_sales": {
        "filename": "retailers_sales.csv",
        "title": "🏬 Retailers Sales Index",
        "description": "332 months of US retail sales index (1992–2019)",
        "badge": "Monthly"
    },
    "house_property_sales": {
        "filename": "house_property_sales.csv",
        "title": "🏡 House Property Index",
        "description": "51 quarters of property sales index (2007–2019)",
        "badge": "Quarterly"
    }
}

_jobs: dict[str, dict] = {}
_lock = threading.Lock()

app = Flask(__name__, static_folder=STATIC_DIR)


def _allowed(filename: str) -> bool:
    return os.path.splitext(filename)[1].lower() in ALLOWED_EXTS


# ── Routes ─────────────────────────────────────────────────────────────────────

@app.route("/")
def index():
    return send_from_directory(STATIC_DIR, "index.html")


@app.route("/api/samples", methods=["GET"])
def list_samples():
    """Return available sample datasets."""
    samples = []
    for s_id, s_info in SAMPLE_DATASETS.items():
        samples.append({
            "id": s_id,
            "title": s_info["title"],
            "description": s_info["description"],
            "badge": s_info["badge"]
        })
    return jsonify(samples)


@app.route("/api/analyze", methods=["POST"])
def start_analyze():
    """Accept a file upload and kick off background analysis."""
    if "file" not in request.files:
        return jsonify({"error": "No file provided"}), 400

    file = request.files["file"]
    if not file.filename:
        return jsonify({"error": "Empty filename"}), 400
    if not _allowed(file.filename):
        allowed = ", ".join(sorted(ALLOWED_EXTS))
        return jsonify({"error": f"Unsupported file type. Allowed: {allowed}"}), 400

    date_col = request.form.get("date_col") or None
    target_col = request.form.get("target_col") or None

    test_size_val = request.form.get("test_size")
    test_size = int(test_size_val) if test_size_val and test_size_val.isdigit() else None

    os.makedirs(UPLOAD_DIR, exist_ok=True)
    safe_name = secure_filename(file.filename)
    unique_path = os.path.join(UPLOAD_DIR, f"{uuid.uuid4().hex[:8]}_{safe_name}")
    file.save(unique_path)

    job_id = uuid.uuid4().hex[:12]
    with _lock:
        _jobs[job_id] = {
            "status": "running",
            "filename": safe_name,
            "result": None,
            "error": None,
        }

    def _run():
        try:
            from analyze import analyze_file
            result = analyze_file(unique_path, date_col, target_col, test_size)
            with _lock:
                _jobs[job_id]["status"] = "done"
                _jobs[job_id]["result"] = result
        except Exception as exc:
            with _lock:
                _jobs[job_id]["status"] = "error"
                _jobs[job_id]["error"] = str(exc)

    threading.Thread(target=_run, daemon=True).start()
    return jsonify({"job_id": job_id, "filename": safe_name})


@app.route("/api/analyze_sample/<sample_id>", methods=["POST"])
def analyze_sample(sample_id: str):
    """Run analysis on a built-in sample dataset."""
    if sample_id not in SAMPLE_DATASETS:
        return jsonify({"error": f"Sample dataset '{sample_id}' not found."}), 404

    s_info = SAMPLE_DATASETS[sample_id]
    sample_path = os.path.join(SAMPLES_DIR, s_info["filename"])

    if not os.path.exists(sample_path):
        return jsonify({"error": f"Sample file '{s_info['filename']}' is missing."}), 500

    job_id = uuid.uuid4().hex[:12]
    with _lock:
        _jobs[job_id] = {
            "status": "running",
            "filename": s_info["filename"],
            "result": None,
            "error": None,
        }

    def _run():
        try:
            from analyze import analyze_file
            result = analyze_file(sample_path)
            with _lock:
                _jobs[job_id]["status"] = "done"
                _jobs[job_id]["result"] = result
        except Exception as exc:
            with _lock:
                _jobs[job_id]["status"] = "error"
                _jobs[job_id]["error"] = str(exc)

    threading.Thread(target=_run, daemon=True).start()
    return jsonify({"job_id": job_id, "filename": s_info["filename"]})


@app.route("/api/status/<job_id>")
def job_status(job_id: str):
    """Return the current state of an analysis job."""
    with _lock:
        job = _jobs.get(job_id)
    if job is None:
        return jsonify({"error": "Job not found"}), 404
    return jsonify(job)


# ── Entry point ────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    os.makedirs(UPLOAD_DIR, exist_ok=True)
    os.makedirs(SAMPLES_DIR, exist_ok=True)
    os.makedirs(os.path.join(STATIC_DIR, "plots"), exist_ok=True)
    print("\n  TrendCast  ->  http://localhost:5000\n")
    app.run(debug=False, port=5000)
