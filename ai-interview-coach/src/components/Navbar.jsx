import { Link, useLocation } from "react-router-dom";
import { Mic } from "lucide-react";
import { useAuth } from "../context/AuthContext";
import { useState } from "react";
import { profileInitial, profileName } from "../services/profileService";

const LINKS = [
  { to: "/setup", label: "New session" },
  { to: "/dashboard", label: "Progress" },
];

export default function Navbar() {
  const location = useLocation();
  const { user, signOut } = useAuth();
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const [profileOpen, setProfileOpen] = useState(false);
  async function exit() {
    setBusy(true); setError("");
    try { await signOut(); setProfileOpen(false); } catch (err) { setError(err.message); }
    finally { setBusy(false); }
  }

  return (
    <header className="sticky top-0 z-40 border-b border-[var(--border)] bg-[var(--bg)]/85 backdrop-blur">
      <nav className="mx-auto flex max-w-6xl flex-wrap items-center justify-between gap-2 px-4 py-4 sm:px-6">
        <Link to="/" className="flex items-center gap-2">
          <span className="flex h-8 w-8 items-center justify-center rounded-md bg-[var(--surface-raised)] border border-[var(--border)]">
            <Mic size={16} className="text-[var(--amber)]" />
          </span>
          <span className="font-[var(--font-display)] text-lg font-semibold tracking-tight">
            Console
          </span>
        </Link>

        <div className="flex items-center gap-1">
          {LINKS.map((link) => {
            const active = location.pathname === link.to;
            return (
              <Link
                key={link.to}
                to={link.to}
                className={`rounded-md px-3 py-2 text-sm transition-colors ${
                  active
                    ? "bg-[var(--surface-raised)] text-[var(--text-primary)]"
                    : "text-[var(--text-muted)] hover:text-[var(--text-primary)]"
                }`}
              >
                {link.label}
              </Link>
            );
          })}
          {user ? <>
            <div className="relative" onBlur={event => { if (!event.currentTarget.contains(event.relatedTarget)) setProfileOpen(false); }} onKeyDown={event => { if (event.key === "Escape") setProfileOpen(false); }}>
              <button aria-label={`Profile: ${profileName(user)}`} aria-expanded={profileOpen} aria-controls="profile-details" onClick={() => setProfileOpen(value => !value)}
                className="ml-2 flex h-9 w-9 items-center justify-center rounded-full bg-[var(--teal)] font-semibold text-black" title={profileName(user)}>
                {profileInitial(user)}
              </button>
              {profileOpen && <div id="profile-details" className="absolute right-0 mt-3 w-60 rounded-lg border border-[var(--border)] bg-[var(--surface)] p-4 shadow-xl">
                <p className="break-words font-medium">{profileName(user)}</p>
                <p className="mt-1 break-all text-sm text-[var(--text-muted)]">{user.email}</p>
                <Link to="/dashboard" onClick={() => setProfileOpen(false)} className="mt-3 block text-sm text-[var(--teal)]">Your progress</Link>
              </div>}
            </div>
            <button disabled={busy} onClick={exit} className="rounded-md px-3 py-2 text-sm text-[var(--teal)]">{busy ? "Signing out…" : "Sign out"}</button>
          </>
            : <Link to="/login" className="rounded-md px-3 py-2 text-sm text-[var(--teal)]">Sign in</Link>}
        </div>
      </nav>
      {error && <p role="alert" className="px-6 pb-3 text-[var(--red)]">{error}</p>}
    </header>
  );
}
