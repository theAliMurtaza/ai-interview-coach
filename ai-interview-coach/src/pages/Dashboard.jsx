import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { Trash2, ArrowRight, Mic } from "lucide-react";
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
} from "recharts";
import { getAllSessions, clearAllSessions } from "../services/storageService";
import { scoreLabel } from "../services/evaluationService";

export default function Dashboard() {
  const [sessions, setSessions] = useState([]);

  useEffect(() => {
    setSessions(getAllSessions());
  }, []);

  const chartData = [...sessions]
    .reverse()
    .map((s, i) => ({
      name: `#${i + 1}`,
      overall: s.summary.overallScore,
      communication: s.summary.communicationScore,
      fillers: s.summary.totalFillers,
    }));

  const handleClear = () => {
    if (confirm("Clear all saved interview sessions? This can't be undone.")) {
      clearAllSessions();
      setSessions([]);
    }
  };

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
      <div className="flex items-center justify-between">
        <div>
          <div className="mb-1 font-[var(--font-mono)] text-xs uppercase tracking-wider text-[var(--text-muted)]">
            Progress
          </div>
          <h1 className="text-3xl font-semibold tracking-tight">Your trend</h1>
        </div>
        <button
          onClick={handleClear}
          className="inline-flex items-center gap-1.5 text-xs text-[var(--text-muted)] hover:text-[var(--red)]"
        >
          <Trash2 size={14} /> Clear history
        </button>
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
            to={`/results/${s.id}`}
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
                {s.summary.overallScore}
                <span className="text-xs text-[var(--text-muted)]">/100</span>
              </div>
              <div className="text-xs text-[var(--text-muted)]">{scoreLabel(s.summary.overallScore)}</div>
            </div>
          </Link>
        ))}
      </div>
    </div>
  );
}
