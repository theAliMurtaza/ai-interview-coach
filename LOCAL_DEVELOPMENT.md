# Run the connected app locally

The frontend now uses FastAPI for registration/login, question creation, answer scoring, follow-ups, saved reports, and interview history. Browser speech recognition supplies transcripts; the backend saves and evaluates them. PDF downloads use the saved server results.

## Start both (Windows / PowerShell)

From the repository root:

```powershell
cd D:\ai-interview-coach
powershell -ExecutionPolicy Bypass -File .\run-local.ps1
```

Open **http://127.0.0.1:5173**. Choose **Sign in → Create an account**, then start an interview. API documentation is **http://127.0.0.1:8000/docs**. Keep the terminal open; Ctrl+C stops both processes. The execution-policy override applies only to this launcher process.

Your existing dependencies are installed in this workspace. On a fresh checkout, first install Node 24.x and Python 3.11, then run:

```powershell
cd D:\ai-interview-coach\console-backend
py -3.11 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
cd ..\ai-interview-coach
npm ci
```

## Two terminals instead

Terminal 1:

```powershell
cd D:\ai-interview-coach\console-backend
.\.venv\Scripts\python.exe local_server.py
```

Terminal 2:

```powershell
cd D:\ai-interview-coach\ai-interview-coach
npm run dev
```

## Local configuration

On **New session**, use **Resume & specialties** to upload a readable PDF, DOCX, or TXT (up to 10 MB), or select a saved resume. Detected skills populate **Specialties to practice**; click skill chips to remove/add topics or edit the comma-separated list. You can enter specialties without a resume. Select your role, style, difficulty, and question count, then begin. Empty specialties use general role questions. Choose at least as many questions as topics to cover every topic.

Resume skill detection and specialty questions work locally without an AI key. Restart the backend after pulling these changes: the launcher adds the new database fields while preserving existing accounts and interviews. Uploaded files persist under `.local/uploads`.

- No Docker, Redis, cloud storage, or AI key is needed for this local launcher. It binds only to `127.0.0.1`, disables Redis rate limits, and uses seed questions and deterministic grading.
- Accounts, answers, and scores persist in `console-backend/.local/console.db`; the local signing secret is in `.local/secret.key`. These files are ignored by Git. Restarting the servers preserves your interviews.
- `local_server.py` explicitly overrides database/storage/AI settings for development without changing your `.env`. Production still requires PostgreSQL/Redis/private storage. SQLite local tests do not replace PostgreSQL migration tests.
- Vite proxies `/api/*` to `http://127.0.0.1:8000`, so no frontend `.env` is required. Remove any old `VITE_API_URL` override or set it to `/api/v1` when testing locally. Restart Vite after editing frontend environment variables.
- Login tokens stay in tab session storage (or memory if tab storage is blocked); refresh tokens rotate automatically. Closing the tab can require signing in again. Interview data remains in the backend.
- A failed request keeps the answer on screen for retry. Reloading resumes at the first unanswered question, but an unsent draft is not saved on the server.
- Older browser-only history remains in localStorage and is not automatically imported into account history.

If the launcher says port 8000 or 5173 is in use, stop the previous server instead of launching a second copy. If an error occurs during hidden backend startup, run Terminal 1's command directly to see its output.

## Tests

```powershell
cd D:\ai-interview-coach\console-backend
.\.venv\Scripts\python.exe -m pytest -q
cd ..\ai-interview-coach
npm test
npm run build
# Either install Chromium with npx playwright install chromium, or use Chrome:
$env:PLAYWRIGHT_EXECUTABLE_PATH='C:\Program Files\Google\Chrome\Application\chrome.exe'
npm run test:e2e
```

The connected browser tests start an isolated backend on port 8001 with a separate `.local/e2e` database, and a frontend preview on port 4173. They exercise real HTTP calls, account isolation, refresh rotation, lost-response recovery, resume, and saved reports. Speech is mocked to avoid depending on microphone hardware.
