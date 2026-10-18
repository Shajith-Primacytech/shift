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
async function voice(page: Page) {
  await page.goto("/knowledge/capture");
  await page.getByRole("tab", { name: "Voice", exact: true }).click();
}
async function fakeRecorder(page: Page, mode = "normal") {
  await page.addInitScript(
    ({ mode }) => {
      const track = new EventTarget() as EventTarget & {
        readyState: string;
        stop: () => void;
      };
      track.readyState = "live";
      track.stop = () => {
        track.readyState = "ended";
      };
      const stream = { getTracks: () => [track] };
      navigator.mediaDevices.getUserMedia = async () =>
        stream as unknown as MediaStream;
      class Recorder {
        state = "inactive";
        mimeType = "audio/webm";
        ondataavailable: ((event: { data: Blob }) => void) | null = null;
        onstop: (() => void) | null = null;
        onerror: (() => void) | null = null;
        constructor() {
          (
            window as unknown as { voiceTestRecorder: Recorder }
          ).voiceTestRecorder = this;
        }
        start() {
          this.state = "recording";
          track.readyState = "live";
        }
        stop() {
          this.state = "inactive";
          this.ondataavailable?.({
            data: new Blob(mode === "empty" ? [] : ["synthetic-test-audio"], {
              type: this.mimeType,
            }),
          });
          queueMicrotask(() => this.onstop?.());
        }
      }
      Object.defineProperty(window, "MediaRecorder", {
        value: Recorder,
        configurable: true,
      });
    },
    { mode },
  );
}
async function record(page: Page) {
  await page
    .getByRole("button", { name: "Start recording", exact: true })
    .click();
  await expect(
    page.getByRole("button", { name: "Stop recording", exact: true }),
  ).toBeVisible();
  await page
    .getByRole("button", { name: "Stop recording", exact: true })
    .click();
  await expect(page.locator(".voice-box audio")).toHaveAttribute(
    "src",
    /^blob:/,
  );
}

test("reviewed voice transcript preserves existing text, uses Gemma and stays approval gated", async ({
  page,
}) => {
  await fakeRecorder(page);
  await signIn(page, "voice-tech");
  await voice(page);
  await page.getByLabel("Observation title").fill("Reviewed voice knowledge");
  await page.getByLabel("Symptom or maintenance context").fill("Vibration");
  await page
    .getByLabel("Written observation")
    .fill("Existing technician note remains intact.");
  await record(page);
  await page
    .getByRole("button", { name: "Transcribe recording", exact: true })
    .click();
  const transcript = page.getByRole("textbox", {
    name: "Reviewed voice transcript",
    exact: true,
  });
  await expect(transcript).toHaveValue(
    "Synthetic vibration after a tool change. The root cause is not confirmed.",
  );
  await expect(page.getByLabel("Written observation")).toHaveValue(
    "Existing technician note remains intact.",
  );
  const edited =
    "Reviewed synthetic vibration. Cause remains unconfirmed; inspection has not been performed.";
  await transcript.fill(edited);
  await page
    .getByRole("button", { name: "Use Transcript", exact: true })
    .click();
  const combined =
    "Existing technician note remains intact.\n\nReviewed voice transcript:\n" +
    edited;
  await expect(page.getByLabel("Written observation")).toHaveValue(combined);
  await expect(
    page.getByRole("button", { name: "Use Transcript", exact: true }),
  ).toBeDisabled();
  const axe = await new AxeBuilder({ page })
    .withTags(["wcag2a", "wcag2aa", "wcag21aa"])
    .analyze();
  expect(axe.violations).toEqual([]);
  for (const width of [390, 768, 1440]) {
    await page.setViewportSize({ width, height: 1000 });
    expect(
      await page.evaluate(
        () => document.documentElement.scrollWidth <= innerWidth,
      ),
    ).toBeTruthy();
  }
  await page.getByRole("heading", { name: "What did you notice?" }).click();
  await page.evaluate(() => window.scrollTo(0, 0));
  await page.screenshot({
    path: "test-results/voice-transcript-review.png",
    fullPage: true,
  });
  const request = page.waitForRequest("**/api/v1/capture/structure");
  await page
    .getByRole("button", { name: "Structure with AI", exact: true })
    .click();
  expect((await request).postDataJSON().content).toBe(combined);
  await expect(
    page.getByRole("textbox", { name: /^Technician observations/ }),
  ).toHaveValue(combined);
  await page.getByRole("checkbox", { name: /I reviewed and edited/ }).check();
  await page.getByRole("button", { name: "Submit for review" }).click();
  await expect(
    page.getByRole("heading", { name: "Saved for supervisor review" }),
  ).toBeVisible();
  await page.getByRole("link", { name: "Open review queue" }).click();
  await page.getByRole("button", { name: /Reviewed voice knowledge/ }).click();
  await expect(page.locator(".observation-content")).toHaveText(combined);
  await expect(page.locator(".review-detail .badge")).toContainText("Pending");
  await expect(
    page.getByRole("button", { name: "Approve for library" }),
  ).toHaveCount(0);
  await expect(
    page.getByRole("link", { name: /Download voice-observation/ }),
  ).toBeVisible();
  await page.getByRole("button", { name: "Sign out" }).click();
  await signIn(page, "super");
  await page.goto("/approvals");
  await page.getByRole("button", { name: /Reviewed voice knowledge/ }).click();
  await expect(page.locator(".observation-content")).toHaveText(combined);
  await page.getByRole("button", { name: "Approve for library" }).click();
  await page.goto("/knowledge?q=Reviewed%20voice%20knowledge");
  await expect(page.locator(".knowledge-card")).toHaveCount(1);
});

