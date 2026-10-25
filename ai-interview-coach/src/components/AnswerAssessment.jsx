export default function AnswerAssessment({ evaluation }) {
  const assessment = evaluation.assessment || { method: "legacy" };
  const graded = assessment.method === "ai" || assessment.method === "unanswered";
  const coverage = assessment.coverage_percentage ?? evaluation.conceptCoverage;
  const improvements = assessment.improvements?.length ? assessment.improvements :
    [evaluation.feedback || "Explain your approach, give a concrete example, and describe the result."];
  const metrics = graded
    ? [["Correct", assessment.correct_percentage], ["Incorrect", assessment.incorrect_percentage], ["Missing", assessment.missing_percentage]]
    : [["Concepts covered", coverage], ["Missing concepts", coverage == null ? null : 100 - coverage]];
  return <section aria-label="Answer assessment" className="mt-4 rounded-lg border border-[var(--border)] p-4">
    <h3 className="font-medium">Answer assessment</h3>
    <div className="mt-3 grid grid-cols-2 gap-3 sm:grid-cols-3">
      {metrics.map(([label, value]) => <div key={label}>
        <p className="text-xs text-[var(--text-muted)]">{label}</p>
        <p className={`text-xl font-semibold ${label === "Incorrect" ? "text-[var(--red)]" : "text-[var(--teal)]"}`}>{value == null ? "Not assessed" : `${Math.round(value * 10) / 10}%`}</p>
      </div>)}
    </div>
    <p className="mt-3 text-xs text-[var(--text-muted)]">{assessment.method === "ai"
      ? "AI estimates of the answer requirements: correctly explained, incorrectly explained, or missing. Missing points are not counted as wrong."
      : assessment.method === "unanswered" ? "No answer recorded. The requirements are missing, not incorrect."
        : "Keyword coverage checks which expected concepts were mentioned. It cannot verify whether statements are right or wrong."}</p>
    {assessment.strengths?.length > 0 && <FeedbackList title="What you got right" items={assessment.strengths} />}
    {assessment.corrections?.length > 0 && <FeedbackList title="What to correct" items={assessment.corrections} />}
    <FeedbackList title="How to improve" items={improvements} />
  </section>;
}

function FeedbackList({ title, items }) {
  return <div className="mt-4"><h4 className="text-sm font-medium">{title}</h4>
    <ul className="mt-2 list-disc space-y-1 pl-5 text-sm text-[var(--text-secondary)]">{items.map((item, index) => <li key={index}>{item}</li>)}</ul>
  </div>;
}
