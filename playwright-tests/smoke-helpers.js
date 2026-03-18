const fs = require("fs");

async function writeArtifact(testInfo, name, data) {
  const target = testInfo.outputPath(name);
  fs.mkdirSync(require("path").dirname(target), { recursive: true });
  fs.writeFileSync(target, JSON.stringify(data, null, 2), "utf8");
}

function uniqueId(prefix) {
  const seed = `${Date.now()}${Math.random().toString(16).slice(2, 8)}`;
  return `${prefix}${seed}`.toLowerCase();
}

async function createRoleSession(page, role, overrides = {}) {
  const username = overrides.username || uniqueId(`${role}_`);
  const payload = {
    name: overrides.name || `${role[0].toUpperCase()}${role.slice(1)} User`,
    email: overrides.email || `${username}@example.com`,
    username,
    password: overrides.password || "supersecure123",
    role,
    interests: overrides.interests || "",
    bio: overrides.bio || "",
  };

  const response = await page.context().request.post("/api/auth/signup", {
    data: payload,
  });
  const body = await response.json();
  if (!response.ok() || !body.ok) {
    throw new Error(`Unable to create ${role} test user: ${JSON.stringify(body)}`);
  }
  return body.user;
}

async function createUserViaApi(request, role, overrides = {}) {
  const username = overrides.username || uniqueId(`${role}_`);
  const payload = {
    name: overrides.name || `${role[0].toUpperCase()}${role.slice(1)} User`,
    email: overrides.email || `${username}@example.com`,
    username,
    password: overrides.password || "supersecure123",
    role,
    interests: overrides.interests || "",
    bio: overrides.bio || "",
  };
  const response = await request.post("/api/auth/signup", { data: payload });
  const body = await response.json();
  if (!response.ok() || !body.ok) {
    throw new Error(`Unable to create ${role} API user: ${JSON.stringify(body)}`);
  }
  return body.user;
}

function attachDiagnostics(page) {
  const apiFailures = [];
  const pageErrors = [];
  const consoleErrors = [];

  page.on("response", async (response) => {
    const url = response.url();
    const isAppApi = url.includes("/api/") || url.includes("/consumer/") || url.includes("/markets/search");
    if (!isAppApi || response.ok()) return;

    let body = "";
    try {
      body = await response.text();
    } catch (error) {
      body = `[unavailable: ${error.message}]`;
    }

    apiFailures.push({
      url,
      status: response.status(),
      statusText: response.statusText(),
      body: body.slice(0, 500),
    });
  });

  page.on("pageerror", (error) => {
    pageErrors.push(String(error));
  });

  page.on("console", (message) => {
    if (message.type() === "error") {
      consoleErrors.push(message.text());
    }
  });

  return {
    apiFailures,
    pageErrors,
    consoleErrors,
  };
}

module.exports = {
  attachDiagnostics,
  createRoleSession,
  createUserViaApi,
  uniqueId,
  writeArtifact,
};
