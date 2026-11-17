interface GenerationProgressProps {
  progress: number;
  message?: string;
}

const GRID = 12;

export default function GenerationProgress({
  progress,
  message = "Generating...",
}: GenerationProgressProps) {
  const pct = Math.max(0, Math.min(100, Math.round(progress)));
  const lit = Math.round((pct / 100) * GRID * GRID);

  return (
    <div className="gen-progress" aria-live="polite">
      <div className="gen-progress-card">
        <div
          className="gen-progress-grid"
          style={{ gridTemplateColumns: `repeat(${GRID}, 1fr)` }}
        >
          {Array.from({ length: GRID * GRID }, (_, index) => {
            const row = Math.floor(index / GRID);
            const col = index % GRID;
            const order = row * GRID + col;
            const active = order < lit;
            const edgeBoost =
              (row < 2 && col < 2) || (row > GRID - 3 && col > GRID - 3)
                ? 1.35
                : 1;
            return (
              <span
                key={index}
                className={`gen-progress-dot${active ? " is-on" : ""}`}
                style={{
                  animationDelay: `${(index % 9) * 0.08}s`,
                  transform: `scale(${active ? edgeBoost : 0.55})`,
                }}
              />
            );
          })}
        </div>
        <div className="gen-progress-badge">{pct}%</div>
      </div>
      <p className="gen-progress-message">{message}</p>
    </div>
  );
}
