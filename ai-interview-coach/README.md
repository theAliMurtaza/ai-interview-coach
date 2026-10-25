# Console frontend

React 19/Vite interview practice app with seven role tracks, technical/behavioral/system-design/mixed questions, three difficulty levels, and 3–40 questions per session.

Create an account, choose voice or typed answers, receive server-generated follow-ups, view score breakdowns, download a PDF, and browse your saved interviews. Questions, answers, and scoring are handled by FastAPI. The local launcher uses deterministic grading; the deployed API can enable LLM grading. Unfinished interviews can be resumed after reloading.

## Development

Node 24.x is required.

Start the backend first with Python 3.11 using `console-backend/local_server.py`, or use the root `run-local.ps1` launcher to start both. See [local setup](../LOCAL_DEVELOPMENT.md).

```sh
npm ci
npm run dev
```

```sh
npm run lint
npm test
npm run build
npx playwright install chromium
npm run test:e2e
```

`test:e2e` serves the existing production build and starts a real isolated FastAPI/SQLite backend on port 8001. Build first and install the backend's development dependencies. Set `PLAYWRIGHT_EXECUTABLE_PATH` to use an installed browser instead of downloading Chromium. Browser tests mock speech; real microphone/voice behavior must be smoke-tested over HTTPS.

## Deploy to Vercel

Set project Root Directory to `ai-interview-coach` and Node to 24.x. Set `VITE_API_URL=https://your-api-domain/api/v1` before deploying and allow the exact Vercel origin in backend CORS. `vercel.ts` derives CSP from that API URL and supplies build/output settings, deep-link rewrites, asset caching, and security headers. Never put secret API keys in frontend environment variables. Follow [Vercel + Render Free + Neon](../DEPLOY_FREE_TIER.md) for the complete setup.

See [deployment instructions](../DEPLOYMENT.md) for Vercel, a separate backend, and optional container hosting. The Docker image includes an unprivileged Nginx server on port 8080.

## Data and browser behavior

Interview history belongs to the authenticated backend account. Login tokens are kept in tab session storage with an in-memory fallback; sign in again in another browser to access the same saved interviews. Unsubmitted drafts are kept in memory and may be lost on reload. Browser-only history from earlier versions is not automatically imported.

Loading and saving show a native progress cursor, a top activity indicator, and contextual spinners. Overlapping requests keep the indicator active until all finish; failures clear it as well. Sign-in/out, resume uploads, session creation, answer saving, report loading, and PDF generation expose their working states. Spinner animations respect the browser's reduced-motion preference.

Voice input depends on browser SpeechRecognition support and microphone permission. The browser vendor may process audio remotely. Both typed and spoken transcripts are sent to the API. Browser recognition disconnections reconnect automatically while preserving the transcript. Permission failures or repeated empty disconnections pause the microphone and offer Retry microphone; switching to typing is a user choice. Submission, changing questions, switching input, and leaving the page cancel pending restarts. Answers retain the existing 20,000-character limit. Text-to-speech depends on installed browser/OS voices.

## API connection

`src/services/apiService.js` handles requests, token rotation, and error messages. `interviewService.js` adapts server records for reports. `AuthContext.jsx` protects account pages. Local Vite proxies `/api` to port 8000 automatically. Results reload from the server, and answer retries reconcile saved state before posting again.

Session setup supports private PDF/DOCX/TXT resume uploads, saved-resume reuse, headline-based role selection, detected skill selection, and manually entered specialties. Recognized headlines automatically select the interview role and relevant skills; unclear headlines require a manual choice. Users can override suggestions. The backend tailors questions to those topics, including during adaptive difficulty changes. Local mode uses built-in topic templates; AI-enabled deployments include the selected topics in the generation prompt.

Starting an interview requires sign-in. Registration collects a full name, and the navbar shows its first letter with a profile popover; older accounts without names use their email initial. Google sign-in uses the backend's public provider configuration and verified ID-token exchange. Follow [Google setup](../GOOGLE_SIGN_IN.md) to enable it.

Job matching and billing do not yet have frontend screens.

Resume project sections are detected in offline mode as well as through the optional AI parser. Named projects are previewed during setup and alternate with role/specialty questions. Saved resumes are supported without re-uploading. Each session snapshots its project context so difficulty changes retain those projects.

Answer feedback is available under Previous answer feedback during the interview and in the saved report/PDF. AI assessments separate correct, incorrect, and missing rubric percentages, with corrections and actionable improvements. With AI disabled, keyword coverage is explicitly labeled and factual correctness is not claimed. Skipped answers count as missing, not wrong. Older reports retain their original scores and are not regraded.
