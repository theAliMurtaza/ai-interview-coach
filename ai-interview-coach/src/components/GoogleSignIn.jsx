import { useEffect, useRef, useState } from "react";
import { api } from "../services/apiService";
import { loadGoogleIdentity } from "../services/googleService";
import { LoadingState } from "./Loading";

export default function GoogleSignIn({ onCredential, disabled }) {
  const host = useRef(null);
  const callback = useRef(onCredential);
  callback.current = onCredential;
  const [status, setStatus] = useState("loading");
  const [error, setError] = useState("");
  const [attempt, setAttempt] = useState(0);

  useEffect(() => {
    let active = true;
    const container = host.current;
    setStatus("loading"); setError("");
    (async () => {
      try {
        const providers = await api("/auth/providers");
        if (!active) return;
        if (!providers.google_client_id) { setStatus("unavailable"); return; }
        const google = await loadGoogleIdentity();
        if (!active) return;
        google.initialize({
          client_id: providers.google_client_id,
          auto_select: false,
          ux_mode: "popup",
          callback: response => { if (active && response.credential) callback.current(response.credential); },
        });
        google.renderButton(container, { type: "standard", theme: "outline", size: "large", text: "continue_with", shape: "rectangular", width: Math.min(400, container.clientWidth || 300) });
        setStatus("ready");
      } catch (err) {
        if (active) { setError(err.message); setStatus("error"); }
      }
    })();
    return () => { active = false; container.replaceChildren(); };
  }, [attempt]);

  return <div className="mb-6">
    <div ref={host} inert={disabled ? true : undefined} className={disabled ? "pointer-events-none opacity-50" : ""} />
    {status === "loading" && <LoadingState className="text-sm text-[var(--text-muted)]">Loading Google sign-in…</LoadingState>}
    {status === "unavailable" && <>
      <button disabled className="w-full rounded border border-[var(--border)] p-3 text-[var(--text-muted)]">Continue with Google</button>
      <p className="mt-2 text-sm text-[var(--text-muted)]">Google sign-in is not available yet. Use email and password below.</p>
    </>}
    {error && <><p role="alert" className="text-sm text-[var(--red)]">{error}</p><button disabled={disabled} onClick={() => setAttempt(value => value + 1)} className="mt-2 text-sm text-[var(--teal)]">Retry Google sign-in</button></>}
    <div className="mt-5 flex items-center gap-3 text-xs text-[var(--text-muted)]"><span className="h-px flex-1 bg-[var(--border)]" />or use email<span className="h-px flex-1 bg-[var(--border)]" /></div>
  </div>;
}
