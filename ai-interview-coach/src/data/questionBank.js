// Question bank: role -> type -> difficulty -> question list.
// Each question carries `expectedConcepts` — keywords/phrases the
// evaluation service uses to gauge technical coverage in the answer.
// This is the piece a real backend would replace with LLM-generated,
// resume-aware, adaptive questions (see README "Swapping in a real AI backend").

export const ROLES = [
  { id: "frontend", label: "Frontend Developer" },
  { id: "backend", label: "Backend Developer" },
  { id: "fullstack", label: "Full-Stack Developer" },
  { id: "mobile", label: "Mobile App Developer" },
  { id: "data-ai", label: "Data / AI Engineer" },
  { id: "devops", label: "DevOps Engineer" },
  { id: "qa", label: "QA Engineer" },
];

export const INTERVIEW_TYPES = [
  { id: "technical", label: "Technical" },
  { id: "behavioral", label: "Behavioral (HR)" },
  { id: "system-design", label: "System Design" },
  { id: "mixed", label: "Mixed" },
];

export const DIFFICULTIES = [
  { id: "internship", label: "Internship" },
  { id: "junior", label: "Junior" },
  { id: "mid", label: "Mid-level" },
];

const behavioral = [
  {
    id: "b1",
    text: "Tell me about a time you disagreed with a teammate on a technical decision. What happened?",
    expectedConcepts: ["disagreement", "communication", "compromise", "outcome", "team"],
    followUpHint: "Ask what the final outcome was and what they'd do differently.",
  },
  {
    id: "b2",
    text: "Describe a project you're proud of. What was your specific contribution?",
    expectedConcepts: ["project", "role", "contribution", "result", "impact"],
    followUpHint: "Ask them to quantify the impact or result.",
  },
  {
    id: "b3",
    text: "Tell me about a time you missed a deadline. What did you learn?",
    expectedConcepts: ["deadline", "cause", "learning", "process change"],
    followUpHint: "Ask what they changed afterward to prevent it happening again.",
  },
  {
    id: "b4",
    text: "How do you prioritize tasks when everything feels urgent?",
    expectedConcepts: ["prioritize", "urgency", "impact", "communication", "stakeholder"],
    followUpHint: "Ask for a concrete example, not just a framework.",
  },
  {
    id: "b5",
    text: "Tell me about a time you had to learn a new technology quickly to finish a task.",
    expectedConcepts: ["learning", "deadline", "resourcefulness", "outcome"],
    followUpHint: "Ask how they'd approach it differently next time.",
  },
  {
    id: "b6",
    text: "Describe a situation where you received critical feedback. How did you respond?",
    expectedConcepts: ["feedback", "response", "change", "growth"],
    followUpHint: "Ask what specifically changed in their work afterward.",
  },
  {
    id: "b7",
    text: "Tell me about a time you had to work with an unclear or changing requirement.",
    expectedConcepts: ["ambiguity", "clarification", "communication", "adaptability"],
    followUpHint: "Ask how they clarified the requirement with stakeholders.",
  },
  {
    id: "b8",
    text: "Why do you want to work in this role, and what makes you a good fit?",
    expectedConcepts: ["motivation", "skills", "fit", "goal"],
    followUpHint: "Ask for a specific skill or project that supports the claim.",
  },
];

