import React from 'react';
import { Navigate, Outlet, useLocation } from 'react-router-dom';
import { ShieldAlert } from 'lucide-react';
import { useAuth } from '../auth/AuthContext';

export function FullPageSpinner({ label = 'Loading…' }) {
  return (
    <div className="flex min-h-screen flex-col items-center justify-center bg-canvas">
      <div className="spinner mb-3" />
      <p className="text-sm text-ink-muted">{label}</p>
    </div>
  );
}

// Gate for authenticated routes. With `permission`, also requires that capability.
export default function ProtectedRoute({ permission, children }) {
  const { status, can } = useAuth();
  const location = useLocation();

  if (status === 'loading') return <FullPageSpinner label="Restoring your session…" />;
  if (status !== 'authenticated') {
    return <Navigate to="/login" replace state={{ from: location.pathname + location.search }} />;
  }
  if (permission && !can(permission)) {
    return (
      <div className="mx-auto max-w-xl px-4 py-20">
        <div className="panel-warning flex items-start gap-3 p-5">
          <ShieldAlert className="mt-0.5 h-5 w-5 shrink-0 text-amber-400" />
          <div>
            <h2 className="text-sm font-semibold">You don&apos;t have access to this page</h2>
            <p className="mt-1 text-[13px] text-ink-muted">Ask an administrator of your organization if you need it.</p>
          </div>
        </div>
      </div>
    );
  }
  return children ?? <Outlet />;
}

// Login/register pages: an already signed-in user goes straight to the app.
export function PublicOnlyRoute({ children }) {
  const { status } = useAuth();
  if (status === 'loading') return <FullPageSpinner label="Restoring your session…" />;
  if (status === 'authenticated') return <Navigate to="/" replace />;
  return children;
}
