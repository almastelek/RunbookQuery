"""Ingestion API routes."""

import uuid
from datetime import datetime

from fastapi import APIRouter, BackgroundTasks

from runbook_query.api.schemas import IngestRequestSchema, IngestResponseSchema

router = APIRouter(prefix="/ingest", tags=["ingestion"])


# Simple job tracking (in-memory for MVP)
_jobs: dict[str, dict] = {}


@router.post("/start", response_model=IngestResponseSchema)
async def start_ingestion(
    request: IngestRequestSchema,
    background_tasks: BackgroundTasks,
):
    """
    Start an ingestion job.

    Runs asynchronously in the background.
    """
    job_id = f"ingest-{datetime.now().strftime('%Y%m%d')}-{uuid.uuid4().hex[:6]}"

    _jobs[job_id] = {
        "status": "started",
        "sources": request.sources,
        "force": request.force_reindex,
        "created_at": datetime.now(),
    }

    # TODO: Add actual background ingestion task
    # background_tasks.add_task(run_ingestion_job, job_id, request)

    return IngestResponseSchema(
        job_id=job_id,
        status="started",
        message="Ingestion job queued. Use CLI for full ingestion in MVP.",
    )


@router.get("/status/{job_id}")
async def get_job_status(job_id: str):
    """Get status of an ingestion job."""
    if job_id not in _jobs:
        return {"error": "Job not found"}
    return _jobs[job_id]
