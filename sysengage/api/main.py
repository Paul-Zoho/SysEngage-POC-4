"""
FastAPI application entry point for SysEngage.

Per Row 4 Applied §6: FastAPI with Jinja2 server-rendered templates.
No authentication for v1 (single-tenant prototype).
No JS framework — Jinja templates suffice for Source Capture UI.

Routes:
  GET  /           → redirect to /source-capture
  GET  /source-capture    → upload form
  POST /source-capture    → trigger mechanism, redirect to summary
  GET  /source-capture/{pass_id}  → execution summary view
"""

import os
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import RedirectResponse

from api.source_capture import router as source_capture_router
from api.row_lens import router as row_lens_router

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

app = FastAPI(
    title="SysEngage",
    description="AI-powered Systems Engineering Tool — Zachman framework analysis",
    version="0.1.0",
)

app.mount(
    "/static",
    StaticFiles(directory=os.path.join(BASE_DIR, "static")),
    name="static",
)

app.include_router(source_capture_router)
app.include_router(row_lens_router)


@app.get("/", include_in_schema=False)
async def root() -> RedirectResponse:
    return RedirectResponse(url="/source-capture")
