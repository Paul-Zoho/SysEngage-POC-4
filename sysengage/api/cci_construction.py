"""
FastAPI routes for CCI Construction (Phase 3 Pass 3b).

Per spec §1: one POST endpoint triggers the mechanism for a given project
and row_ref. Returns pass_id, execution_status, and cci_data summary.

No file upload — mechanism reads Signals from the ledger (Row-Lens Source
Re-Analysis must have already run for this project and row).

Routes:
  POST /cci-construction           → run mechanism, return JSON summary
  GET  /cci-construction/{pass_id} → retrieve prior run summary from ledger
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select

from core.db import get_session
from mechanisms.cci_construction import CCIConstructionError
from mechanisms.cci_construction import run
from models.analysis_pass import AnalysisPassModel

router = APIRouter(prefix="/cci-construction", tags=["cci-construction"])

DEFAULT_PROJECT_ID = "PROJ001"
DEFAULT_PRACTITIONER_ID = "SH002"


class CCIConstructionRequest(BaseModel):
    project_id: str = Field(default=DEFAULT_PROJECT_ID, min_length=1)
    practitioner_id: str = Field(default=DEFAULT_PRACTITIONER_ID, min_length=1)
    row_ref: int = Field(ge=1, le=6, description="Zachman row number (1-6)")
    skip_deduplication: bool = Field(
        default=False,
        description="When true, Step 4 deduplication is skipped and all raw AI candidates are committed as-is.",
    )


class CCIConstructionResponse(BaseModel):
    pass_id: str
    execution_status: str
    cci_data: dict


@router.post("", response_model=CCIConstructionResponse)
async def run_cci_construction(body: CCIConstructionRequest) -> CCIConstructionResponse:
    """
    Trigger Phase 3 Pass 3b CCI Construction.

    Reads Signals from the ledger for the given row.
    Row-Lens Source Re-Analysis must have completed for this project and row_ref.
    """
    try:
        result = run(
            project_id=body.project_id,
            practitioner_id=body.practitioner_id,
            row_ref=body.row_ref,
            skip_deduplication=body.skip_deduplication,
        )
    except CCIConstructionError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    return CCIConstructionResponse(
        pass_id=result["pass_id"],
        execution_status=result["execution_status"],
        cci_data=result["cci_data"],
    )


@router.get("/{pass_id}", response_model=CCIConstructionResponse)
async def get_cci_construction_result(pass_id: str) -> CCIConstructionResponse:
    """
    Retrieve a prior CCI Construction run from the ledger.
    """
    session = get_session()
    try:
        record = session.execute(
            select(AnalysisPassModel).where(
                AnalysisPassModel.pass_id == pass_id,
                AnalysisPassModel.mechanism.in_(["CCIConstruction", "CellContentItemConstruction"]),
            )
        ).scalar_one_or_none()
    finally:
        session.close()

    if not record:
        raise HTTPException(
            status_code=404,
            detail=f"CCIConstruction pass {pass_id!r} not found.",
        )

    outputs = record.outputs or {}
    return CCIConstructionResponse(
        pass_id=record.pass_id,
        execution_status=record.execution_status,
        cci_data=outputs.get("cci_data", {}),
    )
