import { test, expect } from "@playwright/test";

test("authentication shows a busy cursor and spinner and clears them after success or failure", async ({ page }) => {
  let releaseRegistration;
  const registrationGate = new Promise(resolve => { releaseRegistration = resolve; });
  await page.route("**/api/v1/auth/register", async route => {
    await registrationGate;
    await route.continue();
  });
  await page.goto("/login");
  await page.getByRole("button", { name: "Create an account", exact: true }).click();
  await page.getByLabel("Full name", { exact: true }).fill("Loading Candidate");
  await page.getByLabel("Email", { exact: true }).fill(`loading-${crypto.randomUUID()}@example.com`);
  await page.getByLabel("Password", { exact: true }).fill("Local-test-password123");
  await page.getByRole("button", { name: "Create account", exact: true }).click();
  try {
    const button = page.getByRole("button", { name: "Connecting…", exact: true });
    await expect(button).toBeDisabled();
    await expect(button).toHaveAttribute("aria-busy", "true");
    await expect(button.locator("svg")).toBeVisible();
    await expect(button).toHaveCSS("cursor", "progress");
    await expect(page.getByRole("progressbar", { name: "Operation in progress" })).toBeVisible();
  } finally { releaseRegistration(); }
  await expect(page).toHaveURL(/\/dashboard$/);
  await expect(page.locator("html")).not.toHaveAttribute("data-loading");

  let releaseLogout;
  const logoutGate = new Promise(resolve => { releaseLogout = resolve; });
  await page.route("**/api/v1/auth/logout", async route => {
    await logoutGate;
    await route.abort("failed");
  });
  await page.getByRole("button", { name: "Sign out", exact: true }).click();
  try {
    const button = page.getByRole("button", { name: "Signing out…", exact: true });
    await expect(button).toHaveAttribute("aria-busy", "true");
    await expect(button.locator("svg")).toBeVisible();
    await expect(button).toHaveCSS("cursor", "progress");
  } finally { releaseLogout(); }
  await expect(page.getByRole("alert")).toContainText("Cannot reach the server");
  await expect(page.locator("html")).not.toHaveAttribute("data-loading");
  await expect(page.getByRole("progressbar", { name: "Operation in progress" })).toHaveCount(0);
  await expect(page.getByRole("button", { name: "Sign out", exact: true })).toBeEnabled();
  await page.unroute("**/api/v1/auth/logout");
  await page.getByRole("button", { name: "Sign out", exact: true }).click();
  await expect(page).toHaveURL(/\/login$/);
  await expect(page.locator("html")).not.toHaveAttribute("data-loading");
});
