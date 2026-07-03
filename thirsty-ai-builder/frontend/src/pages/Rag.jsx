import React, { useState } from "react";
import { api } from "../api";

export default function RAG() {
  const [embedText, setEmbedText] = useState("");
  const [embedSource, setEmbedSource] = useState("manual");
  const [queryText, setQueryText] = useState("");
  const [lastResult, setLastResult] = useState(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState(null);

  const embed = async (e) => {
    e.preventDefault();
    setBusy(true);
    setError(null);
    try { await api.rag.embed(embedText, embedSource); setEmbedText(""); }
    catch (e) { setError(e.message); }
    finally { setBusy(false); }
  };

  const query = async (e) => {
    e.preventDefault();
    setBusy(true);
    setError(null);
    try { const r = await api.rag.query(queryText, 3); setLastResult(r); }
    catch (e) { setError(e.message); }
    finally { setBusy(false); }
  };

  return (
    <div className="page space-y-6">
      <h1 className="h1">RAG</h1>
      <p className="muted">Embed documents, then query with cosine retrieval + LLM answer.</p>
      <form onSubmit={embed} className="card space-y-3">
        <h2 className="h2">Embed</h2>
        <input className="input" placeholder="Source label" value={embedSource}
          onChange={(e) => setEmbedSource(e.target.value)} />
        <textarea className="input" rows={3} placeholder="Text to embed" value={embedText}
          onChange={(e) => setEmbedText(e.target.value)} required />
        <button className="btn" type="submit" disabled={busy}>Embed</button>
      </form>
      <form onSubmit={query} className="card space-y-3">
        <h2 className="h2">Query</h2>
        <input className="input" placeholder="Question" value={queryText}
          onChange={(e) => setQueryText(e.target.value)} required />
        <button className="btn" type="submit" disabled={busy}>Query</button>
      </form>
      {error && <div className="card text-red-300">{error}</div>}
      {lastResult && (
        <div className="card space-y-3">
          <div className="muted text-xs">
            {lastResult.matches.length} matches • provider: {lastResult.provider}
          </div>
          <div className="text-sm whitespace-pre-wrap">{lastResult.answer}</div>
          {lastResult.matches.length > 0 && (
            <div className="space-y-1 mt-2">
              {lastResult.matches.map((m) => (
                <div key={m.id} className="text-xs text-brand-300">
                  {m.id} • source: {m.source} • score: {m.score.toFixed(4)}
                </div>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
