import React, { useState, useEffect } from 'react';
import {
  apiErrorMessage,
  fetchDisputeById,
  fetchLatestInvestigation,
  triggerInvestigation,
  fetchEvidence,
  fetchTimeline,
  fetchAuditEvents,
  approveDispute,
  rejectDispute,
  fetchDomainDispute,
  fetchUploadedEvidence,
  uploadEvidence
} from '../api';
import StatusBadge from '../components/StatusBadge';
import EvidenceMatrix from '../components/EvidenceMatrix';
import VerificationList from '../components/VerificationList';
import TimelineView from '../components/TimelineView';
import ReadinessGauge from '../components/ReadinessGauge';
import AIReasoningCard from '../components/AIReasoningCard';
import ActionControls from '../components/ActionControls';
import AuditLogView from '../components/AuditLogView';
import { formatINR } from '../utils/format';
import { useAuth, PERMISSIONS } from '../auth/AuthContext';
import { ArrowLeft, RefreshCw, AlertTriangle, Clock } from 'lucide-react';

export default function InvestigationDetail({ disputeId, onBack, failureModeTriggered }) {
  const [dispute, setDispute] = useState(null);
  const [investigation, setInvestigation] = useState(null);
  const [evidenceList, setEvidenceList] = useState([]);
  const [uploadedEvidence, setUploadedEvidence] = useState([]);
  const [timeline, setTimeline] = useState([]);
  const [auditEvents, setAuditEvents] = useState([]);
  const [domainContext, setDomainContext] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [notInvestigated, setNotInvestigated] = useState(false);
  const { can } = useAuth();
  const canInvestigate = can(PERMISSIONS.INVESTIGATE);
  const canReview = can(PERMISSIONS.REVIEW_CASES);

  useEffect(() => {
    loadInvestigationData();
  }, [disputeId, failureModeTriggered]);

  // Shows the latest stored investigation. The pipeline only runs when explicitly re-run,
  // or when none exists yet and the user is allowed to investigate.
  const loadInvestigationData = async ({ rerun = false } = {}) => {
    try {
      setLoading(true);
      setError(null);
      setNotInvestigated(false);

      const dispRes = await fetchDisputeById(disputeId);
      setDispute(dispRes.data);
      try {
        setDomainContext((await fetchDomainDispute(disputeId)).data);
      } catch (domainError) {
        if (domainError.response?.status !== 404) throw domainError;
        setDomainContext(null);
      }

      let inv = null;
      if (!rerun) {
        try {
          inv = (await fetchLatestInvestigation(disputeId)).data;
        } catch (e) {
          if (e.response?.status !== 404) throw e;
        }
      }
      if (!inv && canInvestigate) {
        inv = (await triggerInvestigation(disputeId)).data;
      }
      if (!inv) {
        setInvestigation(null);
        setNotInvestigated(true);
        return;
      }
      setInvestigation(inv);

      const evRes = await fetchEvidence(disputeId);
      setEvidenceList(evRes.data);
      const uploadedRes = await fetchUploadedEvidence(disputeId);
      setUploadedEvidence(uploadedRes.data);

      const timeRes = await fetchTimeline(disputeId);
      setTimeline(timeRes.data);

      const auditRes = await fetchAuditEvents(disputeId);
      setAuditEvents(auditRes.data);
    } catch (err) {
      console.error(err);
      setError(
        err.response?.status === 404
          ? apiErrorMessage(err)
          : 'Failed to complete dispute investigation pipeline.'
      );
    } finally {
      setLoading(false);
    }
  };

  const handleEvidenceUpload = async (formData) => {
    await uploadEvidence(disputeId, formData);
    setUploadedEvidence((await fetchUploadedEvidence(disputeId)).data);
  };

  const handleApprove = async (notes) => {
    try {
      await approveDispute(disputeId, notes);
      await loadInvestigationData();
    } catch (err) {
      alert(apiErrorMessage(err, 'Failed to approve dispute submission.'));
    }
  };

  const handleReject = async (notes) => {
    try {
      await rejectDispute(disputeId, notes);
      await loadInvestigationData();
    } catch (err) {
      alert(apiErrorMessage(err, 'Failed to reject dispute.'));
    }
  };

  if (loading) {
    return (
      <div className="mx-auto flex max-w-7xl flex-col items-center px-4 py-28 text-center">
        <div className="spinner mb-5 h-10 w-10" />
        <h3 className="text-base font-semibold">Running DisputeIQ Investigation Pipeline...</h3>
        <p className="mt-1 text-sm text-ink-muted">Executing deterministic checks, evidence matrix analysis &amp; AI reasoning</p>
      </div>
    );
  }

  if (notInvestigated && dispute) {
    return (
      <div className="mx-auto max-w-7xl space-y-4 px-4 py-12 sm:px-6 lg:px-8">
        <button onClick={onBack} className="btn btn-ghost btn-sm -ml-3">
          <ArrowLeft className="h-4 w-4" />
          <span>Back to Dispute Dashboard</span>
        </button>
        <div className="panel-warning flex items-start gap-3 p-5">
          <Clock className="mt-0.5 h-5 w-5 shrink-0 text-amber-400" />
          <div>
            <h2 className="text-sm font-semibold">
              <span className="font-mono">{dispute.dispute_id}</span> has not been investigated yet
            </h2>
            <p className="mt-1 text-[13px] text-ink-muted">
              An investigator or admin needs to run the investigation pipeline before results are available.
            </p>
          </div>
        </div>
      </div>
    );
  }

  if (error || !dispute || !investigation) {
    return (
      <div className="mx-auto max-w-7xl space-y-4 px-4 py-12 sm:px-6 lg:px-8">
        <button onClick={onBack} className="btn btn-ghost btn-sm -ml-3">
          <ArrowLeft className="h-4 w-4" />
          <span>Back to Dispute Dashboard</span>
        </button>
        <div className="panel-danger flex items-center justify-center gap-2 p-6 text-sm text-rose-300">
          <AlertTriangle className="h-4 w-4" />
          <span>{error || 'Dispute investigation data unavailable.'}</span>
        </div>
      </div>
    );
  }

  const { verification_results, readiness_score, ai_analysis, decision } = investigation;

  const metadata = [
    { label: 'Merchant ID', value: <span className="mono-id text-ink">{dispute.merchant_id}</span> },
    { label: 'Dispute Filed', value: <span className="tabular-nums text-ink">{dispute.dispute_date}</span> },
    { label: 'Readiness Score', value: <span className="font-semibold tabular-nums text-accent-soft">{readiness_score.total_score}/100</span> },
    { label: 'System Recommendation', value: <StatusBadge status={decision.final_decision} type="decision" /> },
  ];

  return (
    <div className="mx-auto max-w-7xl space-y-6 px-4 py-8 sm:px-6 lg:px-8">

      {/* Top Navigation Bar */}
      <div className="flex items-center justify-between">
        <button onClick={onBack} className="btn btn-ghost btn-sm -ml-3">
          <ArrowLeft className="h-4 w-4" />
          <span>Back to Dashboard</span>
        </button>

        {canInvestigate && (
          <button onClick={() => loadInvestigationData({ rerun: true })} className="btn btn-secondary btn-sm">
            <RefreshCw className="h-3.5 w-3.5" />
            <span>Re-run Pipeline</span>
          </button>
        )}
      </div>

      {/* Header Card */}
      <section className="card">
        <div className="flex flex-wrap items-start justify-between gap-6 p-6">
          <div className="min-w-0 space-y-2">
            <div className="eyebrow">Dispute</div>
            <div className="flex flex-wrap items-center gap-3">
              <h1 className="font-mono text-2xl font-semibold tracking-tight">{dispute.dispute_id}</h1>
              <StatusBadge status={dispute.status} />
              <StatusBadge status={dispute.case_type} type="case" />
            </div>
            <p className="text-sm text-ink-muted">
              Dispute Reason: <span className="font-medium text-ink">{dispute.reason}</span>
            </p>
          </div>

          <div className="flex items-stretch divide-x divide-line rounded-lg border border-line bg-raised">
            <div className="px-5 py-3 text-right">
              <div className="eyebrow">Claim Amount</div>
              <div className="mt-1 text-2xl font-semibold tabular-nums text-ink">{formatINR(dispute.amount)}</div>
            </div>
            <div className="flex flex-col justify-center px-5 py-3 text-right">
              <div className="eyebrow">Payment ID</div>
              <div className="mono-id mt-1.5 font-medium text-ink">{dispute.payment_id}</div>
            </div>
          </div>
        </div>

        {/* Header Metadata */}
        <dl className="grid grid-cols-2 divide-line border-t border-line sm:grid-cols-4 sm:divide-x">
          {metadata.map((m) => (
            <div key={m.label} className="space-y-1.5 px-6 py-4">
              <dt className="eyebrow">{m.label}</dt>
              <dd className="text-sm">{m.value}</dd>
            </div>
          ))}
        </dl>
      </section>

      {domainContext && (
        <section className="card">
          <div className="border-b border-line px-6 py-4">
            <div className="eyebrow">Phase 2 Domain Context</div>
            <h2 className="mt-1 text-base font-semibold">Customer, order and transaction relationship</h2>
          </div>
          <dl className="grid grid-cols-1 divide-y divide-line sm:grid-cols-3 sm:divide-x sm:divide-y-0">
            <div className="space-y-1 px-6 py-4"><dt className="eyebrow">Customer</dt><dd className="text-sm font-medium">{domainContext.customer.name}</dd><dd className="text-xs text-ink-muted">{domainContext.customer.email || 'No email'}</dd></div>
            <div className="space-y-1 px-6 py-4"><dt className="eyebrow">Order</dt><dd className="font-mono text-sm text-accent-soft">{domainContext.order.external_order_id}</dd><dd className="text-xs text-ink-muted">{formatINR(domainContext.order.total_amount)} · {domainContext.order.order_status}</dd></div>
            <div className="space-y-1 px-6 py-4"><dt className="eyebrow">Transaction</dt><dd className="font-mono text-sm text-accent-soft">{domainContext.transaction.external_transaction_id}</dd><dd className="text-xs text-ink-muted">{formatINR(domainContext.transaction.amount)} · {domainContext.transaction.transaction_status}</dd></div>
          </dl>
        </section>
      )}

      {/* Main Investigation Split Layout */}
      <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">

        {/* Left Column (2 Cols): Decision Policy, AI Reasoning, Verification Checks, Evidence Matrix */}
        <div className="space-y-6 lg:col-span-2">

          {/* Decision Controls Panel */}
          <ActionControls
            decision={decision}
            disputeStatus={dispute.status}
            onApprove={handleApprove}
            onReject={handleReject}
            canReview={canReview}
          />

          {/* AI Investigation Reasoning Card */}
          <AIReasoningCard
            aiAnalysis={ai_analysis}
            decision={decision}
          />

          {/* Deterministic Verification Results */}
          <VerificationList verificationResults={verification_results} />

          {/* Evidence Documents Matrix */}
          <EvidenceMatrix
            evidenceList={evidenceList}
            uploadedEvidence={uploadedEvidence}
            onUpload={handleEvidenceUpload}
            canUpload={canInvestigate}
          />

        </div>

        {/* Right Column (1 Col): Readiness Gauge, Lifecycle Timeline, Audit Trail */}
        <div className="space-y-6">

          {/* Evidence Readiness Score Gauge */}
          <ReadinessGauge readinessScore={readiness_score} />

          {/* Transaction Lifecycle Timeline */}
          <TimelineView timeline={timeline} />

          {/* Immutable Audit Log Trail */}
          <AuditLogView auditEvents={auditEvents} />

        </div>

      </div>

    </div>
  );
}
