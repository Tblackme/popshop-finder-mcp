const { test, expect } = require("playwright/test");
const {
  attachDiagnostics,
  createRoleSession,
  createUserViaApi,
  writeArtifact,
} = require("./smoke-helpers");

test("smoke API endpoints return stable response shapes", async ({ request }, testInfo) => {
  const endpointLog = [];

  const vendor = await createUserViaApi(request, "vendor");

  const eventsResponse = await request.get("/api/events");
  const eventsBody = await eventsResponse.json();
  endpointLog.push({
    endpoint: "/api/events",
    status: eventsResponse.status(),
    ok: eventsBody.ok,
    count: eventsBody.count,
  });

  const usersResponse = await request.get("/api/users");
  const usersBody = await usersResponse.json();
  endpointLog.push({
    endpoint: "/api/users",
    status: usersResponse.status(),
    ok: usersBody.ok,
    authenticated: usersBody.authenticated,
    count: usersBody.count,
    currentUser: usersBody.current_user?.username || "",
  });

  const shopifyResponse = await request.get("/api/shopify/products");
  const shopifyBody = await shopifyResponse.json();
  endpointLog.push({
    endpoint: "/api/shopify/products",
    status: shopifyResponse.status(),
    ok: shopifyBody.ok,
    productCount: Array.isArray(shopifyBody.products) ? shopifyBody.products.length : 0,
  });

  const vendorProductsResponse = await request.get(`/api/vendors/${vendor.username}/products`);
  const vendorProductsBody = await vendorProductsResponse.json();
  endpointLog.push({
    endpoint: `/api/vendors/${vendor.username}/products`,
    status: vendorProductsResponse.status(),
    ok: vendorProductsBody.ok,
    connected: vendorProductsBody.connected,
    productCount: Array.isArray(vendorProductsBody.products) ? vendorProductsBody.products.length : 0,
  });

  await writeArtifact(testInfo, "api-endpoint-log.json", endpointLog);

  expect(eventsResponse.ok()).toBeTruthy();
  expect(Array.isArray(eventsBody.events)).toBeTruthy();
  expect(usersResponse.ok()).toBeTruthy();
  expect(usersBody.current_user?.username).toBe(vendor.username);
  expect(shopifyResponse.ok()).toBeTruthy();
  expect(Array.isArray(shopifyBody.products)).toBeTruthy();
  expect(vendorProductsResponse.ok()).toBeTruthy();
  expect(Array.isArray(vendorProductsBody.products)).toBeTruthy();
});

test("shopper dashboard keeps loading and empty states stable when data is missing", async ({ page }, testInfo) => {
  const diagnostics = attachDiagnostics(page);

  await createRoleSession(page, "shopper");

  await page.route("**/api/shopper-dashboard", async (route) => {
    await new Promise((resolve) => setTimeout(resolve, 250));
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        ok: true,
        role: "shopper",
        user: { id: 1, username: "stubshopper", role: "shopper" },
        events: [],
        featured_vendors: [],
      }),
    });
  });

  await page.route("**/api/saved-markets", async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({ ok: true, saved_markets: [] }),
    });
  });

  await page.route("**/api/shopper/following", async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({ ok: true, vendors: [], events: [], notifications: [] }),
    });
  });

  await page.goto("/shopper-dashboard");
  await expect(page.getByText(/loading your shopper dashboard/i)).toBeVisible();
  await expect(page.locator("[data-shopper-dashboard-app]")).toContainText(
    /no events loaded yet|not following any vendors yet|no favorites yet/i
  );

  await writeArtifact(testInfo, "empty-state-diagnostics.json", diagnostics);

  expect(diagnostics.apiFailures, "Mocked empty-state smoke should not produce failed API calls").toEqual([]);
  expect(diagnostics.pageErrors, "Mocked empty-state smoke should not crash").toEqual([]);
});
