import React from 'react';
import { GitCommit, ShoppingBag, CreditCard, Receipt, Truck, CheckCircle2, MessageSquare, AlertOctagon } from 'lucide-react';
import StatusBadge from './StatusBadge';
import CardHeader from './CardHeader';
import { humanize } from '../utils/format';

export default function TimelineView({ timeline }) {
  const getEventIcon = (eventType) => {
    switch (eventType) {
      case 'ORDER_PLACED': return ShoppingBag;
      case 'PAYMENT_CAPTURED': return CreditCard;
      case 'INVOICE_GENERATED': return Receipt;
      case 'SHIPMENT_DISPATCHED': return Truck;
      case 'DELIVERY_COMPLETED': return CheckCircle2;
      case 'CUSTOMER_COMMUNICATION': return MessageSquare;
      case 'DISPUTE_FILED': return AlertOctagon;
      default: return GitCommit;
    }
  };

  return (
    <section className="card">
      <CardHeader
        icon={GitCommit}
        tone="violet"
        title="Transaction Lifecycle Timeline"
        subtitle="Chronological reconstruction derived exclusively from verified system records"
      />

      <div className="card-body">
        <ol className="relative">
          {timeline.map((evt, idx) => {
            const Icon = getEventIcon(evt.event_type);
            const isContradicted = evt.verification_state === 'CONTRADICTED';
            const isDispute = evt.event_type === 'DISPUTE_FILED';
            const isLast = idx === timeline.length - 1;

            return (
              <li key={idx} className="relative flex gap-3.5 pb-6 last:pb-0">
                {/* Connector line */}
                {!isLast && <span className="absolute left-[13px] top-8 bottom-0 w-px bg-line" />}

                {/* Timeline node icon */}
                <div
                  className={`relative z-10 flex h-7 w-7 shrink-0 items-center justify-center rounded-full border ${
                    isContradicted
                      ? 'border-rose-500/40 bg-rose-500/15 text-rose-300'
                      : isDispute
                      ? 'border-amber-500/40 bg-amber-500/15 text-amber-300'
                      : 'border-line bg-raised text-ink-muted'
                  }`}
                >
                  <Icon className="h-3.5 w-3.5" />
                </div>

                {/* Event content */}
                <div className="min-w-0 flex-1 pt-0.5">
                  <div className="flex flex-wrap items-center justify-between gap-x-2 gap-y-1">
                    <span
                      className={`text-sm font-medium ${
                        isContradicted ? 'text-rose-300' : isDispute ? 'text-amber-300' : 'text-ink'
                      }`}
                    >
                      {humanize(evt.event_type)}
                    </span>
                    <StatusBadge status={evt.verification_state} type="evidence" />
                  </div>

                  <div className="mt-1 flex flex-wrap items-center gap-2 text-xs text-ink-subtle">
                    <span className="tabular-nums">{evt.timestamp}</span>
                    <span className="h-0.5 w-0.5 rounded-full bg-ink-subtle" />
                    <span>{humanize(evt.source)}</span>
                  </div>

                  <p className="mt-1.5 text-[13px] leading-5 text-ink-muted">{evt.description}</p>
                </div>
              </li>
            );
          })}
        </ol>
      </div>
    </section>
  );
}