for (const failure of ["NotAllowedError", "NotFoundError"]) {
  test(`microphone ${failure} is explicit and manual capture survives`, async ({
    page,
  }) => {
    await page.addInitScript(
      ({ failure }) => {
        navigator.mediaDevices.getUserMedia = async () => {
          throw new DOMException("test", failure);
        };
      },
      { failure },
    );
    await signIn(page);
    await voice(page);
    await page
      .getByRole("button", { name: "Start recording", exact: true })
      .click();
    await expect(page.locator(".voice-box [role=alert]")).toContainText(
      failure === "NotAllowedError"
        ? "access was denied"
        : "No microphone was detected",
    );
    await expect(
      page.getByRole("button", { name: "Submit for review" }),
    ).toBeEnabled();
  });
}

test("unsupported recording API, empty recording and interruption have no fabricated transcript", async ({
  page,
}) => {
  await page.addInitScript(() => {
    Object.defineProperty(window, "MediaRecorder", {
      value: undefined,
      configurable: true,
    });
  });
  await signIn(page);
  await voice(page);
  await page
    .getByRole("button", { name: "Start recording", exact: true })
    .click();
  await expect(page.locator(".voice-box [role=alert]")).toContainText(
    "Recording is unavailable",
  );
});

test("empty recording and interruption do not fabricate a transcript", async ({
  page,
}) => {
  await fakeRecorder(page, "empty");
  await signIn(page);
  await voice(page);
  await page
    .getByRole("button", { name: "Start recording", exact: true })
    .click();
  await page
    .getByRole("button", { name: "Stop recording", exact: true })
    .click();
  await expect(page.locator(".voice-box [role=alert]")).toContainText(
    "Recording is empty",
  );
  await expect(
    page.getByRole("textbox", {
      name: "Reviewed voice transcript",
      exact: true,
    }),
  ).toHaveCount(0);
  await page
    .getByRole("button", { name: "Start recording", exact: true })
    .click();
  await page.evaluate(() => {
    (
      window as unknown as { voiceTestRecorder: { onerror: () => void } }
    ).voiceTestRecorder.onerror();
  });
  await expect(page.locator(".voice-box [role=alert]")).toContainText(
    "Recording was interrupted",
  );
  await expect(
    page.getByRole("button", { name: "Submit for review" }),
  ).toBeEnabled();
});

test("two-minute limit stops recording; leaving Voice stops microphone capture", async ({
  page,
}) => {
  await fakeRecorder(page);
  await signIn(page);
  await voice(page);
  await page.clock.install();
  await page
    .getByRole("button", { name: "Start recording", exact: true })
    .click();
  await page.clock.fastForward(120001);
  await expect(
    page.getByRole("button", { name: "Record again", exact: true }),
  ).toBeVisible();
  await expect(
    page.getByText("Two-minute recording limit reached.", { exact: false }),
  ).toBeVisible();
  await page.getByRole("button", { name: "Record again", exact: true }).click();
  await page.getByRole("tab", { name: "Write", exact: true }).click();
  await page.getByRole("tab", { name: "Voice", exact: true }).click();
  await expect(
    page.getByRole("button", { name: "Record again", exact: true }),
  ).toBeVisible();
  await expect(
    page.getByRole("button", { name: "Stop recording", exact: true }),
  ).toHaveCount(0);
  await page.getByRole("button", { name: "Record again", exact: true }).click();
  await page.evaluate(() => {
    Object.defineProperty(document, "visibilityState", {
      value: "hidden",
      configurable: true,
    });
    document.dispatchEvent(new Event("visibilitychange"));
  });
  await expect(
    page.getByRole("button", { name: "Record again", exact: true }),
  ).toBeVisible();
  await expect(
    page.getByText("Recording stopped when the page was hidden.", {
      exact: false,
    }),
  ).toBeVisible();
});

for (const failure of ["server", "network"]) {
  test(`transcription ${failure} failure preserves audio and written text`, async ({
    page,
  }) => {
    await fakeRecorder(page);
    await signIn(page);
    await voice(page);
    await page
      .getByLabel("Written observation")
      .fill("Existing written observation.");
    await record(page);
    let calls = 0;
    await page.route("**/api/v1/capture/transcribe", (route) => {
      calls++;
      return failure === "network"
        ? route.abort()
        : route.fulfill({
            status: 503,
            json: { detail: "Local transcription failed." },
          });
    });
    await page
      .getByRole("button", { name: "Transcribe recording", exact: true })
      .click();
    await expect(page.locator(".voice-box [role=alert]")).toContainText(
      failure === "network"
        ? "Cannot reach SHIFT"
        : "Local transcription failed",
    );
    await expect(page.getByLabel("Written observation")).toHaveValue(
      "Existing written observation.",
    );
    await expect(page.locator(".voice-box audio")).toBeVisible();
    await expect(
      page.getByRole("button", { name: "Submit for review" }),
    ).toBeEnabled();
    expect(calls).toBe(1);
  });
}

