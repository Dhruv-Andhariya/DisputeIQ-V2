import React from 'react';

const ICON_TONES = {
  neutral: 'border-line bg-raised text-ink-muted',
  blue: 'border-blue-500/20 bg-blue-500/10 text-blue-400',
  violet: 'border-violet-500/20 bg-violet-500/10 text-violet-400',
  emerald: 'border-emerald-500/20 bg-emerald-500/10 text-emerald-400',
  amber: 'border-amber-500/20 bg-amber-500/10 text-amber-400',
  rose: 'border-rose-500/20 bg-rose-500/10 text-rose-400',
};

export default function CardHeader({ icon: Icon, tone = 'neutral', title, subtitle, action }) {
  return (
    <div className="card-header">
      <div className="flex min-w-0 items-start gap-3">
        {Icon && (
          <div className={`icon-tile ${ICON_TONES[tone]}`}>
            <Icon className="h-4 w-4" />
          </div>
        )}
        <div className="min-w-0">
          <h3 className="card-title">{title}</h3>
          {subtitle && <p className="card-subtitle">{subtitle}</p>}
        </div>
      </div>
      {action && <div className="flex shrink-0 items-center gap-2">{action}</div>}
    </div>
  );
}
