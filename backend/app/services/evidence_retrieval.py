from typing import List, Dict, Any
from app.models.domain import (
    Dispute, Evidence, EvidenceCategory, EvidenceState, VerificationStatus, VerificationCheckResult
)
from app.database.db import get_evidence_by_dispute_id

class EvidenceRetrievalService:
    @staticmethod
    def get_required_categories_for_dispute(reason: str) -> List[EvidenceCategory]:
        """Returns mandatory and recommended evidence categories based on dispute reason."""
        # For Goods / Services Not Received MVP
        return [
            EvidenceCategory.PROOF_OF_DELIVERY,
            EvidenceCategory.INVOICE,
            EvidenceCategory.ORDER_CONFIRMATION,
            EvidenceCategory.CUSTOMER_COMMUNICATION,
            EvidenceCategory.TERMS_AND_CONDITIONS
        ]

    @staticmethod
    def retrieve_evidence(dispute_id: str, *, organization_id: str) -> List[Evidence]:
        """Retrieves all evidence records associated with the dispute ID within the tenant."""
        return get_evidence_by_dispute_id(dispute_id, organization_id=organization_id)

    @staticmethod
    def map_evidence_states(
        evidence_list: List[Evidence],
        verification_results: List[VerificationCheckResult]
    ) -> List[Evidence]:
        """Updates verification states of retrieved evidence based on deterministic verification checks."""
        # Check for critical conflicts
        order_conflict = any(r.check == "order_id_consistency" and r.status == VerificationStatus.FAILED for r in verification_results)
        amount_conflict = any(r.check == "payment_amount_consistency" and r.status == VerificationStatus.FAILED for r in verification_results)
        delivery_failed = any(r.check == "delivery_date_validity" and r.status == VerificationStatus.FAILED for r in verification_results)
        
        updated_list = []
        for ev in evidence_list:
            ev_copy = ev.model_copy()
            
            if ev.category == EvidenceCategory.PROOF_OF_DELIVERY:
                if order_conflict or delivery_failed:
                    ev_copy.verification_status = EvidenceState.CONTRADICTED
                else:
                    ev_copy.verification_status = EvidenceState.VERIFIED
                    
            elif ev.category == EvidenceCategory.INVOICE:
                if amount_conflict or order_conflict:
                    ev_copy.verification_status = EvidenceState.CONTRADICTED
                else:
                    ev_copy.verification_status = EvidenceState.VERIFIED
                    
            elif ev.category in [EvidenceCategory.ORDER_CONFIRMATION, EvidenceCategory.TERMS_AND_CONDITIONS]:
                ev_copy.verification_status = EvidenceState.VERIFIED
                
            elif ev.category == EvidenceCategory.CUSTOMER_COMMUNICATION:
                ev_copy.verification_status = EvidenceState.PARTIALLY_VERIFIED
                
            updated_list.append(ev_copy)
            
        return updated_list
