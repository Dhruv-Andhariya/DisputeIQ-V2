import React from 'react';
import { BrowserRouter, Navigate, Outlet, Route, Routes, useLocation, useNavigate, useParams } from 'react-router-dom';
import { AuthProvider, PERMISSIONS } from './auth/AuthContext';
import ProtectedRoute, { PublicOnlyRoute } from './routes/ProtectedRoute';
import Navbar from './components/Navbar';
import Dashboard from './pages/Dashboard';
import DisputeList from './pages/DisputeList';
import InvestigationDetail from './pages/InvestigationDetail';
import Login from './pages/Login';
import Register from './pages/Register';
import Team from './pages/Team';
import DomainWorkspace from './pages/DomainWorkspace';

function AppLayout() {
  return (
    <div className="flex min-h-screen flex-col bg-canvas text-ink">
      <Navbar />

      <main className="flex-1">
        <Outlet />
      </main>

      <footer className="border-t border-line">
        <div className="mx-auto flex max-w-7xl flex-wrap items-center justify-between gap-2 px-4 py-5 text-xs text-ink-subtle sm:px-6 lg:px-8">
          <span>DisputeIQ AI Risk Manager</span>
          <span>Powered by FastAPI &amp; Gemini</span>
        </div>
      </footer>
    </div>
  );
}

function DisputeListRoute() {
  const navigate = useNavigate();
  return <DisputeList onSelectDispute={(id) => navigate(`/disputes/${id}`)} />;
}

function InvestigationRoute() {
  const { disputeId } = useParams();
  const navigate = useNavigate();
  const location = useLocation();
  return (
    <InvestigationDetail
      disputeId={disputeId}
      onBack={() => navigate('/disputes')}
      failureModeTriggered={location.state?.refresh ?? 0}
    />
  );
}

export default function App() {
  return (
    <BrowserRouter>
      <AuthProvider>
        <Routes>
          <Route path="/login" element={<PublicOnlyRoute><Login /></PublicOnlyRoute>} />
          <Route path="/register" element={<PublicOnlyRoute><Register /></PublicOnlyRoute>} />

          <Route element={<ProtectedRoute />}>
            <Route element={<AppLayout />}>
              <Route index element={<Dashboard />} />
              <Route path="disputes" element={<DisputeListRoute />} />
              <Route path="disputes/:disputeId" element={<InvestigationRoute />} />
              <Route path="merchant-data" element={<DomainWorkspace />} />
              <Route
                path="team"
                element={<ProtectedRoute permission={PERMISSIONS.MANAGE_USERS}><Team /></ProtectedRoute>}
              />
            </Route>
          </Route>

          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </AuthProvider>
    </BrowserRouter>
  );
}
