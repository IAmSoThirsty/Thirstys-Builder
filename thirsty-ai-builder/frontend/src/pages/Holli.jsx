import React from "react";
import { api } from "../api";

function ChatPane({ title, persona, send }) {
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState("");
  const [busy, setBusy] = useState(false);
  const [meta, setMeta] = useState(null);

  const submit = async (e) => {
    e.preventDefault();
    if (!input.trim() || busy) return;
    const userMsg = { role: "user", content: input };
    const history = [...messages, userMsg];
    setMessages(history);
    setInput("");
    setBusy(true);
    try {
      const res = await send(userMsg.content, messages);
      setMessages((m) => [...m, { role: "assistant", content: res.reply }]);
      setMeta({ model: res.model, provider: res.provider });
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="card space-y-3">
      <div>
        <h2 className="h2">{title}</h2>
        <div className="muted text-sm">{persona}</div>
      </div>
      <div className="space-y-2 max-h-96 overflow-y-auto">
        {messages.length === 0 ? (
          <div className="muted text-sm">Say something to start.</div>
        ) : (
          messages.map((m, i) => (
            <div
              key={i}
              className={`p-3 rounded-lg text-sm ${
                m.role === "user"
                  ? "bg-brand-700/40 text-brand-50"
                  : "bg-white/5"
              }`}
            >
              <div className="text-xs uppercase tracking-wider text-brand-300 mb-1">
                {m.role}
              </div>
              <div className="whitespace-pre-wrap">{m.content}</div>
            </div>
          ))
        )}
      </div>
      {meta && (
        <div className="muted text-xs">
          model: {meta.model} • provider: {meta.provider}
        </div>
      )}
      <form onSubmit={submit} className="flex gap-2">
        <input
          className="input"
          placeholder={`Message ${title}...`}
          value={input}
          onChange={(e) => setInput(e.target.value)}
        />
        <button className="btn" type="submit" disabled={busy}>
          {busy ? "..." : "Send"}
        </button>
      </form>
    </div>
  );
}

export default function Holli() {
  return (
    <div className="page space-y-4">
      <h1 className="h1">Holli</h1>
      <p className="muted">Holistic operations assistant. LLM-backed, audit-logged.</p>
      <ChatPane
        title="Holli"
        persona="Operations-focused. Suggests next-best-action, summary, decision support."
        send={(msg, hist) => api.holli(msg, hist)}
      />
    </div>
  );
}