test("unprepared local engine is disclosed while recording remains available", async ({
  page,
}) => {
  await page.route("**/api/v1/capture/voice/status", (route) =>
    route.fulfill({
      json: {
        available: false,
        provider: "Local CPU · faster-whisper",
        model: "Systran/faster-whisper-tiny.en",
        language: "en",
        max_duration_seconds: 120,
      },
    }),
  );
  await fakeRecorder(page);
  await signIn(page);
  await voice(page);
  await record(page);
  await expect(
    page.getByRole("button", { name: "Transcribe recording", exact: true }),
  ).toBeDisabled();
  await expect(
    page.getByText("Local transcription unavailable.", { exact: false }),
  ).toBeVisible();
  await expect(
    page.getByRole("button", { name: "Submit for review" }),
  ).toBeEnabled();
});

test("unavailable configured model and failed execution never imply a returned Gemma model", async ({
  page,
}) => {
  await page.route("**/api/v1/ai/configuration", (route) =>
    route.fulfill({
      json: {
        capture: {
          provider: "AMD Token Factory",
          requested_model: "Gemma-4-31B-IT",
          developer: "Google",
          status: "unavailable",
        },
        troubleshooting: {
          provider: "AMD Token Factory",
          requested_model: null,
          status: "unavailable",
        },
      },
    }),
  );
  await page.route("**/api/v1/capture/structure", (route) =>
    route.fulfill({
      status: 503,
      json: {
        detail: "AMD is unavailable; manual capture is available.",
        execution: {
          provider: "AMD Token Factory",
          requested_model: "Gemma-4-31B-IT",
          returned_model: null,
          model_id: "Gemma-4-31B-IT",
          requested_at: "2026-10-17T12:00:00Z",
          latency_ms: 5,
          usage: null,
          status: "failure",
          http_status: 503,
          error_code: "http",
        },
      },
    }),
  );
  await signIn(page);
  await page.goto("/knowledge/capture");
  const model = page.getByRole("region", {
    name: "Knowledge structuring model",
  });
  await expect(model).toContainText("Unavailable · no inference requested");
  await expect(model.locator("details")).toHaveCount(0);
  await page.getByLabel("Observation title").fill("Model unavailable test");
  await page.getByLabel("Symptom or maintenance context").fill("Vibration");
  await page
    .getByLabel("Written observation")
    .fill("Synthetic written observation remains unchanged.");
  await page
    .getByRole("button", { name: "Structure with AI", exact: true })
    .click();
  await expect(model).toContainText("Execution failure");
  await expect(model).toContainText("Returned model not recorded");
  await expect(
    model.getByText("Powered by Google Gemma", { exact: true }),
  ).toHaveCount(0);
  await model
    .getByText("AI Execution Details · AMD Token Factory · failure")
    .click();
  await expect(model).toContainText("Requested model");
  await expect(model).toContainText("Gemma-4-31B-IT");
  await expect(
    page.getByRole("button", { name: "Submit for review" }),
  ).toBeEnabled();
});

test("permission granted after leaving Voice releases the microphone without recording", async ({
  page,
}) => {
  await fakeRecorder(page);
  await page.addInitScript(() => {
    navigator.mediaDevices.getUserMedia = () =>
      new Promise((resolve) => {
        (
          window as unknown as { resolveVoicePermission: typeof resolve }
        ).resolveVoicePermission = resolve;
      });
  });
  await signIn(page);
  await voice(page);
  await page
    .getByRole("button", { name: "Start recording", exact: true })
    .click();
  await expect(
    page.getByRole("button", { name: "Requesting microphone…", exact: true }),
  ).toBeVisible();
  await page.getByRole("tab", { name: "Write", exact: true }).click();
  await page.evaluate(() => {
    const track = {
      readyState: "live",
      stop() {
        this.readyState = "ended";
      },
    };
    (
      window as unknown as { releasedVoiceTrack: typeof track }
    ).releasedVoiceTrack = track;
    (
      window as unknown as {
        resolveVoicePermission: (value: MediaStream) => void;
      }
    ).resolveVoicePermission({
      getTracks: () => [track],
    } as unknown as MediaStream);
  });
  await expect
    .poll(() =>
      page.evaluate(
        () =>
          (window as unknown as { releasedVoiceTrack: { readyState: string } })
            .releasedVoiceTrack.readyState,
      ),
    )
    .toBe("ended");
  await expect(
    page.getByRole("button", { name: "Submit for review" }),
  ).toBeEnabled();
  await page.getByRole("tab", { name: "Voice", exact: true }).click();
  await expect(
    page.getByRole("button", { name: "Start recording", exact: true }),
  ).toBeVisible();
  await expect(page.locator(".voice-box audio")).toHaveCount(0);
});
