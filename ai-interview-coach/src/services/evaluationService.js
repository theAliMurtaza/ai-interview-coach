// evaluationService.js
//
// Turns a raw transcript + timing into the multi-dimensional feedback
// described in the project brief: technical concept coverage,
// communication delivery (fillers, pace, hesitation), and STAR
// structure for behavioral answers.
//
// This runs entirely client-side with transparent heuristics so the
// app works with zero backend / API keys. A production version would
// send the transcript to an LLM for the technical-correctness score
// (see README "Swapping in a real AI backend") but would keep these
// delivery metrics as-is, since they're deterministic and cheap.

const FILLER_WORDS = [
  "um", "uh", "umm", "uhh", "like", "you know", "sort of", "kind of",
  "basically", "actually", "literally", "i mean", "so yeah", "right?",
];

const STAR_SIGNALS = {
  situation: ["when i", "at my", "during", "at the time", "there was a"],
  task: ["i needed to", "my task", "i was responsible", "the goal was"],
  action: ["i decided", "i built", "i implemented", "i created", "i led", "i wrote", "i designed"],
  result: ["as a result", "in the end", "we achieved", "this led to", "the outcome", "ended up"],
};

function countFillerWords(text) {
  const lower = ` ${text.toLowerCase()} `;
  let count = 0;
  const hits = {};
  for (const filler of FILLER_WORDS) {
    const pattern = new RegExp(`\\b${filler.replace(/[.*+?^${}()|[\]\\]/g, "\\$&")}\\b`, "g");
    const matches = lower.match(pattern);
    if (matches) {
      count += matches.length;
      hits[filler] = matches.length;
    }
  }
  return { count, hits };
}

function wordCount(text) {
  return (text.trim().match(/\S+/g) || []).length;
}

/**
 * @param {string} transcript
 * @param {number} durationSeconds - how long the user spoke for
 * @param {string[]} expectedConcepts - keywords the question is looking for
 * @returns {object} full per-answer evaluation
 */
export function evaluateAnswer(transcript, durationSeconds, expectedConcepts = []) {
  const words = wordCount(transcript);
  const minutes = Math.max(durationSeconds / 60, 1 / 60);
  const wpm = Math.round(words / minutes);

  const { count: fillerCount, hits: fillerHits } = countFillerWords(transcript);
  const fillerRatio = words > 0 ? fillerCount / words : 0;

  const lower = transcript.toLowerCase();
  const conceptsHit = expectedConcepts.filter((c) => lower.includes(c.toLowerCase()));
  const conceptCoverage = expectedConcepts.length
    ? Math.round((conceptsHit.length / expectedConcepts.length) * 100)
    : null;

  const starHits = Object.entries(STAR_SIGNALS).reduce((acc, [key, phrases]) => {
    acc[key] = phrases.some((p) => lower.includes(p));
    return acc;
  }, {});
  const starScore = Math.round(
    (Object.values(starHits).filter(Boolean).length / 4) * 100
  );

  // Pace scoring: 120-160 WPM is the comfortable "interview" band.
  let paceLabel = "Good pace";
  if (wpm < 100) paceLabel = "A little slow — you can add a bit more energy";
  else if (wpm > 180) paceLabel = "Quite fast — consider slowing down for clarity";

  // Communication score: blends filler ratio + pace band, out of 100.
  const fillerPenalty = Math.min(fillerRatio * 400, 45); // heavy filler use caps around -45
  const pacePenalty = wpm < 90 || wpm > 200 ? 15 : wpm < 100 || wpm > 180 ? 8 : 0;
  const communicationScore = Math.max(0, Math.round(100 - fillerPenalty - pacePenalty));

  const technicalScore = conceptCoverage;

  // Overall blends whichever scores are available for this question type.
  const scoresToBlend = [communicationScore, technicalScore ?? starScore].filter(
    (s) => s !== null && s !== undefined
  );
  const overallScore = Math.round(
    scoresToBlend.reduce((a, b) => a + b, 0) / scoresToBlend.length
  );

  return {
    words,
    durationSeconds,
    wpm,
    paceLabel,
    fillerCount,
    fillerRatio: Math.round(fillerRatio * 1000) / 10, // percent, 1 decimal
    fillerHits,
    conceptsHit,
    conceptsMissed: expectedConcepts.filter((c) => !conceptsHit.includes(c)),
    conceptCoverage,
    starHits,
    starScore,
    communicationScore,
    technicalScore,
    overallScore,
  };
}

/**
 * Aggregates per-question evaluations into a session-level summary,
 * used to drive the results page and the progress dashboard.
 */
export function summarizeSession(answerEvaluations) {
  if (!answerEvaluations.length) return null;

  const avg = (key) => {
    const vals = answerEvaluations
      .map((a) => a[key])
      .filter((v) => v !== null && v !== undefined);
    return vals.length ? Math.round(vals.reduce((a, b) => a + b, 0) / vals.length) : null;
  };

  const totalFillers = answerEvaluations.reduce((sum, a) => sum + a.fillerCount, 0);
  const avgWpm = avg("wpm");

  const allFillerHits = {};
  answerEvaluations.forEach((a) => {
    Object.entries(a.fillerHits).forEach(([word, n]) => {
      allFillerHits[word] = (allFillerHits[word] || 0) + n;
    });
  });
  const topFillers = Object.entries(allFillerHits)
    .sort((a, b) => b[1] - a[1])
    .slice(0, 5);

  return {
    overallScore: avg("overallScore"),
    communicationScore: avg("communicationScore"),
    technicalScore: avg("technicalScore"),
    avgWpm,
    totalFillers,
    topFillers,
    questionCount: answerEvaluations.length,
  };
}

export function scoreLabel(score) {
  if (score === null || score === undefined) return "—";
  if (score >= 85) return "Strong";
  if (score >= 70) return "Solid";
  if (score >= 50) return "Developing";
  return "Needs work";
}
