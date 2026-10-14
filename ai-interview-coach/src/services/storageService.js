// storageService.js
//
// Frontend-only persistence via localStorage, so the app has a working
// history/progress dashboard with zero backend. Swap this for real
// API calls to your Express + MongoDB backend without touching any
// component — see README "Connecting a backend".

const SESSIONS_KEY = "console_interview_sessions_v1";
let volatileSessions = [];

function validSession(session) {
  const score = (value) => value === null || (Number.isFinite(value) && value >= 0 && value <= 100);
  const summary = session?.summary;
  return typeof session?.id === "string" &&
    [session.roleLabel, session.typeLabel, session.difficultyLabel].every(v => typeof v === "string") &&
    Number.isFinite(Date.parse(session.completedAt)) && summary &&
    [summary.overallScore, summary.communicationScore, summary.technicalScore].every(score) &&
    Number.isFinite(summary.avgWpm) && Number.isFinite(summary.totalFillers) &&
    Array.isArray(summary.topFillers) && summary.topFillers.every(v => Array.isArray(v) && typeof v[0] === "string" && Number.isFinite(v[1])) &&
    Array.isArray(session.answers) && session.answers.length > 0 &&
    session.answers.every(a => typeof a?.question === "string" && typeof a.transcript === "string" &&
      a.evaluation && [a.evaluation.overallScore, a.evaluation.communicationScore, a.evaluation.conceptCoverage, a.evaluation.starScore].every(score) &&
      Array.isArray(a.evaluation.conceptsMissed) && a.evaluation.conceptsMissed.every(v => typeof v === "string"));
}

export function getAllSessions() {
  try {
    const raw = localStorage.getItem(SESSIONS_KEY);
    const parsed = raw ? JSON.parse(raw) : [];
    const stored = Array.isArray(parsed) ? parsed.filter(validSession) : [];
    return [...volatileSessions, ...stored.filter(s => !volatileSessions.some(v => v.id === s.id))].slice(0, 50);
  } catch {
    return volatileSessions;
  }
}

export function saveSession(session) {
  const sessions = [session, ...getAllSessions().filter(s => s.id !== session.id)].slice(0, 50);
  try {
    localStorage.setItem(SESSIONS_KEY, JSON.stringify(sessions));
    volatileSessions = [];
    return { sessions, persisted: true };
  } catch {
    volatileSessions = sessions;
    return { sessions, persisted: false };
  }
}

export function getSessionById(id) {
  return getAllSessions().find((s) => s.id === id) || null;
}

export function clearAllSessions() {
  try {
    localStorage.removeItem(SESSIONS_KEY);
    volatileSessions = [];
    return true;
  } catch {
    return false;
  }
}
