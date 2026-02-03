from fastapi import APIRouter, Request, Depends, BackgroundTasks
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from core.audit.config_models import AuditConfig
from core.audit.loader import load_table
import yaml
import os

router = APIRouter()
templates = Jinja2Templates(directory="core/web/templates")

def get_current_user(request: Request):
    user = request.session.get("user")
    if not user:
        return None
    return user

@router.get("/dashboard", response_class=HTMLResponse)
async def dashboard(request: Request):
    from core.audit.logger import log_audit_event
    user = get_current_user(request)
    if not user:
        return RedirectResponse(url="/login")
    
    log_audit_event("VIEW_DASHBOARD", user_id=user["username"], ip_address=request.client.host, details="User accessed dashboard")
    
    # Load Config to see available tables
    config_path = "config/audit.yaml"
    tables = []
    if os.path.exists(config_path):
        with open(config_path, "r") as f:
            cfg = yaml.safe_load(f) or {}
            tables = list(cfg.get("tables", {}).keys())
            
    # List reports
    reports = []
    output_dir = "outputs"
    if os.path.exists(output_dir):
        # Just simple listing of subdirectories
        reports = sorted([d for d in os.listdir(output_dir) if os.path.isdir(os.path.join(output_dir, d))], reverse=True)

    return templates.TemplateResponse("dashboard.html", {
        "request": request, 
        "user": user, 
        "tables": tables,
        "reports": reports
    })

@router.post("/run-audit")
async def run_audit_endpoint(request: Request, background_tasks: BackgroundTasks):
    from core.audit.logger import log_audit_event
    user = get_current_user(request)
    if not user:
        return RedirectResponse(url="/login")
        
    log_audit_event("TRIGGER_AUDIT", user_id=user["username"], ip_address=request.client.host, details="User triggered new audit")
        
    # In a real app, we would read form data for specific tables
    # form = await request.form()
    # selected_tables = form.getlist("tables")
    
    # Trigger Audit in Background
    # We need to import run_audit here to avoid circular imports?
    # Or just run it as a subprocess to be safe/clean
    import subprocess
    
    def _run_audit_task():
        # Running via subprocess to ensure clean state and independence
        # Passing no_auth=True via environment variable or flag if we modify run_audit.py further?
        # Actually our valid user is authenticated in Web session. 
        # The background worker acts as "System".
        # We might need to adjust run_audit to accept a "bypass_auth" flag or similar if running programmatically.
        # But for now, let's just run it. If run_audit demands input, this will hang.
        # FIX: We need runs_audit to accept a flag to skip CLI auth.
        subprocess.run(["python", "run_audit.py", "--no-input", "--no-auth"], capture_output=True)

    # background_tasks.add_task(_run_audit_task)
    # For MVP, let's not actually run it async as we haven't modified run_audit to NOT block on input yet.
    # We will just show a message.
    
    return templates.TemplateResponse("dashboard.html", {
        "request": request, 
        "user": user, 
        "tables": [],
        "reports": [],
        "message": "Audit triggered! (Simulation - requires update to run_audit.py to be non-interactive)"
    })
