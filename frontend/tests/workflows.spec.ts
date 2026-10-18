import { test, expect, type Page } from "@playwright/test";
import AxeBuilder from "@axe-core/playwright";

async function signIn(page: Page, username = "tech") {
  await page.goto("/");
  await page.getByLabel("Username", { exact: true }).fill(username);
  await page
    .getByLabel("Password", { exact: true })
    .fill("browser-test-only-password");
  await page.getByRole("button", { name: "Sign in", exact: true }).click();
  await expect(page.locator(".app-shell")).toBeVisible();
}
test.beforeEach(async ({ page }) => {
  await signIn(page);
});

test("dashboard, navigation, directory filtering, and unknown machine", async ({
  page,
}) => {
  await page.goto("/");
  await expect(
    page.getByRole("heading", { name: "A clearer picture. A smarter shift." }),
  ).toBeVisible();
  await expect(
    page.getByText("All machines, telemetry, and knowledge are synthetic.", {
      exact: false,
    }),
  ).toBeVisible();
  await page.getByRole("link", { name: "All machines", exact: true }).click();
  await page.getByRole("textbox", { name: "Search machines" }).fill("CNC-01");
  await expect(page.locator(".machine-card")).toHaveCount(1);
  await page.locator(".machine-card").click();
  await expect(
    page.getByRole("heading", { name: "CNC-01", exact: true }),
  ).toBeVisible();
  await page.getByRole("tab", { name: "Knowledge" }).click();
  await expect(
    page.getByText("Spindle vibration: inspection checklist"),
  ).toBeVisible();
  await page.goto("/machines/unknown");
  await expect(
    page.getByRole("heading", { name: "We couldn’t find that page." }),
  ).toBeVisible();
});

test("capture with attachment, authenticated approval, library inclusion, and persistence", async ({
  page,
}) => {
  await page.goto("/knowledge/capture");
  await page
    .getByLabel("Observation title")
    .fill("Synthetic tooling observation");
  await page
    .getByLabel("Symptom or maintenance context")
    .fill("Tool change vibration");
  await page.getByRole("tab", { name: "Documents" }).click();
  await page.locator("input[type=file]").setInputFiles({
    name: "demo-note.txt",
    mimeType: "text/plain",
    buffer: Buffer.from("Synthetic supporting note"),
  });
  await page
    .getByLabel("Written observation")
    .fill(
      "Synthetic observation: vibration was noticed after a tool change. Inspection is requested.",
    );
  await page.getByRole("button", { name: "Submit for review" }).click();
  await expect(
    page.getByRole("heading", { name: "Saved for supervisor review" }),
  ).toBeVisible();
  await page.getByRole("link", { name: "Open review queue" }).click();
  await expect(
    page
      .getByRole("heading", {
        name: "Synthetic tooling observation",
        exact: true,
      })
      .last(),
  ).toBeVisible();
  const download = page.waitForEvent("download");
  await page.getByRole("link", { name: "Download demo-note.txt" }).click();
  expect((await download).suggestedFilename()).toBe("demo-note.txt");
  await expect(
    page.getByRole("button", { name: "Approve for library" }),
  ).toHaveCount(0);
  await page.getByRole("button", { name: "Sign out" }).click();
  await signIn(page, "super");
  await page.goto("/approvals");
  await page
    .getByRole("button", { name: /Synthetic tooling observation/ })
    .click();
  await page.getByRole("button", { name: "Approve for library" }).click();
  await page
    .locator(".sidebar")
    .getByRole("link", { name: "Knowledge library" })
    .click();
  await page
    .getByRole("textbox", { name: "Search approved knowledge" })
    .fill("Synthetic tooling observation");
  await expect(page.locator(".knowledge-card")).toHaveCount(1);
  await page.locator(".knowledge-card").click();
  await expect(page.getByRole("article")).toContainText("Maya Chen");
  await page.reload();
  await page
    .getByRole("textbox", { name: "Search approved knowledge" })
    .fill("Synthetic tooling observation");
  await expect(page.locator(".knowledge-card")).toHaveCount(1);
});

