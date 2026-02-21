import asyncio
import json
import os
import shutil
from datetime import datetime
from typing import List, Optional

import yaml
from fastapi import APIRouter, BackgroundTasks, File, Request, UploadFile
from fastapi.responses import JSONResponse, StreamingResponse

from core.audit.logger import get_logger

router = APIRouter(prefix="/api")
logger = get_logger(__name__)

# Simple in-memory state for the MVP
# In production, use Redis or a database
AUDIT_STATE = {
    "status": "idle",  # idle, running, completed, error
    "message": "Ready to start.",
    "logs": [],
    "progress": 0,
    "last_run_id": None,
    "results_summary": {"pass": 0, "warn": 0, "fail": 0, "error": 0, "total": 0},
    "results_details": [],
}


def get_current_user(request: Request):
    return request.session.get("user")


@router.post("/upload")
async def upload_files(
    request: Request,
    config: Optional[UploadFile] = File(None),
    data_files: Optional[List[UploadFile]] = File(None),
):
    """Upload config YAML and/or data CSV files via drag-and-drop or file picker."""
    user = get_current_user(request)
    if not user:
        return JSONResponse({"error": "Unauthorized"}, status_code=401)

    uploaded = {"config": None, "data_files": []}

    # Save config YAML
    if config and config.filename:
        os.makedirs("config", exist_ok=True)
        config_dest = os.path.join("config", "audit.yaml")
        with open(config_dest, "wb") as f:
            shutil.copyfileobj(config.file, f)
        uploaded["config"] = config.filename
        logger.info(f"Uploaded config: {config.filename} → {config_dest}")

    # Save data CSV files
    if data_files:
        os.makedirs("data", exist_ok=True)
        for df in data_files:
            if df.filename:
                dest = os.path.join("data", df.filename)
                with open(dest, "wb") as f:
                    shutil.copyfileobj(df.file, f)
                uploaded["data_files"].append(df.filename)
                logger.info(f"Uploaded data file: {df.filename} → {dest}")

    return {"status": "ok", "uploaded": uploaded}


@router.get("/config")
async def get_config(request: Request):
    """Return available tables from config."""
    user = get_current_user(request)
    if not user:
        return JSONResponse({"error": "Unauthorized"}, status_code=401)

    config_path = "config/audit.yaml"
    if os.path.exists(config_path):
        with open(config_path, "r") as f:
            cfg = yaml.safe_load(f) or {}
            return {"tables": list(cfg.get("tables", {}).keys())}
    return {"tables": []}


@router.get("/reports")
async def list_reports(request: Request):
    """List generated reports."""
    user = get_current_user(request)
    if not user:
        return JSONResponse({"error": "Unauthorized"}, status_code=401)

    output_dir = "outputs"
    reports = []
    if os.path.exists(output_dir):
        # Sort by creation time (newest first)
        dirs = [
            d
            for d in os.listdir(output_dir)
            if os.path.isdir(os.path.join(output_dir, d))
        ]
        dirs.sort(reverse=True)

        for d in dirs:
            reports.append(
                {"id": d, "date": d.split("_")[0], "name": d}  # Rough parsing
            )
    return {"reports": reports}


@router.get("/reports/{report_id}/download")
async def download_report(request: Request, report_id: str, file: str):
    """
    Download a specific file from a report.
    Applies sanitization if it's a CSV and user is not an Admin (or always, for GDPR).
    For now, we enforce sanitization for everyone to be safe.
    """
    import io

    import pandas as pd
    from fastapi.responses import FileResponse

    from core.sanitization.masking import DataSanitizer

    user = get_current_user(request)
    if not user:
        return JSONResponse({"error": "Unauthorized"}, status_code=401)

    file_path = os.path.join("outputs", report_id, file)
    if not os.path.exists(file_path):
        return JSONResponse({"error": "File not found"}, status_code=404)

    # If it's a CSV, sanitize it
    if file.endswith(".csv"):
        try:
            df = pd.read_csv(file_path)
            sanitizer = DataSanitizer()
            sanitized_df = sanitizer.sanitize(df)

            stream = io.StringIO()
            sanitized_df.to_csv(stream, index=False)
            response = StreamingResponse(
                iter([stream.getvalue()]), media_type="text/csv"
            )
            response.headers["Content-Disposition"] = (
                f"attachment; filename=sanitized_{file}"
            )
            return response
        except Exception as e:
            logger.error(f"Error sanitizing file: {e}")
            return JSONResponse({"error": "Error processing file"}, status_code=500)

    # For other files (PDFs, etc.), serve as is (assuming they are generated safely or generic)
    return FileResponse(file_path, filename=file)


