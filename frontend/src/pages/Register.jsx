import React, { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { Building2 } from 'lucide-react';
import { useAuth } from '../auth/AuthContext';
import AuthLayout, { Field, FormError } from '../auth/AuthLayout';
import { apiErrorMessage } from '../api';

export default function Register() {
  const { register } = useAuth();
  const navigate = useNavigate();
  const [form, setForm] = useState({ organization_name: '', name: '', email: '', password: '' });
  const [error, setError] = useState(null);
  const [submitting, setSubmitting] = useState(false);

  const update = (key) => (e) => setForm((f) => ({ ...f, [key]: e.target.value }));

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError(null);
    if (form.password.length < 8) {
      setError('Password must be at least 8 characters.');
      return;
    }
    setSubmitting(true);
    try {
      await register(form);
      navigate('/', { replace: true });
    } catch (err) {
      setError(apiErrorMessage(err, 'Registration failed.'));
      setSubmitting(false);
    }
  };

  const complete = Object.values(form).every((v) => v.trim());

  return (
    <AuthLayout
      title="Register your organization"
      subtitle="You'll be the administrator of your organization's workspace"
      footer={<>Already have an account? <Link to="/login" className="font-medium text-accent-soft hover:underline">Sign in</Link></>}
    >
      <form onSubmit={handleSubmit} className="space-y-4" noValidate>
        <FormError message={error} />
        <Field id="organization_name" label="Organization name" placeholder="ABC Electronics" required autoFocus
               value={form.organization_name} onChange={update('organization_name')} />
        <Field id="name" label="Your name" autoComplete="name" required
               value={form.name} onChange={update('name')} />
        <Field id="email" label="Work email" type="email" autoComplete="email" required
               value={form.email} onChange={update('email')} />
        <Field id="password" label="Password" type="password" autoComplete="new-password" required
               hint="At least 8 characters." value={form.password} onChange={update('password')} />
        <button type="submit" disabled={submitting || !complete} className="btn btn-primary w-full">
          <Building2 className="h-4 w-4" />
          <span>{submitting ? 'Creating workspace…' : 'Create organization'}</span>
        </button>
      </form>
    </AuthLayout>
  );
}
