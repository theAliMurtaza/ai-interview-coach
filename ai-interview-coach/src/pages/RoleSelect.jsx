import { useNavigate } from "react-router-dom";
import { useState } from "react";
import { ArrowRight, Code2, Server, Layers, Smartphone, BrainCircuit, Wrench, Bug, Mic, Keyboard } from "lucide-react";
import {
  ROLES,
  INTERVIEW_TYPES,
  DIFFICULTIES,
  MIN_QUESTIONS,
  MAX_QUESTIONS,
  DEFAULT_QUESTIONS,
} from "../data/questionBank";
import { useInterview } from "../context/InterviewContext";
import { isSpeechRecognitionSupported } from "../services/speechService";

const COUNT_PRESETS = [5, 10, 15, 20, 30, 40];

const ROLE_ICONS = {
  frontend: Code2,
  backend: Server,
  fullstack: Layers,
  mobile: Smartphone,
  "data-ai": BrainCircuit,
  devops: Wrench,
  qa: Bug,
};

export default function RoleSelect() {
  const navigate = useNavigate();
  const { setup, updateSetup } = useInterview();
  const [role, setRole] = useState(setup.role);
  const [type, setType] = useState(setup.type);
  const [difficulty, setDifficulty] = useState(setup.difficulty);
  const [questionCount, setQuestionCount] = useState(setup.questionCount ?? DEFAULT_QUESTIONS);
  const [inputMode, setInputMode] = useState(setup.inputMode ?? "voice");

  const voiceSupported = isSpeechRecognitionSupported();
  const canStart = Boolean(role);

  const handleStart = () => {
    const roleLabel = ROLES.find((r) => r.id === role)?.label ?? "";
    const typeLabel = INTERVIEW_TYPES.find((t) => t.id === type)?.label ?? "";
    const difficultyLabel = DIFFICULTIES.find((d) => d.id === difficulty)?.label ?? "";
    updateSetup({
      role,
      roleLabel,
      type,
      typeLabel,
      difficulty,
      difficultyLabel,
      questionCount,
      inputMode: voiceSupported ? inputMode : "text",
    });
    navigate("/interview");
  };

  return (
    <div className="mx-auto max-w-4xl px-6 py-14">
      <div className="mb-2 font-[var(--font-mono)] text-xs uppercase tracking-wider text-[var(--text-muted)]">
        Session setup
      </div>
      <h1 className="text-3xl font-semibold tracking-tight">Set your channel</h1>
      <p className="mt-2 max-w-lg text-[var(--text-secondary)]">
        Pick the role you're prepping for, the interview style, and how tough it
        should be. You can change this every session.
      </p>

      {/* Role grid */}
      <div className="mt-10">
        <h2 className="mb-3 text-sm font-medium text-[var(--text-secondary)]">Role</h2>
        <div className="grid grid-cols-2 gap-3 sm:grid-cols-3">
          {ROLES.map((r) => {
            const Icon = ROLE_ICONS[r.id] ?? Code2;
            const active = role === r.id;
            return (
              <button
                key={r.id}
                onClick={() => setRole(r.id)}
                aria-pressed={active}
                className={`flex flex-col items-start gap-2 rounded-lg border p-4 text-left transition-colors ${
                  active
                    ? "border-[var(--teal)] bg-[var(--teal-dim)]/30"
                    : "border-[var(--border)] bg-[var(--surface)] hover:border-[var(--border-soft)]"
                }`}
              >
                <Icon size={18} className={active ? "text-[var(--teal)]" : "text-[var(--text-muted)]"} />
                <span className="text-sm font-medium">{r.label}</span>
              </button>
            );
          })}
        </div>
      </div>

      {/* Interview type */}
      <div className="mt-8">
        <h2 className="mb-3 text-sm font-medium text-[var(--text-secondary)]">Interview type</h2>
        <div className="flex flex-wrap gap-2">
          {INTERVIEW_TYPES.map((t) => (
            <button
              key={t.id}
              onClick={() => setType(t.id)}
              aria-pressed={type === t.id}
              className={`rounded-full border px-4 py-2 text-sm transition-colors ${
                type === t.id
                  ? "border-[var(--amber)] bg-[var(--amber-dim)]/30 text-[var(--text-primary)]"
                  : "border-[var(--border)] text-[var(--text-secondary)] hover:border-[var(--border-soft)]"
              }`}
            >
              {t.label}
            </button>
          ))}
        </div>
      </div>

      {/* Difficulty */}
      <div className="mt-8">
        <h2 className="mb-3 text-sm font-medium text-[var(--text-secondary)]">Difficulty</h2>
        <div className="flex flex-wrap gap-2">
          {DIFFICULTIES.map((d) => (
            <button
              key={d.id}
              onClick={() => setDifficulty(d.id)}
              aria-pressed={difficulty === d.id}
              className={`rounded-full border px-4 py-2 text-sm transition-colors ${
                difficulty === d.id
                  ? "border-[var(--teal)] bg-[var(--teal-dim)]/30 text-[var(--text-primary)]"
                  : "border-[var(--border)] text-[var(--text-secondary)] hover:border-[var(--border-soft)]"
              }`}
            >
              {d.label}
            </button>
          ))}
        </div>
      </div>

      {/* Number of questions */}
      <div className="mt-8">
        <div className="mb-3 flex items-baseline justify-between">
          <h2 className="text-sm font-medium text-[var(--text-secondary)]">Number of questions</h2>
          <span className="font-[var(--font-mono)] text-sm tabular-nums text-[var(--text-primary)]">
            {questionCount}
          </span>
        </div>
        <input
          type="range"
          min={MIN_QUESTIONS}
          max={MAX_QUESTIONS}
          value={questionCount}
          onChange={(e) => setQuestionCount(Number(e.target.value))}
          className="w-full accent-[var(--amber)]"
          aria-label="Number of questions"
        />
        <div className="mt-3 flex flex-wrap gap-2">
          {COUNT_PRESETS.map((n) => (
            <button
              key={n}
              onClick={() => setQuestionCount(n)}
              aria-pressed={questionCount === n}
              className={`rounded-full border px-3 py-1 text-xs transition-colors ${
                questionCount === n
                  ? "border-[var(--amber)] bg-[var(--amber-dim)]/30 text-[var(--text-primary)]"
                  : "border-[var(--border)] text-[var(--text-muted)] hover:border-[var(--border-soft)]"
              }`}
            >
              {n}
            </button>
          ))}
        </div>
        {questionCount > 15 && (
          <p className="mt-2 text-xs text-[var(--text-muted)]">
            Longer sessions reuse questions from a wider pool once the unique set runs
            out — good for repetition practice.
          </p>
        )}
      </div>

      {/* Answer input mode */}
      <div className="mt-8">
        <h2 className="mb-3 text-sm font-medium text-[var(--text-secondary)]">How do you want to answer?</h2>
        <div className="flex flex-wrap gap-2">
          <button
            onClick={() => setInputMode("voice")}
            disabled={!voiceSupported}
            aria-pressed={inputMode === "voice"}
            className={`inline-flex items-center gap-2 rounded-full border px-4 py-2 text-sm transition-colors disabled:cursor-not-allowed disabled:opacity-40 ${
              inputMode === "voice"
                ? "border-[var(--teal)] bg-[var(--teal-dim)]/30 text-[var(--text-primary)]"
                : "border-[var(--border)] text-[var(--text-secondary)] hover:border-[var(--border-soft)]"
            }`}
          >
            <Mic size={15} /> Speak my answers
          </button>
          <button
            onClick={() => setInputMode("text")}
            aria-pressed={inputMode === "text"}
            className={`inline-flex items-center gap-2 rounded-full border px-4 py-2 text-sm transition-colors ${
              inputMode === "text"
                ? "border-[var(--teal)] bg-[var(--teal-dim)]/30 text-[var(--text-primary)]"
                : "border-[var(--border)] text-[var(--text-secondary)] hover:border-[var(--border-soft)]"
            }`}
          >
            <Keyboard size={15} /> Type my answers
          </button>
        </div>
        {!voiceSupported && (
          <p className="mt-2 text-xs text-[var(--text-muted)]">
            Voice input isn't supported in this browser — typing is used automatically.
            Try Chrome for the full voice experience.
          </p>
        )}
        {voiceSupported && (
          <p className="mt-2 text-xs text-[var(--text-muted)]">
            You can switch between speaking and typing mid-session too.
          </p>
        )}
      </div>

      <button
        onClick={handleStart}
        disabled={!canStart}
        className="mt-12 inline-flex items-center gap-2 rounded-md bg-[var(--amber)] px-6 py-3 text-sm font-medium text-[#1a1305] transition-opacity disabled:cursor-not-allowed disabled:opacity-40"
      >
        Begin interview <ArrowRight size={16} />
      </button>
      {!canStart && (
        <p className="mt-2 text-xs text-[var(--text-muted)]">Pick a role to continue.</p>
      )}
    </div>
  );
}
