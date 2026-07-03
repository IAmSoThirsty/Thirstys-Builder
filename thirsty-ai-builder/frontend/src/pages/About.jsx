import React, { useEffect, useState } from "react";
import { api } from "../api";

export default function About() {
  const [data, setData] = useState(null);
  const [error, setError] = useState(null);

  useEffect(() => {
    api.about().then(setData).catch((e) => setError(e.message));
  }, []);

  if (error) return <div className="page"><div className="card text-red-300">{error}</div></div>;
  if (!data) return <div className="page muted">Loading...</div>;

  return (
    <div className="page space-y-6">
      <h1 className="h1">About</h1>
      <div className="card space-y-2">
        <Row k="Product" v={data.product} />
        <Row k="Owner" v={data.owner_name} />
        <Row k="Email" v={data.support_email} />
        <Row k="Entity" v={data.entity_name} />
        <Row k="Entity number" v={data.entity_number} />
        <Row k="Principal office" v={data.principal_office} />
        <Row k="Registered agent" v={data.registered_agent} />
        <Row k="License" v={data.license} />
        <Row k="Deploy paths" v={data.deploy_paths?.join(", ")} />
        <Row k="Copyright" v={data.copyright} />
      </div>
      <div className="card">
        <h2 className="h2 mb-2">What you can do</h2>
        <ul className="list-disc list-inside space-y-1 text-sm muted">
          <li>Sell audits — every Commander audit exports a signed PDF with your letterhead.</li>
          <li>Gate any repo — copy the GitHub Action from rust-auditor/.github/workflows/ into any repo.</li>
          <li>Extend the App Store — add a row to SEED_TOOLS in backend/thirsty_ai_builder_backend/app_store.py.</li>
          <li>Whitelabel — swap ThirstyLogo.jsx and the palette in tailwind.config.js.</li>
        </ul>
      </div>
    </div>
  );
}

function Row({ k, v }) {
  return (
    <div className="grid grid-cols-1 md:grid-cols-3 gap-2 text-sm border-b border-white/5 last:border-0 pb-2 last:pb-0">
      <div className="muted">{k}</div>
      <div className="md:col-span-2 break-words">{v}</div>
    </div>
  );
}
