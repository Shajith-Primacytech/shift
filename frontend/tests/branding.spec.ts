import { test, expect } from "@playwright/test";

test("official assets reserve login space and render both palette variants", async ({
  page,
  request,
}) => {
  let release!: () => void;
  const gate = new Promise<void>((resolve) => {
    release = resolve;
  });
  await page.route("**/branding/shift-logo.svg", async (route) => {
    await gate;
    await route.continue();
  });
  await page.goto("/", { waitUntil: "domcontentloaded" });
  await expect(page.getByLabel("Username", { exact: true })).toBeVisible();
  const logo = page.locator(".auth-card .shift-logo");
  const before = await logo.boundingBox();
  release();
  await expect
    .poll(() =>
      logo
        .locator("img")
        .evaluate((i: HTMLImageElement) => i.complete && i.naturalWidth > 0),
    )
    .toBeTruthy();
  expect(await logo.boundingBox()).toEqual(before);
  for (const width of [320, 390, 768, 1440]) {
    await page.setViewportSize({ width, height: 1000 });
    await expect(logo).toBeVisible();
    expect(
      await page.evaluate(
        () => document.documentElement.scrollWidth <= innerWidth,
      ),
    ).toBeTruthy();
  }
  for (const asset of ["shift-logo.svg", "shift-logo-light.svg"]) {
    const response = await request.get(`/branding/${asset}`);
    expect(response.ok()).toBeTruthy();
    expect(response.headers()["content-type"]).toContain("image/svg+xml");
  }
});

test("shared wordmark stays visible and proportionate across routes and mobile navigation", async ({
  page,
}) => {
  await page.goto("/");
  await page.getByLabel("Username", { exact: true }).fill("tech");
  await page
    .getByLabel("Password", { exact: true })
    .fill("browser-test-only-password");
  await page.getByRole("button", { name: "Sign in", exact: true }).click();
  await expect(page.locator(".app-shell")).toBeVisible();
  for (const route of [
    "/",
    "/machines",
    "/machines/CNC-01",
    "/knowledge",
    "/knowledge/capture",
    "/approvals",
    "/troubleshoot",
  ]) {
    await page.goto(route);
    const logo = page.locator(".sidebar .shift-logo img");
    await expect(logo).toBeVisible();
    await expect
      .poll(() =>
        logo.evaluate(
          (i: HTMLImageElement) => i.complete && i.naturalWidth > 0,
        ),
      )
      .toBeTruthy();
    const box = await logo.boundingBox();
    expect(box!.width / box!.height).toBeCloseTo(1264 / 168, 1);
  }
  await page.setViewportSize({ width: 390, height: 844 });
  await page
    .getByRole("button", { name: "Open navigation", exact: true })
    .click();
  await expect
    .poll(() =>
      page
        .locator(".sidebar")
        .evaluate((el) => Math.round(el.getBoundingClientRect().x)),
    )
    .toBe(0);
  const box = await page.locator(".sidebar .shift-logo img").boundingBox();
  expect(box!.x).toBeGreaterThanOrEqual(0);
  expect(box!.x + box!.width).toBeLessThanOrEqual(245);
});
