"""
Gunicorn configuration file.
Gunicorn auto-discovers this file when run from the project root.
This ensures PYTHONPATH is set correctly regardless of how the start command is configured.
"""
import os
import sys

# Ensure the project root is in sys.path so `albatross_pro` package is importable
# This is needed because albatross_pro is NOT installed as a package (no setup.py/pyproject.toml)
project_root = os.path.dirname(os.path.abspath(__file__))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# Workers
workers = int(os.getenv("WEB_CONCURRENCY", "4"))
worker_class = "uvicorn.workers.UvicornWorker"

# Binding
bind = f"0.0.0.0:{os.getenv('PORT', '8000')}"

# Logging
loglevel = "info"
accesslog = "-"
errorlog = "-"
