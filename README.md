# DisputeIQ — AI-Powered Dispute Investigation & Evidence Intelligence Layer


> **Official Project Objective:** *"Stop the merchant losing money to fraud, returns and chargebacks."*

---

## 1. Problem Statement & Context
Merchant dispute and chargeback investigation is **not** simply about receiving a dispute notification and blindly submitting an evidence PDF.

Existing payment infrastructure tells the merchant:
```
"A dispute has been raised."
```

**DisputeIQ** sits on top of existing payment/dispute infrastructure to answer:
```
"Is this dispute defensible?
 What evidence supports the merchant?
 Is the evidence internally consistent?
 What happened across the transaction lifecycle?
 What should the merchant do, and why?"
```

---

## 2. Core Architecture Philosophy

```
┌────────────────────────────────────────────────────────┐
│  DETERMINISTIC CODE  =  CORRECTNESS                    │
│  AI                  =  REASONING                      │
│  HUMAN               =  FINAL JUDGMENT                 │
│  AUDIT               =  ACCOUNTABILITY                 │
└────────────────────────────────────────────────────────┘
```

DisputeIQ strictly enforces this distinction:
- **Deterministic Code**: Handles factual consistency, ID matching, amount verification, timestamp validation, and safety override blocks.
- **AI Reasoning**: Interprets customer communications, synthesizes context across verified facts, and generates structured explanations.
- **Human Controls**: Human operators retain sole execution authority for financial submissions.
- **Audit Trail**: Every verification, retry, LLM output, and human approval is immutably logged.

---

## 3. Non-Negotiable Differentiators

### 1. Evidence Verification & Deterministic Overrides
Never blindly trust evidence. Deterministic verification detects data corruptions and conflicts BEFORE AI reasoning.
- **Example**: Dispute raised for Order `ORD1001`, invoice shows `ORD1001`, but delivery proof references `ORD1002`.
- **System Action**: Flags a **HIGH Severity Order Identity Conflict**.
- **Critical Safety Rule**: The LLM CANNOT override this deterministic check. Even if AI suggests `CONTEST` with 94% confidence, the final system decision is forcibly set to `HUMAN_REVIEW` and automated action is blocked!

### 2. Chronological Timeline Reconstruction
DisputeIQ reconstructs the complete transaction lifecycle:
$$\text{Order} \longrightarrow \text{Payment} \longrightarrow \text{Invoice} \longrightarrow \text{Shipment} \longrightarrow \text{Delivery} \longrightarrow \text{Customer Comm} \longrightarrow \text{Dispute}$$
- Assembled 100% deterministically from verified DB records.
- The AI is strictly forbidden from fabricating timeline events.

### 3. Bounded AI + Human-in-the-Loop Controls
- **AI Capabilities**: Investigates, reasons, summarizes, identifies supporting evidence, flags missing evidence, and suggests recommendations.
- **AI Boundaries**: Cannot fabricate evidence, alter verified facts, override deterministic checks, or execute financial actions.
- **Human Control Point**: Final contest submission requires explicit human approval.

---

## 4. Scope (MVP)
Supported Dispute Category: **Goods / Services Not Received**

---

## 5. Technology Stack
- **Backend**: Python 3.11+, FastAPI, Pydantic v2
- **Database**: SQLite. Identity tables via SQLAlchemy 2.0; dispute pipeline via `sqlite3` + JSON fields. Schema managed by Alembic migrations
- **Auth**: JWT (PyJWT) bearer tokens, Argon2id password hashing, permission-based RBAC, tenant isolation
- **Frontend**: React (Vite), React Router, Tailwind CSS, Axios, Lucide React Icons
- **AI Service**: Google Gemini API via `google-genai` (wrapped inside `ai_service.py`)
- **Testing & Evaluation**: Pytest, standalone evaluation benchmark pipeline

---

## 6. Architecture & Modular Structure

