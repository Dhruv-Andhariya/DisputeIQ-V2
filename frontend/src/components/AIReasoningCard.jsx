import React from 'react';
import { Cpu, CheckCircle, ShieldAlert, Sparkles, HelpCircle, Layers } from 'lucide-react';
import StatusBadge from './StatusBadge';
import CardHeader from './CardHeader';

function EvidenceGroup({ icon: Icon, title, items, panelClass, titleClass, textClass }) {
  return (
    <div className={`${panelClass} p-4`}>
      <h4 className={`mb-2 flex items-center gap-1.5 text-[13px] font-semibold ${titleClass}`}>
        <Icon className="h-3.5 w-3.5" />
        <span>{title}</span>
      </h4>
      <ul className={`space-y-1 text-[13px] leading-5 ${textClass}`}>
        {items.map((item, idx) => (
          <li key={idx} className="flex gap-2">
            <span className="mt-2 h-1 w-1 shrink-0 rounded-full bg-current opacity-60" />
            <span>{item}</span>
          </li>
        ))}
      </ul>
    </div>
  );
}

export default function AIReasoningCard({ aiAnalysis, decision }) {
  if (!aiAnalysis) {
    return (
      <section className="card flex flex-col items-center p-10 text-center">
        <Cpu className="mb-3 h-8 w-8 text-ink-subtle" />
        <p className="text-sm text-ink-muted">AI Investigation pending or unavailable.</p>
      </section>
    );
  }

  const { recommendation, confidence, case_summary, reasoning, supporting_evidence, missing_evidence, risk_flags } = aiAnalysis;
  const confPct = Math.round(confidence * 100);

  return (
    <section className="card">
      <CardHeader
        icon={Sparkles}
        tone="violet"
        title="AI Evidence Investigation & Reasoning"
        subtitle="Structured LLM Synthesis over Verified Context"
        action={
          <>
            <div className="w-28">
              <div className="flex items-baseline justify-between">
                <span className="text-xs text-ink-subtle">Confidence</span>
                <span className="text-sm font-semibold tabular-nums text-ink">{confPct}%</span>
              </div>
              <div className="mt-1 h-1 overflow-hidden rounded-full bg-raised">
                <div className="h-full rounded-full bg-violet-400" style={{ width: `${confPct}%` }} />
              </div>
            </div>
            <StatusBadge status={recommendation} type="recommendation" />
          </>
        }
      />

      <div className="card-body space-y-4">
        {/* Case Summary Box */}
        <div className="inset-panel p-4">
          <h4 className="eyebrow mb-1.5 flex items-center gap-1.5">
            <Layers className="h-3.5 w-3.5" />
            <span>Executive Case Summary</span>
          </h4>
          <p className="text-sm leading-6 text-ink">{case_summary}</p>
        </div>

        {/* Grid: Reasoning vs Evidence/Risk */}
        <div className="grid grid-cols-1 gap-4 md:grid-cols-2">

          {/* Reasoning Points */}
          <div className="inset-panel p-4">
            <h4 className="eyebrow mb-3 flex items-center gap-1.5">
              <Cpu className="h-3.5 w-3.5" />
              <span>AI Reasoning Logic</span>
            </h4>
            <ol className="space-y-2.5">
              {reasoning.map((point, idx) => (
                <li key={idx} className="flex gap-3 text-[13px] leading-5 text-ink-muted">
                  <span className="flex h-5 w-5 shrink-0 items-center justify-center rounded bg-violet-500/10 text-2xs font-semibold tabular-nums text-violet-300">
                    {idx + 1}
                  </span>
                  <span>{point}</span>
                </li>
              ))}
            </ol>
          </div>

          {/* Risk Flags & Missing Evidence */}
          <div className="space-y-3">
            {risk_flags.length > 0 && (
              <EvidenceGroup
                icon={ShieldAlert}
                title="Detected Risk Flags"
                items={risk_flags}
                panelClass="panel-danger"
                titleClass="text-rose-300"
                textClass="text-rose-200/90"
              />
            )}

            {missing_evidence.length > 0 && (
              <EvidenceGroup
                icon={HelpCircle}
                title="Missing Evidence Items"
                items={missing_evidence}
                panelClass="panel-warning"
                titleClass="text-amber-300"
                textClass="text-amber-200/90"
              />
            )}

            {supporting_evidence.length > 0 && (
              <EvidenceGroup
                icon={CheckCircle}
                title="Supporting Evidence"
                items={supporting_evidence}
                panelClass="panel-success"
                titleClass="text-emerald-300"
                textClass="text-emerald-200/90"
              />
            )}
          </div>

        </div>
      </div>
    </section>
  );
}
