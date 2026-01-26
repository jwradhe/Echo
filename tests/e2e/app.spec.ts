import { test, expect } from "@playwright/test";

test.describe("Echo lifecycle E2E", () => {
  test.describe.configure({ mode: "serial" });

  const echo = `E2E Echo ${Date.now()}`;

  test("Create a new Echo", async ({ page }) => {
    await page.goto("/dashboard");

    // Klicka på Let's Echo knapp
    await page.getByRole("button", { name: "Let's Echo" }).click();

    // Fyll i Echo textarea
    await page.getByPlaceholder("What do you want to echo?").fill(echo);

    // Posta Echo
    await page.getByRole("button", { name: "Post Echo" }).click();

    // Verifiera att den syns i feed efter redirect/reload
    await expect(page.getByText(echo)).toBeVisible();
  });

  
});
