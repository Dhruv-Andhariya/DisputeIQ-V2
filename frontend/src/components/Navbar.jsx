import React, { useState } from 'react';
import { Link, NavLink, useMatch, useNavigate } from 'react-router-dom';
import { ShieldCheck, AlertTriangle, LayoutGrid, Home, Users, Database, LogOut } from 'lucide-react';
import { useAuth, PERMISSIONS } from '../auth/AuthContext';
import { triggerDemoFailure } from '../api';

const PRINCIPLES = [
  { key: 'Code', value: 'Correctness', dot: 'bg-emerald-400' },
  { key: 'AI', value: 'Reasoning', dot: 'bg-blue-400' },
  { key: 'Human', value: 'Judgment', dot: 'bg-amber-400' },
];

const navClass = ({ isActive }) =>
  `btn btn-sm ${isActive ? 'bg-raised text-ink border border-line' : 'btn-ghost'}`;

export default function Navbar() {
  const { user, organization, can, logout } = useAuth();
  const navigate = useNavigate();
  const disputeMatch = useMatch('/disputes/:disputeId');
  const currentDisputeId = disputeMatch?.params.disputeId;
  const [simulating, setSimulating] = useState(false);

  const handleTriggerFailure = async () => {
    setSimulating(true);
    try {
      await triggerDemoFailure(currentDisputeId);
      // New state value makes InvestigationDetail reload the (now failed) investigation
      navigate(`/disputes/${currentDisputeId}`, { replace: true, state: { refresh: Date.now() } });
    } catch {
      alert('Failed to simulate system failure scenario.');
    } finally {
      setSimulating(false);
    }
  };

  const handleLogout = async () => {
    await logout();
    navigate('/login', { replace: true });
  };

  return (
    <nav className="sticky top-0 z-50 border-b border-line bg-canvas/80 backdrop-blur-lg">
      <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
        <div className="flex h-16 items-center justify-between gap-4">

          {/* Logo & Brand Identity */}
          <Link
            to="/"
            className="group flex items-center gap-3 rounded-lg text-left focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent/60"
          >
            <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-accent text-white shadow-sm">
              <ShieldCheck className="h-5 w-5" />
            </div>
            <div className="hidden leading-tight sm:block">
              <div className="flex items-center gap-2">
                <span className="text-[15px] font-semibold tracking-tight text-ink">DisputeIQ</span>
                <span className="rounded border border-line bg-raised px-1.5 py-px text-2xs font-medium text-ink-muted">
                  AI Risk Manager
                </span>
              </div>
              <p className="text-xs text-ink-subtle">Evidence Intelligence Layer</p>
            </div>
          </Link>

          {/* Architecture Philosophy */}
          <div className="hidden items-center divide-x divide-line rounded-lg border border-line bg-surface 2xl:flex">
            {PRINCIPLES.map((p) => (
              <div key={p.key} className="flex items-center gap-2 px-3 py-1.5 text-xs">
                <span className={`h-1.5 w-1.5 rounded-full ${p.dot}`} />
                <span className="font-semibold text-ink">{p.key}</span>
                <span className="text-ink-subtle">=</span>
                <span className="text-ink-muted">{p.value}</span>
              </div>
            ))}
          </div>

          {/* Navigation & Action Controls */}
          <div className="flex items-center gap-2">
            <NavLink to="/" end className={navClass}>
              <Home className="h-4 w-4" />
              <span className="hidden md:inline">Dashboard</span>
            </NavLink>
            <NavLink to="/disputes" className={navClass}>
              <LayoutGrid className="h-4 w-4" />
              <span className="hidden md:inline">Disputes</span>
            </NavLink>
            <NavLink to="/merchant-data" className={navClass}>
              <Database className="h-4 w-4" />
              <span className="hidden md:inline">Merchant Data</span>
            </NavLink>
            {can(PERMISSIONS.MANAGE_USERS) && (
              <NavLink to="/team" className={navClass}>
                <Users className="h-4 w-4" />
                <span className="hidden md:inline">Team</span>
              </NavLink>
            )}

            {currentDisputeId && can(PERMISSIONS.INVESTIGATE) && (
              <button
                onClick={handleTriggerFailure}
                disabled={simulating}
                className="btn btn-sm btn-danger"
                title="Demonstrate Scenario 3: External Carrier Logistics API Failure"
              >
                <AlertTriangle className="h-4 w-4" />
                <span className="hidden lg:inline">Simulate System Failure</span>
              </button>
            )}

            {/* Current identity */}
            <div className="ml-2 flex items-center gap-3 border-l border-line pl-4">
              <div className="hidden text-right leading-tight sm:block">
                <div className="max-w-[180px] truncate text-[13px] font-medium text-ink" title={organization.name}>
                  {organization.name}
                </div>
                <div className="flex items-center justify-end gap-1.5 text-xs text-ink-subtle">
                  <span className="max-w-[120px] truncate">{user.name}</span>
                  <span className="rounded border border-line bg-raised px-1 py-px text-2xs font-semibold text-ink-muted">
                    {user.role}
                  </span>
                </div>
              </div>
              <button onClick={handleLogout} className="btn btn-ghost btn-icon" title="Sign out" aria-label="Sign out">
                <LogOut className="h-4 w-4" />
              </button>
            </div>
          </div>

        </div>
      </div>
    </nav>
  );
}
