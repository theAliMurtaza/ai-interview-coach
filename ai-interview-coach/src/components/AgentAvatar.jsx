// AgentAvatar.jsx
//
// A small abstract "face" for the interview agent — deliberately not a
// stock robot icon or a stock-photo headshot. It's built from the same
// signal/waveform language as the rest of the app: the mouth IS a tiny
// waveform that animates when the agent talks, so the avatar and the
// big Waveform panel read as one consistent character rather than two
// unrelated UI pieces.

const RING_COLOR = {
  speaking: "var(--amber)",
  listening: "var(--teal)",
  thinking: "var(--text-muted)",
  idle: "var(--border-soft)",
};

export default function AgentAvatar({ state = "idle", size = 84 }) {
  const ring = RING_COLOR[state] || RING_COLOR.idle;
  const isSpeaking = state === "speaking";
  const isThinking = state === "thinking";

  return (
    <div className="relative shrink-0" style={{ width: size, height: size }}>
      {state === "speaking" && (
        <span
          className="pulse-ring absolute inset-0 rounded-full"
          style={{ color: ring }}
          aria-hidden="true"
        />
      )}
      <svg
        viewBox="0 0 84 84"
        width={size}
        height={size}
        role="img"
        aria-label={
          isSpeaking
            ? "Interview agent speaking"
            : state === "listening"
            ? "Interview agent listening"
            : isThinking
            ? "Interview agent reviewing your answer"
            : "Interview agent"
        }
      >
        <circle cx="42" cy="42" r="40" fill="var(--surface-raised)" stroke={ring} strokeWidth="2" />

        {/* eyes */}
        <rect className="agent-eye" x="27" y="34" width="6" height="9" rx="3" fill="var(--text-secondary)" />
        <rect className="agent-eye" x="51" y="34" width="6" height="9" rx="3" fill="var(--text-secondary)" />

        {/* mouth */}
        {isSpeaking ? (
          <g transform="translate(29, 54)">
            {[0, 1, 2, 3, 4].map((i) => (
              <rect
                key={i}
                className="wave-bar"
                x={i * 6}
                y={0}
                width={3}
                height={10}
                rx={1.5}
                fill="var(--amber)"
                style={{
                  transformOrigin: "center",
                  animationDelay: `${i * 0.08}s`,
                  animationDuration: `${0.5 + (i % 3) * 0.1}s`,
                }}
              />
            ))}
          </g>
        ) : isThinking ? (
          <g transform="translate(30, 58)">
            {[0, 1, 2].map((i) => (
              <circle
                key={i}
                cx={i * 8}
                cy={0}
                r={2.4}
                fill="var(--text-muted)"
                className="wave-bar"
                style={{ animationDelay: `${i * 0.15}s`, animationDuration: "0.9s" }}
              />
            ))}
          </g>
        ) : state === "listening" ? (
          <circle cx="42" cy="58" r="3" fill="var(--teal)" />
        ) : (
          <rect x="32" y="57" width="20" height="2.5" rx="1.25" fill="var(--text-muted)" />
        )}
      </svg>
    </div>
  );
}
