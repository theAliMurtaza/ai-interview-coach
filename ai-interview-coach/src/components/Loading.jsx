import { useEffect, useSyncExternalStore } from "react";
import { LoaderCircle } from "lucide-react";
import { beginActivity, getPendingActivity, subscribeToActivity } from "../services/activityService";

export function Spinner({ className = "" }) {
  return <LoaderCircle aria-hidden="true" size={16} className={`inline-block shrink-0 animate-spin align-middle ${className}`} />;
}

export function useBusyCursor(busy) {
  useEffect(() => {
    if (busy) return beginActivity();
  }, [busy]);
}

export function LoadingState({ children = "Loading…", className = "p-8 text-center" }) {
  useBusyCursor(true);
  return <p role="status" className={className}><Spinner className="mr-2" />{children}</p>;
}

export function GlobalLoadingIndicator() {
  const pending = useSyncExternalStore(subscribeToActivity, getPendingActivity, () => 0);
  if (!pending) return null;
  return <div role="progressbar" aria-label="Operation in progress" aria-valuetext="Loading"
    className="pointer-events-none fixed inset-x-0 top-0 z-50 h-1 animate-pulse bg-[var(--teal)]" />;
}
