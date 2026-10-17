"""Batch I/O endpoints (upload / list / detail / results / generate). Bank communication is SIMULATED only."""
from pathlib import Path
from typing import List, Optional

from fastapi import APIRouter, File, HTTPException, Query, UploadFile
from fastapi.responses import FileResponse

from app.services.batch_pipeline import get_pipeline, TERMINAL
from app.services.synthetic_batch import write_batch

router = APIRouter()


@router.post("/upload")
async def upload_batch(file: UploadFile = File(...)):
    """Accepts .json (record | list | envelope), .jsonl/.ndjson, or .json.gz. Processing is asynchronous."""
    name = (file.filename or "upload.json")
    low = name.lower()
    if not low.endswith((".json", ".jsonl", ".ndjson", ".json.gz", ".jsonl.gz", ".ndjson.gz")):
        raise HTTPException(status_code=415, detail="Unsupported file type. Use .json, .jsonl, .ndjson or .json.gz")
    batch_id = get_pipeline().save_upload(name, file.file)
    return {"batch_id": batch_id, "status": "QUEUED"}


@router.get("")
def list_batches():
    return get_pipeline().list_batches()


@router.post("/generate")
def generate_batch(
    count: int = Query(1000, ge=1, le=1_000_000),
    seed: int = Query(1),
    rails: str = Query("GB,US,EU"),
    duplicate_rate: float = Query(0.0, ge=0.0, le=0.5),
    malformed_rate: float = Query(0.0, ge=0.0, le=0.5),
    repeatable: bool = Query(False, description="true = identical ids/UETRs for the same seed (second run is 100% duplicates by design)"),
):
    """Writes a deterministic synthetic batch (valid MOD-97 IBANs) into the inbox and queues it."""
    pl = get_pipeline()
    batch_id = pl.new_batch_id("GEN")
    path = pl.inbox / f"{batch_id}__synthetic_{count}_seed{seed}.jsonl"
    write_batch(path, count, seed, [r for r in rails.split(",") if r.strip()],
                duplicate_rate=duplicate_rate, malformed_rate=malformed_rate, tag=f"G{seed}" if repeatable else f"G{seed}-{batch_id[-6:]}",
                salt=None if repeatable else batch_id)
    pl.submit_file(path, batch_id=batch_id, filename=path.name)
    return {"batch_id": batch_id, "status": "QUEUED", "count": count}


def _get_or_404(batch_id: str):
    b = get_pipeline().get_batch(batch_id)
    if not b:
        raise HTTPException(status_code=404, detail=f"Batch {batch_id} not found")
    return b


@router.get("/{batch_id}")
def get_batch(batch_id: str):
    return _get_or_404(batch_id)


def _download(batch_id: str, suffix: str, media: str):
    b = _get_or_404(batch_id)
    if b["status"] not in TERMINAL:
        raise HTTPException(status_code=409, detail=f"Batch {batch_id} is {b['status']}; results are available when it finishes")
    p = get_pipeline().outbox / f"{batch_id}.{suffix}"
    if not p.exists():
        raise HTTPException(status_code=404, detail=f"{suffix} not available for batch {batch_id}")
    return FileResponse(str(p), media_type=media, filename=p.name)


@router.get("/{batch_id}/results")
def download_results(batch_id: str):
    return _download(batch_id, "results.jsonl", "application/x-ndjson")


@router.get("/{batch_id}/summary")
def download_summary(batch_id: str):
    return _download(batch_id, "summary.json", "application/json")


@router.get("/{batch_id}/bank-handoff")
def download_bank_handoff(batch_id: str):
    """Simulated bank hand-off file (STP-eligible only; empty/absent in SHADOW mode)."""
    return _download(batch_id, "bank_handoff.jsonl", "application/x-ndjson")
