import json
import uuid
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import desc, select
from sqlalchemy.orm import Session

from app.ai.ai_service import AIService
from app.core.config import settings
from app.core.errors import NotFoundError
from app.document_intelligence.models import DocumentProcessing
from app.document_intelligence.processors import classify_document, extract_structured, select_processor
from app.document_intelligence.schemas import ProcessingResponse
from app.document_intelligence.vision import GeminiVisionProcessor
from app.evidence.models import EvidenceRecord
from app.evidence.storage import storage
from app.services.audit_service import AuditService


def _now():
    return datetime.now(timezone.utc)


def _json(value, default):
    try:
        return json.loads(value or "")
    except (TypeError, json.JSONDecodeError):
        return default


def to_response(record: DocumentProcessing) -> dict:
    return {
        "id": record.id, "organization_id": record.organization_id, "evidence_id": record.evidence_id,
        "processor": record.processor, "processor_version": record.processor_version,
        "document_type": record.document_type, "classification_confidence": record.classification_confidence,
        "status": record.status, "raw_text": record.raw_text, "pages": _json(record.page_data_json, []),
        "structured_data": _json(record.structured_data_json, {}),
        "confidence_metadata": _json(record.confidence_metadata_json, {}),
        "extraction_schema": record.extraction_schema, "error_message": record.error_message,
        "attempt_count": record.attempt_count, "created_at": record.created_at, "updated_at": record.updated_at,
    }


def get_evidence(db: Session, evidence_id: str, organization_id: str):
    record = db.scalar(select(EvidenceRecord).where(
        EvidenceRecord.id == evidence_id,
        EvidenceRecord.organization_id == organization_id,
        EvidenceRecord.status != "DELETED",
    ))
    if record is None:
        raise NotFoundError("Evidence not found.")
    return record


def latest(db: Session, evidence_id: str, organization_id: str):
    get_evidence(db, evidence_id, organization_id)
    result = db.scalar(select(DocumentProcessing).where(
        DocumentProcessing.evidence_id == evidence_id,
        DocumentProcessing.organization_id == organization_id,
    ).order_by(desc(DocumentProcessing.created_at)))
    if result is None:
        raise NotFoundError("Document has not been processed yet.")
    return to_response(result)


def process(db: Session, evidence_id: str, organization_id: str, actor_user_id: str):
    evidence = get_evidence(db, evidence_id, organization_id)
    previous = db.scalar(select(DocumentProcessing).where(
        DocumentProcessing.evidence_id == evidence_id,
        DocumentProcessing.organization_id == organization_id,
    ).order_by(desc(DocumentProcessing.created_at)))
    record = DocumentProcessing(
        id=str(uuid.uuid4()), organization_id=organization_id, evidence_id=evidence_id,
        processor="PENDING", processor_version="PENDING", document_type=evidence.evidence_type,
        status="PROCESSING", attempt_count=(previous.attempt_count + 1 if previous else 1),
        created_at=_now(), updated_at=_now(),
    )
    db.add(record)
    db.commit()
    AuditService.log_event("DOCUMENT_PROCESSING_STARTED", f"Document processing started for '{evidence.original_filename}'.",
                           organization_id=organization_id, actor_user_id=actor_user_id,
                           dispute_id=evidence.dispute_id, resource_type="DOCUMENT_PROCESSING", resource_id=record.id)

    try:
        content = storage.read(evidence.storage_key)
        processor = select_processor(content, evidence.original_filename, evidence.mime_type)
        raw_text, pages, ocr_confidence = processor.process(content, evidence.original_filename, evidence.mime_type)
        document_type, classification_confidence = classify_document(evidence.evidence_type, evidence.original_filename, raw_text)
        structured, schema, extraction_confidence = extract_structured(document_type, raw_text)
        confidence = {**ocr_confidence, **extraction_confidence, "classification_confidence": classification_confidence}

        if settings.ENABLE_VLM_PROCESSING and confidence.get("ocr_confidence", 0) < 0.60 and settings.GEMINI_API_KEY:
            vision = GeminiVisionProcessor(settings.GEMINI_MODEL, settings.GEMINI_API_KEY)
            vision_result = vision.extract(content, evidence.mime_type, document_type)
            if vision_result:
                confidence["vlm_used"] = True
                confidence["vlm_processor"] = vision.name
                confidence["vlm_model"] = vision.version
        else:
            confidence["vlm_used"] = False

        record.processor = processor.name
        record.processor_version = processor.version
        record.document_type = document_type
        record.classification_confidence = classification_confidence
        record.status = "PROCESSED"
        record.raw_text = raw_text
        record.page_data_json = json.dumps([page.model_dump() for page in pages])
        record.structured_data_json = json.dumps(structured)
        record.confidence_metadata_json = json.dumps(confidence)
        record.extraction_schema = schema
        record.updated_at = _now()
        db.commit()
        AuditService.log_event("DOCUMENT_PROCESSED", f"Document '{evidence.original_filename}' processed.",
                               {"document_type": document_type, "processor": processor.name, "processor_version": processor.version},
                               organization_id=organization_id, actor_user_id=actor_user_id,
                               dispute_id=evidence.dispute_id, resource_type="DOCUMENT_PROCESSING", resource_id=record.id)
    except Exception as exc:
        record.status = "FAILED"
        record.processor = record.processor if record.processor != "PENDING" else "DOCUMENT_PROCESSOR"
        record.processor_version = record.processor_version if record.processor_version != "PENDING" else "1.0"
        record.error_message = str(exc)[:500]
        record.updated_at = _now()
        db.commit()
        AuditService.log_event("DOCUMENT_PROCESSING_FAILED", f"Document processing failed for '{evidence.original_filename}'.",
                               {"error": record.error_message}, organization_id=organization_id, actor_user_id=actor_user_id,
                               dispute_id=evidence.dispute_id, resource_type="DOCUMENT_PROCESSING", resource_id=record.id)
    return to_response(record)
