import React, { useState } from 'react';
import { Link, useLocation, useNavigate } from 'react-router-dom';
import { LogIn } from 'lucide-react';
import { useAuth } from '../auth/AuthContext';
import AuthLayout, { Field, FormError } from '../auth/AuthLayout';
import { apiErrorMessage } from '../api';

export default function Login() {
  const { login } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState(null);
  const [submitting, setSubmitting] = useState(false);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError(null);
    setSubmitting(true);
    try {
      await login(email, password);
      navigate(location.state?.from || '/', { replace: true });
    } catch (err) {
      setError(apiErrorMessage(err, 'Sign-in failed.'));
      setSubmitting(false);
    }
  };

  return (
    <AuthLayout
      title="Sign in to DisputeIQ"
      subtitle="Evidence intelligence for dispute investigation"
      footer={<>New merchant? <Link to="/register" className="font-medium text-accent-soft hover:underline">Register your organization</Link></>}
    >
      <form onSubmit={handleSubmit} className="space-y-4" noValidate>
        <FormError message={error} />
        <Field id="email" label="Email" type="email" autoComplete="email" required autoFocus
               value={email} onChange={(e) => setEmail(e.target.value)} />
        <Field id="password" label="Password" type="password" autoComplete="current-password" required
               value={password} onChange={(e) => setPassword(e.target.value)} />
        <button type="submit" disabled={submitting || !email || !password} className="btn btn-primary w-full">
          <LogIn className="h-4 w-4" />
          <span>{submitting ? 'Signing in…' : 'Sign in'}</span>
        </button>
      </form>
    </AuthLayout>
  );
}