```
DisputeIQ/
├── PROJECT_SPEC.md              # Authoritative product & engineering specification
├── README.md                    # System documentation
├── .env.example                 # Environment variables configuration template
├── backend/
│   ├── app/
│   │   ├── main.py              # FastAPI app, lifespan (migrate/seed), CORS, error handlers
│   │   ├── core/
│   │   │   ├── config.py        # Settings from .env (secrets, CORS, DB path)
│   │   │   ├── database.py      # SQLAlchemy engine/session (identity layer)
│   │   │   ├── security.py      # Argon2id hashing, JWT issue/verify
│   │   │   ├── migrations.py    # Programmatic Alembic runner
│   │   │   └── errors.py        # 400/401/403/404/409 error types
│   │   ├── auth/                # /auth routes, login/register service, dependencies, RBAC permissions
│   │   ├── organizations/       # Organization model, /organizations/me routes
│   │   ├── users/               # User + Role model, member management routes
│   │   ├── api/routes.py        # Dispute endpoints (authenticated, tenant-scoped)
│   │   ├── models/domain.py     # Pydantic domain entities
│   │   ├── services/
│   │   │   ├── verification_engine.py   # Deterministic verification functions
│   │   │   ├── evidence_retrieval.py    # Database evidence retrieval & mapping
│   │   │   ├── timeline_builder.py      # Chronological timeline builder
│   │   │   ├── readiness_score.py       # Decomposable Evidence Readiness Score
│   │   │   ├── decision_engine.py       # Policy decision matrix & safety overrides
│   │   │   ├── audit_service.py         # Immutable SQLite audit logger
│   │   │   ├── razorpay_service.py      # Mock Razorpay Adapter
│   │   │   └── dispute_service.py       # Main pipeline orchestrator
│   │   ├── ai/
│   │   │   ├── ai_service.py            # Gemini LLM integration & safe fallback
│   │   │   ├── prompts.py               # System prompt & 13 guardrail directives
│   │   │   └── guardrails.py            # Pydantic JSON parser & validator
│   │   └── database/
│   │       ├── db.py                    # Tenant-scoped SQLite persistence layer
│   │       └── seed.py                  # Demo dataset seeder (into the "Demo Merchant" org)
│   ├── migrations/              # Alembic migrations (0001 baseline, 0002 identity & tenancy)
│   ├── alembic.ini
│   ├── manage.py                # CLI: migrate | seed | create-user
│   └── tests/
│       ├── test_verification.py         # Deterministic verification engine
│       ├── test_auth.py                 # Registration, login, token validation
│       ├── test_rbac.py                 # Role/permission enforcement
│       ├── test_tenant_isolation.py     # PERMANENT cross-tenant security regression tests
│       └── test_migrations.py           # Fresh + legacy DB migrations
├── pytest.ini
├── frontend/
│   └── src/
│       ├── auth/                # AuthContext, token storage, login/register layout, roles
│       ├── routes/              # ProtectedRoute / PublicOnlyRoute
│       ├── components/          # React UI components (EvidenceMatrix, VerificationList, etc.)
│       └── pages/               # Login, Register, Dashboard, Team, DisputeList, InvestigationDetail
├── data/synthetic/              # Seed generator (40 disputes across 5 archetypes)
└── evaluation/                  # Evaluation pipeline & held-out test suite
```

---

## 7. Synthetic Data Archetypes
Generated using a fixed random seed (`seed=42`) creating 40 dispute records:
1. `STRONG_CASE` (12 disputes): Full proof of delivery signed by customer, matching amounts/IDs, valid timeline.
2. `WEAK_CASE` (8 disputes): Delivery proof signed by reception/guard, or missing carrier signature.
3. `CONTRADICTORY_CASE` (10 disputes): Controlled corruptions (Order ID mismatch `ORD1001` vs `ORD1002`, amount mismatch, delivery date after dispute filing).
4. `MISSING_EVIDENCE_CASE` (5 disputes): Missing carrier tracking proof or invoice document.
5. `EDGE_CASE` (5 disputes): Wrong category conflict (Customer complaints about damaged goods filed under Goods Not Received).

---

## 8. Decomposable Evidence Readiness Score (0 - 100)
Every score is fully explainable with 4 sub-component progress indicators:
- **Required Evidence Completeness**: 40 pts (POD 20, Invoice 10, Order Conf 10)
- **Evidence Data Consistency**: 30 pts (Deductions for check failures)
- **Timeline & Delivery Support**: 15 pts (Carrier verified status 10, Recipient signature 5)
- **Customer Communication Integrity**: 15 pts (Customer interaction logs present 15)

---

## 9. Evaluation Results (Held-Out Test Set)

Run evaluation script:
```bash
python evaluation/evaluate.py
```
Output saved to `evaluation/results/summary.json`:
- **Held-Out Test Cases**: 25 disputes
- **Recommendation Accuracy**: `92.0%`
- **False-Contest Rate**: `0.0%` (Zero dangerous false contests on contradictory cases!)
- **False-Acceptance Rate**: `0.0%`
- **Human Escalation Rate**: `64.0%` (Safely escalates ambiguous & contradictory cases to humans)

---

## 10. Installation & Quickstart

### Prerequisites
- Python 3.11+
- Node.js 18+ & npm

