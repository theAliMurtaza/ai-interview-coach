# Console — AI Voice Interview Coach (Frontend)

Console is a spoken mock-interview coach. You pick a developer role, a
question type, and a difficulty band; a voice AI agent asks you real
interview questions out loud; you answer out loud; and at the end you
get a scored report on both **what you said** (technical/behavioral
coverage) and **how you said it** (pace, filler words, structure) —
plus a downloadable PDF and a trend chart across sessions.

This repository is the **frontend**. It is fully functional on its
own — it uses the browser's native speech APIs and a set of
transparent scoring heuristics, so you can run and demo it with zero
backend, zero API keys, and zero cost. A real backend (LLM-generated
questions, Whisper transcription, a natural TTS voice, resume-aware
follow-ups) can be dropped in later without changing the UI — see
[Swapping in a real AI backend](#swapping-in-a-real-ai-backend) below.

---

## 1. Why this exists (the problem it solves)

Most "practice interview" tools are really just quiz apps: a fixed
list of questions, typed answers, a generic score. That doesn't train
the actual skill people are worried about — **speaking clearly and
confidently under pressure**. Console is built around the voice
interaction itself:

- You **speak** your answers, not type them.
- The agent can **follow up** on a shallow answer instead of moving
  on, so it feels like a real interviewer, not a script.
- The report separates **content** from **delivery**, because those
  are different skills and most people already know they're weak in
  one but not the other.
- Progress is tracked **across sessions**, not just within one.

## 2. Feature list

| Feature | Status in this repo |
|---|---|
| Role selection (7 tracks: Frontend, Backend, Full-Stack, Mobile, Data/AI, DevOps, QA) | ✅ |
| Interview type (Technical / Behavioral / System Design / Mixed) | ✅ |
| Difficulty (Internship / Junior / Mid-level) | ✅ |
| Configurable question count (3–40, slider + presets) | ✅ |
| Choice of voice or typed answers, switchable mid-session | ✅ |
| Visual agent avatar (speaking / listening / thinking states) | ✅ |
| Text-to-speech agent voice (browser `SpeechSynthesis`) | ✅ |
| Speech-to-text live transcription (browser `SpeechRecognition`) | ✅ |
| Typed-answer fallback for unsupported browsers | ✅ |
| Adaptive follow-up question on a weak answer | ✅ (heuristic-triggered) |
| Filler-word detection & count | ✅ |
| Speaking pace (WPM) scoring | ✅ |
| Technical concept-coverage scoring | ✅ (keyword-based) |
| STAR-method structure detection for behavioral answers | ✅ |
| Per-question and overall session report | ✅ |
| Downloadable PDF report | ✅ (`jsPDF`, client-side) |
| Session history + progress trend chart | ✅ (`localStorage` + `recharts`) |
| LLM-generated, resume-aware, truly adaptive questions | ⛳ backend hook — see below |
| Real neural TTS voice (ElevenLabs / OpenAI) | ⛳ backend hook — see below |
| Server-side Whisper transcription | ⛳ backend hook — see below |
| Auth / multi-device sync | ⛳ not implemented |

## 3. Tech stack

- **React 19** + **Vite** — SPA, fast dev server
- **React Router** — page navigation (`/`, `/setup`, `/interview`, `/results/:id`, `/dashboard`)
- **Tailwind CSS v4** — utility styling, theme tokens defined in `src/index.css`
- **Framer Motion** — installed and ready for micro-interactions (see `package.json`)
- **Recharts** — progress trend chart on the dashboard
- **jsPDF** — client-side PDF report generation
- **lucide-react** — icon set
- **Web Speech API** (`SpeechRecognition` + `SpeechSynthesis`) — native browser STT/TTS, no API key needed

No backend, database, or API key is required to run this project as-is.

## 4. Getting started

```bash
npm install
npm run dev       # starts the dev server, usually http://localhost:5173
```

```bash
npm run build      # production build to /dist
npm run preview    # preview the production build locally
```

### Browser support note

Live voice input uses the `SpeechRecognition` Web API, which is
currently best supported in **Chrome/Chromium-based browsers**
(desktop and Android). Safari and Firefox have partial or no support.
The app detects this automatically and falls back to a typed-answer
textarea so the interview flow still works everywhere — you just lose
the live-mic experience. Text-to-speech (`SpeechSynthesis`) has wider
support but voice quality varies a lot by OS/browser.

Microphone access requires **HTTPS or `localhost`** — this is a
browser security requirement, not a bug in the app.

## 5. Project structure

```
src/
├─ App.jsx                  # router + layout shell
├─ main.jsx                 # entry point
├─ index.css                # design tokens (colors, type, motion) — see section 7
├─ context/
│  └─ InterviewContext.jsx  # holds the current role/type/difficulty setup across pages
├─ data/
│  └─ questionBank.js       # question sets per role/type/difficulty + expected concepts
├─ services/
│  ├─ speechService.js      # STT/TTS — the ONLY file that touches the Web Speech API
│  ├─ evaluationService.js  # scoring heuristics (fillers, WPM, concept coverage, STAR)
│  ├─ storageService.js     # localStorage persistence for session history
│  └─ reportService.js      # PDF report generation (jsPDF)
├─ components/
│  ├─ Waveform.jsx           # signature visual — see section 9
│  ├─ AgentAvatar.jsx         # the agent's face — see section 8
│  ├─ ScoreBar.jsx            # score metric rendered as a waveform-style bar
│  └─ Navbar.jsx
└─ pages/
   ├─ Landing.jsx            # marketing/home page
   ├─ RoleSelect.jsx         # role + type + difficulty picker ("/setup")
   ├─ Interview.jsx          # the live interview loop ("/interview")
   ├─ Results.jsx            # single-session report ("/results/:id")
   └─ Dashboard.jsx          # session history + trend chart ("/dashboard")
```

The **services layer is the seam** for backend integration. Every
service file has a docblock explaining exactly what a production
version would replace it with.

## 6. How the interview loop works

1. `RoleSelect` writes the chosen role/type/difficulty into
   `InterviewContext` and navigates to `/interview`.
2. `Interview.jsx` builds an ordered question list via
   `buildQuestionSet()` from `questionBank.js`.
3. For each question: the agent speaks it (`speechService.speak`),
   then starts listening (`speechService.startListening`), streaming
   interim transcript text to the screen in real time.
4. When the user clicks **"I'm done answering"**, the transcript and
   elapsed time are sent to `evaluationService.evaluateAnswer()`,
   which returns pace, filler count, concept coverage, and an overall
   score.
5. **Adaptive follow-up:** if the score is low and this question
   hasn't had a follow-up yet, the agent asks a clarifying follow-up
   *on the same question* instead of moving on, and the two answers
   are combined before final scoring. This is the heuristic stand-in
   for what an LLM-driven agent would do dynamically — see section 11.
6. After the last question, `evaluationService.summarizeSession()`
   aggregates all answers, the session is saved via
   `storageService.saveSession()`, and the user is routed to
   `/results/:id`.
7. `Results.jsx` renders the breakdown and can export a PDF via
   `reportService.generateSessionPdf()`.
8. `Dashboard.jsx` reads all saved sessions and charts the score trend
   over time.

## 7. Design direction

The visual language is a **late-night broadcast/recording console**,
not a generic "AI product" gradient page — because the whole product
is about turning a voice into a signal, so the UI borrows from studio
gear: meters, an on-air light, a patch-panel dot grid.

- **Color:** near-black graphite background (`#12151A`) with a warm
  amber "on-air" accent (`#E8A33D`) and a cool teal "signal" accent
  (`#48C9B0`), plus a muted red for the live-recording indicator.
- **Type:** Space Grotesk for display headings, Inter for body text,
  IBM Plex Mono for anything that reads like data — transcripts,
  scores, timestamps.
- **Structure:** question numbering (`Question 3 / 6`) is only used
  where order is real — the live interview sequence and the PDF's
  question-by-question breakdown. Everywhere else avoids decorative
  01/02/03 markers.

All tokens live as CSS variables in `src/index.css` under `:root` and
are re-exposed to Tailwind via the `@theme` block, so changing the
palette is a one-file edit.

## 8. Question count, input mode, and the agent avatar

**Question count (3–40).** `RoleSelect.jsx` exposes a slider plus preset
buttons (5/10/15/20/30/40). Under the hood, `buildQuestionSet()` in
`questionBank.js` first tries to give you a unique set; if the requested
count is larger than the unique pool for that role/type/difficulty, it
re-shuffles and appends fresh batches (never repeating the same question
twice in a row) until it reaches the target. Each returned question gets
an `instanceId` so repeats are tracked independently — a repeated
question can still trigger its own follow-up, for example.

**Voice or typed answers.** The setup page lets the user pick "Speak my
answers" or "Type my answers" up front (`setup.inputMode`), and a
"Switch to voice / Switch to typing" button in the interview screen lets
them change their mind mid-session — useful if a room gets noisy or the
mic stops cooperating. If the browser doesn't support
`SpeechRecognition` at all, typing is selected automatically and the
voice option is disabled with an explanation.

**Agent avatar.** `components/AgentAvatar.jsx` is a small SVG face —
not a stock robot icon or a photo — built from the same signal/waveform
language as the rest of the app: the mouth is a tiny animated waveform
that moves while the agent talks, a single dot while it's listening,
and three pulsing dots while it's "thinking" through your answer. It
sits next to the big Waveform panel in the interview screen so the
avatar and the signal panel read as one character instead of two
unrelated widgets.

## 9. The signature element: `Waveform`

`src/components/Waveform.jsx` is the one visual motif reused
everywhere: a row of vertical bars standing in for "voice as signal."

- `mode="listening"` / `"speaking"` — continuously animated bars,
  shown while the mic is live or the agent is talking.
- `mode="static"` — bars sized by a `value` (0–100), used to render
  **scores** in the results screen instead of a generic progress ring.
- `mode="idle"` — low, still bars, used decoratively.

Reusing one component for both "the agent is listening" and "here is
your score" ties the interaction and the results screen together
visually — the same shape that represented your voice while you were
answering comes back to represent how well you did.

## 10. Scoring methodology (current heuristics)

Everything in `evaluationService.js` is deterministic and
transparent — good for a demo/FYP because you can explain exactly why
a score is what it is:

- **Filler words** — a fixed word/phrase list (`um`, `uh`, `like`,
  `you know`, `basically`, …) counted per answer.
- **Pace (WPM)** — word count ÷ speaking duration. 120–160 WPM is
  treated as the comfortable interview band; outside ~90–200 WPM
  incurs a penalty.
- **Concept coverage** — each question carries an `expectedConcepts`
  keyword list; the score is the fraction of those concepts mentioned
  in the transcript. This is intentionally simple (keyword matching,
  not semantic understanding) so it works with **zero API calls**.
- **STAR structure** (behavioral questions) — checks for
  Situation/Task/Action/Result signal phrases in the transcript.
- **Communication score** — blends the filler ratio and pace penalty.
- **Overall score** — average of communication and technical/STAR.

This is a deliberate MVP trade-off: keyword matching can't tell a
*correct* technical answer from one that just happens to use the
right words. Section 11 below is exactly how you'd fix that.

## 11. Swapping in a real AI backend

The frontend was structured so this is additive, not a rewrite.

**1. LLM-generated & adaptive questions**
Replace `buildQuestionSet()` in `questionBank.js` with an API call to
your backend (e.g. `POST /api/questions`) that prompts an LLM with the
role/type/difficulty (and optionally a parsed resume) and returns a
question list in the same shape (`{ id, text, expectedConcepts,
followUpHint }`). No other file needs to change.

**2. Real follow-up logic**
In `Interview.jsx`, `handleDoneAnswering()` currently decides to
follow up using a score threshold. Replace that branch with a call to
`POST /api/followup` that sends the transcript + question and lets the
LLM decide whether to probe deeper and generate the actual follow-up
text — instead of the generic hint used today.

**3. Whisper for transcription**
In `speechService.js`, instead of `SpeechRecognition`, record audio
with `MediaRecorder` and stream/POST chunks to a backend endpoint that
calls the Whisper API, then push the returned text into the same
`onResult` callback shape the UI already expects.

**4. A real neural voice**
Also in `speechService.js`, replace `speak()`'s
`SpeechSynthesisUtterance` call with a fetch to your backend's
ElevenLabs/OpenAI TTS endpoint, and play the returned audio via an
`<audio>` element instead of `window.speechSynthesis`.

**5. LLM-graded technical correctness**
In `evaluationService.js`, keep the delivery metrics (fillers, WPM —
they're free and instant) but replace `conceptCoverage` with a call to
`POST /api/evaluate` that sends the transcript + question to an LLM
and returns a graded score + written feedback.

**6. Persistence**
Replace `storageService.js`'s `localStorage` calls with `fetch()`
calls to your Express + MongoDB API (`GET/POST /api/sessions`) — the
function signatures (`getAllSessions`, `saveSession`,
`getSessionById`) can stay identical so no page component needs to
change.

Suggested backend shape (not included in this repo):

```
Node.js + Express
 ├─ /api/questions      → LLM question generation
 ├─ /api/followup        → LLM follow-up decision + text
 ├─ /api/transcribe       → Whisper STT proxy
 ├─ /api/speak            → TTS proxy (returns audio)
 ├─ /api/evaluate         → LLM technical grading
 └─ /api/sessions         → MongoDB persistence (CRUD)
```

## 12. Known limitations (be upfront about these in a demo/viva)

- Concept coverage is **keyword-based**, not semantic — a correct
  answer phrased unusually can score lower than it should. This is
  the single biggest reason to add the LLM grading step in section 11.
- `SpeechRecognition` support is inconsistent across browsers (best in
  Chrome). The typed-answer fallback keeps the flow usable everywhere,
  but the "voice-first" experience is Chrome-first for now.
- There's no "silence detection" auto-stop — the user manually clicks
  "I'm done answering." This was a deliberate reliability trade-off:
  auto-stop-on-silence is flaky across browsers and would risk cutting
  people off mid-answer.
- All data is local to the browser (`localStorage`); there's no
  account system or cross-device sync yet.
- Session history is capped at the 50 most recent sessions.

## 13. Suggested next steps for the full project

1. Build the Node/Express backend described in section 11.
2. Add auth (even a simple email/password with JWT) so sessions sync
   across devices — this also unlocks a real "growth over time" story
   for a portfolio demo.
3. Add resume upload + parsing so questions can reference the user's
   actual listed projects.
4. Add a lightweight admin/question-bank editor so the question set
   can grow without a code change.
5. Record a short demo video walking through one full interview +
   the resulting PDF — this is usually the single most convincing
   artifact for a portfolio or FYP defense.

---

Built as a frontend-first foundation for a full-stack AI interview
coach project. See section 11 before assuming any AI call in this
version is calling an external API — by default, everything runs
locally in the browser.
