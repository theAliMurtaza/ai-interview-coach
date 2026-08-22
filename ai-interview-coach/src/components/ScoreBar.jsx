import Waveform from "./Waveform";
import { scoreLabel } from "../services/evaluationService";

export default function ScoreBar({ label, value, sublabel }) {
  const color =
    value >= 85 ? "var(--teal)" : value >= 60 ? "var(--amber)" : "var(--red)";

  return (
    <div className="rounded-lg border border-[var(--border)] bg-[var(--surface)] p-4">
      <div className="mb-2 flex items-baseline justify-between">
        <span className="text-sm text-[var(--text-secondary)]">{label}</span>
        <span className="font-[var(--font-mono)] text-lg font-medium tabular-nums">
          {value ?? "—"}
          <span className="text-xs text-[var(--text-muted)]">/100</span>
        </span>
      </div>
      <Waveform mode="static" value={value ?? 0} color={color} height={36} barCount={32} />
      <div className="mt-2 flex items-center justify-between text-xs text-[var(--text-muted)]">
        <span>{scoreLabel(value)}</span>
        {sublabel && <span>{sublabel}</span>}
      </div>
    </div>
  );
}
