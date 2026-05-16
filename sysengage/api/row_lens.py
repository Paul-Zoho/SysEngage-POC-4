"""
FastAPI routes for Row-Lens Source Re-Analysis (Phase 3 Pass 3a).

Per spec §1: one POST endpoint triggers the mechanism for a given project
and row_ref. Returns pass_id, execution_status, and row_lens_data summary.

No file upload — mechanism reads Sources from ledger (Source Capture must
have already run for this project).

Routes:
  POST /row-lens-analysis        → run mechanism, return JSON summary
  GET  /row-lens-analysis/{pass_id} → retrieve prior run summary from ledger
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select

from core.db import get_session
from mechanisms.row_lens_source_reanalysis import run
from mechanisms.row_lens_source_reanalysis import RowLensExecutionError
from models.analysis_pass import AnalysisPassModel

router = APIRouter(prefix="/row-lens-analysis", tags=["row-lens"])

DEFAULT_PROJECT_ID = "PROJ001"
DEFAULT_PRACTITIONER_ID = "SH002"


class RowLensRequest(BaseModel):
    project_id: str = Field(default=DEFAULT_PROJECT_ID, min_length=1)
    practitioner_id: str = Field(default=DEFAULT_PRACTITIONER_ID, min_length=1)
    row_ref: int = Field(ge=1, le=6, description="Zachman row number (1-6)")


class RowLensResponse(BaseModel):
    pass_id: str
    execution_status: str
    row_lens_data: dict


@router.post("", response_model=RowLensResponse)
async def run_row_lens(body: RowLensRequest) -> RowLensResponse:
    """
    Trigger Phase 3 Pass 3a Row-Lens Source Re-Analysis.

    Reads Sources from ledger (Source Capture must have completed first).
    At row_ref=1: stream 2 is empty; all Sources processed as residual.
    At row_ref>1: requires Row N-1 Domains and Requirements in ledger.
    """
    try:
        result = run(
            project_id=body.project_id,
            practitioner_id=body.practitioner_id,
            row_ref=body.row_ref,
        )
    except RowLensExecutionError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    return RowLensResponse(
        pass_id=result["pass_id"],
        execution_status=result["execution_status"],
        row_lens_data=result["row_lens_data"],
    )


@router.get("/{pass_id}", response_model=RowLensResponse)
async def get_row_lens_result(pass_id: str) -> RowLensResponse:
    """
    Retrieve a prior Row-Lens Source Re-Analysis run from the ledger.
    """
    session = get_session()
    try:
        record = session.execute(
            select(AnalysisPassModel).where(
                AnalysisPassModel.pass_id == pass_id,
                AnalysisPassModel.mechanism == "RowLensSourceReanalysis",
            )
        ).scalar_one_or_none()
    finally:
        session.close()

    if not record:
        raise HTTPException(
            status_code=404,
            detail=f"RowLensSourceReanalysis pass {pass_id!r} not found.",
        )

    outputs = record.outputs or {}
    return RowLensResponse(
        pass_id=record.pass_id,
        execution_status=record.execution_status,
        row_lens_data=outputs.get("row_lens_data", {}),
    )
