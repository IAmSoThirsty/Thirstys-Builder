import React, { useEffect, useState } from "react";
import { api, backendUrl } from "../api";

export default function Commander() {
  const [audits, setAudits] = useState([]);
  const [running, setRunning] = useState(false);
  const [error, setError] = useState(null);
  const [target, setTarget] = useState("constitutional-builder");

  const refresh = () =>
    api.commander.list().then((r) => setAudits(r.audits)).catch((e) => setError(e.message));

  useEffect(() => { refresh(); }, []);

  const run = async () => {
    setRunning(true);
    setError(null);
    try {
      await api.commander.run(target);
      await refresh();
    } catch (e) { setError(e.message); }
    finally { setRunning(false); }
  };

  return (
    <div className="page space-y-6">
      <h1 className="h1">Commander</h1>
      <p className="muted">Run governance audits, sign PDFs, gate your work.</p>

      <div className="card space-y-3">
        <label className="block text-sm font-medium">Audit target</label>
        <input className="input" value={target} onChange={(e) => setTarget(e.target.value)} />
        <button className="btn" onClick={run} disabled={running}>
          {running ? "Running..." : "Run audit"}
        </button>
        {error && <div className="text-red-300 text-sm">{error}</div>}
      </div>

      <div className="space-y-3">
        <h2 className="h2">Past audits</h2>
        {audits.length === 0 ? (
          <div className="muted text-sm">No audits yet. Click "Run audit" above.</div>
        ) : (
          audits.map((a) => (
            <div key={a.id} className="card flex items-center justify-between gap-3">
              <div>
                <div className="font-medium">{a.title}</div>
                <div className="muted text-xs">
                  {a.created_at} • sha256: {a.sha256?.slice(0, 16)}...
                </div>
              </div>
              <a
                className="btn"
                href={api.commander.pdfUrl(a.id)}
                target="_blank"
                rel="noreferrer"
              >
                Download PDF
              </a>
            </div>
          ))
        )}
      </div>
    </div>
  );
}
