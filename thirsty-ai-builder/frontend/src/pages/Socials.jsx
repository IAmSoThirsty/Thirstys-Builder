import React, { useEffect, useState } from "react";
import { api } from "../api";

const CHANNELS = ["twitter", "linkedin", "mastodon", "bluesky"];

export default function Socials() {
  const [posts, setPosts] = useState([]);
  const [channel, setChannel] = useState("twitter");
  const [text, setText] = useState("");
  const [error, setError] = useState(null);

  const refresh = () => api.socials.list().then((r) => setPosts(r.posts)).catch((e) => setError(e.message));
  useEffect(() => { refresh(); }, []);

  const submit = async (e) => {
    e.preventDefault();
    try {
      await api.socials.queue(channel, text);
      setText("");
      await refresh();
    } catch (e) { setError(e.message); }
  };

  return (
    <div className="page space-y-6">
      <h1 className="h1">Socials</h1>
      <form onSubmit={submit} className="card space-y-3">
        <div className="flex gap-2 flex-wrap">
          {CHANNELS.map((c) => (
            <button
              key={c}
              type="button"
              onClick={() => setChannel(c)}
              className={`px-3 py-1.5 rounded-full text-sm transition ${
                channel === c ? "bg-brand-700 text-white" : "bg-white/5 text-brand-200 hover:bg-white/10"
              }`}
            >{c}</button>
          ))}
        </div>
        <textarea className="input" rows={3} placeholder="Compose a post..." value={text}
          onChange={(e) => setText(e.target.value)} required />
        <button className="btn" type="submit">Queue</button>
        {error && <div className="text-red-300 text-sm">{error}</div>}
      </form>
      <div className="space-y-2">
        <h2 className="h2">Queued</h2>
        {posts.length === 0 ? <div className="muted text-sm">Empty queue.</div> :
          posts.map((p) => (
            <div key={p.id} className="card">
              <div className="text-xs uppercase tracking-wider text-brand-300">{p.channel}</div>
              <div className="text-sm whitespace-pre-wrap">{p.text}</div>
              <div className="muted text-xs mt-1">{p.queued_at}</div>
            </div>
          ))
        }
      </div>
    </div>
  );
}