const systemDesign = [
  {
    id: "sd1",
    text: "How would you design a URL shortener that needs to handle high read traffic?",
    expectedConcepts: ["hashing", "database", "cache", "scalability", "load balancer", "read replica"],
    followUpHint: "Ask how they'd handle a hash collision or hot-key traffic.",
  },
  {
    id: "sd2",
    text: "Walk me through how you'd design the backend for a real-time chat feature.",
    expectedConcepts: ["websocket", "database", "message queue", "scalability", "delivery guarantee"],
    followUpHint: "Ask how they'd guarantee message ordering or handle offline users.",
  },
  {
    id: "sd3",
    text: "How would you design a rate limiter that multiple services can share?",
    expectedConcepts: ["token bucket", "redis", "distributed", "throttle", "window"],
    followUpHint: "Ask how they'd keep it consistent across multiple servers.",
  },
  {
    id: "sd4",
    text: "How would you design a notification system that sends emails, SMS, and push notifications?",
    expectedConcepts: ["queue", "worker", "retry", "provider", "fan-out"],
    followUpHint: "Ask how they'd handle a failed delivery or retry storm.",
  },
  {
    id: "sd5",
    text: "How would you design an image-upload service that needs to resize and store millions of photos?",
    expectedConcepts: ["object storage", "cdn", "queue", "thumbnail", "scalability"],
    followUpHint: "Ask how they'd handle a traffic spike during peak upload hours.",
  },
];