async def event_generator():
    """Generate SSE events from AUDIT_STATE."""
    while True:
        # Check if client is still connected (implicitly handled by StreamingResponse)
        # Yield current state
        data = json.dumps(AUDIT_STATE)
        yield f"data: {data}\n\n"

        if AUDIT_STATE["status"] in ["completed", "error", "idle"]:
            # Slow down updates when idle
            await asyncio.sleep(2)
        else:
            # Fast updates when running
            await asyncio.sleep(0.5)


@router.get("/stream")
async def stream_audit_progress(request: Request):
    """Server-Sent Events endpoint for live progress."""
    user = get_current_user(request)
    if not user:
        return JSONResponse({"error": "Unauthorized"}, status_code=401)

    return StreamingResponse(event_generator(), media_type="text/event-stream")


def run_audit_background_task(selected_tables):
    """Task to run in background."""
    AUDIT_STATE["status"] = "running"
    AUDIT_STATE["logs"] = []
    AUDIT_STATE["progress"] = 0
    AUDIT_STATE["message"] = "Initializing audit..."

    try:
        from core.audit.enums import CheckStatus
        from reports.report_builder import build_report
        from run_audit import run_audit

        def progress_callback(msg: str):
            AUDIT_STATE["logs"].append(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}")
            AUDIT_STATE["message"] = msg
            # Simple progress increment (fake logic for MVP)
            if AUDIT_STATE["progress"] < 95:
                AUDIT_STATE["progress"] += 5

        # Run the audit with callback
        # args: config_path, tables_to_run, progress_callback(added via wrapper or direct mod)
        # We need to modify run_audit.py to accept this callback
        results = run_audit(
            tables_to_run=selected_tables,
            no_auth=True,  # Bypass CLI auth
            progress_callback=progress_callback,
        )

        AUDIT_STATE["message"] = "Generating reports..."
        AUDIT_STATE["progress"] = 98

        # Build Report
        build_report(results, client="Web Dashboard User", migration="Manual Web Run")

        # Compute results summary for charts
        summary = {"pass": 0, "warn": 0, "fail": 0, "error": 0, "total": 0}
        details = []
        for r in results:
            status_str = str(getattr(r, "status", "")).lower()
            if "pass" in status_str or status_str == str(CheckStatus.PASS).lower():
                summary["pass"] += 1
            elif "warn" in status_str:
                summary["warn"] += 1
            elif "fail" in status_str:
                summary["fail"] += 1
            elif "error" in status_str:
                summary["error"] += 1
            summary["total"] += 1
            details.append(
                {
                    "name": getattr(r, "name", "Unknown"),
                    "status": status_str,
                    "message": getattr(r, "message", ""),
                }
            )
        AUDIT_STATE["results_summary"] = summary
        AUDIT_STATE["results_details"] = details

        AUDIT_STATE["status"] = "completed"
        AUDIT_STATE["message"] = "Audit completed successfully."
        AUDIT_STATE["progress"] = 100

    except Exception as e:
        AUDIT_STATE["status"] = "error"
        AUDIT_STATE["message"] = f"Error: {str(e)}"
        logger.error(f"Background audit failed: {e}")


@router.post("/audit/start")
async def start_audit(request: Request, background_tasks: BackgroundTasks):
    """Trigger an audit run."""
    user = get_current_user(request)
    if not user:
        return JSONResponse({"error": "Unauthorized"}, status_code=401)

    body = await request.json()
    tables = body.get("tables", [])

    if AUDIT_STATE["status"] == "running":
        return JSONResponse({"error": "Audit already running"}, status_code=409)

    background_tasks.add_task(run_audit_background_task, tables)

    return {"status": "started", "message": "Audit started in background"}


@router.get("/audit/results")
async def get_audit_results(request: Request):
    """Return the latest audit results summary for chart rendering."""
    user = get_current_user(request)
    if not user:
        return JSONResponse({"error": "Unauthorized"}, status_code=401)

    return {
        "status": AUDIT_STATE["status"],
        "summary": AUDIT_STATE["results_summary"],
        "details": AUDIT_STATE["results_details"],
    }
