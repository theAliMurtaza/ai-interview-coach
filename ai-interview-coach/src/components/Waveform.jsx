// Waveform.jsx — the app's signature element.
//
// A row of vertical bars that stands in for "voice as signal" across
// three contexts:
//   mode="listening" / "speaking"  -> continuously animated, used while
//        the mic is live or the agent is talking
//   mode="static"                  -> bars sized by `value` (0-100),
//        used to render scores in the results screen instead of a
//        generic progress ring or donut chart
//   mode="idle"                    -> low, still bars, decorative

const BAR_COUNT_DEFAULT = 28;

export default function Waveform({
  mode = "idle",
  value = 40,
  barCount = BAR_COUNT_DEFAULT,
  color,
  height = 64,
  className = "",
}) {
  const resolvedColor =
    color || (mode === "speaking" ? "var(--amber)" : mode === "static" ? "var(--teal)" : "var(--teal)");

  const bars = Array.from({ length: barCount });

  return (
    <div
      className={`flex items-end gap-[3px] ${className}`}
      style={{ height }}
      role="img"
      aria-label={
        mode === "listening"
          ? "Listening to your answer"
          : mode === "speaking"
          ? "AI agent speaking"
          : mode === "static"
          ? `Score visualization: ${value} out of 100`
          : "Idle audio signal"
      }
    >
      {bars.map((_, i) => {
        const isAnimated = mode === "listening" || mode === "speaking";

        let barHeight;
        if (mode === "static") {
          // Bars ramp toward the middle then taper, scaled by value,
          // so it reads as a signal shape rather than a flat bar chart.
          const mid = barCount / 2;
          const distanceFromMid = Math.abs(i - mid) / mid;
          const shape = 1 - distanceFromMid * 0.7;
          barHeight = `${Math.max(8, shape * value)}%`;
        } else if (mode === "idle") {
          barHeight = `${18 + (i % 3) * 6}%`;
        } else {
          barHeight = "60%";
        }

        return (
          <div
            key={i}
            className={isAnimated ? "wave-bar" : ""}
            style={{
              width: 3,
              height: barHeight,
              minHeight: 3,
              borderRadius: 2,
              background: resolvedColor,
              opacity: mode === "idle" ? 0.35 : 0.9,
              animationDelay: isAnimated ? `${(i % 7) * 0.09}s` : undefined,
              animationDuration: isAnimated ? `${0.6 + (i % 5) * 0.12}s` : undefined,
            }}
          />
        );
      })}
    </div>
  );
}
