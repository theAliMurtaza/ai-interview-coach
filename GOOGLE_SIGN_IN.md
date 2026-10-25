# Enable Google sign-in on the deployed app

The sign-in and registration pages now support Google's official **Continue with Google** button. The backend validates the Google ID token and creates an app session. Configure one public OAuth client ID on Render; no Google client secret or additional Vercel environment variable is needed.

## 1. Create a Google Web client

1. Open [Google Cloud Console](https://console.cloud.google.com/) and select or create a project.
2. Open **Google Auth Platform**. Complete **Branding** with the app name, support email, and developer contact details. Configure **Audience** for the intended users. If an external app remains in Testing, add the Google accounts you will use under Test users.
3. Under **Clients**, create an OAuth client with application type **Web application**.
4. Add this exact **Authorized JavaScript origin** for the current deployment:

   ```text
   https://ai-interview-coach-z1fh-omega.vercel.app
   ```

   Do not include `/login` or a trailing slash. Add any custom frontend domain separately. For local development, also add `http://localhost` and `http://localhost:5173`, then open the frontend using `localhost`.
5. Save and copy the **Client ID**, ending in `.apps.googleusercontent.com`. This integration uses a JavaScript callback in popup mode, so it does not need an authorized redirect URI.

See Google's [client setup instructions](https://developers.google.com/identity/gsi/web/guides/get-google-api-clientid) for console setup and browser requirements.

## 2. Configure Render

1. Open the API service on Render, then **Environment**.
2. Add `GOOGLE_OAUTH_CLIENT_ID` with the copied client ID, without surrounding quotes.
3. Confirm `BACKEND_CORS_ORIGINS` contains the exact frontend origin:

   ```json
   ["https://ai-interview-coach-z1fh-omega.vercel.app"]
   ```

4. Save and redeploy the backend with the updated code. Keep all existing database, Redis, storage, and app-secret values.
5. Open [the provider configuration endpoint](https://interview-coach-api-ytw5.onrender.com/api/v1/auth/providers). It should return `google_client_id` containing your public client ID. A `null` value means the environment variable is missing; a 404 means the backend code has not been updated.

For local development, set `GOOGLE_OAUTH_CLIENT_ID` in the backend's untracked `.env` and restart it. Email/password login remains available without this setting.

## 3. Redeploy Vercel and verify

1. Push the changes and deploy the frontend. The updated Vercel configuration allows Google's required script, frame, and connection URLs and sets the popup-compatible opener policy.
2. Keep `VITE_API_URL=https://interview-coach-api-ytw5.onrender.com/api/v1` in Vercel.
3. Open the app while signed out and click **Start a mock interview**. Sign in with Google; you should return to interview setup and see your name's initial in the profile circle.
4. Sign out and sign back in with the same Google account. Confirm that the same profile and saved interviews appear.

Existing password accounts are not automatically linked to a Google account with the same email. Continue using email/password for those accounts. Google sign-in supports new accounts and accounts already registered through Google.

If Google reports `origin_mismatch`, compare the browser's exact origin with the Web client's authorized JavaScript origins. If the button is unavailable, check the provider endpoint and Render environment. A sleeping Render service may need time to start. Allow Google configuration changes time to propagate.

The automated tests cover the button, credential exchange, name display, and failure handling using a simulated Google response. The real Google account flow still needs this deployment smoke test.

## Resume-driven interview setup

Uploading or selecting a saved resume examines the readable headline near the top of the document. A recognized headline such as **Backend Developer**, **Frontend Engineer**, **Full Stack Developer**, **Data Scientist**, **DevOps Engineer**, **Mobile Developer**, or **QA Engineer** automatically selects the role and relevant detected skills. Users can change the role and specialties before starting.

Ambiguous headlines such as **Software Engineer** leave role selection to the user. Past employment titles are not used as the current headline. Scanned PDFs need a readable text layer. The feature works with AI disabled and existing saved resumes; it needs no new database migration.
