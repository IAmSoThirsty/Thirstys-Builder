import React, { useEffect, useState } from "react";
import { api } from "../api";

export default function Architecture() {
  const [data, setData] = useState(null);
  const [error, setError] = useState(null);

  useEffect(() => {
    api.architecture().then(setData).catch((e) => setError(e.message));
  }, []);

  return (
    <div className="page space-y-4">
      <h1 className="h1">Architecture</h1>
      {error && <div className="card text-red-300">{error}</div>}
      {data && (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {Object.entries(data).map(([k, v]) => (
            <div key={k} className="card">
              <div className="text-xs uppercase tracking-wider text-brand-300 mb-1">{k}</div>
              <div className="text-sm">{v}</div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
