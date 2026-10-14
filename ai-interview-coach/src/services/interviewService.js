import { api } from "./apiService";
import { ROLES, INTERVIEW_TYPES, DIFFICULTIES } from "../data/questionBank";
import { summarizeSession } from "./evaluationService";

const label = (items, value) => items.find(item => item.id === value)?.label || value;

export function toSession(interview) {
  const answers = (interview.questions || []).filter(q => q.answer?.evaluation).map(q => {
    const a = q.answer, e = a.evaluation;
    return { question: q.text, transcript: a.transcript || "(skipped)", evaluation: {
      overallScore: e.overall_score, communicationScore: e.communication_score,
      technicalScore: e.technical_score, conceptCoverage: e.technical_score,
      starScore: e.star_score, wpm: e.wpm, fillerCount: e.filler_count,
      fillerHits: e.filler_breakdown, conceptsHit: e.concepts_hit,
      conceptsMissed: e.concepts_missed, durationSeconds: a.duration_seconds,
      words: a.word_count, feedback: e.feedback,
      paceLabel: e.wpm < 100 ? "A little slow" : e.wpm > 180 ? "Quite fast" : "Good pace",
    }};
  });
  return {
    id: interview.id, status: interview.status, completedAt: interview.created_at,
    roleLabel: label(ROLES, interview.role), typeLabel: label(INTERVIEW_TYPES, interview.interview_type),
    difficultyLabel: label(DIFFICULTIES, interview.difficulty), answers,
    summary: {
      ...summarizeSession(answers.map(a => a.evaluation)),
      overallScore: interview.overall_score, communicationScore: interview.communication_score,
      technicalScore: interview.technical_score, questionCount: answers.length,
    },
  };
}

export const getInterview = id => api(`/interviews/${encodeURIComponent(id)}`);
export const getSession = async id => toSession(await getInterview(id));
export const listSessions = async (offset = 0) => (await api(`/interviews?limit=20&offset=${offset}`)).map(toSession);
export const createInterview = setup => api("/interviews", { method: "POST", body: {
  role: setup.role, interview_type: setup.type, difficulty: setup.difficulty,
  question_count: setup.questionCount,
  resume_id: setup.resumeId || null, specialties: setup.specialties ?? [],
}});
export const submitAnswer = (id, transcript, duration) => api(`/questions/${encodeURIComponent(id)}/answer`, {
  method: "POST", body: { transcript, duration_seconds: Math.min(7200, Math.max(1, duration)) },
});
export const completeInterview = id => api(`/interviews/${encodeURIComponent(id)}/complete`, { method: "POST" });
