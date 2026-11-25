from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.ai.engine import (
    answer_natural_language_query,
    extract_structured_clinical_note,
    generate_patient_summary,
)
from app.core.deps import get_current_user, log_audit
from app.db.session import get_db
from app.models import User
from app.schemas import (
    AIQueryRequest,
    AIQueryResponse,
    AISummaryResponse,
    NoteExtractionRequest,
    NoteExtractionResponse,
)

router = APIRouter(prefix="/api/ai", tags=["AI Medical Summarisation & Retrieval"])


@router.get("/patients/{patient_id}/summary", response_model=AISummaryResponse)
def get_ai_patient_summary(
    patient_id: int,
    refresh: bool = Query(False, description="Force regeneration of AI summary"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        summary = generate_patient_summary(db, patient_id=patient_id, force_refresh=refresh)
        log_audit(
            db,
            current_user.id,
            "AI_GENERATE_SUMMARY",
            patient_id=patient_id,
            detail=f"Generated grounded AI summary for {summary.patient_mrn} (cached={summary.cached})",
        )
        return summary
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))


@router.post("/query", response_model=AIQueryResponse)
def execute_natural_language_query(
    payload: AIQueryRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not payload.query or not payload.query.strip():
        raise HTTPException(status_code=400, detail="Query text cannot be empty.")

    result = answer_natural_language_query(
        db=db,
        query=payload.query.strip(),
        patient_id=payload.patient_id,
    )
    log_audit(
        db,
        current_user.id,
        "AI_HISTORICAL_RETRIEVAL",
        patient_id=payload.patient_id,
        detail=f"NL Query: '{payload.query[:120]}' -> {result.total_matches} matches",
    )
    return result


@router.post("/extract-note", response_model=NoteExtractionResponse)
def extract_clinical_note_entities(
    payload: NoteExtractionRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not payload.note_text or not payload.note_text.strip():
        raise HTTPException(status_code=400, detail="Clinical note text cannot be empty.")

    res = extract_structured_clinical_note(payload.note_text)
    log_audit(
        db,
        current_user.id,
        "AI_EXTRACT_CLINICAL_NOTE",
        detail=f"Extracted structured clinical entities from note ({len(payload.note_text)} chars)",
    )
    return res
