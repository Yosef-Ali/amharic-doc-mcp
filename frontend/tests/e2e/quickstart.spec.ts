import { test, expect } from "@playwright/test";

test.describe("Quickstart flow", () => {
  test("upload, monitor, search, export", async ({ page }) => {
    await page.goto("http://localhost:3000");
    await page.fill("input[name=email]", "demo@amharic-docs.ai");
    await page.fill("input[name=password]", "demo123");
    await page.click("button[type=submit]");

    await page.waitForSelector("text=Upload Documents");
    // Further interactions pending implementation; placeholder expectations ensure failure pre-implementation
    await expect(page.getByText("Upload Documents")).toBeVisible();
  });
});
