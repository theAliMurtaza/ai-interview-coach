import { useParams, Link } from "react-router-dom";
import { useEffect, useState } from "react";
import { Download, RotateCcw, LayoutDashboard, ChevronDown } from "lucide-react";
import { getSession } from "../services/interviewService";
import { generateSessionPdf } from "../services/reportService";
import ScoreBar from "../components/ScoreBar";
import { scoreLabel } from "../services/evaluationService";

export default function Results() {
  const { id } = useParams();
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [retry, setRetry] = useState(0);
  const [session, setSession] = useState(null);
  const [openIndex, setOpenIndex] = useState(0);

  useEffect(() => {
    let active = true;
    setLoading(true); setError(""); setSession(null);
    getSession(id).then(value => { if (active) setSession(value); })
      .catch(err => { if (active) setError(err.message); })
      .finally(() => { if (active) setLoading(false); });
    return () => { active = false; };
  }, [id, retry]);

  if (loading) return <p role="status" className="p-8 text-center">Loading your saved report…</p>;
  if (error) return <div className="p-8 text-center"><p role="alert">{error}</p><button onClick={() => setRetry(v => v + 1)} className="mt-4 text-[var(--teal)]">Retry connection</button></div>;
  if (session?.status !== "completed" && session) return <div className="p-8 text-center">This interview is still in progress. <Link to={`/interview/${id}`} className="text-[var(--teal)]">Resume interview</Link></div>;

  if (!session) {
    return (
      <div className="mx-auto max-w-2xl px-6 py-20 text-center text-[var(--text-secondary)]">
        Couldn't find that session.{" "}
        <Link to="/setup" className="text-[var(--teal)] underline">
          Start a new one
        </Link>
        .
      </div>
    );
  }

  const { summary } = session;

  return (
    <div className="mx-auto max-w-3xl px-6 py-12">
      <div className="mb-1 font-[var(--font-mono)] text-xs uppercase tracking-wider text-[var(--text-muted)]">
        Session report
      </div>
      <h1 className="text-3xl font-semibold tracking-tight">
        {session.roleLabel} · {session.typeLabel}
      </h1>
      <p className="mt-1 text-sm text-[var(--text-muted)]">
        {session.difficultyLabel} · {new Date(session.completedAt).toLocaleString()}
      </p>

      {/* Overall headline score */}
      <div className="mt-8 flex items-center gap-6 rounded-xl border border-[var(--border)] bg-[var(--surface)] p-6">
        <div className="font-[var(--font-mono)] text-5xl font-semibold tabular-nums text-[var(--amber)]">
          {summary.overallScore ?? "—"}
        </div>
        <div>
          <div className="text-sm font-medium">{scoreLabel(summary.overallScore)} overall</div>
          <div className="mt-1 text-sm text-[var(--text-muted)]">
            {summary.questionCount} responses, including follow-ups · avg pace {summary.avgWpm} wpm ·{" "}
            {summary.totalFillers} filler words
          </div>
        </div>
      </div>

      {/* Score breakdown */}
      <div className="mt-6 grid grid-cols-1 gap-4 sm:grid-cols-2">
        <ScoreBar label="Communication" value={summary.communicationScore} sublabel="pace + fillers" />
        <ScoreBar
          label="Technical / structure"
          value={summary.technicalScore}
          sublabel="concept coverage"
        />
      </div>

      {summary.topFillers?.length > 0 && (
        <div className="mt-4 rounded-lg border border-[var(--border)] bg-[var(--surface)] p-4">
          <div className="mb-2 text-sm font-medium">Most-used filler words</div>
          <div className="flex flex-wrap gap-2">
            {summary.topFillers.map(([word, count]) => (
              <span
                key={word}
                className="rounded-full border border-[var(--border-soft)] bg-[var(--surface-raised)] px-3 py-1 font-[var(--font-mono)] text-xs text-[var(--text-secondary)]"
              >
                "{word}" × {count}
              </span>
            ))}
          </div>
        </div>
      )}

      {/* Actions */}
      <div className="mt-6 flex flex-wrap gap-3">
        <button
          onClick={() => generateSessionPdf(session)}
          className="inline-flex items-center gap-2 rounded-md bg-[var(--amber)] px-4 py-2.5 text-sm font-medium text-[#1a1305]"
        >
          <Download size={16} /> Download PDF report
        </button>
        <Link
          to="/setup"
          className="inline-flex items-center gap-2 rounded-md border border-[var(--border)] px-4 py-2.5 text-sm text-[var(--text-secondary)] hover:text-[var(--text-primary)]"
        >
          <RotateCcw size={16} /> Practice again
        </Link>
        <Link
          to="/dashboard"
          className="inline-flex items-center gap-2 rounded-md border border-[var(--border)] px-4 py-2.5 text-sm text-[var(--text-secondary)] hover:text-[var(--text-primary)]"
        >
          <LayoutDashboard size={16} /> View progress
        </Link>
      </div>

      {/* Per-question breakdown */}
      <h2 className="mb-3 mt-10 text-lg font-medium">Question-by-question</h2>
      <div className="space-y-3">
        {session.answers.map((a, i) => {
          const open = openIndex === i;
          const e = a.evaluation;
          return (
            <div key={i} className="rounded-lg border border-[var(--border)] bg-[var(--surface)]">
              <button
                onClick={() => setOpenIndex(open ? -1 : i)}
                className="flex w-full items-center justify-between gap-3 p-4 text-left"
              >
                <div>
                  <div className="font-[var(--font-mono)] text-xs text-[var(--text-muted)]">
                    Q{i + 1} · Score {e.overallScore}/100
                  </div>
                  <div className="mt-0.5 text-sm font-medium">{a.question}</div>
                </div>
                <ChevronDown
                  size={18}
                  className={`shrink-0 text-[var(--text-muted)] transition-transform ${
                    open ? "rotate-180" : ""
                  }`}
                />
              </button>
              {open && (
                <div className="border-t border-[var(--border-soft)] p-4 text-sm">
                  <p className="text-[var(--text-secondary)]">
                    <span className="text-[var(--text-muted)]">Your answer: </span>
                    {a.transcript || "(no answer recorded)"}
                  </p>
                  <div className="mt-3 grid grid-cols-2 gap-3 font-[var(--font-mono)] text-xs text-[var(--text-muted)] sm:grid-cols-4">
                    <Metric label="Pace" value={`${e.wpm} wpm`} />
                    <Metric label="Fillers" value={e.fillerCount} />
                    <Metric
                      label={e.conceptCoverage !== null ? "Coverage" : "STAR structure"}
                      value={`${e.conceptCoverage !== null ? e.conceptCoverage : e.starScore}%`}
                    />
                    <Metric label="Communication" value={`${e.communicationScore}/100`} />
                  </div>
                  {e.conceptsMissed?.length > 0 && (
                    <p className="mt-3 text-xs text-[var(--amber)]">
                      Consider mentioning: {e.conceptsMissed.join(", ")}
                    </p>
                  )}
                  {e.feedback && <p className="mt-3 text-[var(--text-secondary)]">{e.feedback}</p>}
                </div>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}

function Metric({ label, value }) {
  return (
    <div className="rounded-md border border-[var(--border-soft)] bg-[var(--surface-raised)] p-2">
      <div className="text-[10px] uppercase tracking-wider">{label}</div>
      <div className="mt-0.5 text-sm text-[var(--text-primary)]">{value}</div>
    </div>
  );
}
