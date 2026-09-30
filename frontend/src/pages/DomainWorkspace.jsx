import React, { useEffect, useState } from 'react';
import { AlertTriangle, CheckCircle2, CreditCard, Link2, Package, Plus, RefreshCw, ShoppingBag, UserRound } from 'lucide-react';
import {
  apiErrorMessage,
  createCustomer,
  createDomainDispute,
  createOrder,
  createTransaction,
  fetchCustomers,
  fetchDomainDisputes,
  fetchOrders,
  fetchTransactions,
} from '../api';
import { useAuth, PERMISSIONS } from '../auth/AuthContext';
import { useNavigate } from 'react-router-dom';
import StatusBadge from '../components/StatusBadge';
import { formatINR } from '../utils/format';

const TABS = [
  { key: 'customers', label: 'Customers', icon: UserRound },
  { key: 'orders', label: 'Orders', icon: ShoppingBag },
  { key: 'transactions', label: 'Transactions', icon: CreditCard },
  { key: 'disputes', label: 'Disputes', icon: AlertTriangle },
];

const EMPTY = {
  customer: { external_customer_id: '', name: '', email: '', phone: '' },
  order: { customer_id: '', external_order_id: '', order_status: 'CREATED', currency: 'INR', total_amount: '', order_created_at: '' },
  transaction: { order_id: '', external_transaction_id: '', payment_method: 'card', transaction_status: 'SUCCESS', amount: '', currency: 'INR', transaction_type: 'PAYMENT', transaction_timestamp: '' },
  dispute: { customer_id: '', order_id: '', transaction_id: '', external_dispute_id: '', dispute_type: 'PAYMENT_DISPUTE', reason: '', description: '', opened_at: '' },
};

function Field({ label, name, value, onChange, type = 'text', required = false, children }) {
  return (
    <label className="block space-y-1.5">
      <span className="field-label">{label}</span>
      {children || (
        <input className="input" name={name} type={type} value={value} onChange={onChange} required={required} />
      )}
    </label>
  );
}

function SelectField({ label, name, value, onChange, options, placeholder }) {
  return (
    <Field label={label} name={name} value={value} onChange={onChange} required>
      <select className="input" name={name} value={value} onChange={onChange} required>
        <option value="">{placeholder}</option>
        {options.map((option) => <option key={option.value} value={option.value}>{option.label}</option>)}
      </select>
    </Field>
  );
}

