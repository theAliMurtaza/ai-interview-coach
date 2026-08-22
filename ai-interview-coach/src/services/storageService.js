// storageService.js
//
// Frontend-only persistence via localStorage, so the app has a working
// history/progress dashboard with zero backend. Swap this for real
// API calls to your Express + MongoDB backend without touching any
// component — see README "Connecting a backend".

const SESSIONS_KEY = "console_interview_sessions_v1";

export function getAllSessions() {
  try {
    const raw = localStorage.getItem(SESSIONS_KEY);
    return raw ? JSON.parse(raw) : [];
  } catch {
    return [];
  }
}

export function saveSession(session) {
  const sessions = getAllSessions();
  sessions.unshift(session);
  localStorage.setItem(SESSIONS_KEY, JSON.stringify(sessions.slice(0, 50)));
  return sessions;
}

export function getSessionById(id) {
  return getAllSessions().find((s) => s.id === id) || null;
}

export function clearAllSessions() {
  localStorage.removeItem(SESSIONS_KEY);
}
