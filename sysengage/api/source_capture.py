"""
FastAPI routes for Source Capture.

Per Row 4 Applied §6 and Implementation Spec §12.
Provides:
  GET  /source-capture          → upload form (Jinja template)
  POST /source-capture          → file upload, run mechanism, redirect to summary
  GET  /source-capture/{pass_id} → execution summary (Jinja template)

No /re-execute endpoint for v1 per architectural decision confirmed in Plan Mode.
Re-execution is exercisable via the mechanism API directly (tested via pytest).
"""

import os
import shutil
import tempfile
from pathlib import Path

from fastapi import APIRouter, File, Form, Request, UploadFile
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import select

from core.db import get_session
from core.orchestrator import run_source_capture_for_project
from models.analysis_pass import AnalysisPassModel
from models.source import SourceModel
from models.segment import SegmentModel
from models.source_atom import SourceAtomModel

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
templates = Jinja2Templates(directory=os.path.join(BASE_DIR, "templates"))

router = APIRouter(prefix="/source-capture", tags=["source-capture"])

DEFAULT_PROJECT_ID = "PROJ001"
DEFAULT_PRACTITIONER_ID = "SH002"


@router.get("", response_class=HTMLResponse)
async def upload_form(request: Request) -> HTMLResponse:
    """Render the file upload form."""
    return templates.TemplateResponse(
        "source_capture/upload.html",
        {"request": request},
    )


@router.post("", response_class=RedirectResponse)
async def run_capture(
    request: Request,
    file: UploadFile = File(...),
    project_id: str = Form(default=DEFAULT_PROJECT_ID),
    practitioner_id: str = Form(default=DEFAULT_PRACTITIONER_ID),
) -> RedirectResponse:
    """
    Receive uploaded file, run Source Capture mechanism, redirect to summary.

    Saves uploaded file to a temp directory, invokes the orchestrator,
    then redirects to the execution summary page.
    """
    tmp_dir = tempfile.mkdtemp(prefix="sysengage_upload_")
    try:
        filename = file.filename or "uploaded_file"
        tmp_path = Path(tmp_dir) / filename

        with open(tmp_path, "wb") as f:
            shutil.copyfileobj(file.file, f)

        result = run_source_capture_for_project(
            tmp_path,
            project_id=project_id,
            practitioner_id=practitioner_id,
        )
    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)

    return RedirectResponse(
        url=f"/source-capture/{result.pass_id}",
        status_code=303,
    )


@router.get("/{pass_id}", response_class=HTMLResponse)
async def execution_summary(request: Request, pass_id: str) -> HTMLResponse:
    """
    Render the execution summary for a completed Source Capture pass.
    Queries the ledger for AnalysisPass, Sources, Segments, and SourceAtoms.
    """
    session = get_session()
    try:
        analysis_pass = session.execute(
            select(AnalysisPassModel).where(AnalysisPassModel.pass_id == pass_id)
        ).scalar_one_or_none()

        if not analysis_pass:
            return templates.TemplateResponse(
                "source_capture/upload.html",
                {
                    "request": request,
                    "error": f"AnalysisPass {pass_id} not found.",
                },
                status_code=404,
            )

        outputs = analysis_pass.outputs or {}
        mechanism_data = outputs.get("mechanism_data", {})
        read_witness = outputs.get("read_witness", {})

        source_ids = mechanism_data.get("source_ids", [])
        sources = []
        if source_ids:
            sources = session.execute(
                select(SourceModel).where(SourceModel.source_id.in_(source_ids))
            ).scalars().all()

        segments = session.execute(
            select(SegmentModel).where(
                SegmentModel.project_id == analysis_pass.project_id
            )
        ).scalars().all()

        atom_count = mechanism_data.get("source_atom_count", 0)

    finally:
        session.close()

    return templates.TemplateResponse(
        "source_capture/summary.html",
        {
            "request": request,
            "analysis_pass": analysis_pass,
            "read_witness": read_witness,
            "mechanism_data": mechanism_data,
            "sources": sources,
            "segments": segments,
            "atom_count": atom_count,
            "outputs": outputs,
        },
    )
