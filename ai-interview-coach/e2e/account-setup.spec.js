import { test, expect } from "@playwright/test";

test("starting an interview requires login, shows the name initial, and detects the resume role", async ({ page }) => {
  await page.goto("/");
  await page.getByRole("link", { name: "Start a mock interview" }).click();
  await expect(page).toHaveURL(/\/login$/);
  await page.getByRole("button", { name: "Create an account", exact: true }).click();
  await page.getByLabel("Full name").fill("Ali Candidate");
  await page.getByLabel("Email", { exact: true }).fill(`profile-${crypto.randomUUID()}@example.com`);
  await page.getByLabel("Password", { exact: true }).fill("Local-test-password123");
  await page.getByRole("button", { name: "Create account", exact: true }).click();
  await expect(page).toHaveURL(/\/setup$/);
  const profile = page.getByRole("button", { name: "Profile: Ali Candidate", exact: true });
  await expect(profile).toHaveText("A");
  await profile.click();
  await expect(page.locator("#profile-details")).toContainText("Ali Candidate");
  await profile.press("Escape");
  await expect(page.locator("#profile-details")).toHaveCount(0);
  const upload = page.getByLabel("Upload resume (optional)");
  await expect(upload).toBeEnabled();
  await upload.setInputFiles({ name: "resume.txt", mimeType: "text/plain", buffer: Buffer.from("Ali Candidate\nBackend Developer\nSkills: Python, FastAPI, React") });
  await expect(page.getByRole("button", { name: "Backend Developer", exact: true })).toHaveAttribute("aria-pressed", "true");
  await expect(page.getByLabel("Specialties to practice")).toHaveValue("Python, FastAPI");
  await page.getByRole("button", { name: "Frontend Developer", exact: true }).click();
  await expect(page.getByRole("button", { name: "Frontend Developer", exact: true })).toHaveAttribute("aria-pressed", "true");
  await page.reload();
  await expect(profile).toHaveText("A");
  await page.getByLabel("Saved resume").selectOption({ index: 1 });
  await expect(page.getByRole("button", { name: "Backend Developer", exact: true })).toHaveAttribute("aria-pressed", "true");
  await page.getByRole("button", { name: "Sign out", exact: true }).click();
  await expect(profile).toHaveCount(0);
  await expect(page).toHaveURL(/\/login$/);
});

test("Google button exchanges its credential and returns to session setup", async ({ page, request }) => {
  // Only Google itself and its verified-token exchange are mocked here. Other
  // requests use real account tokens; backend tests verify Google token validation.
  const registered = await request.post("http://127.0.0.1:8001/api/v1/auth/register", { data: {
    email: `google-ui-${crypto.randomUUID()}@example.com`, password: "Local-test-password123", full_name: "Grace Candidate",
  } });
  const tokens = await registered.json();
  await page.route("**/api/v1/auth/providers", route => route.fulfill({ json: { google_client_id: "test.apps.googleusercontent.com" } }));
  await page.route("https://accounts.google.com/gsi/client", route => route.fulfill({ contentType: "text/javascript", body: `
    window.google = { accounts: { id: {
      initialize(options) { this.options = options; },
      renderButton(container) {
        const button = document.createElement('button'); button.textContent = 'Continue with Google';
        button.onclick = () => this.options.callback({credential: 'verified-google-test-token'});
        container.appendChild(button);
      }
    } } };
  ` }));
  let exchanges = 0;
  await page.route("**/api/v1/auth/google", async route => {
    exchanges++;
    expect(route.request().postDataJSON()).toEqual({ id_token: "verified-google-test-token" });
    await route.fulfill({ json: tokens });
  });
  await page.goto("/setup");
  await page.getByRole("button", { name: "Continue with Google", exact: true }).click();
  await expect(page).toHaveURL(/\/setup$/);
  await expect(page.getByRole("button", { name: "Profile: Grace Candidate" })).toHaveText("G");
  expect(exchanges).toBe(1);
});

test("Google script failure keeps email sign-in available and supports retry", async ({ page }) => {
  await page.route("**/api/v1/auth/providers", route => route.fulfill({ json: { google_client_id: "test.apps.googleusercontent.com" } }));
  await page.route("https://accounts.google.com/gsi/client", route => route.abort());
  await page.goto("/login");
  await expect(page.getByRole("alert")).toContainText("Google sign-in could not load");
  await expect(page.getByRole("button", { name: "Sign in", exact: true })).toBeEnabled();
  await page.getByRole("button", { name: "Retry Google sign-in" }).click();
  await expect(page.getByRole("alert")).toContainText("Google sign-in could not load");
});
