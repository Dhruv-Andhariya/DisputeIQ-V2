import React, { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { fetchDisputes, fetchEvaluationSummary } from '../api';
import StatusBadge from '../components/StatusBadge';
import { humanize, formatINR } from '../utils/format';
import { Search, AlertTriangle, ArrowRight, BarChart2, CheckCircle2, UserCheck, Sparkles, Layers, X } from 'lucide-react';

export default function DisputeList({ onSelectDispute }) {
  const [disputes, setDisputes] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [search, setSearch] = useState('');
  const [filterType, setFilterType] = useState('ALL');
  const [evalSummary, setEvalSummary] = useState(null);
  const [showEvalModal, setShowEvalModal] = useState(false);

  useEffect(() => {
    loadDisputes();
    loadEvalSummary();
  }, []);

  const loadDisputes = async () => {
    try {
      setLoading(true);
      const res = await fetchDisputes();
      setDisputes(res.data);
    } catch (err) {
      console.error(err);
      setError('Failed to connect to DisputeIQ backend API.');
    } finally {
      setLoading(false);
    }
  };

  const loadEvalSummary = async () => {
    try {
      const res = await fetchEvaluationSummary();
      if (res.data && !['NOT_RUN', 'NOT_AVAILABLE'].includes(res.data.status)) {
        setEvalSummary(res.data);
      }
    } catch (e) {
      console.log('Eval summary not loaded yet');
    }
  };

  const filtered = disputes.filter((d) => {
    const matchesSearch =
      d.dispute_id.toLowerCase().includes(search.toLowerCase()) ||
      d.payment_id.toLowerCase().includes(search.toLowerCase()) ||
      d.case_type.toLowerCase().includes(search.toLowerCase());

    const matchesFilter = filterType === 'ALL' || d.case_type === filterType;

    return matchesSearch && matchesFilter;
  });

  const caseTypes = ['ALL', 'STRONG_CASE', 'WEAK_CASE', 'CONTRADICTORY_CASE', 'MISSING_EVIDENCE_CASE', 'EDGE_CASE'];

  const stats = {
    total: disputes.length,
    strong: disputes.filter(d => d.case_type === 'STRONG_CASE').length,
    contradictory: disputes.filter(d => d.case_type === 'CONTRADICTORY_CASE').length,
    reviewNeeded: disputes.filter(d => d.status === 'HUMAN_REVIEW').length,
  };

  const statCards = [
    { label: 'Total Disputes', value: stats.total, note: 'Synthetic Dataset (Seed 42)', icon: Layers, tone: 'text-ink-muted' },
    { label: 'Strong Cases', value: stats.strong, note: 'High Evidence Readiness', icon: CheckCircle2, tone: 'text-emerald-400' },
    { label: 'Contradictions', value: stats.contradictory, note: 'Order ID / Amount Conflicts', icon: AlertTriangle, tone: 'text-rose-400' },
    { label: 'Human Review', value: stats.reviewNeeded, note: 'Auto Action Blocked', icon: UserCheck, tone: 'text-amber-400' },
  ];

  const metrics = evalSummary
    ? [
        { label: 'Accuracy', value: evalSummary.metrics.recommendation_accuracy, tone: 'text-emerald-400' },
        { label: 'False Contest', value: evalSummary.metrics.false_contest_rate, tone: 'text-rose-400' },
        { label: 'False Acceptance', value: evalSummary.metrics.false_acceptance_rate, tone: 'text-amber-400' },
        { label: 'Escalation', value: evalSummary.metrics.human_escalation_rate, tone: 'text-blue-400' },
      ]
    : [];

  return (
    <div className="mx-auto max-w-7xl space-y-6 px-4 py-8 sm:px-6 lg:px-8">

      {/* Page Header */}
      <header className="flex flex-wrap items-end justify-between gap-6 pb-2">
        <div className="max-w-3xl space-y-3">
          <div className="chip">
            <Sparkles className="h-3.5 w-3.5 text-accent-soft" />
            <span>AI Risk Manager</span>
          </div>
          <h1 className="text-2xl font-semibold sm:text-[28px] sm:leading-9">
            Dispute Investigation &amp; Risk Intelligence
          </h1>
          <p className="max-w-2xl text-[15px] leading-6 text-ink-muted">
            Automated evidence verification, lifecycle timeline reconstruction, and bounded AI decision policy for merchant chargebacks.
          </p>
        </div>

        {evalSummary && (
          <button onClick={() => setShowEvalModal(true)} className="btn btn-secondary">
            <BarChart2 className="h-4 w-4 text-accent-soft" />
            <span>View Benchmark Evaluation</span>
            <span className="rounded bg-emerald-500/10 px-1.5 py-px text-xs font-semibold tabular-nums text-emerald-300">
              {evalSummary.metrics.recommendation_accuracy}
            </span>
          </button>
        )}
      </header>

      {/* Metrics Summary Cards */}
      <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
        {statCards.map(({ label, value, note, icon: Icon, tone }) => (
          <div key={label} className="card p-5">
            <div className="flex items-center justify-between">
              <span className="text-[13px] font-medium text-ink-muted">{label}</span>
              <Icon className={`h-4 w-4 ${tone}`} />
            </div>
            <div className="mt-3 text-3xl font-semibold tabular-nums tracking-tight text-ink">{value}</div>
            <div className="mt-1 text-xs text-ink-subtle">{note}</div>
          </div>
        ))}
      </div>

      {/* Filter & Search Bar */}
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div className="relative min-w-[260px] flex-1 lg:max-w-sm">
          <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-ink-subtle" />
          <input
            type="text"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Search dispute ID, payment reference, or archetype..."
            className="input h-9 pl-9"
          />
        </div>

        <div className="flex items-center gap-1 overflow-x-auto rounded-lg border border-line bg-surface p-1">
          {caseTypes.map((type) => (
            <button
              key={type}
              onClick={() => setFilterType(type)}
              className={`h-7 whitespace-nowrap rounded-md px-3 text-[13px] font-medium transition-colors ${
                filterType === type
                  ? 'bg-raised-hover text-ink shadow-sm'
                  : 'text-ink-muted hover:text-ink'
              }`}
            >
              {humanize(type)}
            </button>
          ))}
        </div>
      </div>

      {/* Disputes Table */}
      {loading ? (
        <div className="card flex flex-col items-center justify-center py-20">
          <div className="spinner mb-3" />
          <p className="text-sm text-ink-muted">Loading dispute records...</p>
        </div>
      ) : error ? (
        <div className="panel-danger flex items-center justify-center gap-2 p-6 text-sm text-rose-300">
          <AlertTriangle className="h-4 w-4" />
          <span>{error}</span>
        </div>
      ) : (
        <div className="card overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full border-collapse text-left">
              <thead>
                <tr className="border-b border-line bg-raised/50">
                  {['Dispute ID', 'Payment Ref', 'Claim Amount', 'Dispute Category', 'Archetype', 'Status'].map((h) => (
                    <th key={h} className="eyebrow whitespace-nowrap px-5 py-3 font-medium">{h}</th>
                  ))}
                  <th className="eyebrow px-5 py-3 text-right font-medium">Action</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-line text-sm">
                {filtered.map((d) => (
                  <tr key={d.dispute_id} className="group transition-colors hover:bg-raised/60">
                    <td className="mono-id whitespace-nowrap px-5 py-3.5 font-medium text-accent-soft">
                      {d.dispute_id}
                    </td>
                    <td className="mono-id whitespace-nowrap px-5 py-3.5 text-ink-muted">
                      {d.payment_id}
                    </td>
                    <td className="whitespace-nowrap px-5 py-3.5 font-medium tabular-nums text-ink">
                      {formatINR(d.amount)}
                    </td>
                    <td className="px-5 py-3.5 text-ink-muted">
                      {d.reason}
                    </td>
                    <td className="px-5 py-3.5">
                      <StatusBadge status={d.case_type} type="case" />
                    </td>
                    <td className="px-5 py-3.5">
                      <StatusBadge status={d.status} />
                    </td>
                    <td className="px-5 py-3.5 text-right">
                      <Link
                        to={`/disputes/${d.dispute_id}`}
                        className="btn btn-sm btn-secondary group-hover:border-accent/40 group-hover:text-accent-soft"
                      >
                        <span>Investigate</span>
                        <ArrowRight className="h-3.5 w-3.5 transition-transform group-hover:translate-x-0.5" />
                      </Link>
                    </td>
                  </tr>
                ))}
                {filtered.length === 0 && (
                  <tr>
                    <td colSpan={7} className="px-5 py-14 text-center text-sm text-ink-muted">
                      No disputes match your search or filter.
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Evaluation Modal */}
      {showEvalModal && evalSummary && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 p-4 backdrop-blur-sm">
          <div className="max-h-[90vh] w-full max-w-2xl overflow-y-auto rounded-xl border border-line bg-surface shadow-pop">
            <div className="flex items-center justify-between border-b border-line px-6 py-4">
              <h3 className="flex items-center gap-2.5 text-base font-semibold">
                <BarChart2 className="h-5 w-5 text-accent-soft" />
                <span>Held-Out Benchmark Evaluation Report</span>
              </h3>
              <button
                onClick={() => setShowEvalModal(false)}
                className="btn btn-ghost btn-icon"
                aria-label="Close"
              >
                <X className="h-4 w-4" />
              </button>
            </div>

            <div className="space-y-5 p-6">
              <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
                {metrics.map((m) => (
                  <div key={m.label} className="inset-panel p-4">
                    <div className="eyebrow">{m.label}</div>
                    <div className={`mt-1.5 text-2xl font-semibold tabular-nums ${m.tone}`}>{m.value}</div>
                  </div>
                ))}
              </div>

              <div>
                <h4 className="eyebrow mb-2">Confusion Matrix</h4>
                <div className="code-block text-accent-soft">
                  <pre>{JSON.stringify(evalSummary.confusion_matrix, null, 2)}</pre>
                </div>
              </div>
            </div>

            <div className="flex justify-end border-t border-line px-6 py-4">
              <button onClick={() => setShowEvalModal(false)} className="btn btn-secondary">
                Close Report
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
