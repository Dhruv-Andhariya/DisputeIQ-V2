import uuid
from datetime import datetime
from typing import Optional, Dict, Any, List
from app.models.domain import (
    Dispute, Investigation, DisputeStatus, FinalDecision, AuditEvent,
    DecisionResult, VerificationStatus
)
from app.database.db import (
    get_dispute_by_id, get_payment_by_id, get_order_by_id, get_delivery_by_order_id,
    save_dispute, save_investigation, get_investigation_by_dispute_id
)
from app.services.verification_engine import VerificationEngine
from app.services.evidence_retrieval import EvidenceRetrievalService
from app.services.timeline_builder import TimelineBuilderService
from app.services.readiness_score import ReadinessScoreCalculator
from app.services.decision_engine import DecisionEngine
from app.services.audit_service import AuditService
from app.services.razorpay_service import MockRazorpayAdapter
from app.ai.ai_service import AIService

class DisputeService:
    @staticmethod
    def _get_dispute(dispute_id: str, organization_id: str) -> Dispute:
        dispute = get_dispute_by_id(dispute_id, organization_id=organization_id)
        if not dispute:
            # Same error whether the dispute doesn't exist or belongs to another tenant.
            raise ValueError(f"Dispute {dispute_id} not found.")
        return dispute

    @staticmethod
    def _auditor(dispute: Dispute, actor_user_id: Optional[str]):
        """Returns an audit logger bound to this dispute's tenant and the acting user."""
        def log(event_type: str, description: str, metadata: Dict[str, Any] = None) -> AuditEvent:
            return AuditService.log_event(
                event_type, description, metadata,
                organization_id=dispute.organization_id,
                actor_user_id=actor_user_id,
                dispute_id=dispute.dispute_id,
            )
        return log

    @staticmethod
    def run_investigation(dispute_id: str, *, organization_id: str, actor_user_id: Optional[str]) -> Investigation:
        dispute = DisputeService._get_dispute(dispute_id, organization_id)
        audit = DisputeService._auditor(dispute, actor_user_id)

        # 1. Fetch related entities (all scoped to the dispute's organization)
        payment = get_payment_by_id(dispute.payment_id, organization_id=organization_id)
        order = get_order_by_id(payment.order_id, organization_id=organization_id) if payment else None
        delivery = get_delivery_by_order_id(order.order_id, organization_id=organization_id) if order else None
        
        # Audit Log: Evidence Retrieval
        audit(
            event_type="EVIDENCE_RETRIEVED",
            description="Retrieved transaction records, payment status, order payload, delivery logs, and evidence files.",
            metadata={"payment_id": dispute.payment_id, "order_id": payment.order_id if payment else "N/A"}
        )
        
        # 2. Retrieve Evidence
        evidence_list = EvidenceRetrievalService.retrieve_evidence(dispute_id, organization_id=organization_id)
        
        # 3. Deterministic Verification Engine
        verification_results = VerificationEngine.run_all_checks(
            dispute=dispute,
            payment=payment,
            order=order,
            delivery=delivery,
            evidence_list=evidence_list
        )
        
        # Map Evidence States based on check results
        mapped_evidence = EvidenceRetrievalService.map_evidence_states(evidence_list, verification_results)
        
        # Audit Log: Verification
        failed_count = sum(1 for v in verification_results if v.status == VerificationStatus.FAILED)
        if failed_count > 0:
            audit(
                event_type="EVIDENCE_CONFLICT",
                description=f"Deterministic verification completed with {failed_count} check failure(s).",
                metadata={"failed_checks": [v.check for v in verification_results if v.status == VerificationStatus.FAILED]}
            )
        else:
            audit(
                event_type="EVIDENCE_VERIFIED",
                description="Deterministic verification completed successfully. All factual consistency checks passed.",
                metadata={"passed_checks": len(verification_results)}
            )

        # 4. Reconstruct Timeline
        timeline = TimelineBuilderService.build_timeline(
            dispute=dispute,
            payment=payment,
            order=order,
            delivery=delivery,
            evidence_list=mapped_evidence,
            verification_results=verification_results
        )
        
        audit(
            event_type="TIMELINE_CREATED",
            description=f"Reconstructed lifecycle timeline containing {len(timeline)} verified event milestone(s).",
            metadata={"event_count": len(timeline)}
        )

        # 5. Readiness Score
        readiness_score = ReadinessScoreCalculator.calculate_score(
            evidence_list=mapped_evidence,
            verification_results=verification_results,
            delivery=delivery
        )

        # 6. AI Investigation
        ai_analysis = AIService.analyze_dispute(
            dispute=dispute,
            payment=payment,
            order=order,
            delivery=delivery,
            evidence_list=mapped_evidence,
            verification_results=verification_results,
            readiness_score=readiness_score
        )
        
        audit(
            event_type="AI_ANALYSIS_COMPLETED",
            description=f"AI reasoning completed. Suggested recommendation: {ai_analysis.recommendation.value} (Confidence: {ai_analysis.confidence:.2f}).",
            metadata={"recommendation": ai_analysis.recommendation.value, "confidence": ai_analysis.confidence}
        )

        # 7. Decision Engine (combines verification + AI + safety overrides)
        decision = DecisionEngine.evaluate_decision(
            verification_results=verification_results,
            readiness_score=readiness_score,
            ai_analysis=ai_analysis
        )

        # Update dispute status
        if decision.final_decision == FinalDecision.HUMAN_REVIEW:
            dispute.status = DisputeStatus.HUMAN_REVIEW
            audit(
                event_type="HUMAN_REVIEW_REQUESTED",
                description=f"Case escalated to Human Analyst. Reason: {decision.override_reason or 'Requires human judgment'}.",
                metadata={"override_triggered": decision.safety_override_triggered}
            )
        elif decision.final_decision == FinalDecision.CONTEST:
            dispute.status = DisputeStatus.INVESTIGATING
        else:
            dispute.status = DisputeStatus.INVESTIGATING
            
        dispute.updated_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        save_dispute(dispute)

        # Save Investigation
        investigation = Investigation(
            investigation_id=f"INV-{uuid.uuid4().hex[:8].upper()}",
            dispute_id=dispute_id,
            verification_results=verification_results,
            readiness_score=readiness_score,
            timeline=timeline,
            ai_analysis=ai_analysis,
            decision=decision,
            status="COMPLETED",
            created_at=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            organization_id=organization_id
        )
        save_investigation(investigation)
        return investigation

    @staticmethod
    def simulate_system_failure(dispute_id: str, *, organization_id: str, actor_user_id: Optional[str]) -> Investigation:
        """
        Demonstrates SCENARIO 3: Bounded retries on external evidence retrieval failure.
        Safely degrades to HUMAN_REVIEW without crashing.
        """
        dispute = DisputeService._get_dispute(dispute_id, organization_id)
        audit = DisputeService._auditor(dispute, actor_user_id)

        # Log retries
        for attempt in range(1, 4):
            audit(
                event_type="RETRY_ATTEMPT",
                description=f"[Attempt {attempt}/3] Connecting to external carrier evidence API...",
                metadata={"attempt": attempt, "target": "Carrier Logistics Gateway API"}
            )

        audit(
            event_type="API_FAILURE",
            description="External Carrier Logistics API failed to respond after 3 bounded retry attempts (HTTP 504 Gateway Timeout).",
            metadata={"status_code": 504, "error": "Gateway Timeout"}
        )

        audit(
            event_type="ESCALATED",
            description="Evidence marked UNAVAILABLE. Reduced investigation confidence to 0.20 and escalated case to HUMAN_REVIEW.",
            metadata={"action": "SAFE_DEGRADATION"}
        )

        # Build investigation object reflecting system failure
        existing_inv = get_investigation_by_dispute_id(dispute_id, organization_id=organization_id)
        
        decision = DecisionResult(
            final_decision=FinalDecision.HUMAN_REVIEW,
            confidence=0.20,
            recommended_action="System Failure: Escalate to Human Analyst. External Logistics API was unavailable.",
            safety_override_triggered=True,
            override_reason="External carrier evidence API failure after 3 retry attempts.",
            reasoning_summary=[
                "Carrier tracking evidence API timed out after 3 retry attempts.",
                "System degraded safely to prevent automated submission of unverified claims.",
                "Escalated to Human Review for manual evidence verification."
            ]
        )
        
        dispute.status = DisputeStatus.HUMAN_REVIEW
        dispute.updated_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        save_dispute(dispute)

        inv = Investigation(
            investigation_id=f"INV-FAIL-{uuid.uuid4().hex[:6].upper()}",
            dispute_id=dispute_id,
            verification_results=existing_inv.verification_results if existing_inv else [],
            readiness_score=existing_inv.readiness_score if existing_inv else ReadinessScoreCalculator.calculate_score([], [], None),
            timeline=existing_inv.timeline if existing_inv else [],
            ai_analysis=existing_inv.ai_analysis if existing_inv else None,
            decision=decision,
            status="SYSTEM_FAILURE_ESCALATED",
            created_at=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            organization_id=organization_id
        )
        save_investigation(inv)
        return inv

    @staticmethod
    def approve_investigation(
        dispute_id: str, notes: Optional[str] = None, *, organization_id: str, actor_user_id: str
    ) -> Dispute:
        """Human approval action."""
        dispute = DisputeService._get_dispute(dispute_id, organization_id)
        audit = DisputeService._auditor(dispute, actor_user_id)

        # Simulate submission via Mock Razorpay Adapter
        MockRazorpayAdapter.submit_contest(dispute_id, {"human_notes": notes})
        
        dispute.status = DisputeStatus.CONTESTED
        dispute.updated_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        save_dispute(dispute)
        
        audit(
            event_type="HUMAN_APPROVED",
            description=f"Human Analyst approved dispute defense submission via Mock Razorpay Adapter. Notes: '{notes or 'No notes provided'}'.",
            metadata={"notes": notes}
        )
        return dispute

    @staticmethod
    def reject_investigation(
        dispute_id: str, notes: Optional[str] = None, *, organization_id: str, actor_user_id: str
    ) -> Dispute:
        """Human rejection action."""
        dispute = DisputeService._get_dispute(dispute_id, organization_id)
        audit = DisputeService._auditor(dispute, actor_user_id)

        dispute.status = DisputeStatus.REJECTED
        dispute.updated_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        save_dispute(dispute)
        
        audit(
            event_type="HUMAN_REJECTED",
            description=f"Human Analyst rejected contesting this dispute. Dispute marked accepted/lost. Notes: '{notes or 'No notes provided'}'.",
            metadata={"notes": notes}
        )
        return dispute
