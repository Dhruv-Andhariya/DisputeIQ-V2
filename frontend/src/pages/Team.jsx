import React, { useEffect, useState } from 'react';
import { Users, UserPlus } from 'lucide-react';
import { useAuth } from '../auth/AuthContext';
import { ROLES, ROLE_DESCRIPTIONS } from '../auth/roles';
import { apiErrorMessage, createOrganizationUser, fetchOrganizationUsers, updateOrganizationUser } from '../api';
import CardHeader from '../components/CardHeader';
import { Field, FormError } from '../auth/AuthLayout';
import { humanize } from '../utils/format';

const EMPTY = { name: '', email: '', password: '', role: 'INVESTIGATOR' };

export default function Team() {
  const { user: me, organization } = useAuth();
  const [members, setMembers] = useState([]);
  const [loading, setLoading] = useState(true);
  const [form, setForm] = useState(EMPTY);
  const [error, setError] = useState(null);
  const [notice, setNotice] = useState(null);
  const [submitting, setSubmitting] = useState(false);

  const load = () =>
    fetchOrganizationUsers()
      .then((res) => setMembers(res.data))
      .catch((err) => setError(apiErrorMessage(err)))
      .finally(() => setLoading(false));

  useEffect(() => { load(); }, []);

  const handleCreate = async (e) => {
    e.preventDefault();
    setError(null);
    setNotice(null);
    setSubmitting(true);
    try {
      const res = await createOrganizationUser(form);
      setNotice(`${res.data.email} added as ${humanize(res.data.role)}. Share the initial password with them securely.`);
      setForm(EMPTY);
      await load();
    } catch (err) {
      setError(apiErrorMessage(err, 'Could not create user.'));
    } finally {
      setSubmitting(false);
    }
  };

  const handleUpdate = async (member, patch) => {
    setError(null);
    setNotice(null);
    try {
      await updateOrganizationUser(member.id, patch);
      await load();
    } catch (err) {
      setError(apiErrorMessage(err, 'Could not update user.'));
    }
  };

  return (
    <div className="mx-auto max-w-7xl space-y-6 px-4 py-8 sm:px-6 lg:px-8">
      <header className="space-y-1">
        <div className="eyebrow">{organization.name}</div>
        <h1 className="text-2xl font-semibold">Team</h1>
        <p className="text-[15px] text-ink-muted">Users and roles in your organization.</p>
      </header>

      <FormError message={error} />
      {notice && <div className="panel-success p-3 text-[13px] text-emerald-300">{notice}</div>}

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
        <section className="card overflow-hidden lg:col-span-2">
          <CardHeader icon={Users} tone="blue" title="Members" action={<span className="chip tabular-nums">{members.length}</span>} />
          {loading ? (
            <div className="flex justify-center py-10"><div className="spinner" /></div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-left text-sm">
                <thead>
                  <tr className="border-b border-line bg-raised/50">
                    {['Name', 'Role', 'Status', 'Last sign-in'].map((h) => (
                      <th key={h} className="eyebrow whitespace-nowrap px-5 py-3 font-medium">{h}</th>
                    ))}
                  </tr>
                </thead>
                <tbody className="divide-y divide-line">
                  {members.map((m) => {
                    const isMe = m.id === me.id;
                    return (
                      <tr key={m.id} className={m.is_active ? '' : 'opacity-60'}>
                        <td className="px-5 py-3">
                          <div className="font-medium text-ink">{m.name}{isMe && <span className="ml-2 chip">You</span>}</div>
                          <div className="text-xs text-ink-subtle">{m.email}</div>
                        </td>
                        <td className="px-5 py-3">
                          <select
                            aria-label={`Role for ${m.email}`}
                            className="input h-8 w-auto pr-8"
                            value={m.role}
                            disabled={isMe}
                            onChange={(e) => handleUpdate(m, { role: e.target.value })}
                          >
                            {ROLES.map((r) => <option key={r} value={r}>{humanize(r)}</option>)}
                          </select>
                        </td>
                        <td className="px-5 py-3">
                          <button
                            className="btn btn-ghost btn-sm -ml-3"
                            disabled={isMe}
                            onClick={() => handleUpdate(m, { is_active: !m.is_active })}
                            title={m.is_active ? 'Deactivate: revokes access immediately' : 'Reactivate'}
                          >
                            <span className={`h-1.5 w-1.5 rounded-full ${m.is_active ? 'bg-emerald-400' : 'bg-ink-subtle'}`} />
                            {m.is_active ? 'Active' : 'Deactivated'}
                          </button>
                        </td>
                        <td className="whitespace-nowrap px-5 py-3 text-xs tabular-nums text-ink-muted">
                          {m.last_login_at ? new Date(m.last_login_at).toLocaleString() : 'Never'}
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          )}
        </section>

        <section className="card">
          <CardHeader icon={UserPlus} tone="emerald" title="Add a user" subtitle="They sign in with this email and password" />
          <form onSubmit={handleCreate} className="card-body space-y-4">
            <Field id="new-name" label="Name" required value={form.name}
                   onChange={(e) => setForm({ ...form, name: e.target.value })} />
            <Field id="new-email" label="Email" type="email" required value={form.email}
                   onChange={(e) => setForm({ ...form, email: e.target.value })} />
            <Field id="new-password" label="Initial password" type="password" autoComplete="new-password" required
                   hint="At least 8 characters." value={form.password}
                   onChange={(e) => setForm({ ...form, password: e.target.value })} />
            <div>
              <label htmlFor="new-role" className="field-label">Role</label>
              <select id="new-role" className="input h-9" value={form.role}
                      onChange={(e) => setForm({ ...form, role: e.target.value })}>
                {ROLES.map((r) => <option key={r} value={r}>{humanize(r)}</option>)}
              </select>
              <p className="mt-1 text-xs text-ink-subtle">{ROLE_DESCRIPTIONS[form.role]}</p>
            </div>
            <button type="submit" className="btn btn-primary w-full"
                    disabled={submitting || !form.name || !form.email || form.password.length < 8}>
              <UserPlus className="h-4 w-4" />
              <span>{submitting ? 'Adding…' : 'Add user'}</span>
            </button>
          </form>
        </section>
      </div>
    </div>
  );
}
