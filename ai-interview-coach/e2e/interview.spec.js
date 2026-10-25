import { test, expect } from "@playwright/test";

const password = "Local-test-password123";
async function register(page) {
  await page.addInitScript(() => {
    Object.defineProperty(window, "speechSynthesis", { value: {
      cancel() {}, getVoices() { return []; },
      speak(utterance) { setTimeout(() => utterance.onend?.(), 10); },
    }});
  });
  const email = `browser-${crypto.randomUUID()}@example.com`;
  await page.goto("/setup");
  await expect(page).toHaveURL(/\/login$/);
  await page.getByRole("button", { name: "Create an account", exact: true }).click();
  await page.getByLabel("Full name", { exact: true }).fill("Alex Candidate");
  await page.getByLabel("Email", { exact: true }).fill(email);
  await page.getByLabel("Password", { exact: true }).fill(password);
  await page.getByRole("button", { name: "Create account", exact: true }).click();
  await expect(page).toHaveURL(/\/setup$/);
  return email;
}

async function start(page) {
  await page.getByRole("button", { name: "Frontend Developer", exact: true }).click();
  await page.getByRole("button", { name: "Type my answers" }).click();
  await page.getByRole("slider").fill("3");
  await page.getByRole("button", { name: "Begin interview" }).click();
  await expect(page.getByRole("textbox", { name: "Your answer" })).toBeEnabled();
}

async function skipRemaining(page) {
  for (let attempt = 0; attempt < 7; attempt++) {
    if (page.url().includes("/results/")) break;
    await page.getByRole("button", { name: "Skip question" }).click();
    await page.waitForFunction(() => location.pathname.startsWith("/results/") ||
      [...document.querySelectorAll("button")].some(button => button.textContent.includes("Skip question") && !button.disabled));
  }
  await expect(page).toHaveURL(/\/results\//);
}

test("register, answer, follow up, persist, reload, PDF, logout and login", async ({ page }) => {
  const email = await register(page);
  await start(page);
  const interviewId = page.url().split("/").at(-1);
  await page.getByRole("textbox").fill("I do not know this topic");
  await page.getByRole("button", { name: "Submit answer" }).click();
  await expect(page.getByRole("heading", { name: /Follow-up:/ })).toBeVisible();
  await expect(page.getByRole("textbox")).toHaveValue("");
  await page.getByRole("textbox").fill("This is my additional explanation");
  await page.getByRole("button", { name: "Submit answer" }).click();
  await expect(page.getByText("Question 2 / 3", { exact: true })).toBeVisible();
  await skipRemaining(page);
  await expect(page.getByText("Question-by-question", { exact: true })).toBeVisible();
  await page.reload();
  await expect(page.getByText("I do not know this topic", { exact: false })).toBeVisible();
  const download = page.waitForEvent("download");
  await page.getByRole("button", { name: "Download PDF report" }).click();
  expect((await download).suggestedFilename()).toMatch(/\.pdf$/);
  await page.getByRole("button", { name: "Sign out", exact: true }).click();
  await expect(page).toHaveURL(/\/login$/);
  await page.getByLabel("Email", { exact: true }).fill(email);
  await page.getByLabel("Password", { exact: true }).fill(password);
  await page.getByRole("button", { name: "Sign in", exact: true }).click();
  await expect(page).toHaveURL(new RegExp(`/results/${interviewId}$`));
  await page.getByRole("link", { name: "Progress", exact: true }).click();
  await expect(page.locator(`a[href="/results/${interviewId}"]`)).toBeVisible();
});

test("upload a resume, choose specialties, and reuse the saved resume", async ({ page }) => {
  await register(page);
  const upload = page.getByLabel("Upload resume (optional)");
  await expect(upload).toBeEnabled();
  await upload.setInputFiles({ name: "candidate.txt", mimeType: "text/plain", buffer: Buffer.from("Skills: React, TypeScript, Python") });
  await expect(page.getByLabel("Specialties to practice")).toHaveValue("React, TypeScript, Python");
  await page.getByRole("button", { name: "Python", exact: true }).click();
  await page.getByLabel("Specialties to practice").fill("React, TypeScript, GraphQL");
  const created = page.waitForResponse(response => response.url().endsWith("/api/v1/interviews") && response.request().method() === "POST");
  await start(page);
  const session = await (await created).json();
  expect(session.resume_id).toBeTruthy();
  expect(session.specialties).toEqual(["React", "TypeScript", "GraphQL"]);
  session.questions.forEach((question, index) => expect(question.text).toContain(session.specialties[index]));
  await expect(page.getByRole("heading", { name: /React/ })).toBeVisible();
  await page.reload();
  await expect(page.getByRole("heading", { name: /React/ })).toBeVisible();
  await page.goto("/setup");
  await page.getByLabel("Saved resume").selectOption(session.resume_id);
  await expect(page.getByLabel("Specialties to practice")).toHaveValue("React, TypeScript, Python");
  await upload.setInputFiles({ name: "invalid.pdf", mimeType: "application/pdf", buffer: Buffer.from("not a PDF") });
  await expect(page.getByRole("alert")).toContainText("Invalid document");
  await expect(page.getByLabel("Saved resume")).toHaveValue(session.resume_id);
});

test("in-progress interviews resume after refresh and access tokens refresh automatically", async ({ page }) => {
  await register(page); await start(page);
  await page.getByRole("button", { name: "Skip question" }).click();
  await expect(page.getByText("Question 2 / 3", { exact: true })).toBeVisible();
  await page.evaluate(() => {
    const tokens = JSON.parse(sessionStorage.getItem("console_auth_v1"));
    tokens.access_token = "expired-test-token";
    sessionStorage.setItem("console_auth_v1", JSON.stringify(tokens));
  });
  await page.reload();
  await expect(page.getByText("Question 2 / 3", { exact: true })).toBeVisible();
  const access = await page.evaluate(() => JSON.parse(sessionStorage.getItem("console_auth_v1")).access_token);
  expect(access).not.toBe("expired-test-token");
});

test("a lost submission response preserves the draft and retries without duplicate answers", async ({ page }) => {
  await register(page); await start(page);
  let intercepted = false;
  await page.route("**/api/v1/questions/*/answer", async route => {
    if (intercepted) { await route.continue(); return; }
    intercepted = true;
    await route.fetch(); // The real server commits, but the browser loses the response.
    await route.abort("failed");
  });
  await page.getByRole("textbox").fill("I do not know this topic");
  await page.getByRole("button", { name: "Submit answer" }).click();
  await expect(page.getByRole("alert")).toContainText("Your answer is still here");
  await expect(page.getByRole("textbox")).toHaveValue("I do not know this topic");
  await page.getByRole("button", { name: "Submit answer" }).click();
  await expect(page.getByRole("heading", { name: /Follow-up:/ })).toBeVisible();
  await expect(page.getByRole("alert")).toHaveCount(0);
});

test("another account cannot read a saved interview", async ({ page, browser }) => {
  await register(page); await start(page);
  const id = page.url().split("/").at(-1);
  const other = await browser.newContext({ baseURL: "http://127.0.0.1:4173" });
  try {
    const otherPage = await other.newPage();
    await register(otherPage);
    await otherPage.goto(`/results/${id}`);
    await expect(otherPage.getByRole("alert")).toContainText("different user");
  } finally { await other.close(); }
});
