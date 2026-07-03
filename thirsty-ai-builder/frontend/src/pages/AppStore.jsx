import React, { useEffect, useState } from "react";
import { api } from "../api";

export default function AppStore() {
  const [tools, setTools] = useState([]);
  const [installs, setInstalls] = useState([]);
  const [busy, setBusy] = useState(null);
  const [error, setError] = useState(null);

  const refresh = async () => {
    try {
      const [t, i] = await Promise.all([api.appstore.list(), api.appstore.installs()]);
      setTools(t.tools);
      setInstalls(i.installs);
    } catch (e) { setError(e.message); }
  };

  useEffect(() => { refresh(); }, []);

  const install = async (tool_id) => {
    setBusy(tool_id);
    try {
      await api.appstore.install(tool_id);
      await refresh();
    } catch (e) { setError(e.message); }
    finally { setBusy(null); }
  };

  return (
    <div className="page space-y-6">
      <h1 className="h1">App Store</h1>
      {error && <div className="card text-red-300">{error}</div>}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {tools.map((tool) => {
          const installed = installs.some((i) => i.tool_id === tool.id);
          return (
            <div key={tool.id} className="card space-y-2">
              <div className="text-xs uppercase tracking-wider text-brand-300">{tool.category}</div>
              <div className="text-lg font-semibold">{tool.name}</div>
              <div className="muted text-sm">{tool.description}</div>
              <div className="flex items-center justify-between">
                <span className="text-xs text-brand-300">v{tool.version}</span>
                <button
                  className="btn"
                  onClick={() => install(tool.id)}
                  disabled={busy === tool.id || installed}
                >
                  {installed ? "Installed" : busy === tool.id ? "..." : "Install"}
                </button>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
