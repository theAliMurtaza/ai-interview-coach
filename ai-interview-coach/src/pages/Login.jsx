import { useRef, useState } from "react";
import { Navigate, useLocation, useNavigate } from "react-router-dom";
import { useAuth } from "../context/AuthContext";
import GoogleSignIn from "../components/GoogleSignIn";

export default function Login() {
  const { user, signIn, loading } = useAuth();
  const location = useLocation();
  const navigate = useNavigate();
  const [mode, setMode] = useState("login");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const submitting = useRef(false);
  const destination = location.state?.from?.startsWith("/") && !location.state.from.startsWith("//") ? location.state.from : "/dashboard";
  if (loading) return <p className="p-8 text-center">Loading…</p>;
  if (user) return <Navigate to={destination} replace />;
  async function submit(event) {
    event.preventDefault();
    const data = new FormData(event.currentTarget);
    await login(mode, { email: data.get("email"), password: data.get("password"), ...(mode === "register" ? { full_name: data.get("name")?.trim() || null } : {}) });
  }
  async function login(method, credentials) {
    if (submitting.current) return;
    submitting.current = true;
    setBusy(true); setError("");
    try {
      await signIn(method, credentials);
      navigate(destination, { replace: true });
    } catch (err) { setError(err.message); }
    finally { submitting.current = false; setBusy(false); }
  }
  const inputClass = "mt-2 mb-5 w-full rounded border border-[var(--border)] bg-[var(--surface)] p-3";
  return <main className="mx-auto max-w-md px-6 py-14">
    <h1 className="mb-3 text-3xl font-semibold">{mode === "register" ? "Create your account" : "Sign in"}</h1>
    <p className="mb-6 text-[var(--text-muted)]">{destination === "/setup" ? "Sign in to start your interview and save your progress." : "Save interviews and results to your account."}</p>
    <GoogleSignIn disabled={busy} onCredential={credential => login("google", { id_token: credential })} />
    <form onSubmit={submit}>
      {mode === "register" && <label>Full name<input name="name" autoComplete="name" maxLength={255} required pattern=".*\S.*" className={inputClass} /></label>}
      <label>Email<input name="email" type="email" autoComplete="email" required className={inputClass} /></label>
      <label>Password<input name="password" type="password" autoComplete={mode === "register" ? "new-password" : "current-password"} minLength={mode === "register" ? 8 : 1} maxLength={128} required className={inputClass} /></label>
      {error && <p role="alert" className="mb-4 text-[var(--red)]">{error}</p>}
      <button disabled={busy} className="w-full rounded bg-[var(--amber)] p-3 text-black disabled:opacity-50">{busy ? "Connecting…" : mode === "register" ? "Create account" : "Sign in"}</button>
    </form>
    <button disabled={busy} onClick={() => { setMode(mode === "login" ? "register" : "login"); setError(""); }} className="mt-5 text-[var(--teal)]">{mode === "login" ? "Create an account" : "Already have an account? Sign in"}</button>
  </main>;
}
