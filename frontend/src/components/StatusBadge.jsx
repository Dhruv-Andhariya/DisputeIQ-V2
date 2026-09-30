import React from 'react';
import { CheckCircle2, AlertTriangle, XCircle, ShieldAlert, Clock, UserCheck, Zap } from 'lucide-react';
import { humanize } from '../utils/format';

const TONES = {
  success: 'bg-emerald-500/10 text-emerald-300 border-emerald-500/20',
  danger: 'bg-rose-500/10 text-rose-300 border-rose-500/25',
  warning: 'bg-amber-500/10 text-amber-300 border-amber-500/25',
  info: 'bg-blue-500/10 text-blue-300 border-blue-500/20',
  violet: 'bg-violet-500/10 text-violet-300 border-violet-500/20',
  neutral: 'bg-raised text-ink-muted border-line',
};

// [tone, icon, optional label override]
const DECISION = {
  CONTEST: ['success', CheckCircle2],
  DO_NOT_CONTEST: ['danger', XCircle],
  HUMAN_REVIEW: ['warning', UserCheck, 'Human review required'],
};

const VARIANTS = {
  verification: {
    PASSED: ['success', CheckCircle2],
    FAILED: ['danger', XCircle],
    WARNING: ['warning', AlertTriangle],
  },
  decision: DECISION,
  recommendation: DECISION,
  evidence: {
    VERIFIED: ['success', CheckCircle2],
    CONTRADICTED: ['danger', ShieldAlert],
    MISSING: ['danger', XCircle],
    PARTIALLY_VERIFIED: ['warning', AlertTriangle],
  },
  case: {
    STRONG_CASE: ['success', null],
    CONTRADICTORY_CASE: ['danger', null],
  },
  status: {
    OPEN: ['info', Clock],
    INVESTIGATING: ['violet', Zap],
    HUMAN_REVIEW: ['warning', UserCheck, 'Human review'],
    CONTESTED: ['success', CheckCircle2],
    REJECTED: ['neutral', XCircle],
  },
};

const FALLBACK = {
  case: ['warning', null],
  default: ['neutral', Clock],
};

export default function StatusBadge({ status, type = 'status' }) {
  const [tone, Icon, label] =
    (VARIANTS[type] || VARIANTS.status)[status] || FALLBACK[type] || FALLBACK.default;

  return (
    <span
      className={`inline-flex items-center gap-1.5 whitespace-nowrap rounded-md border px-2 py-0.5 text-xs font-medium ${TONES[tone]}`}
    >
      {Icon && <Icon className="h-3.5 w-3.5 shrink-0" />}
      <span>{label || humanize(status)}</span>
    </span>
  );
}
