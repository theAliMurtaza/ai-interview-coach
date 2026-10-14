import { Link } from "react-router-dom";
import { ArrowRight, Mic, Target, LineChart, FileDown } from "lucide-react";
import Waveform from "../components/Waveform";

const FEATURES = [
  {
    icon: Target,
    title: "Role-specific questions",
    text: "Pick your track — Frontend, Backend, Mobile, Data/AI, DevOps, QA — and a difficulty band from internship to mid-level.",
  },
  {
    icon: Mic,
    title: "You talk, it listens",
    text: "Answer out loud like a real interview. The agent follows up when an answer is shallow, instead of reading off a fixed script.",
  },
  {
    icon: LineChart,
    title: "Delivery, not just content",
    text: "Get scored on filler words, pace, and structure — the things that actually separate a nervous answer from a confident one.",
  },
  {
    icon: FileDown,
    title: "A report you keep",
    text: "Every session ends with a downloadable PDF breakdown, plus a running trend line across all your past sessions.",
  },
];

export default function Landing() {
  return (
    <div>
      {/* Hero */}
      <section className="dot-grid relative overflow-hidden border-b border-[var(--border)]">
        <div className="mx-auto grid max-w-6xl grid-cols-1 items-center gap-12 px-6 py-20 md:grid-cols-2 md:py-28">
          <div>
            <div className="mb-5 inline-flex items-center gap-2 rounded-full border border-[var(--border)] bg-[var(--surface)] px-3 py-1 text-xs text-[var(--text-muted)]">
              <span className="relative flex h-2 w-2">
                <span className="pulse-ring absolute h-2 w-2 text-[var(--red)]" />
                <span className="h-2 w-2 rounded-full bg-[var(--red)]" />
              </span>
              Practice interviews with saved results in your account
            </div>

            <h1 className="text-4xl font-semibold leading-[1.05] tracking-tight md:text-5xl">
              Say your answer out loud.
              <br />
              <span className="text-[var(--amber)]">Get told the truth about it.</span>
            </h1>

            <p className="mt-5 max-w-md text-[var(--text-secondary)]">
              Console is a spoken mock-interview coach. Pick a developer role, talk
              through real questions with a voice AI agent, and walk away with a
              scored breakdown of what you said and how you said it.
            </p>

            <div className="mt-8 flex flex-wrap items-center gap-3">
              <Link
                to="/setup"
                className="group inline-flex items-center gap-2 rounded-md bg-[var(--amber)] px-5 py-3 text-sm font-medium text-[#1a1305] transition-transform hover:translate-x-0.5"
              >
                Start a mock interview
                <ArrowRight size={16} className="transition-transform group-hover:translate-x-0.5" />
              </Link>
              <Link
                to="/dashboard"
                className="rounded-md border border-[var(--border)] px-5 py-3 text-sm text-[var(--text-secondary)] hover:text-[var(--text-primary)]"
              >
                View past sessions
              </Link>
            </div>
          </div>

          {/* Console panel visual */}
          <div className="relative rounded-xl border border-[var(--border)] bg-[var(--surface)] p-6 shadow-2xl shadow-black/40">
            <div className="mb-6 flex items-center justify-between">
              <span className="font-[var(--font-mono)] text-xs uppercase tracking-wider text-[var(--text-muted)]">
                Channel 01 · Live input
              </span>
              <span className="flex items-center gap-1.5 text-xs text-[var(--red)]">
                <span className="h-1.5 w-1.5 rounded-full bg-[var(--red)]" />
                REC
              </span>
            </div>

            <Waveform mode="listening" height={120} barCount={40} className="w-full justify-between" />

            <div className="mt-6 grid grid-cols-3 gap-3 font-[var(--font-mono)] text-xs text-[var(--text-muted)]">
              <div className="rounded-md border border-[var(--border-soft)] bg-[var(--surface-raised)] p-3">
                <div className="text-[10px] uppercase tracking-wider">Pace</div>
                <div className="mt-1 text-lg text-[var(--text-primary)]">142 wpm</div>
              </div>
              <div className="rounded-md border border-[var(--border-soft)] bg-[var(--surface-raised)] p-3">
                <div className="text-[10px] uppercase tracking-wider">Fillers</div>
                <div className="mt-1 text-lg text-[var(--text-primary)]">3</div>
              </div>
              <div className="rounded-md border border-[var(--border-soft)] bg-[var(--surface-raised)] p-3">
                <div className="text-[10px] uppercase tracking-wider">Coverage</div>
                <div className="mt-1 text-lg text-[var(--teal)]">82%</div>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* Features */}
      <section className="mx-auto max-w-6xl px-6 py-20">
        <h2 className="text-2xl font-semibold tracking-tight">
          Built to feel like an interview, not a quiz
        </h2>
        <p className="mt-2 max-w-xl text-[var(--text-secondary)]">
          Most mock-interview tools are a static question list. Console pays
          attention to how you actually answer.
        </p>

        <div className="mt-10 grid grid-cols-1 gap-5 sm:grid-cols-2">
          {FEATURES.map(({ icon: Icon, title, text }) => (
            <div
              key={title}
              className="rounded-lg border border-[var(--border)] bg-[var(--surface)] p-5 transition-colors hover:border-[var(--border-soft)]"
            >
              <Icon size={20} className="text-[var(--teal)]" />
              <h3 className="mt-3 font-medium text-[var(--text-primary)]">{title}</h3>
              <p className="mt-1.5 text-sm text-[var(--text-secondary)]">{text}</p>
            </div>
          ))}
        </div>
      </section>

      {/* CTA strip */}
      <section className="border-t border-[var(--border)] bg-[var(--surface)]">
        <div className="mx-auto flex max-w-6xl flex-col items-start justify-between gap-6 px-6 py-14 md:flex-row md:items-center">
          <div>
            <h3 className="text-xl font-semibold">Your mic is the whole interface.</h3>
            <p className="mt-1 text-sm text-[var(--text-secondary)]">
              Six questions, one voice, one honest report.
            </p>
          </div>
          <Link
            to="/setup"
            className="inline-flex items-center gap-2 rounded-md bg-[var(--teal)] px-5 py-3 text-sm font-medium text-[#06231d]"
          >
            Choose your role <ArrowRight size={16} />
          </Link>
        </div>
      </section>
    </div>
  );
}
