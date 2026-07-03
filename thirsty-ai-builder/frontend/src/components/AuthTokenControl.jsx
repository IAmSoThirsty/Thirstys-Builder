import React, { useEffect, useState } from "react";
import { getApiToken, setApiToken } from "../api";

export default function AuthTokenControl() {
  const [token, setToken] = useState("");
  const [editing, setEditing] = useState(false);

  useEffect(() => {
    const sync = () => setToken(getApiToken());
    sync();
    window.addEventListener("thirsty-auth-token-changed", sync);
    return () => window.removeEventListener("thirsty-auth-token-changed", sync);
  }, []);

  const save = (event) => {
    event.preventDefault();
    const value = event.currentTarget.elements.apiToken.value;
    setApiToken(value);
    setEditing(false);
  };

  if (!editing) {
    return (
      <button
        className={`auth-token-button ${token ? "is-set" : ""}`}
        type="button"
        onClick={() => setEditing(true)}
      >
        {token ? "Token set" : "Set token"}
      </button>
    );
  }

  return (
    <form className="auth-token-form" onSubmit={save}>
      <input
        className="input auth-token-input"
        name="apiToken"
        type="password"
        defaultValue={token}
        autoComplete="off"
        placeholder="CB_API_KEY"
      />
      <button className="btn auth-token-save" type="submit">Save</button>
      <button
        className="auth-token-button"
        type="button"
        onClick={() => {
          setApiToken("");
          setEditing(false);
        }}
      >
        Clear
      </button>
    </form>
  );
}
