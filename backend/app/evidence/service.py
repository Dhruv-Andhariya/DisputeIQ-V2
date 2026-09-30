import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from sqlalchemy import func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.errors import BadRequestError, ConflictError, NotFoundError
from app.database.db import get_dispute_by_id, save_evidence
from app.models.domain import Evidence, EvidenceCategory
from app.services.audit_service import AuditService
from app.domain.models import DomainDispute
from app.evidence.models import EvidenceRecord
from app.evidence.schemas import EVIDENCE_STATUSES, EVIDENCE_TYPES, SOURCE_TYPES, EvidenceUpdate
from app.evidence.storage import storage

MAX_FILENAME_LENGTH = 255
BLOCKED_EXTENSIONS = {".exe", ".bat", ".cmd", ".com", ".dll", ".msi", ".ps1", ".sh"}


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _metadata(record: EvidenceRecord) -> dict:
    try:
        return json.loads(record.metadata_json or "{}")
    except json.JSONDecodeError:
        return {}


def to_response_data(record: EvidenceRecord) -> dict:
    data = {column.name: getattr(record, column.name) for column in EvidenceRecord.__table__.columns}
    data["metadata"] = _metadata(record)
    data.pop("metadata_json", None)
    return data


def _validate_filename(filename: str) -> str:
    if not filename or len(filename) > MAX_FILENAME_LENGTH or "\x00" in filename:
        raise BadRequestError("Invalid evidence filename.")
    if Path(filename).name != filename or filename in {".", ".."}:
        raise BadRequestError("Evidence filename must not contain a path.")
    if Path(filename).suffix.lower() in BLOCKED_EXTENSIONS:
        raise BadRequestError("Executable evidence files are not allowed.")
    return filename


