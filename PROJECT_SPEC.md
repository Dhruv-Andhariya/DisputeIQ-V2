# DisputeIQ: Product & Engineering Specification

## 1. Executive Summary
**DisputeIQ** is an AI-powered dispute investigation and evidence intelligence layer that operates on top of payment and dispute infrastructure (such as Razorpay, Paypal).
Instead of simply notifying merchants that a dispute has been raised, DisputeIQ provides automated, deterministic evidence verification, timeline reconstruction, AI-assisted reasoning, and human-in-the-loop decision controls.

## 2. Core Architecture Philosophy
```
DETERMINISTIC CODE = CORRECTNESS
AI                  = REASONING
HUMAN               = FINAL JUDGMENT
AUDIT               = ACCOUNTABILITY
```

- **Deterministic Code**: Validates factual consistency (Order IDs, amounts, dates, tracking numbers). Deterministic checks are absolute.
- **AI Reasoning**: Analyzes customer communications, synthesizes verified context, identifies subtle risks, and produces structured recommendations.
- **Human Controls**: Human operators retain final decision-making power. Automatic action is blocked if critical conflicts exist.
- **Audit Trail**: Every action, verification, retry, and human decision is immutably logged for accountability.

## 3. Product Scope (MVP)
- Supported Dispute Category: **Goods / Services Not Received**
- System Architecture: **Modular Monolith**
- Backend: Python 3.11+, FastAPI, Pydantic v2
- Database: SQLite
- Frontend: React, Vite, Tailwind CSS, Axios
- AI Provider: Google Gemini via `ai_service.py` wrapper

## 4. Key Components

### 4.1 Verification Engine
Deterministic verification checks executed BEFORE AI reasoning:
1. `verify_payment_amount()`: Payment amount == Dispute amount == Order amount.
2. `verify_order_id_consistency()`: Order ID on Dispute == Order ID on Invoice == Order ID on Delivery.
3. `verify_customer_id_consistency()`: Customer ID consistency across payment, order, delivery.
4. `verify_delivery_date()`: Delivery date <= Dispute creation date.
5. `verify_dispute_date()`: Dispute date >= Order date.
6. `check_required_evidence()`: Ensures mandatory evidence (Proof of Delivery, Invoice, Order Confirmation) exists.
7. `detect_duplicate_evidence()`: Identifies redundant or duplicate documents.
8. `detect_missing_evidence()`: Reports missing critical documents.

> **CRITICAL OVERRIDE RULE**: Any `CRITICAL` or `HIGH` severity verification failure (such as an Order ID mismatch `ORD1001` vs `ORD1002`) MUST override an optimistic AI recommendation (`CONTEST`) and force the final decision to `HUMAN_REVIEW`.

### 4.2 Timeline Builder
Reconstructs the chronological event stream from available records:
- Order Placed
- Payment Processed
- Invoice Generated
- Carrier Shipment Dispatched
- Delivery Completed
- Customer Communication Received
- Dispute Filed

### 4.3 Evidence Readiness Score (0 - 100)
Decomposable readiness metric:
- Required Evidence Completeness: 40 pts
- Evidence Data Consistency: 30 pts
- Lifecycle Timeline Support: 15 pts
- Customer Communication Integrity: 15 pts

### 4.4 AI Investigation Service (`ai_service.py`)
Provides structured JSON analysis:
- `recommendation`: `CONTEST` | `DO_NOT_CONTEST` | `HUMAN_REVIEW`
- `confidence`: float (0.0 to 1.0)
- `case_summary`: string
- `reasoning`: array of strings
- `supporting_evidence`: array of strings
- `missing_evidence`: array of strings
- `risk_flags`: array of strings

### 4.5 Decision Engine
Combines verification check results, readiness score, and AI reasoning:
- High confidence + No critical flags + Verified evidence -> `CONTEST`
- Clear evidence against merchant -> `DO_NOT_CONTEST`
- Medium confidence / Missing evidence / Verification flags -> `HUMAN_REVIEW`
- Critical verification conflict -> `HUMAN_REVIEW` (Auto-action blocked)

### 4.6 Failure Handling & Resilience
- External API timeouts: Bounded retries (up to 3 attempts), exponential backoff, safe fallback to `HUMAN_REVIEW` with evidence marked unavailable.
- LLM API failure: Returns structured failure message, preserves deterministic findings, degrades to `HUMAN_REVIEW`.
- Malformed evidence: Flags malformed document, continues analysis with remaining valid evidence.

### 4.7 Audit Trail
Immutable log events: `DISPUTE_RECEIVED`, `EVIDENCE_RETRIEVED`, `EVIDENCE_VERIFIED`, `EVIDENCE_CONFLICT`, `TIMELINE_CREATED`, `AI_ANALYSIS_COMPLETED`, `HUMAN_REVIEW_REQUESTED`, `HUMAN_APPROVED`, `HUMAN_REJECTED`, `API_FAILURE`, `RETRY_ATTEMPT`, `ESCALATED`.

### 4.8 Evaluation Framework
Runs benchmark evaluation on a held-out dataset of synthetic test cases. Outputs metrics:
- Recommendation Accuracy
- False-Contest Rate
- False-Acceptance Rate
- Human Escalation Rate
- Results saved to `evaluation/results/summary.json`.
