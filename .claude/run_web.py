"""Serve TRADEGEN as a web app on 127.0.0.1 without opening a browser, so the
Browser pane can screenshot each page. Dev-only launcher: Flet's exported
ASGI app under uvicorn. The port comes from PORT (the preview harness assigns
one) and falls back to 8562."""
import os, sys
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT); os.chdir(ROOT)
import flet as ft
import uvicorn
import main

app = ft.run(main.main, export_asgi_app=True, assets_dir=os.path.join(ROOT, "assets"))
uvicorn.run(app, host="127.0.0.1", port=int(os.environ.get("PORT", "8562")), log_level="info")
