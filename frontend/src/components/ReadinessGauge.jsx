import React from 'react';
import { Gauge } from 'lucide-react';
import CardHeader from './CardHeader';

const RADIUS = 34;
const CIRCUMFERENCE = 2 * Math.PI * RADIUS;

function scoreTone(pct, warnAt, goodAt) {
  if (pct < warnAt) return { stroke: 'stroke-rose-400', bar: 'bg-rose-400', text: 'text-rose-300' };
  if (pct < goodAt) return { stroke: 'stroke-amber-400', bar: 'bg-amber-400', text: 'text-amber-300' };
  return { stroke: 'stroke-emerald-400', bar: 'bg-emerald-400', text: 'text-emerald-300' };
}

export default function ReadinessGauge({ readinessScore }) {
  const { total_score, components, summary } = readinessScore;
  const tone = scoreTone(total_score, 55, 75);
  const clamped = Math.max(0, Math.min(100, total_score));

  return (
    <section className="card">
      <CardHeader
        icon={Gauge}
        tone="blue"
        title="Evidence Readiness Score"
        subtitle="Decomposable strength metric for merchant defense package"
      />

      <div className="card-body space-y-5">
        <div className="flex items-center gap-5">
          {/* Radial score */}
          <div className="relative h-20 w-20 shrink-0">
            <svg viewBox="0 0 80 80" className="h-full w-full -rotate-90">
              <circle cx="40" cy="40" r={RADIUS} fill="none" strokeWidth="6" className="stroke-raised" />
              <circle
                cx="40"
                cy="40"
                r={RADIUS}
                fill="none"
                strokeWidth="6"
                strokeLinecap="round"
                className={`${tone.stroke} transition-[stroke-dashoffset] duration-700`}
                strokeDasharray={CIRCUMFERENCE}
                strokeDashoffset={CIRCUMFERENCE * (1 - clamped / 100)}
              />
            </svg>
            <div className="absolute inset-0 flex flex-col items-center justify-center">
              <span className={`text-xl font-semibold tabular-nums leading-none ${tone.text}`}>{total_score}</span>
              <span className="mt-0.5 text-2xs text-ink-subtle">/ 100</span>
            </div>
          </div>

          <p className="text-[13px] leading-5 text-ink-muted">{summary}</p>
        </div>

        {/* Breakdown progress bars */}
        <div className="space-y-4 border-t border-line pt-5">
          {components.map((comp, idx) => {
            const pct = Math.round((comp.score / comp.max_score) * 100);
            const barTone = scoreTone(pct, 50, 75);

            return (
              <div key={idx} className="space-y-1.5">
                <div className="flex items-baseline justify-between gap-3 text-[13px]">
                  <span className="font-medium text-ink">{comp.name}</span>
                  <span className="shrink-0 tabular-nums text-ink-subtle">
                    <span className="font-semibold text-ink">{comp.score}</span> / {comp.max_score} pts ({pct}%)
                  </span>
                </div>

                <div className="h-1.5 w-full overflow-hidden rounded-full bg-raised">
                  <div
                    className={`h-full rounded-full transition-all duration-500 ${barTone.bar}`}
                    style={{ width: `${pct}%` }}
                  />
                </div>

                <p className="text-xs leading-5 text-ink-subtle">{comp.explanation}</p>
              </div>
            );
          })}
        </div>
      </div>
    </section>
  );
}