export default function DomainWorkspace() {
  const { can } = useAuth();
  const navigate = useNavigate();
  const canManage = can(PERMISSIONS.MANAGE_ORGANIZATION);
  const [tab, setTab] = useState('customers');
  const [customers, setCustomers] = useState([]);
  const [orders, setOrders] = useState([]);
  const [transactions, setTransactions] = useState([]);
  const [disputes, setDisputes] = useState([]);
  const [forms, setForms] = useState(EMPTY);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState(null);
  const [notice, setNotice] = useState(null);

  const load = async () => {
    setLoading(true);
    setError(null);
    try {
      const [customerRes, orderRes, transactionRes, disputeRes] = await Promise.all([
        fetchCustomers(), fetchOrders(), fetchTransactions(), fetchDomainDisputes(),
      ]);
      setCustomers(customerRes.data);
      setOrders(orderRes.data);
      setTransactions(transactionRes.data);
      setDisputes(disputeRes.data);
    } catch (err) {
      setError(apiErrorMessage(err, 'Merchant data could not be loaded.'));
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { load(); }, []);

  const updateForm = (type) => (event) => {
    const { name, value } = event.target;
    setForms((current) => ({ ...current, [type]: { ...current[type], [name]: value } }));
  };

  const submit = async (event) => {
    event.preventDefault();
    setSaving(true);
    setError(null);
    setNotice(null);
    try {
      const formKey = tab === 'customers' ? 'customer' : tab.slice(0, -1);
      const data = forms[formKey];
      if (tab === 'customers') await createCustomer(data);
      if (tab === 'orders') await createOrder({ ...data, total_amount: Number(data.total_amount) });
      if (tab === 'transactions') await createTransaction({ ...data, amount: Number(data.amount) });
      if (tab === 'disputes') await createDomainDispute(data);
      setForms((current) => ({ ...current, [tab === 'customers' ? 'customer' : tab.slice(0, -1)]: EMPTY[tab === 'customers' ? 'customer' : tab.slice(0, -1)] }));
      setNotice(`${tab[0].toUpperCase()}${tab.slice(1, -1)} created successfully.`);
      await load();
    } catch (err) {
      setError(apiErrorMessage(err, 'The record could not be created.'));
    } finally {
      setSaving(false);
    }
  };

  const currentFormKey = tab === 'customers' ? 'customer' : tab.slice(0, -1);
  const form = forms[currentFormKey];
  const onChange = updateForm(currentFormKey);
  const customerOptions = customers.map((item) => ({ value: item.id, label: `${item.name}${item.email ? ` (${item.email})` : ''}` }));
  const orderOptions = orders.map((item) => ({ value: item.id, label: `${item.external_order_id} - ${formatINR(item.total_amount)}` }));
  const transactionOptions = transactions.map((item) => ({ value: item.id, label: item.external_transaction_id }));

  return (
    <div className="mx-auto max-w-7xl space-y-6 px-4 py-8 sm:px-6 lg:px-8">
      <header className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <div className="eyebrow">Phase 2 Merchant Domain</div>
          <h1 className="mt-2 text-2xl font-semibold">Customers, orders, payments, disputes</h1>
          <p className="mt-2 text-[15px] text-ink-muted">Build the transaction chain before running the existing investigation workflow.</p>
        </div>
        <button onClick={load} className="btn btn-secondary btn-sm" disabled={loading}>
          <RefreshCw className="h-4 w-4" />
          <span>Refresh data</span>
        </button>
      </header>

      {error && <div className="panel-danger flex items-center gap-2 p-4 text-sm text-rose-300"><AlertTriangle className="h-4 w-4" />{error}</div>}
      {notice && <div className="panel-success flex items-center gap-2 p-4 text-sm text-emerald-300"><CheckCircle2 className="h-4 w-4" />{notice}</div>}

      <div className="flex flex-wrap gap-2 border-b border-line pb-3">
        {TABS.map(({ key, label, icon: Icon }) => (
          <button key={key} onClick={() => setTab(key)} className={`btn btn-sm ${tab === key ? 'bg-raised text-ink border border-line' : 'btn-ghost'}`}>
            <Icon className="h-4 w-4" />
            <span>{label}</span>
            <span className="rounded bg-surface px-1.5 py-px text-2xs text-ink-subtle">{({ customers, orders, transactions, disputes })[key].length}</span>
          </button>
        ))}
      </div>

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
        <section className="card lg:col-span-1">
          <div className="border-b border-line px-5 py-4">
            <div className="flex items-center gap-2 text-sm font-semibold"><Plus className="h-4 w-4 text-accent-soft" />Create {tab.slice(0, -1)}</div>
            {!canManage && <p className="mt-1 text-xs text-ink-muted">Only organization admins can create merchant records.</p>}
          </div>
          <form onSubmit={submit} className="card-body space-y-4">
            {tab === 'customers' && <>
              <Field label="External customer ID" name="external_customer_id" value={form.external_customer_id} onChange={onChange} />
              <Field label="Name" name="name" value={form.name} onChange={onChange} required />
              <Field label="Email" name="email" type="email" value={form.email} onChange={onChange} />
              <Field label="Phone" name="phone" value={form.phone} onChange={onChange} />
            </>}
            {tab === 'orders' && <>
              <SelectField label="Customer" name="customer_id" value={form.customer_id} onChange={onChange} options={customerOptions} placeholder="Select customer" />
              <Field label="External order ID" name="external_order_id" value={form.external_order_id} onChange={onChange} required />
              <Field label="Total amount" name="total_amount" type="number" value={form.total_amount} onChange={onChange} required />
              <Field label="Order created at" name="order_created_at" type="datetime-local" value={form.order_created_at} onChange={onChange} required />
            </>}
            {tab === 'transactions' && <>
              <SelectField label="Order" name="order_id" value={form.order_id} onChange={onChange} options={orderOptions} placeholder="Select order" />
              <Field label="External transaction ID" name="external_transaction_id" value={form.external_transaction_id} onChange={onChange} required />
              <Field label="Amount" name="amount" type="number" value={form.amount} onChange={onChange} required />
              <Field label="Payment method" name="payment_method" value={form.payment_method} onChange={onChange} required />
              <Field label="Transaction timestamp" name="transaction_timestamp" type="datetime-local" value={form.transaction_timestamp} onChange={onChange} required />
            </>}
            {tab === 'disputes' && <>
              <SelectField label="Customer" name="customer_id" value={form.customer_id} onChange={onChange} options={customerOptions} placeholder="Select customer" />
              <SelectField label="Order" name="order_id" value={form.order_id} onChange={onChange} options={orderOptions} placeholder="Select order" />
              <SelectField label="Transaction" name="transaction_id" value={form.transaction_id} onChange={onChange} options={transactionOptions} placeholder="Select transaction" />
              <Field label="External dispute ID" name="external_dispute_id" value={form.external_dispute_id} onChange={onChange} required />
              <Field label="Reason" name="reason" value={form.reason} onChange={onChange} required />
              <Field label="Opened at" name="opened_at" type="datetime-local" value={form.opened_at} onChange={onChange} required />
              <Field label="Description" name="description" value={form.description} onChange={onChange} />
            </>}
            <button className="btn btn-primary w-full" type="submit" disabled={!canManage || saving || loading}>
              <Plus className="h-4 w-4" />
              <span>{saving ? 'Creating...' : `Create ${tab.slice(0, -1)}`}</span>
            </button>
          </form>
        </section>

        <section className="card overflow-hidden lg:col-span-2">
          <div className="border-b border-line px-5 py-4">
            <div className="flex items-center gap-2 text-sm font-semibold"><Link2 className="h-4 w-4 text-accent-soft" />{tab[0].toUpperCase() + tab.slice(1)} in this organization</div>
          </div>
          {loading ? <div className="flex justify-center py-16"><div className="spinner" /></div> : <RecordList tab={tab} records={{ customers, orders, transactions, disputes }} onOpenDispute={(id) => navigate(`/disputes/${id}`)} />}
        </section>
      </div>
    </div>
  );
}

function RecordList({ tab, records, onOpenDispute }) {
  if (records[tab].length === 0) return <div className="px-5 py-16 text-center text-sm text-ink-muted">No {tab} yet.</div>;
  return <div className="divide-y divide-line">{records[tab].map((record) => {
    if (tab === 'customers') return <div key={record.id} className="px-5 py-4"><div className="font-medium">{record.name}</div><div className="mt-1 text-xs text-ink-muted">{record.email || 'No email'} {record.external_customer_id && `· ${record.external_customer_id}`}</div></div>;
    if (tab === 'orders') return <div key={record.id} className="flex items-center justify-between gap-3 px-5 py-4"><div><div className="font-mono text-sm text-accent-soft">{record.external_order_id}</div><div className="mt-1 text-xs text-ink-muted">{record.customer.name} · {formatINR(record.total_amount)}</div></div><StatusBadge status={record.order_status} /></div>;
    if (tab === 'transactions') return <div key={record.id} className="flex items-center justify-between gap-3 px-5 py-4"><div><div className="font-mono text-sm text-accent-soft">{record.external_transaction_id}</div><div className="mt-1 text-xs text-ink-muted">{record.order.external_order_id} · {formatINR(record.amount)} · {record.payment_method}</div></div><StatusBadge status={record.transaction_status} /></div>;
    return <div key={record.id} className="flex flex-wrap items-center justify-between gap-3 px-5 py-4"><div><div className="font-mono text-sm text-accent-soft">{record.external_dispute_id}</div><div className="mt-1 text-xs text-ink-muted">{record.customer.name} · {record.order.external_order_id} · {record.reason}</div></div><div className="flex items-center gap-2"><StatusBadge status={record.status} /><button onClick={() => onOpenDispute(record.legacy_dispute_id)} className="btn btn-secondary btn-sm"><span>Open dispute</span></button></div></div>;
  })}</div>;
}
