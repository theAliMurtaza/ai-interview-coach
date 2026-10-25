// Count overlapping operations so one completed request cannot clear another's cursor.
let pending = 0;
const subscribers = new Set();

export const getPendingActivity = () => pending;
export function subscribeToActivity(callback) {
  subscribers.add(callback);
  return () => subscribers.delete(callback);
}

function notify() {
  if (typeof document !== "undefined") document.documentElement.toggleAttribute("data-loading", pending > 0);
  subscribers.forEach(callback => callback());
}

export function beginActivity() {
  pending++;
  notify();
  let finished = false;
  return () => {
    if (finished) return;
    finished = true;
    pending--;
    notify();
  };
}