test("rejection requires a reason and rejected content stays excluded", async ({
  page,
}) => {
  await page.getByRole("button", { name: "Sign out" }).click();
  await signIn(page, "super");
  await page.goto("/approvals");
  await page.getByRole("button", { name: "Reject submission" }).click();
  await expect(page.locator(".form-error[role=alert]").first()).toContainText(
    "Add a reason",
  );
  await page
    .getByLabel("Review note")
    .fill("Please include the tool identifier and observation time.");
  await page.getByRole("button", { name: "Reject submission" }).click();
  await page.getByRole("button", { name: "Rejected", exact: false }).click();
  await expect(page.locator(".review-detail")).toContainText(
    "Please include the tool identifier",
  );
  await page
    .locator(".sidebar")
    .getByRole("link", { name: "Knowledge library" })
    .click();
  await page
    .getByRole("textbox", { name: "Search approved knowledge" })
    .fill("Intermittent vibration during finishing");
  await expect(page.locator(".knowledge-card")).toHaveCount(0);
});

test("grounded workflow has verified source references and logs a pending outcome", async ({
  page,
}) => {
  await page.goto("/troubleshoot");
  await page.getByRole("button", { name: "Review evidence" }).click();
  await expect(
    page.getByText("AI-selected approved guidance", { exact: true }),
  ).toBeVisible();
  await expect(page.locator(".source-card")).toHaveCount(2);
  const model = page.getByRole("region", {
    name: "Troubleshooting evidence selection",
  });
  await expect(model).toContainText("test-only-mocked-amd");
  await expect(model).toContainText("Inference via AMD Token Factory");
  await expect(
    model.getByText("Powered by Google Gemma", { exact: true }),
  ).toHaveCount(0);
  await page.getByRole("button", { name: "Continue to checks" }).click();
  await expect(
    page.getByRole("button", { name: "Log outcome" }),
  ).toBeDisabled();
  for (const checkbox of await page.getByRole("checkbox").all())
    await checkbox.check();
  await page.getByRole("button", { name: "Log outcome" }).click();
  await page
    .getByLabel("Resolution or handover notes")
    .fill(
      "Demo inspection was escalated. The cause remains unconfirmed and requires supervisor review.",
    );
  await page.getByRole("radio", { name: "Helpful", exact: true }).check();
  await page.getByRole("button", { name: "Submit outcome" }).click();
  await expect(
    page.getByRole("heading", { name: "Outcome logged for review" }),
  ).toBeVisible();
  await page.getByRole("link", { name: "Review submission" }).click();
  await expect(page.locator(".review-detail")).toContainText(
    "Demo inspection was escalated",
  );
  await expect(page.locator(".review-detail .badge")).toContainText("Pending");
});

test("unsupported cases show no evidence; library search responds to a new global query", async ({
  page,
}) => {
  await page.goto("/troubleshoot?machine=CNC-02");
  await page.getByRole("button", { name: "Review evidence" }).click();
  await expect(
    page.getByRole("heading", { name: "Insufficient approved evidence" }),
  ).toBeVisible();
  await expect(
    page.getByRole("button", { name: "Continue to checks" }),
  ).toBeDisabled();
  await page.goto("/knowledge?q=spindle");
  await page
    .getByRole("textbox", { name: "Search knowledge", exact: true })
    .fill("Hydraulic");
  await page
    .getByRole("textbox", { name: "Search knowledge", exact: true })
    .press("Enter");
  await expect(
    page.getByRole("textbox", { name: "Search approved knowledge" }),
  ).toHaveValue("Hydraulic");
  await expect(page.locator(".knowledge-card")).toHaveCount(1);
});

test("microphone denial is actionable and leaves text submission available", async ({
  page,
}) => {
  await page.addInitScript(() => {
    navigator.mediaDevices.getUserMedia = async () => {
      throw new DOMException("Denied", "NotAllowedError");
    };
  });
  await page.goto("/knowledge/capture");
  await page.getByRole("tab", { name: "Voice" }).click();
  await page.getByRole("button", { name: "Start recording" }).click();
  await expect(
    page.locator(".voice-box .form-error[role=alert]"),
  ).toContainText("Microphone access was denied");
  await expect(
    page.getByRole("button", { name: "Submit for review" }),
  ).toBeEnabled();
});

