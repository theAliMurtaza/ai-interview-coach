import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { ArrowRight, Mic } from "lucide-react";
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
} from "recharts";
import { listSessions } from "../services/interviewService";
import { scoreLabel } from "../services/evaluationService";

export default function Dashboard() {
  const [sessions, setSessions] = useState([]);
  const [storageError, setStorageError] = useState("");
  const [loading, setLoading] = useState(true);
  const [more, setMore] = useState(false);
  const [loadingMore, setLoadingMore] = useState(false);
  const [retry, setRetry] = useState(0);

  useEffect(() => {
    let active = true;
    setLoading(true); setStorageError("");
    listSessions().then(rows => { if (active) { setSessions(rows); setMore(rows.length === 20); } })
      .catch(err => { if (active) setStorageError(err.message); })
      .finally(() => { if (active) setLoading(false); });
    return () => { active = false; };
  }, [retry]);

  async function loadMore() {
    if (loadingMore) return;
    setLoadingMore(true); setStorageError("");
    try {
      const rows = await listSessions(sessions.length);
      setSessions(previous => [...previous, ...rows.filter(row => !previous.some(item => item.id === row.id))]);
      setMore(rows.length === 20);
    } catch (err) { setStorageError(err.message); }
    finally { setLoadingMore(false); }
  }

  const chartData = [...sessions]
    .filter(s => s.status === "completed")
    .reverse()
    .map((s, i) => ({
      name: `#${i + 1}`,
      overall: s.summary.overallScore,
      communication: s.summary.communicationScore,
    }));

  if (loading) return <p role="status" className="p-8 text-center">Loading your saved interviews…</p>;
  if (storageError && !sessions.length) return <div className="p-8 text-center"><p role="alert">{storageError}</p><button onClick={() => setRetry(v => v + 1)} className="mt-4 text-[var(--teal)]">Retry connection</button></div>;

  if (sessions.length === 0) {
    return (
      <div className="mx-auto max-w-2xl px-6 py-24 text-center">
        <Mic size={28} className="mx-auto mb-4 text-[var(--text-muted)]" />
        <h1 className="text-xl font-medium">No sessions yet</h1>
        <p className="mt-2 text-[var(--text-secondary)]">
          Run your first mock interview to start building a progress trend.
        </p>
        <Link
          to="/setup"
          className="mt-6 inline-flex items-center gap-2 rounded-md bg-[var(--amber)] px-5 py-2.5 text-sm font-medium text-[#1a1305]"
        >
          Start a session <ArrowRight size={16} />
        </Link>
      </div>
    );
  }

  return (
    <div className="mx-auto max-w-4xl px-6 py-12">
      {storageError && <p role="alert" className="mb-4 text-[var(--red)]">{storageError}</p>}
      <div className="flex items-center justify-between">
        <div>
          <div className="mb-1 font-[var(--font-mono)] text-xs uppercase tracking-wider text-[var(--text-muted)]">
            Progress
          </div>
          <h1 className="text-3xl font-semibold tracking-tight">Your trend</h1>
        </div>
      </div>

      {/* Trend chart */}
      <div className="mt-8 rounded-xl border border-[var(--border)] bg-[var(--surface)] p-4">
        <div className="mb-3 text-sm text-[var(--text-secondary)]">Overall score by session</div>
        <div style={{ width: "100%", height: 220 }}>
          <ResponsiveContainer>
            <LineChart data={chartData} margin={{ top: 5, right: 10, bottom: 0, left: -20 }}>
              <CartesianGrid stroke="var(--border-soft)" strokeDasharray="3 3" />
              <XAxis dataKey="name" stroke="var(--text-muted)" fontSize={12} />
              <YAxis stroke="var(--text-muted)" fontSize={12} domain={[0, 100]} />
              <Tooltip
                contentStyle={{
                  background: "var(--surface-raised)",
                  border: "1px solid var(--border)",
                  borderRadius: 8,
                  fontSize: 12,
                }}
              />
              <Line type="monotone" dataKey="overall" stroke="var(--amber)" strokeWidth={2} dot={{ r: 3 }} />
              <Line
                type="monotone"
                dataKey="communication"
                stroke="var(--teal)"
                strokeWidth={2}
                dot={{ r: 3 }}
              />
            </LineChart>
          </ResponsiveContainer>
        </div>
        <div className="mt-2 flex gap-4 text-xs text-[var(--text-muted)]">
          <span className="flex items-center gap-1.5">
            <span className="h-2 w-2 rounded-full bg-[var(--amber)]" /> Overall
          </span>
          <span className="flex items-center gap-1.5">
            <span className="h-2 w-2 rounded-full bg-[var(--teal)]" /> Communication
          </span>
        </div>
      </div>

      {/* Session list */}
      <h2 className="mb-3 mt-10 text-lg font-medium">Session history</h2>
      <div className="space-y-2">
        {sessions.map((s) => (
          <Link
            key={s.id}
            to={s.status === "completed" ? `/results/${s.id}` : `/interview/${s.id}`}
            className="flex items-center justify-between rounded-lg border border-[var(--border)] bg-[var(--surface)] p-4 transition-colors hover:border-[var(--border-soft)]"
          >
            <div>
              <div className="text-sm font-medium">
                {s.roleLabel} · {s.typeLabel}
              </div>
              <div className="mt-0.5 text-xs text-[var(--text-muted)]">
                {s.difficultyLabel} · {new Date(s.completedAt).toLocaleString()}
              </div>
            </div>
            <div className="text-right">
              <div className="font-[var(--font-mono)] text-lg tabular-nums">
                {s.status === "completed" ? s.summary.overallScore : "Resume"}
                {s.status === "completed" && <span className="text-xs text-[var(--text-muted)]">/100</span>}
              </div>
              <div className="text-xs text-[var(--text-muted)]">{s.status === "completed" ? scoreLabel(s.summary.overallScore) : "In progress"}</div>
            </div>
          </Link>
        ))}
      </div>
      {more && <button disabled={loadingMore} onClick={loadMore} className="mt-6 text-[var(--teal)]">{loadingMore ? "Loading…" : "Load more interviews"}</button>}
    </div>
  );
}
