import { Link, useLocation } from "react-router-dom";
import { Mic } from "lucide-react";

const LINKS = [
  { to: "/setup", label: "New session" },
  { to: "/dashboard", label: "Progress" },
];

export default function Navbar() {
  const location = useLocation();

  return (
    <header className="sticky top-0 z-40 border-b border-[var(--border)] bg-[var(--bg)]/85 backdrop-blur">
      <nav className="mx-auto flex max-w-6xl items-center justify-between px-6 py-4">
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
        </div>
      </nav>
    </header>
  );
}
