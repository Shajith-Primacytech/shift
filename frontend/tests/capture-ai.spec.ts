import { test, expect, type Page } from "@playwright/test";
import AxeBuilder from "@axe-core/playwright";

const original =
  "Synthetic vibration after a tool change. The root cause is unconfirmed. Inspection is planned.";
async function signIn(page: Page, username = "tech") {
  await page.goto("/");
  await page.getByLabel("Username", { exact: true }).fill(username);
  await page
    .getByLabel("Password", { exact: true })
    .fill("browser-test-only-password");
  await page.getByRole("button", { name: "Sign in", exact: true }).click();
  await expect(page.locator(".app-shell")).toBeVisible();
}
async function fillCapture(page: Page, title: string) {
  await page.goto("/knowledge/capture");
  await page.getByLabel("Observation title").fill(title);
  await page
    .getByLabel("Symptom or maintenance context")
    .fill("Synthetic vibration");
  await page.getByLabel("Written observation").fill(original);
}

test("AI proposal is editable, review is explicit, original and metadata survive supervisor approval", async ({
  page,
}) => {
  await signIn(page);
  await fillCapture(page, "AI-assisted synthetic capture");
  await expect(
    page.getByText("Powered by Google Gemma", { exact: true }),
  ).toBeVisible();
  await expect(
    page.getByText("Configured · not executed for this draft", { exact: true }),
  ).toBeVisible();
  await page
    .getByRole("button", { name: "Structure with AI", exact: true })
    .click();
  const observations = page.getByRole("textbox", {
    name: /^Technician observations/,
  });
  await expect(observations).toHaveValue(original);
  await expect(page.getByLabel("Written observation")).toHaveValue(original);
  await expect(
    page.getByRole("textbox", { name: /^Confirmed root cause/ }),
  ).toHaveValue("");
  await page.getByRole("button", { name: "Submit for review" }).click();
  await expect(
    page.getByText("Review and confirm the current AI structure", {
      exact: false,
    }),
  ).toBeVisible();
  const confirm = page.getByRole("checkbox", { name: /I reviewed and edited/ });
  await confirm.check();
  const outcome = page.getByRole("textbox", { name: /^Observed outcome/ });
  await outcome.fill("Escalated for inspection; no repair confirmed.");
  await expect(confirm).not.toBeChecked();
  await confirm.check();
  const results = await new AxeBuilder({ page })
    .withTags(["wcag2a", "wcag2aa", "wcag21aa"])
    .analyze();
  expect(results.violations).toEqual([]);
  for (const width of [390, 768, 1440]) {
    await page.setViewportSize({ width, height: 1000 });
    expect(
      await page.evaluate(
        () => document.documentElement.scrollWidth <= innerWidth,
      ),
    ).toBeTruthy();
  }
  await page.screenshot({
    path: "test-results/capture-ai-review.png",
    fullPage: true,
  });
  await page.getByRole("button", { name: "Submit for review" }).click();
  await expect(
    page.getByRole("heading", { name: "Saved for supervisor review" }),
  ).toBeVisible();
  await page.getByRole("link", { name: "Open review queue" }).click();
  await page
    .getByRole("button", { name: /AI-assisted synthetic capture/ })
    .click();
  await expect(page.locator(".observation-content")).toHaveText(original);
  await expect(
    page.getByRole("region", { name: "Technician-reviewed AI structure" }),
  ).toContainText("Escalated for inspection; no repair confirmed.");
  await expect(
    page.getByRole("button", { name: "Approve for library" }),
  ).toHaveCount(0);
  await page.reload();
  await page
    .getByRole("button", { name: /AI-assisted synthetic capture/ })
    .click();
  await page
    .getByText("AI Execution Details · AMD Token Factory · success")
    .click();
  await expect(
    page.getByText("self-dploy/Gemma-4-31B-IT", { exact: true }).first(),
  ).toBeVisible();
  await page.getByRole("button", { name: "Sign out" }).click();
  await signIn(page, "super");
  await page.goto("/approvals");
  await page
    .getByRole("button", { name: /AI-assisted synthetic capture/ })
    .click();
  await expect(
    page.getByRole("region", { name: "Technician-reviewed AI structure" }),
  ).toBeVisible();
  await page.getByRole("button", { name: "Approve for library" }).click();
  await page.goto("/knowledge?q=AI-assisted%20synthetic%20capture");
  await page.locator(".knowledge-card").click();
  await expect(page.getByRole("article")).toContainText(
    "Escalated for inspection; no repair confirmed.",
  );
});

test("stale AI proposal requires discard; manual capture remains available", async ({
  page,
}) => {
  await signIn(page, "super"); // Separate owner avoids the preceding test's 30-second cost guard.
  await fillCapture(page, "Changed source capture");
  await page
    .getByRole("button", { name: "Structure with AI", exact: true })
    .click();
  await expect(
    page.getByRole("textbox", { name: /^Technician observations/ }),
  ).toBeVisible();
  await page.getByRole("checkbox", { name: /I reviewed and edited/ }).check();
  await page
    .getByLabel("Written observation")
    .fill(original + " Additional technician detail.");
  await expect(
    page.getByText("Original fields changed after structuring.", {
      exact: false,
    }),
  ).toBeVisible();
  await page.getByRole("button", { name: "Submit for review" }).click();
  await expect(
    page.getByRole("heading", { name: "Saved for supervisor review" }),
  ).toHaveCount(0);
  await page
    .getByRole("button", { name: "Discard AI proposal; continue manually" })
    .click();
  await page.getByRole("button", { name: "Submit for review" }).click();
  await expect(
    page.getByRole("heading", { name: "Saved for supervisor review" }),
  ).toBeVisible();
});

test("AI failure exposes sanitized execution evidence and preserves manual submission", async ({
  page,
}) => {
  await signIn(page);
  await fillCapture(page, "Manual capture after AI timeout");
  let calls = 0;
  await page.route("**/api/v1/capture/structure", (route) => {
    calls++;
    return route.fulfill({
      status: 504,
      json: {
        detail: "Gemma timed out. Original text unchanged.",
        execution: {
          provider: "AMD Token Factory",
          requested_model: "Gemma-4-31B-IT",
          model_id: "Gemma-4-31B-IT",
          returned_model: null,
          requested_at: "2026-10-17T12:00:00Z",
          latency_ms: 55000,
          usage: null,
          status: "failure",
          http_status: null,
          error_code: "timeout",
        },
      },
    });
  });
  await page
    .getByRole("button", { name: "Structure with AI", exact: true })
    .click();
  await expect(
    page.getByText("Gemma timed out.", { exact: false }),
  ).toBeVisible();
  await expect(page.getByLabel("Written observation")).toHaveValue(original);
  await page
    .getByText("AI Execution Details · AMD Token Factory · failure")
    .click();
  await expect(page.getByText("timeout", { exact: true })).toBeVisible();
  expect(calls).toBe(1);
  await page.getByRole("button", { name: "Submit for review" }).click();
  await expect(
    page.getByRole("heading", { name: "Saved for supervisor review" }),
  ).toBeVisible();
});