const byRole = {
  frontend: {
    technical: {
      internship: [
        {
          id: "fe-i-1",
          text: "What's the difference between let, const, and var in JavaScript?",
          expectedConcepts: ["scope", "block", "hoisting", "reassignment", "function scope"],
        },
        {
          id: "fe-i-2",
          text: "What is the virtual DOM and why does React use it?",
          expectedConcepts: ["virtual dom", "diffing", "reconciliation", "performance", "real dom"],
        },
        {
          id: "fe-i-3",
          text: "How does CSS Flexbox differ from CSS Grid, and when would you use each?",
          expectedConcepts: ["one-dimensional", "two-dimensional", "axis", "layout"],
        },
      ],
      junior: [
        {
          id: "fe-j-1",
          text: "Explain how React's useEffect dependency array works and a bug you've hit with it.",
          expectedConcepts: ["dependency array", "re-render", "cleanup", "stale closure"],
          followUpHint: "Ask about a specific bug they've personally hit.",
        },
        {
          id: "fe-j-2",
          text: "How would you optimize a React app that's re-rendering too often?",
          expectedConcepts: ["memo", "usecallback", "usememo", "key prop", "state colocation"],
        },
        {
          id: "fe-j-3",
          text: "What's the difference between server-side rendering and client-side rendering?",
          expectedConcepts: ["seo", "time to first byte", "hydration", "initial load"],
        },
      ],
      mid: [
        {
          id: "fe-m-1",
          text: "How would you architect state management in a large React application?",
          expectedConcepts: ["global state", "context", "redux", "colocation", "server state"],
          followUpHint: "Ask how they'd decide between local state, context, and a library.",
        },
        {
          id: "fe-m-2",
          text: "Walk me through how you'd debug a memory leak in a single-page application.",
          expectedConcepts: ["memory leak", "event listener", "profiler", "devtools", "unmount"],
        },
      ],
    },
    behavioral,
    "system-design": systemDesign,
  },
  backend: {
    technical: {
      internship: [
        {
          id: "be-i-1",
          text: "What's the difference between SQL and NoSQL databases?",
          expectedConcepts: ["schema", "relational", "scalability", "consistency", "joins"],
        },
        {
          id: "be-i-2",
          text: "What is REST and what makes an API RESTful?",
          expectedConcepts: ["stateless", "resource", "http verbs", "endpoint"],
        },
        {
          id: "be-i-3",
          text: "What is the difference between authentication and authorization?",
          expectedConcepts: ["identity", "permission", "token", "role"],
        },
      ],
      junior: [
        {
          id: "be-j-1",
          text: "How would you design a database schema for an e-commerce order system?",
          expectedConcepts: ["normalization", "foreign key", "orders", "inventory", "index"],
        },
        {
          id: "be-j-2",
          text: "Explain how JWT-based authentication works, end to end.",
          expectedConcepts: ["token", "signature", "expiry", "refresh token", "stateless"],
        },
        {
          id: "be-j-3",
          text: "What's an N+1 query problem and how would you fix it?",
          expectedConcepts: ["n+1", "join", "eager loading", "batching"],
        },
      ],
      mid: [
        {
          id: "be-m-1",
          text: "How would you design rate limiting for a public API?",
          expectedConcepts: ["token bucket", "sliding window", "redis", "429", "throttle"],
        },
        {
          id: "be-m-2",
          text: "Walk me through how you'd handle a database migration on a live production system with zero downtime.",
          expectedConcepts: ["backward compatible", "rollback", "migration", "downtime", "versioning"],
        },
      ],
    },
    behavioral,
    "system-design": systemDesign,
  },
  fullstack: {
    technical: {
      internship: [
        {
          id: "fs-i-1",
          text: "Walk me through what happens, end to end, when a user submits a login form on a MERN app.",
          expectedConcepts: ["request", "api", "database", "token", "response", "state update"],
        },
        {
          id: "fs-i-2",
          text: "What's the difference between client-side and server-side validation, and why do you need both?",
          expectedConcepts: ["security", "user experience", "trust", "bypass"],
        },
      ],
      junior: [
        {
          id: "fs-j-1",
          text: "How do you keep your frontend and backend data models in sync as an application evolves?",
          expectedConcepts: ["shared types", "api contract", "versioning", "validation"],
        },
        {
          id: "fs-j-2",
          text: "How would you handle file uploads in a full-stack app, from the browser to storage?",
          expectedConcepts: ["multipart", "storage", "validation", "size limit", "cdn"],
        },
      ],
      mid: [
        {
          id: "fs-m-1",
          text: "How would you structure a monorepo for a full-stack team of 5-6 engineers?",
          expectedConcepts: ["shared code", "ci/cd", "workspace", "versioning", "build pipeline"],
        },
      ],
    },
    behavioral,
    "system-design": systemDesign,
  },
  mobile: {
    technical: {
      internship: [
        {
          id: "mo-i-1",
          text: "What's the difference between native and cross-platform mobile development?",
          expectedConcepts: ["performance", "code reuse", "platform api", "flutter", "react native"],
        },
        {
          id: "mo-i-2",
          text: "How does state persist across screen rotations or app restarts on mobile?",
          expectedConcepts: ["lifecycle", "state saving", "local storage", "configuration change"],
        },
      ],
      junior: [
        {
          id: "mo-j-1",
          text: "How would you handle offline support in a mobile app?",
          expectedConcepts: ["local database", "sync", "cache", "conflict resolution"],
        },
      ],
      mid: [
        {
          id: "mo-m-1",
          text: "How would you optimize a mobile app that's draining battery in the background?",
          expectedConcepts: ["background task", "battery", "polling", "push notification"],
        },
      ],
    },
    behavioral,
    "system-design": systemDesign,
  },
  "data-ai": {
    technical: {
      internship: [
        {
          id: "ai-i-1",
          text: "What's the difference between supervised and unsupervised learning?",
          expectedConcepts: ["labeled data", "classification", "clustering", "ground truth"],
        },
        {
          id: "ai-i-2",
          text: "What is overfitting, and how would you detect it?",
          expectedConcepts: ["training accuracy", "validation accuracy", "generalization", "regularization"],
        },
      ],
      junior: [
        {
          id: "ai-j-1",
          text: "How would you evaluate whether a classification model is actually good?",
          expectedConcepts: ["precision", "recall", "f1", "confusion matrix", "class imbalance"],
        },
        {
          id: "ai-j-2",
          text: "Explain the difference between a Large Language Model and a traditional ML model at a high level.",
          expectedConcepts: ["transformer", "pretraining", "tokens", "generalization"],
        },
      ],
      mid: [
        {
          id: "ai-m-1",
          text: "How would you design a system to serve an ML model in production reliably?",
          expectedConcepts: ["latency", "versioning", "monitoring", "rollback", "a/b test"],
        },
      ],
    },
    behavioral,
    "system-design": systemDesign,
  },
  devops: {
    technical: {
      internship: [
        {
          id: "do-i-1",
          text: "What is CI/CD and why does it matter?",
          expectedConcepts: ["automation", "pipeline", "testing", "deployment"],
        },
        {
          id: "do-i-2",
          text: "What's the difference between a container and a virtual machine?",
          expectedConcepts: ["isolation", "kernel", "overhead", "image"],
        },
      ],
      junior: [
        {
          id: "do-j-1",
          text: "Walk me through a CI/CD pipeline you'd set up for a Node.js application.",
          expectedConcepts: ["build", "test", "lint", "deploy", "artifact"],
        },
      ],
      mid: [
        {
          id: "do-m-1",
          text: "How would you design a zero-downtime deployment strategy?",
          expectedConcepts: ["blue-green", "canary", "rolling update", "health check"],
        },
      ],
    },
    behavioral,
    "system-design": systemDesign,
  },
  qa: {
    technical: {
      internship: [
        {
          id: "qa-i-1",
          text: "What's the difference between manual and automated testing, and when would you use each?",
          expectedConcepts: ["repetition", "regression", "cost", "coverage"],
        },
        {
          id: "qa-i-2",
          text: "What is the difference between a bug and a defect?",
          expectedConcepts: ["requirement", "expected behavior", "severity", "priority"],
        },
      ],
      junior: [
        {
          id: "qa-j-1",
          text: "How would you design a test plan for a login feature?",
          expectedConcepts: ["edge case", "boundary", "positive test", "negative test", "security"],
        },
      ],
      mid: [
        {
          id: "qa-m-1",
          text: "How would you introduce test automation into a team that's fully manual today?",
          expectedConcepts: ["roi", "prioritization", "flaky test", "ci integration"],
        },
      ],
    },
    behavioral,
    "system-design": systemDesign,
  },
};

