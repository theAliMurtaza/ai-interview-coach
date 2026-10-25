import { createContext, useContext, useEffect, useState } from "react";
import { Navigate, useLocation } from "react-router-dom";
import { api, authenticate, hasSession, logout } from "../services/apiService";
import { LoadingState } from "../components/Loading";

const AuthContext = createContext(null);
export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [retry, setRetry] = useState(0);
  useEffect(() => {
    let active = true;
    const expired = () => { setUser(null); setError(""); };
    window.addEventListener("console-auth-expired", expired);
    setLoading(true);
    setError("");
    (hasSession() ? api("/users/me") : Promise.resolve(null))
      .then(value => { if (active) setUser(value); })
      .catch(err => { if (active && err.status !== 401) setError(err.message); })
      .finally(() => { if (active) setLoading(false); });
    return () => { active = false; window.removeEventListener("console-auth-expired", expired); };
  }, [retry]);
  async function signIn(mode, credentials) { setUser(await authenticate(mode, credentials)); setError(""); }
  async function signOut() { await logout(); setUser(null); }
  return <AuthContext.Provider value={{ user, loading, error, retry: () => setRetry(v => v + 1), signIn, signOut }}>{children}</AuthContext.Provider>;
}
export const useAuth = () => useContext(AuthContext);
export function RequireAuth({ children }) {
  const { user, loading, error, retry } = useAuth();
  const location = useLocation();
  if (loading) return <LoadingState>Connecting to your account…</LoadingState>;
  if (error) return <div className="p-8 text-center"><p role="alert">{error}</p><button onClick={retry} className="mt-4 text-[var(--teal)]">Retry connection</button></div>;
  if (!user) return <Navigate to="/login" state={{ from: location.pathname }} replace />;
  return children;
}