def _detect_mime(content: bytes, filename: str) -> str:
    suffix = Path(filename).suffix.lower()
    if content.startswith(b"%PDF-") and suffix == ".pdf":
        return "application/pdf"
    if content.startswith(b"\x89PNG\r\n\x1a\n") and suffix == ".png":
        return "image/png"
    if content.startswith(b"\xff\xd8\xff") and suffix in {".jpg", ".jpeg"}:
        return "image/jpeg"
    if content[:6] in {b"GIF87a", b"GIF89a"} and suffix == ".gif":
        return "image/gif"
    if len(content) >= 12 and content[:4] == b"RIFF" and content[8:12] == b"WEBP" and suffix == ".webp":
        return "image/webp"
    if suffix == ".json":
        try:
            json.loads(content.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise BadRequestError("The JSON evidence file is invalid.") from exc
        return "application/json"
    if suffix in {".txt", ".csv"}:
        try:
            content.decode("utf-8")
        except UnicodeDecodeError as exc:
            raise BadRequestError("Text evidence must be valid UTF-8.") from exc
        return "text/csv" if suffix == ".csv" else "text/plain"
    raise BadRequestError("Unsupported evidence file. Use PDF, PNG, JPG, GIF, WEBP, JSON, CSV, or TXT.")


def _resolve_dispute(db: Session, dispute_id: str, organization_id: str):
    domain = db.scalar(select(DomainDispute).where(
        DomainDispute.organization_id == organization_id,
        or_(
            DomainDispute.id == dispute_id,
            DomainDispute.external_dispute_id == dispute_id,
            DomainDispute.legacy_dispute_id == dispute_id,
        ),
    ))
    if domain:
        return {
            "dispute_id": domain.legacy_dispute_id,
            "domain_dispute_id": domain.id,
            "customer_id": domain.customer_id,
            "order_id": domain.order_id,
            "transaction_id": domain.transaction_id,
        }
    legacy = get_dispute_by_id(dispute_id, organization_id=organization_id)
    if not legacy:
        raise NotFoundError("Dispute not found.")
    return {"dispute_id": legacy.dispute_id, "domain_dispute_id": None, "customer_id": None, "order_id": None, "transaction_id": None}


def list_for_dispute(db: Session, dispute_id: str, organization_id: str):
    context = _resolve_dispute(db, dispute_id, organization_id)
    records = db.scalars(select(EvidenceRecord).where(
        EvidenceRecord.organization_id == organization_id,
        EvidenceRecord.dispute_id == context["dispute_id"],
        EvidenceRecord.status != "DELETED",
    ).order_by(EvidenceRecord.uploaded_at.desc())).all()
    return [to_response_data(record) for record in records]


def get_record(db: Session, evidence_id: str, organization_id: str) -> EvidenceRecord:
    record = db.scalar(select(EvidenceRecord).where(
        EvidenceRecord.id == evidence_id,
        EvidenceRecord.organization_id == organization_id,
        EvidenceRecord.status != "DELETED",
    ))
    if not record:
        raise NotFoundError("Evidence not found.")
    return record


def _legacy_category(evidence_type: str) -> EvidenceCategory:
    mapping = {
        "PAYMENT_RECEIPT": EvidenceCategory.INVOICE,
        "INVOICE": EvidenceCategory.INVOICE,
        "ORDER_RECORD": EvidenceCategory.ORDER_CONFIRMATION,
        "TRANSACTION_RECORD": EvidenceCategory.INVOICE,
        "SHIPPING_DOCUMENT": EvidenceCategory.PROOF_OF_DELIVERY,
        "DELIVERY_PROOF": EvidenceCategory.PROOF_OF_DELIVERY,
        "CUSTOMER_COMMUNICATION": EvidenceCategory.CUSTOMER_COMMUNICATION,
        "REFUND_RECORD": EvidenceCategory.TERMS_AND_CONDITIONS,
        "CANCELLATION_RECORD": EvidenceCategory.TERMS_AND_CONDITIONS,
        "IDENTITY_DOCUMENT": EvidenceCategory.TERMS_AND_CONDITIONS,
        "SCREENSHOT": EvidenceCategory.TERMS_AND_CONDITIONS,
        "OTHER": EvidenceCategory.TERMS_AND_CONDITIONS,
    }
    return mapping[evidence_type]


def create_record(
    db: Session,
    *,
    dispute_id: str,
    evidence_type: str,
    source_type: str,
    upload,
    organization_id: str,
    actor_user_id: str,
):
    if evidence_type not in EVIDENCE_TYPES:
        raise BadRequestError("Unsupported evidence type.")
    if source_type not in SOURCE_TYPES:
        raise BadRequestError("Unsupported evidence source.")

    filename = _validate_filename(upload.filename or "")
    content = upload.file.read(settings.EVIDENCE_MAX_FILE_SIZE + 1)
    if not content:
        raise BadRequestError("Evidence file cannot be empty.")
    if len(content) > settings.EVIDENCE_MAX_FILE_SIZE:
        raise BadRequestError(f"Evidence file exceeds the {settings.EVIDENCE_MAX_FILE_SIZE // (1024 * 1024)} MB limit.")
    mime_type = _detect_mime(content, filename)
    context = _resolve_dispute(db, dispute_id, organization_id)
    content_hash = hashlib.sha256(content).hexdigest()
    duplicate = db.scalar(select(EvidenceRecord).where(
        EvidenceRecord.organization_id == organization_id,
        EvidenceRecord.dispute_id == context["dispute_id"],
        EvidenceRecord.content_hash == content_hash,
        EvidenceRecord.status != "DELETED",
    ))

    evidence_id = str(__import__("uuid").uuid4())
    storage_key = storage.key_for(organization_id, context["dispute_id"], evidence_id)
    storage.write(storage_key, content)
    record = EvidenceRecord(
        id=evidence_id,
        organization_id=organization_id,
        **context,
        evidence_type=evidence_type,
        source_type=source_type,
        original_filename=filename,
        mime_type=mime_type,
        file_size=len(content),
        storage_key=storage_key,
        content_hash=content_hash,
        uploaded_by_user_id=actor_user_id,
        uploaded_at=_now(),
        status="READY",
        metadata_json=json.dumps({"duplicate_of": duplicate.id} if duplicate else {}),
    )
    db.add(record)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        storage.delete(storage_key)
        raise ConflictError("Evidence could not be stored.") from exc

    # Compatibility projection lets the existing deterministic pipeline see the item.
    legacy_evidence = Evidence(
        evidence_id=f"EVD-{evidence_id}",
        dispute_id=context["dispute_id"],
        category=_legacy_category(evidence_type),
        file_name=filename,
        file_type=mime_type,
        content={"phase3_evidence_id": evidence_id, "content_hash": content_hash, "source_type": source_type},
        created_at=record.uploaded_at.strftime("%Y-%m-%d %H:%M:%S"),
        organization_id=organization_id,
    )
    save_evidence(legacy_evidence)
    AuditService.log_event(
        "EVIDENCE_UPLOADED",
        f"Evidence '{filename}' uploaded for dispute '{context['dispute_id']}'.",
        {"evidence_type": evidence_type, "source_type": source_type, "content_hash": content_hash, "duplicate_of": duplicate.id if duplicate else None},
        organization_id=organization_id,
        actor_user_id=actor_user_id,
        dispute_id=context["dispute_id"],
        resource_type="EVIDENCE",
        resource_id=evidence_id,
    )
    return to_response_data(record)


def update_record(db: Session, evidence_id: str, data: EvidenceUpdate, organization_id: str, actor_user_id: str):
    record = get_record(db, evidence_id, organization_id)
    if data.metadata is not None:
        record.metadata_json = json.dumps(data.metadata)
    record.updated_at = _now()
    db.commit()
    AuditService.log_event("EVIDENCE_UPDATED", f"Evidence '{record.original_filename}' metadata updated.",
                           organization_id=organization_id, actor_user_id=actor_user_id,
                           dispute_id=record.dispute_id, resource_type="EVIDENCE", resource_id=record.id)
    return to_response_data(record)


def delete_record(db: Session, evidence_id: str, organization_id: str, actor_user_id: str):
    record = get_record(db, evidence_id, organization_id)
    record.status = "DELETED"
    record.deleted_at = _now()
    record.updated_at = _now()
    db.commit()
    AuditService.log_event("EVIDENCE_DELETED", f"Evidence '{record.original_filename}' archived from active evidence.",
                           organization_id=organization_id, actor_user_id=actor_user_id,
                           dispute_id=record.dispute_id, resource_type="EVIDENCE", resource_id=record.id)


def download_record(db: Session, evidence_id: str, organization_id: str):
    record = get_record(db, evidence_id, organization_id)
    try:
        content = storage.read(record.storage_key)
    except FileNotFoundError as exc:
        raise NotFoundError("Evidence artifact is unavailable.") from exc
    return record, content