export const MAX_QUESTIONS = 40;
export const MIN_QUESTIONS = 3;
export const DEFAULT_QUESTIONS = 6;

/** Gathers the full candidate pool for a role/type/difficulty combo. */
function collectPool(role, type, difficulty) {
  const roleBank = byRole[role] || byRole.fullstack;

  if (type === "behavioral") return behavioral;
  if (type === "system-design") return systemDesign;

  if (type === "mixed") {
    const allTechnical = Object.values(roleBank.technical).flat();
    return [...allTechnical, ...behavioral, ...systemDesign];
  }

  // technical: prefer the chosen difficulty, extend with the role's other
  // difficulty tiers so a large practice count still has real variety
  // instead of repeating the same 2-3 questions.
  const primary = roleBank.technical[difficulty] || roleBank.technical.junior;
  const rest = Object.entries(roleBank.technical)
    .filter(([tier]) => tier !== difficulty)
    .flatMap(([, qs]) => qs);
  return [...primary, ...rest];
}

/**
 * Build an ordered question set for a session, up to MAX_QUESTIONS.
 * When the requested count exceeds the unique pool size (a small
 * question bank asked for a long 30-40 question practice run), the
 * pool is re-shuffled and appended in fresh batches so questions
 * repeat as little as possible and never back-to-back.
 */
export function buildQuestionSet({ role, type, difficulty, count = DEFAULT_QUESTIONS }) {
  const target = Math.max(MIN_QUESTIONS, Math.min(MAX_QUESTIONS, count));
  const pool = collectPool(role, type, difficulty);
  if (pool.length === 0) return [];

  let result = shuffle(pool);

  while (result.length < target) {
    let batch = shuffle(pool);
    // avoid an immediate repeat across the batch boundary
    if (batch.length > 1 && batch[0].id === result[result.length - 1].id) {
      [batch[0], batch[1]] = [batch[1], batch[0]];
    }
    result = result.concat(batch);
  }

  return result.slice(0, target).map((q, i) => ({ ...q, instanceId: `${q.id}__${i}` }));
}

function shuffle(arr) {
  const copy = [...arr];
  for (let i = copy.length - 1; i > 0; i--) {
    const j = Math.floor(Math.random() * (i + 1));
    [copy[i], copy[j]] = [copy[j], copy[i]];
  }
  return copy;
}
