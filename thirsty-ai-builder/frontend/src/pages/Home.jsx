import React, { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api } from "../api";

export default function Home() {
  const [home, setHome] = useState(null);
  const [health, setHealth] = useState(null);
  const [error, setError] = useState(null);

  useEffect(() => {
    Promise.all([api.home(), api.health()])
      .then(([h, hl]) => { setHome(h); setHealth(hl); })
      .catch((e) => setError(e.message));
  }, []);

  return (
    <div className="page space-y-8">
      <header className="space-y-3">
        <h1 className="h1">ThirstyAi Builder</h1>
        <p className="muted text-lg max-w-2xl">
          {home?.tagline ?? "Loading..."}
        </p>
      </header>
      {error && <div className="card border-red-500/40 text-red-300">Backend error: {error}</div>}
      <section className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
        {(home?.pages ?? []).map((p) => (
          <Link
            key={p}
            to={"/" + p.toLowerCase().replace(/[^a-z]+/g, "").replace("home", "")}
            className="card hover:bg-white/[0.06] transition"
          >
            <div className="text-xs uppercase tracking-wider text-brand-300">page</div>
            <div className="text-lg font-semibold mt-1">{p}</div>
          </Link>
        ))}
      </section>
      <section className="card">
        <div className="text-xs uppercase tracking-wider text-brand-300 mb-1">System status</div>
        <div className="text-2xl font-semibold">{health?.status ?? "..."}</div>
        <div className="muted text-sm mt-1">
          LLM provider: {health?.llm_provider ?? "..."} • v{health?.version ?? "?"}
        </div>
      </section>
    </div>
  );
}