### Backend Setup
```bash
# Clone and enter repository
cd DisputeIQ

# Create virtual environment & install requirements
python -m venv venv
venv\Scripts\activate
pip install -r backend/requirements.txt

# Create .env file, then set JWT_SECRET_KEY (and GEMINI_API_KEY if you have one)
cp .env.example .env
python -c "import secrets; print(secrets.token_urlsafe(64))"

# Apply migrations (safe on an existing disputeiq.db: data is preserved and
# assigned to the "Demo Merchant" organization) and seed the 40 demo disputes
python backend/manage.py migrate
python backend/manage.py seed

# Create a login for the Demo Merchant organization (prompts for a password)
python backend/manage.py create-user --org demo-merchant --email you@yourcompany.com --name "Your Name" --role ADMIN

# Run the test suite (auth, RBAC, tenant isolation, migrations, verification)
python -m pytest

# Start FastAPI backend server
python -m uvicorn app.main:app --app-dir backend --host 0.0.0.0 --port 8000 --reload
```
Backend server will start at `http://localhost:8000`, with interactive API docs at `http://localhost:8000/docs`.
Use **Authorize** in the docs with the `access_token` from `POST /auth/login`.

### Frontend Setup
```bash
cd frontend
npm install
npm run dev
```
Frontend app will start at `http://localhost:3000`. API calls go through the Vite proxy at `/api` (override with `VITE_API_BASE_URL`).

### Evidence Uploads (Phase 3)
Evidence uploads are organization-scoped and stored locally outside SQLite. The database stores provenance metadata and a SHA-256 content hash; it does not claim that an uploaded artifact is authentic.

- Allowed formats: PDF, PNG, JPG/JPEG, GIF, WEBP, JSON, CSV, and TXT
- Default maximum size: 10 MiB (`EVIDENCE_MAX_FILE_SIZE`)
- Local storage: `storage/evidence` (override with `EVIDENCE_STORAGE_PATH`)
- Uploads use generated storage keys; original filenames are metadata only
- Artifacts are soft-deleted and remain auditable

### Document Intelligence (Phase 4)
Evidence can be processed from the dispute detail page. Text/JSON/CSV and text-layer PDFs use deterministic local extraction; image evidence uses the PaddleOCR adapter. Processing stores raw text, page/block layout, document classification, structured Pydantic extraction, confidence metadata, and processor version without treating extraction as verification. Failed processing can be retried. VLM fallback is disabled by default and can be enabled with `ENABLE_VLM_PROCESSING=true`.

---

## Multi-Tenancy & Security (Phase 1)

```
JWT (sub = user id only) → get_current_user() loads user from DB
  → user.organization_id  → every query filtered by organization_id
```

- **Organizations** are tenants; every **user** belongs to exactly one. Roles: `ADMIN`, `INVESTIGATOR`, `ANALYST`, `VIEWER`, mapped to permissions in `backend/app/auth/permissions.py`.
- The backend **never accepts an organization id from the client**. The tenant is always the authenticated user's organization, loaded from the database on each request, so role changes and deactivation take effect immediately.
- Tenant-scoped data-access functions require `organization_id` as a keyword argument, and writes refuse records without one.
- Another tenant's resources return **404**, identical to non-existent ones, so their existence isn't revealed.
- Audit events record `organization_id`, `actor_user_id`, `resource_type`, and `resource_id`. Logins, failed logins, user and organization changes, and every investigation step are attributed.
- `backend/tests/test_tenant_isolation.py` is the permanent regression suite for these guarantees.

---

## 11. Three Live Demo Scenarios

### SCENARIO 1 — Strong Case (Automated Contest Path)
- Select `DSP-2026-001` (Case Type: `STRONG_CASE`).
- **Observed Behavior**: All deterministic checks pass, Evidence Readiness > 85/100, AI recommends `CONTEST`, decision is `CONTEST`.
- Human click "Approve & Prepare Submission" -> Mock Razorpay Adapter logs submission.

### SCENARIO 2 — Contradictory Case (Order ID Mismatch - Primary Demo Moment)
- Select `DSP-2026-005` (Case Type: `CONTRADICTORY_CASE`, Order ID mismatch `ORD-1005` vs `ORD-ERR-005`).
- **Observed Behavior**: Deterministic verification check `order_id_consistency` **FAILS** with `HIGH` severity.
- **Safety Override Triggered**: Decision engine forcibly overrides decision to **`HUMAN_REVIEW`** and blocks automated contesting!

### SCENARIO 3 — System Failure & Safe Degradation
- On any Investigation Detail page, click the **"Simulate System Failure"** button.
- **Observed Behavior**: System logs 3 bounded retry attempts to external Carrier Logistics API, captures HTTP 504 timeout, marks evidence unavailable, drops confidence to 0.20, degrades safely to **`HUMAN_REVIEW`**, and logs audit events!

---

