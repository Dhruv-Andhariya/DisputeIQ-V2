import React, { useState } from 'react';
import { UserCheck, ShieldAlert, CheckCircle, XCircle, Lock, ArrowRight } from 'lucide-react';
import StatusBadge from './StatusBadge';
import CardHeader from './CardHeader';

export default function ActionControls({ decision, disputeStatus, onApprove, onReject, canReview = true }) {
  const [notes, setNotes] = useState('');
  const [loading, setLoading] = useState(false);

  const { final_decision, recommended_action, safety_override_triggered, override_reason, reasoning_summary } = decision;

  const handleApprove = async () => {
    setLoading(true);
    await onApprove(notes);
    setLoading(false);
  };

  const handleReject = async () => {
    setLoading(true);
    await onReject(notes);
    setLoading(false);
  };

  const isClosed = disputeStatus === 'CONTESTED' || disputeStatus === 'REJECTED';

  return (
    <section className="card">
      <CardHeader
        icon={UserCheck}
        tone="amber"
        title="Decision Engine & Human Control Point"
        subtitle="Bounded AI Decision Policy + Merchant Analyst Control Interface"
        action={
          <>
            <span className="text-xs text-ink-subtle">System Recommendation</span>
            <StatusBadge status={final_decision} type="decision" />
          </>
        }
      />

      <div className="card-body space-y-5">
        {/* Safety Override Alert (PRIMARY DEMO MOMENT CARD) */}
        {safety_override_triggered && (
          <div className="panel-danger border-l-2 border-l-rose-500 p-4">
            <div className="flex items-start gap-3">
              <ShieldAlert className="mt-0.5 h-5 w-5 shrink-0 text-rose-400" />
              <div className="min-w-0 space-y-1.5">
                <div className="flex flex-wrap items-center gap-2">
                  <h4 className="text-sm font-semibold text-rose-200">Deterministic Safety Override Triggered</h4>
                  <span className="rounded bg-rose-500 px-1.5 py-px text-2xs font-semibold uppercase tracking-wide text-white">
                    Auto-contest blocked
                  </span>
                </div>
                <p className="text-sm font-medium text-rose-300">{override_reason}</p>
                <p className="text-[13px] leading-5 text-ink-muted">
                  Deterministic rules detected a critical data conflict. Even if the AI model suggests contesting, the safety rule overrides the final decision to <span className="font-medium text-amber-300">Human review</span>.
                </p>
              </div>
            </div>
          </div>
        )}

        {/* Action Recommendation Box */}
        <div className="inset-panel p-4">
          <h4 className="eyebrow">Recommended Action Policy</h4>
          <p className="mt-1.5 text-sm font-medium text-ink">{recommended_action}</p>

          {reasoning_summary && reasoning_summary.length > 0 && (
            <ul className="mt-3 space-y-1 border-t border-line pt-3">
              {reasoning_summary.map((line, idx) => (
                <li key={idx} className="text-[13px] leading-5 text-ink-muted">{line}</li>
              ))}
            </ul>
          )}
        </div>

        {/* Human Action Input */}
        {!isClosed && !canReview ? (
          <div className="inset-panel flex items-center gap-2 p-4 text-[13px] text-ink-muted">
            <Lock className="h-4 w-4 shrink-0 text-amber-400" />
            <span>Awaiting a final decision from an organization admin. Your role can view this case but not approve or reject it.</span>
          </div>
        ) : !isClosed ? (
          <div className="space-y-4">
            <div>
              <label htmlFor="analyst-notes" className="field-label">
                Human Analyst Case Notes &amp; Audit Rationale
              </label>
              <textarea
                id="analyst-notes"
                rows={3}
                value={notes}
                onChange={(e) => setNotes(e.target.value)}
                placeholder="Enter notes regarding evidence review, customer history, or approval rationale..."
                className="input resize-y py-2.5 leading-5"
              />
            </div>

            <div className="flex flex-wrap items-center justify-between gap-4 border-t border-line pt-4">
              <div className="flex items-center gap-2 text-[13px] text-ink-muted">
                <Lock className="h-4 w-4 shrink-0 text-amber-400" />
                <span>Human approval required for financial submission</span>
              </div>

              <div className="flex items-center gap-2">
                <button disabled={loading} onClick={handleReject} className="btn btn-secondary">
                  <XCircle className="h-4 w-4 text-ink-muted" />
                  <span>Reject / Accept Dispute</span>
                </button>

                <button disabled={loading} onClick={handleApprove} className="btn btn-primary">
                  <CheckCircle className="h-4 w-4" />
                  <span>Approve &amp; Submit Contest</span>
                  <ArrowRight className="h-4 w-4" />
                </button>
              </div>
            </div>
          </div>
        ) : (
          <div className="panel-success flex flex-wrap items-center justify-between gap-3 p-4">
            <div className="flex items-center gap-2.5 text-sm text-emerald-300">
              <CheckCircle className="h-5 w-5 text-emerald-400" />
              <span>Human Analyst Action Completed. Status: <span className="font-semibold text-ink">{disputeStatus}</span></span>
            </div>
            <span className="chip">Mock Razorpay Logged</span>
          </div>
        )}
      </div>
    </section>
  );
}
