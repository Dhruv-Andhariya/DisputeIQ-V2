import React from 'react';
import { Terminal } from 'lucide-react';
import CardHeader from './CardHeader';
import { humanize } from '../utils/format';

export default function AuditLogView({ auditEvents }) {
  const getEventBadgeClass = (type) => {
    switch (type) {
      case 'EVIDENCE_CONFLICT':
      case 'API_FAILURE':
        return 'text-rose-300 bg-rose-500/10 border-rose-500/25';
      case 'EVIDENCE_VERIFIED':
      case 'HUMAN_APPROVED':
        return 'text-emerald-300 bg-emerald-500/10 border-emerald-500/20';
      case 'RETRY_ATTEMPT':
      case 'HUMAN_REVIEW_REQUESTED':
      case 'ESCALATED':
        return 'text-amber-300 bg-amber-500/10 border-amber-500/25';
      default:
        return 'text-blue-300 bg-blue-500/10 border-blue-500/20';
    }
  };

  return (
    <section className="card">
      <CardHeader
        icon={Terminal}
        tone="emerald"
        title="Immutable Audit Trail"
        subtitle="Full compliance audit log recorded in database"
        action={<span className="chip tabular-nums">{auditEvents.length} Events Logged</span>}
      />

      <ul className="max-h-96 divide-y divide-line overflow-y-auto">
        {auditEvents.map((evt) => (
          <li key={evt.event_id} className="space-y-1.5 px-5 py-3.5">
            <div className="flex flex-wrap items-center justify-between gap-2">
              <span className={`rounded-md border px-2 py-0.5 text-xs font-medium ${getEventBadgeClass(evt.event_type)}`}>
                {humanize(evt.event_type)}
              </span>
              <span className="text-xs tabular-nums text-ink-subtle">{evt.timestamp}</span>
            </div>

            <p className="text-[13px] leading-5 text-ink-muted">{evt.description}</p>
            <p className="text-2xs text-ink-subtle">
              <span className="font-medium text-ink-muted">{evt.actor_name ? `${evt.actor_name} (${evt.actor_email})` : 'System'}</span>
              <span className="mx-1.5">·</span>
              <span className="font-mono">{evt.event_id}</span>
            </p>

            {evt.metadata && Object.keys(evt.metadata).length > 0 && (
              <div className="code-block p-2 text-2xs">
                <pre>{JSON.stringify(evt.metadata, null, 2)}</pre>
              </div>
            )}
          </li>
        ))}
      </ul>
    </section>
  );
}
