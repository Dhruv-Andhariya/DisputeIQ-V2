import React from 'react';
import { ShieldCheck, AlertTriangle, XCircle, CheckCircle2 } from 'lucide-react';
import StatusBadge from './StatusBadge';
import CardHeader from './CardHeader';
import { humanize } from '../utils/format';

export default function VerificationList({ verificationResults }) {
  return (
    <section className="card">
      <CardHeader
        icon={ShieldCheck}
        tone="emerald"
        title="Deterministic Verification Engine Output"
        subtitle="Hard factual consistency checks executed prior to AI reasoning"
        action={<span className="chip">9 Deterministic Rules Executed</span>}
      />

      <ul className="divide-y divide-line">
        {verificationResults.map((item, idx) => {
          const isFailed = item.status === 'FAILED';
          const isWarning = item.status === 'WARNING';
          const isCritical = item.severity === 'CRITICAL' || item.severity === 'HIGH';

          return (
            <li
              key={idx}
              className={`relative px-5 py-4 ${
                isFailed ? 'bg-rose-500/[0.04]' : isWarning ? 'bg-amber-500/[0.04]' : ''
              }`}
            >
              {(isFailed || isWarning) && (
                <span className={`absolute inset-y-0 left-0 w-0.5 ${isFailed ? 'bg-rose-500' : 'bg-amber-500'}`} />
              )}

              <div className="flex flex-wrap items-start justify-between gap-2">
                <div className="flex items-start gap-3">
                  {isFailed ? (
                    <XCircle className="mt-0.5 h-4 w-4 shrink-0 text-rose-400" />
                  ) : isWarning ? (
                    <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0 text-amber-400" />
                  ) : (
                    <CheckCircle2 className="mt-0.5 h-4 w-4 shrink-0 text-emerald-400" />
                  )}
                  <div>
                    <h4 className="text-sm font-medium text-ink">{humanize(item.check)}</h4>
                    <span className="text-xs text-ink-subtle">
                      Severity:{' '}
                      <span className={isCritical ? 'font-medium text-rose-400' : 'text-ink-muted'}>
                        {humanize(item.severity)}
                      </span>
                    </span>
                  </div>
                </div>
                <StatusBadge status={item.status} type="verification" />
              </div>

              <p className={`ml-7 mt-2 text-[13px] leading-5 ${isFailed ? 'text-rose-300' : isWarning ? 'text-amber-300' : 'text-ink-muted'}`}>
                {item.message}
              </p>

              {/* Expected vs Actual */}
              <dl className="ml-7 mt-3 grid grid-cols-1 gap-2 sm:grid-cols-2">
                <div className="inset-panel px-3 py-2">
                  <dt className="eyebrow">Expected</dt>
                  <dd className="mt-0.5 break-all font-mono text-xs text-emerald-300">{String(item.expected)}</dd>
                </div>
                <div className="inset-panel px-3 py-2">
                  <dt className="eyebrow">Actual</dt>
                  <dd className={`mt-0.5 break-all font-mono text-xs ${isFailed ? 'text-rose-300' : isWarning ? 'text-amber-300' : 'text-ink'}`}>
                    {String(item.actual)}
                  </dd>
                </div>
              </dl>
            </li>
          );
        })}
      </ul>
    </section>
  );
}
