from __future__ import annotations

import os
import uuid
from pathlib import Path

from fastapi import APIRouter, File, HTTPException, Request, UploadFile

from app.core.config import get_settings
from app.core.logging import get_logger, request_id_ctx
from app.graphs.contract_analysis.graph import contract_analysis_graph
from app.schemas.contract import ContractAnalysisResponse

router = APIRouter(tags=["contract-analysis"])
logger = get_logger("bayyinah.api.contract")
settings = get_settings()

ALLOWED_EXTENSIONS = {".pdf", ".docx"}


@router.post("/contract-analysis", response_model=ContractAnalysisResponse)
async def analyze_contract(request: Request, file: UploadFile = File(...)) -> ContractAnalysisResponse:
    request_id = request_id_ctx.get()

    suffix = Path(file.filename or "").suffix.lower()
    if suffix not in ALLOWED_EXTENSIONS:
        raise HTTPException(status_code=400, detail="نوع الملف غير مدعوم. يُرجى رفع ملف PDF أو DOCX.")

    contents = await file.read()
    size_mb = len(contents) / (1024 * 1024)
    if size_mb > settings.MAX_FILE_SIZE_MB:
        raise HTTPException(status_code=400, detail=f"حجم الملف يتجاوز الحد المسموح ({settings.MAX_FILE_SIZE_MB}MB).")

    document_id = str(uuid.uuid4())
    upload_dir = Path(settings.UPLOAD_DIR)
    upload_dir.mkdir(parents=True, exist_ok=True)

    file_path = upload_dir / f"{document_id}{suffix}"
    with open(file_path, "wb") as f:
        f.write(contents)

    try:
        initial_state = {
            "document_id": document_id,
            "filename": file.filename,
            "file_path": str(file_path),
            "request_id": request_id,
            "warnings": [],
        }

        result = await contract_analysis_graph.ainvoke(initial_state)

        return ContractAnalysisResponse(
            document_id=document_id,
            filename=file.filename or "document",
            summary=result["summary"],
            clauses=result.get("clause_analyses", []),
            risks=result.get("risks", []),
            missing_clauses=result.get("missing_clauses", []),
            recommendations_ar=result.get("recommendations_ar", []),
            overall_risk_level=result.get("overall_risk_level", "low"),
            warnings=result.get("warnings", []),
            request_id=request_id,
        )
    finally:
        try:
            os.remove(file_path)
        except OSError:
            pass