test("backend offline state can recover on retry", async ({ page }) => {
  await page.route("**/api/v1/health", (route) => route.abort());
  await page.goto("/");
  await expect(
    page.getByText("API offline · saved data unavailable"),
  ).toBeVisible();
  await page.route("**/api/v1/health", (route) =>
    route.fulfill({ json: { status: "ok", service: "shift-api" } }),
  );
  await page
    .getByRole("button", { name: "Recheck backend connection" })
    .click();
  await expect(page.getByText("SHIFT API connected")).toBeVisible();
});

test("all main views meet automated accessibility checks", async ({ page }) => {
  for (const path of [
    "/",
    "/machines",
    "/machines/CNC-01",
    "/knowledge",
    "/knowledge/capture",
    "/approvals",
    "/troubleshoot",
  ]) {
    await page.goto(path);
    await page.locator("main h1").waitFor();
    const results = await new AxeBuilder({ page })
      .withTags(["wcag2a", "wcag2aa", "wcag21aa"])
      .analyze();
    expect(
      results.violations,
      `${path}: ${JSON.stringify(results.violations.map((v) => ({ id: v.id, nodes: v.nodes.map((n) => n.target) })))}`,
    ).toEqual([]);
  }
});

test("mobile and tablet views do not overflow and mobile navigation works", async ({
  page,
}) => {
  for (const width of [390, 768]) {
    await page.setViewportSize({ width, height: 844 });
    for (const path of [
      "/",
      "/machines",
      "/machines/CNC-01",
      "/knowledge",
      "/knowledge/capture",
      "/approvals",
      "/troubleshoot",
    ]) {
      await page.goto(path);
      await page.locator("main h1").waitFor();
      expect(
        await page.evaluate(
          () => document.documentElement.scrollWidth <= innerWidth,
        ),
        `${path} at ${width}px`,
      ).toBeTruthy();
    }
  }
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto("/");
  await page.getByRole("button", { name: "Open navigation" }).click();
  await page
    .locator(".sidebar")
    .getByRole("link", { name: "Approvals" })
    .click();
  await expect(
    page.getByRole("heading", { name: "Turn observations into knowledge." }),
  ).toBeVisible();
  await page.screenshot({
    path: "test-results/shift-mobile.png",
    fullPage: true,
  });
});

test("mobile menu traps focus and closes with Escape", async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto("/");
  await page
    .getByRole("heading", { name: "A clearer picture. A smarter shift." })
    .waitFor();
  const trigger = page.getByRole("button", { name: "Open navigation" });
  await trigger.click();
  await expect(page.getByRole("button", { name: "Close menu" })).toBeFocused();
  await page.keyboard.press("Shift+Tab");
  await expect(
    page.locator(".sidebar").getByRole("button", { name: "Sign out" }),
  ).toBeFocused();
  await page.keyboard.press("Escape");
  await expect(trigger).toBeFocused();
  await expect(page.locator(".sidebar")).toHaveAttribute("inert", "");
});

test("browser audio recording can be captured, previewed, and removed", async ({
  browser,
}) => {
  const context = await browser.newContext({ permissions: ["microphone"] });
  const page = await context.newPage();
  // A generated audio stream exercises MediaRecorder without accessing a real microphone.
  await page.addInitScript(() => {
    navigator.mediaDevices.getUserMedia = async () => {
      const audio = new AudioContext();
      const oscillator = audio.createOscillator();
      const destination = audio.createMediaStreamDestination();
      oscillator.connect(destination);
      oscillator.start();
      const track = destination.stream.getAudioTracks()[0];
      const stop = track.stop.bind(track);
      track.stop = () => {
        oscillator.stop();
        void audio.close();
        stop();
      };
      return destination.stream;
    };
  });
  await signIn(page);
  await page.goto("/knowledge/capture");
  await page.getByRole("tab", { name: "Voice" }).click();
  await page.getByRole("button", { name: "Start recording" }).click();
  await expect(
    page.getByRole("button", { name: "Finish voice capture first" }),
  ).toBeDisabled();
  await page.getByRole("button", { name: "Stop recording" }).click();
  await expect(page.getByText("Voice recording attached")).toBeVisible();
  await expect(page.locator("audio")).toHaveAttribute("src", /^blob:/);
  await page.getByRole("button", { name: "Remove recording" }).click();
  await expect(page.locator("audio")).toHaveCount(0);
  await context.close();
});

