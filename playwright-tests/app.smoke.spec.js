const { test, expect } = require("playwright/test");
const {
  attachDiagnostics,
  createRoleSession,
  writeArtifact,
} = require("./smoke-helpers");

test("homepage, discover, and vendor dashboard routes load through primary navigation", async ({ page }, testInfo) => {
  const diagnostics = attachDiagnostics(page);
  const routes = [];

  const vendor = await createRoleSession(page, "vendor");
  const homeResponse = await page.goto("/");
  routes.push({
    route: "/",
    status: homeResponse?.status() || 0,
    finalUrl: page.url(),
  });

  await expect(page.getByRole("heading", { name: /run your side of the market in one place/i })).toBeVisible();
  await expect(page.getByRole("link", { name: /i'm a vendor/i })).toBeVisible();
  await expect(page.locator("#vendor-tools")).toContainText(/plan, discover, and commit with confidence/i);
  await expect(page.locator("#organizer-tools")).toContainText(/create listings and keep vendor review moving/i);
  await expect(page.locator("#shopper-tools")).toContainText(/save favorites and follow/i);
  await expect(page.getByRole("link", { name: /open profit planner/i })).toBeVisible();
  await expect(page.getByRole("link", { name: /open organizer dashboard/i })).toBeVisible();
  await expect(page.getByRole("link", { name: /open shopper view/i })).toBeVisible();

  await page.locator('header .nav-links a[href="/discover"]').click();
  await page.waitForURL("**/discover");
  routes.push({ route: "/discover", status: 200, finalUrl: page.url() });
  await expect(page.getByRole("heading", { name: /find events that fit your style/i })).toBeVisible();

  await page.locator('header .nav-links a[href="/dashboard"]').click();
  await page.waitForURL("**/dashboard");
  routes.push({ route: "/dashboard", status: 200, finalUrl: page.url(), user: vendor.username });
  await expect(page.locator("[data-guided-dashboard]")).toContainText(/start planning|resume planning/i);
  await expect(page.locator("[data-guided-dashboard]")).toContainText(/business page studio|shopify and storefront|event plan and route/i);

  await writeArtifact(testInfo, "route-log.json", routes);
  await writeArtifact(testInfo, "page-diagnostics.json", diagnostics);

  expect(diagnostics.apiFailures, "Unexpected API failures while loading primary routes").toEqual([]);
  expect(diagnostics.pageErrors, "Unexpected page errors while loading primary routes").toEqual([]);
});

test("vendor planning flow reaches discover results and records responsive buttons", async ({ page }, testInfo) => {
  const diagnostics = attachDiagnostics(page);
  const buttonLog = [];

  await createRoleSession(page, "vendor");
  await page.goto("/dashboard");
  await expect(page.locator('[data-guided-start="weekend"]')).toBeVisible();

  await page.locator('[data-guided-start="weekend"]').click();
  buttonLog.push({ button: "Start Planning", outcome: "clicked" });

  const earlySteps = [
    { selector: "[data-weekend-travel]", label: "travel" },
    { selector: "[data-weekend-transportation]", label: "transportation" },
    { selector: "[data-weekend-booth]", label: "booth" },
  ];

  for (const step of earlySteps) {
    const choice = page.locator(step.selector).first();
    await expect(choice).toBeVisible();
    await choice.dispatchEvent("click");
    await page.waitForTimeout(350);
    buttonLog.push({ button: step.label, outcome: "answered" });
  }

  await page.evaluate(() => {
    const answers = {
      travel: "30",
      transportation: "none",
      boothFeeComfort: "low",
      setup: "light",
      mustHaves: ["parking"],
      goal: "profit",
      risk: "safe",
    };

    const appState = {
      version: 1,
      journey: {
        answers,
        draft: answers,
        progress: {
          mode: "home",
          weekendStep: 7,
          profitStep: 0,
          eventStep: 0,
        },
        discover: {},
      },
      profiles: [],
      currentProfileId: null,
      selectedEvents: [],
      eventHistory: [],
      shopify: {
        connected: false,
        shop: null,
        updatedAt: "",
        products: [],
        status: "idle",
        error: "",
      },
    };

    localStorage.setItem("vendorAtlasAppState", JSON.stringify(appState));
    localStorage.setItem("vendorAtlasPlanningAnswers", JSON.stringify(answers));
    localStorage.setItem("vendorAtlasPlanningDraft", JSON.stringify(answers));
    localStorage.setItem(
      "vendorAtlasJourneyProgress",
      JSON.stringify({ mode: "home", weekendStep: 7, profitStep: 0, eventStep: 0 })
    );
  });

  await page.goto("/discover?from=planning");
  // Verify the planning-mode discover page loaded (shows planning answer context)
  await expect(page.locator("[data-discover-app]")).toContainText(/we chose these events based on your planning answers|event discovery|0 events ranked/i);
  buttonLog.push({ button: "planning redirect", outcome: page.url() });

  // If the DB has events, also verify the Add to Plan button works
  const addButton = page.locator("[data-add-plan]").first();
  if (await addButton.count()) {
    await addButton.click();
    await expect(addButton).toContainText(/added to plan/i);
    buttonLog.push({ button: "Add to My Plan", outcome: "added" });
  } else {
    buttonLog.push({ button: "Add to My Plan", outcome: "skipped — no events in test DB" });
  }

  await writeArtifact(testInfo, "button-log.json", buttonLog);
  await writeArtifact(testInfo, "vendor-diagnostics.json", diagnostics);

  expect(diagnostics.apiFailures, "Vendor flow should not produce failed API calls").toEqual([]);
  expect(diagnostics.pageErrors, "Vendor flow should not crash").toEqual([]);
});

test("organizer and shopper flows complete core smoke actions", async ({ browser }, testInfo) => {
  const buttonLog = [];
  const baseURL = testInfo.project.use.baseURL;

  const organizerContext = await browser.newContext({ baseURL });
  const organizerPage = await organizerContext.newPage();
  const organizerDiagnostics = attachDiagnostics(organizerPage);
  await createRoleSession(organizerPage, "market");
  await organizerPage.goto("/market-dashboard");
  await expect(organizerPage.locator("[data-market-dashboard-app]")).toContainText(/organizer tools|review applications|listing health/i);
  await organizerPage.fill("#market_event_name", "Playwright Makers Fair");
  await organizerPage.fill("#market_event_city", "Austin");
  await organizerPage.fill("#market_event_state", "TX");
  await organizerPage.fill("#market_event_date", "2026-04-25");
  await organizerPage.fill("#market_event_fee", "125");
  await organizerPage.locator('[data-market-event-form] button[type="submit"]').click();
  await expect(organizerPage.locator("[data-market-dashboard-app]")).toContainText(/ready for applications|playwright makers fair/i);
  buttonLog.push({ flow: "organizer", button: "Create Event", outcome: "created" });
  await organizerPage.locator('[data-edit-market]').first().click();
  await organizerPage.fill("#market_event_name", "Playwright Makers Fair Updated");
  await organizerPage.fill("#market_event_city", "Dallas");
  await organizerPage.locator('[data-market-event-form] button[type="submit"]').click();
  await expect(organizerPage.locator("[data-market-dashboard-app]")).toContainText(/changes are live|playwright makers fair updated/i);
  buttonLog.push({ flow: "organizer", button: "Edit Event", outcome: "updated" });
  const organizerMessageInput = organizerPage.locator("[data-app-message]").first();
  if (await organizerMessageInput.count()) {
    await organizerMessageInput.fill("Bring your best spring collection.");
    await organizerPage.locator('[data-app-action*="Accepted"]').first().click();
    await expect(organizerPage.locator("[data-market-dashboard-app]")).toContainText(/bring your best spring collection|application accepted/i);
    buttonLog.push({ flow: "organizer", button: "Accept with message", outcome: "thread visible" });
  }
  await organizerPage.reload();
  await expect(organizerPage.locator("[data-market-dashboard-app]")).toContainText(/playwright makers fair updated/i);
  buttonLog.push({ flow: "organizer", button: "Edit Event", outcome: "persisted after reload" });

  const vendorContext = await browser.newContext({ baseURL });
  const vendorPage = await vendorContext.newPage();
  const vendor = await createRoleSession(vendorPage, "vendor", {
    interests: "Jewelry",
    bio: "Handmade pieces for weekend markets.",
  });
  await vendorContext.close();

  const shopperContext = await browser.newContext({ baseURL });
  const shopperPage = await shopperContext.newPage();
  const shopperDiagnostics = attachDiagnostics(shopperPage);
  await createRoleSession(shopperPage, "shopper");
  await shopperPage.goto("/shopper-dashboard");
  await expect(shopperPage.locator("[data-shopper-dashboard-app]")).toContainText(/events worth checking out|featured vendors/i);

  const firstEventCard = shopperPage.locator(".dashboard-card").filter({ hasText: "Events worth checking out" }).locator(".atlas-stream-card, .history-item").first();
  const savedEventName = (await firstEventCard.locator("strong").first().textContent())?.trim() || "Event";
  const favoriteButton = firstEventCard.locator("[data-shopper-favorite]").first();
  await favoriteButton.click();
  await expect(shopperPage.locator("[data-shopper-dashboard-app]")).toContainText(/saved to favorites/i);
  await expect(shopperPage.locator(".dashboard-card").filter({ hasText: "Your saved shortlist" })).toContainText(new RegExp(savedEventName, "i"));
  buttonLog.push({ flow: "shopper", button: "Save", outcome: "saved" });
  await shopperPage.reload();
  await expect(shopperPage.locator(".dashboard-card").filter({ hasText: "Your saved shortlist" })).toContainText(new RegExp(savedEventName, "i"));
  buttonLog.push({ flow: "shopper", button: "Save", outcome: "persisted after reload" });

  await shopperPage.goto(`/u/${vendor.username}`);
  const followButton = shopperPage.locator("[data-follow-vendor]");
  await followButton.click();
  await expect(shopperPage.locator("[data-follow-vendor]")).toContainText(/following/i);
  await shopperPage.goto("/shopper-dashboard");
  await expect(shopperPage.locator("[data-shopper-dashboard-app]")).toContainText(new RegExp(vendor.username, "i"));
  buttonLog.push({ flow: "shopper", button: "Follow", outcome: "following" });
  await shopperPage.reload();
  await expect(shopperPage.locator("[data-shopper-dashboard-app]")).toContainText(new RegExp(vendor.username, "i"));
  buttonLog.push({ flow: "shopper", button: "Follow", outcome: "persisted after reload" });

  const eventsResponse = await shopperPage.context().request.get("/api/events");
  const eventsBody = await eventsResponse.json();
  const shopperEventId = eventsBody.events[0].id;
  await shopperPage.goto(`/event-details/${shopperEventId}`);
  const rsvpButton = shopperPage.locator("[data-event-rsvp]");
  await expect(rsvpButton).toBeVisible();
  await rsvpButton.click();
  await shopperPage.goto("/shopper-dashboard");
  await expect(shopperPage.locator("[data-shopper-dashboard-app]")).toContainText(/events you're planning to attend/i);
  buttonLog.push({ flow: "shopper", button: "RSVP", outcome: "saved to dashboard" });
  const mapButton = shopperPage.locator("[data-shopper-map-event]").first();
  if (await mapButton.count()) {
    await mapButton.click();
    await expect(shopperPage).toHaveURL(/\/event-details\//);
    buttonLog.push({ flow: "shopper", button: "Map event", outcome: "opened event detail" });
  }

  await writeArtifact(testInfo, "role-flow-buttons.json", buttonLog);
  await writeArtifact(testInfo, "organizer-diagnostics.json", organizerDiagnostics);
  await writeArtifact(testInfo, "shopper-diagnostics.json", shopperDiagnostics);

  expect(organizerDiagnostics.apiFailures, "Organizer flow should not have failed API calls").toEqual([]);
  expect(organizerDiagnostics.pageErrors, "Organizer flow should not crash").toEqual([]);
  expect(shopperDiagnostics.apiFailures, "Shopper flow should not have failed API calls").toEqual([]);
  expect(shopperDiagnostics.pageErrors, "Shopper flow should not crash").toEqual([]);

  await organizerContext.close();
  await shopperContext.close();
});

test("public vendor profile keeps storefront products stable across empty and connected states", async ({ browser }, testInfo) => {
  const diagnostics = [];
  const baseURL = testInfo.project.use.baseURL;

  const vendorContext = await browser.newContext({ baseURL });
  const vendorPage = await vendorContext.newPage();
  const vendor = await createRoleSession(vendorPage, "vendor", {
    interests: "Candles",
    bio: "Small-batch candles and home scent goods.",
  });
  await vendorContext.close();

  const shopperContext = await browser.newContext({ baseURL });
  const shopperPage = await shopperContext.newPage();
  const shopperDiagnostics = attachDiagnostics(shopperPage);
  await createRoleSession(shopperPage, "shopper");

  await shopperPage.route(`**/api/vendors/${vendor.username}/products`, async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        ok: true,
        connected: true,
        shop: "demo-shop.myshopify.com",
        message: "Products are ready to browse.",
        products: [
          {
            id: "gid://shopify/Product/1",
            name: "Amber Candle",
            handle: "amber-candle",
            image: "https://cdn.example.com/candle.jpg",
            price: 24,
            product_url: "https://demo-shop.myshopify.com/products/amber-candle",
          },
        ],
      }),
    });
  });

  await shopperPage.goto(`/u/${vendor.username}`);
  await expect(shopperPage.locator("[data-profile-app]")).toContainText(/shop products|inventory highlights/i);
  await expect(shopperPage.locator("[data-profile-app]")).toContainText(/amber candle/i);
  await expect(shopperPage.getByRole("link", { name: /buy from vendor/i })).toBeVisible();
  diagnostics.push({ state: "connected_products", url: shopperPage.url() });

  await shopperPage.unroute(`**/api/vendors/${vendor.username}/products`);
  await shopperPage.route(`**/api/vendors/${vendor.username}/products`, async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        ok: true,
        connected: false,
        shop: "",
        message: "This vendor has not connected Shopify products yet.",
        products: [],
      }),
    });
  });

  await shopperPage.reload();
  await expect(shopperPage.locator("[data-profile-app]")).toContainText(/no products connected yet/i);
  diagnostics.push({ state: "empty_products", url: shopperPage.url() });

  await writeArtifact(testInfo, "vendor-storefront-profile.json", diagnostics);
  await writeArtifact(testInfo, "vendor-storefront-diagnostics.json", shopperDiagnostics);

  expect(shopperDiagnostics.apiFailures, "Public storefront profile should not have failed API calls").toEqual([]);
  expect(shopperDiagnostics.pageErrors, "Public storefront profile should not crash").toEqual([]);

  await shopperContext.close();
});
