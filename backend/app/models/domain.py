from enum import Enum
from typing import List, Optional, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field


class DisputeReason(str, Enum):
    GOODS_SERVICES_NOT_RECEIVED = "Goods / Services Not Received"


class DisputeStatus(str, Enum):
    OPEN = "OPEN"
    INVESTIGATING = "INVESTIGATING"
    HUMAN_REVIEW = "HUMAN_REVIEW"
    CONTESTED = "CONTESTED"
    REJECTED = "REJECTED"
    CLOSED = "CLOSED"


class VerificationStatus(str, Enum):
    PASSED = "PASSED"
    FAILED = "FAILED"
    WARNING = "WARNING"
    SKIPPED = "SKIPPED"


class VerificationSeverity(str, Enum):
    CRITICAL = "CRITICAL"
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"
    INFO = "INFO"


class EvidenceCategory(str, Enum):
    PROOF_OF_DELIVERY = "PROOF_OF_DELIVERY"
    INVOICE = "INVOICE"
    CUSTOMER_COMMUNICATION = "CUSTOMER_COMMUNICATION"
    ORDER_CONFIRMATION = "ORDER_CONFIRMATION"
    TERMS_AND_CONDITIONS = "TERMS_AND_CONDITIONS"


class EvidenceState(str, Enum):
    FOUND = "FOUND"
    VERIFIED = "VERIFIED"
    PARTIALLY_VERIFIED = "PARTIALLY_VERIFIED"
    CONTRADICTED = "CONTRADICTED"
    MISSING = "MISSING"


class FinalDecision(str, Enum):
    CONTEST = "CONTEST"
    DO_NOT_CONTEST = "DO_NOT_CONTEST"
    HUMAN_REVIEW = "HUMAN_REVIEW"


# Core Database & Domain Entities

class Payment(BaseModel):
    payment_id: str
    order_id: str
    customer_id: str
    amount: float
    currency: str = "INR"
    status: str = "captured"
    method: str = "card"
    created_at: str
    organization_id: Optional[str] = None


class OrderItem(BaseModel):
    item_id: str
    name: str
    quantity: int
    price: float


class Order(BaseModel):
    order_id: str
    customer_id: str
    items: List[OrderItem] = []
    total_amount: float
    currency: str = "INR"
    shipping_address: str
    customer_email: str
    customer_name: str
    created_at: str
    organization_id: Optional[str] = None


class Delivery(BaseModel):
    delivery_id: str
    order_id: str
    carrier: str
    tracking_number: str
    status: str  # DELIVERED, IN_TRANSIT, FAILED, PENDING
    estimated_delivery_date: str
    actual_delivery_date: Optional[str] = None
    recipient_name: Optional[str] = None
    signed_by: Optional[str] = None
    delivery_address: str
    created_at: str
    organization_id: Optional[str] = None


class Evidence(BaseModel):
    evidence_id: str
    dispute_id: str
    category: EvidenceCategory
    file_name: str
    file_type: str = "application/json"
    content: Dict[str, Any]
    verification_status: EvidenceState = EvidenceState.FOUND
    created_at: str
    organization_id: Optional[str] = None


class Dispute(BaseModel):
    dispute_id: str
    payment_id: str
    merchant_id: str  # payment-gateway merchant account reference (not the tenant key)
    amount: float
    currency: str = "INR"
    reason: DisputeReason = DisputeReason.GOODS_SERVICES_NOT_RECEIVED
    status: DisputeStatus = DisputeStatus.OPEN
    dispute_date: str
    case_type: str = "STRONG_CASE" # STRONG_CASE, WEAK_CASE, CONTRADICTORY_CASE, MISSING_EVIDENCE_CASE, EDGE_CASE
    created_at: str
    updated_at: str
    organization_id: Optional[str] = None  # owning tenant


# Verification Engine Output Models

class VerificationCheckResult(BaseModel):
    check: str
    status: VerificationStatus
    severity: VerificationSeverity
    expected: Any
    actual: Any
    message: str


# Timeline Event Model

class TimelineEvent(BaseModel):
    event_id: str
    timestamp: str
    event_type: str  # ORDER_PLACED, PAYMENT_CAPTURED, INVOICE_GENERATED, SHIPMENT_DISPATCHED, DELIVERY_COMPLETED, CUSTOMER_COMMUNICATION, DISPUTE_FILED
    source: str
    description: str
    verification_state: EvidenceState = EvidenceState.VERIFIED
    metadata: Dict[str, Any] = {}


# Readiness Score Model

class ScoreComponent(BaseModel):
    name: str
    score: float
    max_score: float
    explanation: str


class EvidenceReadinessScore(BaseModel):
    total_score: float  # 0 to 100
    components: List[ScoreComponent]
    summary: str


# AI Reasoning Output Model

class AIReasoningOutput(BaseModel):
    recommendation: FinalDecision
    confidence: float
    case_summary: str
    reasoning: List[str]
    supporting_evidence: List[str]
    missing_evidence: List[str]
    risk_flags: List[str]


# Final Decision Engine Output

class DecisionResult(BaseModel):
    final_decision: FinalDecision
    confidence: float
    recommended_action: str
    safety_override_triggered: bool = False
    override_reason: Optional[str] = None
    reasoning_summary: List[str] = []


# Investigation Entity

class Investigation(BaseModel):
    investigation_id: str
    dispute_id: str
    verification_results: List[VerificationCheckResult]
    readiness_score: EvidenceReadinessScore
    timeline: List[TimelineEvent]
    ai_analysis: Optional[AIReasoningOutput] = None
    decision: DecisionResult
    status: str = "COMPLETED"
    created_at: str
    organization_id: Optional[str] = None


# Audit Event Entity

class AuditEvent(BaseModel):
    event_id: str
    dispute_id: Optional[str] = None  # None for non-dispute events (login, user management)
    event_type: str  # DISPUTE_RECEIVED, EVIDENCE_RETRIEVED, EVIDENCE_VERIFIED, EVIDENCE_CONFLICT, TIMELINE_CREATED, AI_ANALYSIS_COMPLETED, HUMAN_REVIEW_REQUESTED, HUMAN_APPROVED, HUMAN_REJECTED, API_FAILURE, RETRY_ATTEMPT, ESCALATED
    description: str
    metadata: Dict[str, Any] = {}
    timestamp: str
    organization_id: Optional[str] = None
    actor_user_id: Optional[str] = None  # None for system-initiated events
    resource_type: Optional[str] = None  # DISPUTE, USER, ORGANIZATION
    resource_id: Optional[str] = None
    # Resolved from users at read time; not stored on the event
    actor_name: Optional[str] = None
    actor_email: Optional[str] = None