test("failed capture remains editable and never reports a successful save", async ({
  page,
}) => {
  await page.goto("/knowledge/capture");
  await page
    .getByLabel("Observation title")
    .fill("Failure handling observation");
  await page
    .getByLabel("Symptom or maintenance context")
    .fill("Synthetic vibration");
  await page
    .getByLabel("Written observation")
    .fill("Synthetic observation for a failed storage request.");
  await page.route("**/api/v1/submissions", (route) =>
    route.fulfill({
      status: 503,
      json: { detail: "Storage unavailable. Try again." },
    }),
  );
  await page.getByRole("button", { name: "Submit for review" }).click();
  await expect(page.locator(".capture-form [role=alert]")).toContainText(
    "Storage unavailable",
  );
  await expect(page.getByLabel("Observation title")).toHaveValue(
    "Failure handling observation",
  );
  await expect(
    page.getByRole("heading", { name: "Saved for supervisor review" }),
  ).toHaveCount(0);
});

test("supervisor revocation removes a saved source from the library", async ({
  page,
}) => {
  const created = await page.request.post("/api/v1/submissions", {
    headers: { "X-Shift-Request": "1" },
    multipart: {
      metadata: JSON.stringify({
        machineId: "CNC-01",
        title: "Synthetic revocation source",
        symptom: "Vibration",
        content: "A synthetic observation to exercise revocation.",
      }),
    },
  });
  expect(created.status()).toBe(201);
  await page.getByRole("button", { name: "Sign out" }).click();
  await signIn(page, "super");
  await page.goto("/approvals");
  await page
    .getByRole("button", { name: /Synthetic revocation source/ })
    .click();
  await page.getByRole("button", { name: "Approve for library" }).click();
  await expect(
    page.getByRole("status").filter({ hasText: "approved and saved" }),
  ).toBeVisible();
  await page.getByRole("button", { name: /^Approved/ }).click();
  await page
    .getByRole("button", { name: /Synthetic revocation source/ })
    .click();
  await page
    .getByLabel("Review note")
    .fill("Synthetic source withdrawn for correction.");
  await page.getByRole("button", { name: "Revoke approval" }).click();
  await expect(
    page.getByRole("status").filter({ hasText: "revoked" }),
  ).toBeVisible();
  await page.goto("/knowledge?q=Synthetic%20revocation%20source");
  await expect(
    page.getByRole("heading", { name: "No matching knowledge" }),
  ).toBeVisible();
});

test("troubleshooting timeout displays an error without demo fallback", async ({
  page,
}) => {
  await page.goto("/troubleshoot");
  await page.route("**/api/v1/troubleshoot", (route) =>
    route.fulfill({
      status: 504,
      json: { detail: "Inference timed out. No answer is available." },
    }),
  );
  await page.getByRole("button", { name: "Review evidence" }).click();
  await expect(page.locator(".guidance-box [role=alert]")).toContainText(
    "Inference timed out",
  );
  await expect(
    page.getByRole("button", { name: "Continue to checks" }),
  ).toBeDisabled();
  await expect(page.locator(".source-card")).toHaveCount(0);
  await expect(
    page.getByRole("button", { name: "Retry troubleshooting" }),
  ).toBeVisible();
});

test("custom troubleshooting question requires text and stays within API length", async ({
  page,
}) => {
  await page.goto("/troubleshoot");
  const context = page.getByLabel("Additional context", { exact: false });
  await expect(context).toHaveAttribute("maxlength", "1400");
  await page
    .getByRole("button", { name: "Something else", exact: true })
    .click();
  const submit = page.getByRole("button", {
    name: "Review evidence",
    exact: true,
  });
  await expect(submit).toBeDisabled();
  await context.fill("    ");
  await expect(submit).toBeDisabled();
  await context.fill("Spindle vibration after a tool change");
  await expect(submit).toBeEnabled();
});
