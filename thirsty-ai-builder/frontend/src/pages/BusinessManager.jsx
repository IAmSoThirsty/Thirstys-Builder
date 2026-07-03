import React, { useEffect, useState } from "react";
import { api } from "../api";

export default function BusinessManager() {
  const [clients, setClients] = useState([]);
  const [form, setForm] = useState({ name: "", contact_email: "", notes: "" });
  const [error, setError] = useState(null);

  const refresh = () => api.business.list().then((r) => setClients(r.clients)).catch((e) => setError(e.message));
  useEffect(() => { refresh(); }, []);

  const submit = async (e) => {
    e.preventDefault();
    try {
      await api.business.create(form);
      setForm({ name: "", contact_email: "", notes: "" });
      await refresh();
    } catch (e) { setError(e.message); }
  };

  return (
    <div className="page space-y-6">
      <h1 className="h1">Business Manager</h1>
      <form onSubmit={submit} className="card space-y-3">
        <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
          <input className="input" placeholder="Name" value={form.name}
            onChange={(e) => setForm({ ...form, name: e.target.value })} required />
          <input className="input" type="email" placeholder="Contact email" value={form.contact_email}
            onChange={(e) => setForm({ ...form, contact_email: e.target.value })} required />
        </div>
        <textarea className="input" placeholder="Notes" rows={2} value={form.notes}
          onChange={(e) => setForm({ ...form, notes: e.target.value })} />
        <button className="btn" type="submit">Add client</button>
        {error && <div className="text-red-300 text-sm">{error}</div>}
      </form>
      <div className="space-y-2">
        {clients.length === 0 ? (
          <div className="muted text-sm">No clients yet.</div>
        ) : clients.map((c) => (
          <div key={c.id} className="card">
            <div className="font-medium">{c.name}</div>
            <div className="muted text-sm">{c.contact_email}</div>
            {c.notes && <div className="text-sm mt-1">{c.notes}</div>}
          </div>
        ))}
      </div>
    </div>
  );
}
