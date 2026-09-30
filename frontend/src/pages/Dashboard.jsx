import React, { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { Building2, UserCircle2, KeyRound, ShieldCheck, Layers, ArrowRight, Activity, Check } from 'lucide-react';
import { useAuth, PERMISSIONS } from '../auth/AuthContext';
import { PERMISSION_LABELS, ROLE_DESCRIPTIONS } from '../auth/roles';
import { fetchDisputes, fetchOrganizationActivity } from '../api';
import CardHeader from '../components/CardHeader';
import { humanize } from '../utils/format';

export default function Dashboard() {
  const { user, organization, can } = useAuth();
  const [disputeCount, setDisputeCount] = useState(null);
  const [activity, setActivity] = useState([]);
  const canSeeActivity = can(PERMISSIONS.VIEW_ORGANIZATION_AUDIT);

  useEffect(() => {
    fetchDisputes().then((res) => setDisputeCount(res.data.length)).catch(() => setDisputeCount(null));
    if (canSeeActivity) {
      fetchOrganizationActivity(8).then((res) => setActivity(res.data)).catch(() => setActivity([]));
    }
  }, [canSeeActivity]);

  const identity = [
    { label: 'Organization', value: organization.name, sub: organization.slug, icon: Building2 },
    { label: 'User', value: user.name, sub: user.email, icon: UserCircle2 },
    { label: 'Role', value: user.role, sub: ROLE_DESCRIPTIONS[user.role], icon: KeyRound },
    { label: 'Status', value: 'Authenticated', sub: 'Session verified by the API', icon: ShieldCheck, tone: 'text-emerald-400' },
  ];

  return (
    <div className="mx-auto max-w-7xl space-y-6 px-4 py-8 sm:px-6 lg:px-8">
      <header className="space-y-1">
        <div className="eyebrow">{organization.name}</div>
        <h1 className="text-2xl font-semibold">Welcome, {user.name}</h1>
        <p className="text-[15px] text-ink-muted">Everything you see in DisputeIQ is scoped to your organization.</p>
      </header>

      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
        {identity.map(({ label, value, sub, icon: Icon, tone }) => (
          <div key={label} className="card p-5">
            <div className="flex items-center justify-between">
              <span className="text-[13px] font-medium text-ink-muted">{label}</span>
              <Icon className={`h-4 w-4 ${tone || 'text-ink-subtle'}`} />
            </div>
            <div className={`mt-3 truncate text-lg font-semibold ${tone || 'text-ink'}`}>{value}</div>
            <div className="mt-1 line-clamp-2 text-xs text-ink-subtle">{sub}</div>
          </div>
        ))}
      </div>

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
        <section className="card lg:col-span-1">
          <CardHeader icon={Layers} tone="blue" title="Your workspace" subtitle="Disputes owned by your organization" />
          <div className="card-body space-y-4">
            <div className="text-3xl font-semibold tabular-nums">{disputeCount ?? '—'}</div>
            <Link to="/disputes" className="btn btn-secondary btn-sm">
              <span>Open disputes</span>
              <ArrowRight className="h-3.5 w-3.5" />
            </Link>
          </div>
        </section>

        <section className="card lg:col-span-2">
          <CardHeader icon={KeyRound} tone="violet" title="Your permissions" subtitle={`Granted by the ${user.role} role`} />
          <ul className="card-body grid grid-cols-1 gap-2 sm:grid-cols-2">
            {Object.entries(PERMISSION_LABELS).map(([perm, label]) => {
              const granted = user.permissions.includes(perm);
              return (
                <li key={perm} className={`flex items-center gap-2 text-[13px] ${granted ? 'text-ink' : 'text-ink-subtle line-through'}`}>
                  <Check className={`h-3.5 w-3.5 ${granted ? 'text-emerald-400' : 'opacity-0'}`} />
                  {label}
                </li>
              );
            })}
          </ul>
        </section>
      </div>

      {canSeeActivity && (
        <section className="card">
          <CardHeader icon={Activity} tone="emerald" title="Recent organization activity" subtitle="Every event is attributed to the user who performed it" />
          <ul className="divide-y divide-line">
            {activity.length === 0 && <li className="px-5 py-6 text-sm text-ink-muted">No activity yet.</li>}
            {activity.map((e) => (
              <li key={e.event_id} className="flex flex-wrap items-center justify-between gap-2 px-5 py-3 text-[13px]">
                <div className="min-w-0">
                  <span className="font-medium text-ink">{humanize(e.event_type)}</span>
                  <span className="ml-2 text-ink-muted">{e.description}</span>
                </div>
                <div className="text-xs tabular-nums text-ink-subtle">
                  {e.actor_name || 'System'} · {e.timestamp}
                </div>
              </li>
            ))}
          </ul>
        </section>
      )}
    </div>
  );
}
