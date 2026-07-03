import React, { useState } from "react";
import { api } from "../api";

const VOICES = ["professional", "casual", "witty", "technical"];

export default function Marketing() {
  const [topic, setTopic] = useState("");
  const [voice, setVoice] = useState("professional");
  const [audience, setAudience] = useState("general");
  const [result, setResult] = useState(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState(null);

  const submit = async (e) => {
    e.preventDefault();
    setBusy(true);
    setError(null);
    try {
      const r = await api.marketing(topic, voice, audience);
      setResult(r);
    } catch (e) { setError(e.message); }
    finally { setBusy(false); }
  };

  return (
    <div className="page space-y-6">
      <h1 className="h1">Marketing</h1>
      <form onSubmit={submit} className="card space-y-3">
        <input className="input" placeholder="Topic" value={topic}
          onChange={(e) => setTopic(e.target.value)} required />
        <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
          <select className="input" value={voice} onChange={(e) => setVoice(e.target.value)}>
            {VOICES.map((v) => <option key={v} value={v}>{v}</option>)}
          </select>
          <input className="input" placeholder="Audience" value={audience}
            onChange={(e) => setAudience(e.target.value)} />
        </div>
        <button className="btn" type="submit" disabled={busy}>
          {busy ? "Generating..." : "Generate copy"}
        </button>
        {error && <div className="text-red-300 text-sm">{error}</div>}
      </form>
      {result && (
        <div className="card space-y-2">
          <div className="muted text-xs">
            provider: {result.provider}
          </div>
          <div className="text-sm whitespace-pre-wrap">{result.copy}</div>
        </div>
      )}
    </div>
  );
}
