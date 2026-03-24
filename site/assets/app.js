const vendorScenarios = {
  farmer: {
    title: "Farmers Market Vendor",
    text: "A produce vendor can filter nearby weekend markets by city, compare traffic estimates, and keep a running shortlist of applications inside the dashboard.",
  },
  jewelry: {
    title: "Handmade Jewelry Seller",
    text: "A jewelry maker searches upcoming craft fairs, saves the ones accepting handmade goods, and tracks deadlines and organizer links in one private dashboard.",
  },
  vintage: {
    title: "Vintage Clothing Seller",
    text: "A vintage reseller compares booth cost against expected traffic, then prioritizes markets with stronger repeat-event history and more fashion-friendly audiences.",
  },
  foodtruck: {
    title: "Food Truck Vendor",
    text: "Sarah runs a taco truck and wants high-traffic weekend markets nearby. She filters events by city and vendor type, then saves three promising festivals to revisit later.",
  },
  artist: {
    title: "Local Artist",
    text: "An illustrator uses Vendor Atlas to find art walks, maker weekends, and pop-up events that match her style, price range, and local travel radius.",
  },
  boutique: {
    title: "Pop-Up Boutique Owner",
    text: "A boutique owner uses the finder to shortlist stylish city markets, then shares the best options with their small team from the dashboard.",
  },
};

const weekdayLabels = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"];
const monthLabels = [
  "January", "February", "March", "April", "May", "June",
  "July", "August", "September", "October", "November", "December",
];
const dashboardTracker = {
  summary: {
    rankedMarkets: 5,
    budgetEvents: 17,
    formulas: 57,
  },
  suggestedPlan: {
    title: "Suggested plan",
    headline: "Start with two high-confidence applications, then use the budget tracker to protect margin.",
    items: [
      "Apply first to the best-fit weekend markets with the strongest traffic-to-fee balance.",
      "Track projected revenue before each event, then log actual sales and units sold after the booth closes.",
      "Use the criteria guide as a final filter before paying any nonrefundable booth fee.",
    ],
  },
  tabs: [
    {
      name: "Application Calendar",
      icon: "📅",
      blurb: "All 5 ranked markets with status badges, booth fees, traffic, vendor counts, priority stars, and planning notes.",
      highlights: ["Apply Now", "Watch", "Research"],
      footnote: "Best for quick deadline scanning and market-by-market follow-up.",
      tier: "primary",
    },
    {
      name: "Booth Budget Tracker",
      icon: "💰",
      blurb: "17 pre-filled 2026 events from April through December with booth costs, extra spend, projected revenue, actual revenue, units sold, net profit, and ROI.",
      highlights: ["Blue cells = editable inputs", "Yellow cells = post-event fields", "Summary bar auto-totals"],
      footnote: "Designed for before-and-after event analysis without rebuilding your sheet each time.",
      tier: "primary",
    },
    {
      name: "Selection Criteria",
      icon: "📋",
      blurb: "A quick-reference cheat sheet for booth price ranges, traffic signals, and warning signs pulled into one decision guide.",
      highlights: ["Booth price guide", "Traffic benchmarks", "Warning sign checklist"],
      footnote: "Keeps the decision rules beside the tracker instead of spread across notes.",
      tier: "support",
    },
  ],
};
const LOCAL_TRACKER_STORAGE_KEY = "vendorAtlasLocalTrackerDraft";

function escapeHtml(s) {
  if (s == null) return "";
  return String(s)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}

function formatMoney(value) {
  if (value === null || value === undefined || value === "") return "TBD";
  return new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: "USD",
    maximumFractionDigits: 0,
  }).format(Number(value));
}

function renderMetricGrid(items) {
  return `
    <div class="atlas-metric-grid">
      ${items.map((item) => `
        <div class="atlas-metric-card" data-tone="${escapeHtml(item.tone || "default")}">
          <span class="atlas-metric-label">${escapeHtml(item.label || "")}</span>
          <strong>${item.value || "0"}</strong>
          ${item.note ? `<div class="atlas-stream-note">${escapeHtml(item.note)}</div>` : ""}
        </div>
      `).join("")}
    </div>
  `;
}

function renderHighlightCard(title, body) {
  return `
    <div class="atlas-highlight">
      <strong>${escapeHtml(title || "")}</strong>
      <div class="atlas-stream-note">${escapeHtml(body || "")}</div>
    </div>
  `;
}

function renderStreamList(items, renderItem) {
  return `<div class="atlas-stream">${items.map(renderItem).join("")}</div>`;
}

async function api(path, options = {}) {
  const response = await fetch(path, {
    credentials: "include",
    headers: {
      "Content-Type": "application/json",
      ...(options.headers || {}),
    },
    ...options,
  });

  const contentType = response.headers.get("content-type") || "";
  const data = contentType.includes("application/json") ? await response.json() : {};
  if (!response.ok) {
    const error = new Error(data.error || "Request failed");
    error.status = response.status;
    error.data = data;
    throw error;
  }
  return data;
}

function attachButtonPress(selector, root = document) {
  root.querySelectorAll(selector).forEach((el) => {
    el.addEventListener("mousedown", () => el.setAttribute("data-pressed", "true"));
    ["mouseup", "mouseleave", "blur"].forEach((ev) => {
      el.addEventListener(ev, () => el.removeAttribute("data-pressed"));
    });
  });
}

let toastTimer = null;
function ensureToast() {
  let el = document.getElementById("toast");
  if (!el) {
    el = document.createElement("div");
    el.id = "toast";
    el.className = "toast";
    el.setAttribute("aria-live", "polite");
    document.body.appendChild(el);
  }
  return el;
}

function showToast(message, tone) {
  const el = ensureToast();
  el.textContent = message || "";
  el.className = `toast show${tone ? ` ${tone}` : ""}`;
  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => {
    el.className = "toast";
  }, 2200);
}

function setInlineStatus(elementId, message, tone) {
  const el = document.getElementById(elementId);
  if (!el) return;
  if (!message) {
    el.textContent = "";
    el.className = "inline-status";
    el.style.display = "none";
    return;
  }
  el.textContent = message;
  el.className = `inline-status ${tone || ""}`.trim();
  el.style.display = "block";
}

function shopifyLoadData() {
  window.shopifyLoading = true;
  setInlineStatus("shopify-inline-status", "Loading store status…", "");
  setShopifySnapshot({ status: "loading", error: "" });
  return api("/api/shopify/me", { method: "GET" })
    .then((data) => {
      window.shopifyConnected = data.connected === true;
      window.shopifyShop = data.shop || null;
      window.shopifyUpdatedAt = data.updated_at || "";
      window.shopifyOauthAvailable = data.oauth_available === true;
      setShopifySnapshot({
        connected: window.shopifyConnected,
        shop: window.shopifyShop,
        updatedAt: window.shopifyUpdatedAt,
        oauthAvailable: window.shopifyOauthAvailable,
        status: "ready",
        error: "",
      });
      if (window.shopifyConnected) {
        return api("/api/shopify/products", { method: "GET" });
      }
      return { ok: true, products: [] };
    })
    .then((data) => {
      window.shopifyProducts = Array.isArray(data.products) ? data.products : [];
      window.shopifyLoading = false;
      setShopifySnapshot({
        connected: window.shopifyConnected,
        shop: window.shopifyShop,
        updatedAt: window.shopifyUpdatedAt,
        oauthAvailable: window.shopifyOauthAvailable,
        products: window.shopifyProducts,
        status: "ready",
        error: "",
      });
      setInlineStatus("shopify-inline-status", "", "");
      return { products: window.shopifyProducts };
    })
    .catch((error) => {
      const snapshot = getShopifySnapshot();
      window.shopifyConnected = Boolean(snapshot.connected);
      window.shopifyShop = snapshot.shop || null;
      window.shopifyUpdatedAt = snapshot.updatedAt || "";
      window.shopifyProducts = Array.isArray(snapshot.products) ? snapshot.products : [];
      window.shopifyLoading = false;
      setShopifySnapshot({
        ...snapshot,
        status: "error",
        error: error?.message || "We couldn't load Shopify right now. Try again.",
      });
      setInlineStatus("shopify-inline-status", "We couldn't load Shopify right now. Try again.", "error");
      return { products: window.shopifyProducts, error: error?.message || "Request failed" };
    });
}


function shopifyConnectFromInput(inputId = "shopify-shop-input") {
  const input = document.getElementById(inputId);
  let shop = input && input.value ? input.value.trim() : "";
  // Strip protocol and trailing slashes
  shop = shop.replace(/^https?:\/\//i, "").replace(/\/+$/, "");
  // Strip .myshopify.com suffix so server can re-add it cleanly
  shop = shop.replace(/\.myshopify\.com$/i, "").replace(/^www\./i, "").replace(/^admin\./i, "");
  if (!shop) {
    showToast("Enter your store name (e.g. mystore)", "error");
    return;
  }
  window.location.href = "/api/shopify/connect?shop=" + encodeURIComponent(shop);
}

function shopifySyncAndRefresh(onDone) {
  window.shopifyLoading = true;
  setInlineStatus("shopify-inline-status", "Syncing products…", "");
  setShopifySnapshot({ status: "loading", error: "" });
  api("/api/shopify/sync", { method: "POST", body: JSON.stringify({}) })
    .then((data) => {
      showToast(data.synced ? `Synced ${data.synced} products` : "Synced products", "success");
      return shopifyLoadData().then(() => {
        if (typeof onDone === "function") onDone();
      });
    })
    .catch((error) => {
      window.shopifyLoading = false;
      const message = error?.message || "Sync failed. Please try again.";
      showToast(message, "error");
      setShopifySnapshot({ status: "error", error: message });
      setInlineStatus("shopify-inline-status", message, "error");
      if (typeof onDone === "function") onDone();
    });
}

function shopifyDisconnectSoft(onDone) {
  if (!window.shopifyDisconnectArmed) {
    window.shopifyDisconnectArmed = true;
    showToast("Click Disconnect again to confirm", "error");
    setTimeout(() => {
      window.shopifyDisconnectArmed = false;
    }, 2800);
    return;
  }
  window.shopifyDisconnectArmed = false;
  fetch("/api/shopify/disconnect", { method: "POST", credentials: "include" })
    .then((r) => r.json())
    .then((data) => {
      if (data.ok) {
        window.shopifyConnected = false;
        window.shopifyProducts = [];
        window.shopifyShop = null;
        window.shopifyUpdatedAt = "";
        setShopifySnapshot({
          connected: false,
          shop: null,
          updatedAt: "",
          products: [],
          status: "ready",
          error: "",
        });
        setInlineStatus("shopify-inline-status", "", "");
        showToast("Store disconnected", "success");
        if (typeof onDone === "function") onDone();
      }
    })
    .catch((error) => {
      const message = error?.message || "We couldn't disconnect your store right now.";
      setShopifySnapshot({ status: "error", error: message });
      setInlineStatus("shopify-inline-status", message, "error");
      showToast(message, "error");
      if (typeof onDone === "function") onDone();
    });
}

async function getAuthState() {
  try {
    return await api("/api/auth/me", { method: "GET" });
  } catch {
    return { authenticated: false, user: null };
  }
}

function setStatus(element, message, type = "") {
  if (!element) return;
  element.textContent = message;
  element.className = `status${type ? ` ${type}` : ""}`;
}

function renderRecurrencePill(recurrence) {
  if (!recurrence) return "";
  if (recurrence.is_recurring) {
    const repeatCount = recurrence.repeat_count ? ` · ${recurrence.repeat_count} dates` : "";
    return `<span class="pill pill-recurring">${recurrence.label}${repeatCount}</span>`;
  }
  return `<span class="pill pill-oneoff">One-off</span>`;
}

function dashboardPathForRole(role) {
  if (role === "market") return "/market-dashboard";
  if (role === "shopper") return "/shopper-dashboard";
  return "/dashboard";
}

function eventDetailPath(eventId) {
  if (!eventId) return "";
  return `/event-details/${encodeURIComponent(String(eventId))}`;
}

function renderAuthNav(auth) {
  const desktop = document.querySelector("[data-auth-nav]");
  const navDesktop = document.querySelector(".nav-links");
  const navMobile = document.querySelector("[data-mobile-drawer]");

  if (!auth.authenticated) {
    // ── Logged-out: simplified public navigation ────────────────────────────
    const _p = location.pathname.replace(/\/$/, "") || "/";
    const _a = (href, label) =>
      `<a href="${href}"${_p === href ? ' class="active"' : ""}>${label}</a>`;
    if (navDesktop) {
      navDesktop.innerHTML =
        _a("/", "Home") +
        `<a href="/#vendors">Vendors</a>` +
        `<a href="/#shoppers">Shoppers</a>` +
        `<a href="/#organizers">Organizers</a>` +
        _a("/feed", "Feed") +
        _a("/community", "Community");
    }
    if (navMobile) {
      navMobile.innerHTML =
        `<a href="/">Home</a>` +
        `<a href="/#vendors">Vendors</a>` +
        `<a href="/#shoppers">Shoppers</a>` +
        `<a href="/#organizers">Organizers</a>` +
        `<a href="/feed">Feed</a>` +
        `<a href="/community">Community</a>` +
        `<div data-mobile-auth-nav></div>`;
    }
    const mobileAuth = document.querySelector("[data-mobile-auth-nav]");
    [desktop, mobileAuth].filter(Boolean).forEach((node) => {
      node.innerHTML =
        `<a href="/signin">Sign In</a>` +
        `<a class="btn btn-primary" href="/signup">Create Account</a>`;
    });
    return;
  }

  // ── Logged-in: role-based navigation ───────────────────────────────────────
  const role = auth.user?.role || "vendor";
  const dashboardPath = dashboardPathForRole(role);
  const dashboardLabel = role === "market" ? "Organizer" : role === "shopper" ? "Shopper" : "Dashboard";
  const mobile = document.querySelector("[data-mobile-auth-nav]");
  const nodes = [desktop, mobile].filter(Boolean);

  function syncRoleNav(node, isMobile = false) {
    if (!node) return;
    const links = [...node.querySelectorAll("a")];
    links.forEach((link) => {
      const href = link.getAttribute("href") || "";
      if (href === "/dashboard" || href === "/shopper-dashboard" || href === "/market-dashboard") {
        link.setAttribute("href", dashboardPath);
        link.textContent = role === "shopper" ? "Shopper" : role === "market" ? "Organizer" : "Plan";
        link.classList.toggle("active", window.location.pathname === dashboardPath);
      }
      if (href === "/final-plan") {
        if (role === "vendor") {
          link.textContent = "Profit";
          link.style.display = "";
        } else {
          link.style.display = "none";
        }
      }
    });
    if (isMobile) {
      const extraVendorLink = links.find((link) => (link.getAttribute("href") || "") === "/final-plan");
      if (extraVendorLink && role !== "vendor") extraVendorLink.style.display = "none";
    }
  }

  syncRoleNav(navDesktop);
  syncRoleNav(navMobile, true);

  nodes.forEach((node) => {
    node.innerHTML = `
      <a href="${dashboardPath}">${dashboardLabel}</a>
      <a href="/u/${encodeURIComponent(auth.user.username || "")}">@${escapeHtml(auth.user.username || "profile")}</a>
      <button class="linklike" data-logout-button type="button">Logout</button>
    `;
  });

  document.querySelectorAll("[data-logout-button]").forEach((button) => {
    button.addEventListener("click", async () => {
      await api("/api/auth/logout", { method: "POST", body: JSON.stringify({}) });
      window.location.href = "/";
    });
  });
}

function setupAuthGuard(auth) {
  if (auth.authenticated) return;
  const protectedPaths = [
    "/my-shop", "/messages", "/settings",
    "/market-analytics", "/market-applications",
  ];
  const path = location.pathname;
  const isProtected = protectedPaths.some(
    (p) => path === p || path.startsWith(p + "/")
  );
  if (isProtected) {
    window.location.href = "/signin?next=" + encodeURIComponent(path);
  }
}

function setupPreviewGate(auth) {
  if (auth.authenticated) return;

  function showJoinPrompt() {
    if (document.getElementById("va-preview-prompt")) return;
    const el = document.createElement("div");
    el.id = "va-preview-prompt";
    el.innerHTML = [
      '<div style="position:fixed;inset:0;background:rgba(0,0,0,.55);z-index:9998;display:flex;align-items:center;justify-content:center;" id="va-preview-backdrop">',
      '<div style="background:#fff;border-radius:20px;padding:36px 32px;max-width:360px;width:90%;text-align:center;box-shadow:0 8px 40px rgba(0,0,0,.28);">',
      '<div style="font-size:2.2rem;margin-bottom:14px;">👋</div>',
      '<h3 style="margin:0 0 10px;font-size:1.15rem;color:#132623;">Create an account to join the conversation.</h3>',
      '<p style="color:#54645d;margin:0 0 22px;font-size:.9rem;line-height:1.5;">Sign up free to like posts, join groups, message vendors, and save events.</p>',
      '<div style="display:flex;gap:10px;justify-content:center;flex-wrap:wrap;">',
      '<a href="/signup" style="background:#0f766e;color:#fff;padding:11px 22px;border-radius:99px;font-weight:700;font-size:.9rem;text-decoration:none;">Create Account</a>',
      '<a href="/signin" style="background:#f4efe6;color:#132623;padding:11px 22px;border-radius:99px;font-weight:700;font-size:.9rem;text-decoration:none;border:1px solid rgba(19,38,35,0.14);">Sign In</a>',
      '</div>',
      '<button onclick="document.getElementById(\'va-preview-prompt\').remove()" style="margin-top:18px;background:none;border:none;color:#54645d;cursor:pointer;font-size:.85rem;text-decoration:underline;">Continue browsing</button>',
      '</div></div>',
    ].join("");
    // Close on backdrop click
    el.querySelector("#va-preview-backdrop").addEventListener("click", (e) => {
      if (e.target === e.currentTarget) el.remove();
    });
    document.body.appendChild(el);
  }

  // ── Community preview ───────────────────────────────────────────────────────
  const communityLanding = document.getElementById("communityLanding");
  if (communityLanding) {
    const banner = document.createElement("div");
    banner.className = "preview-mode-banner";
    banner.innerHTML =
      `<span>👀 <strong>Preview mode</strong> — browsing is open.</span>` +
      `<a href="/signup" class="preview-mode-cta">Create an account</a>` +
      `<span>to join groups and post.</span>`;
    const main = communityLanding.querySelector("main");
    if (main) main.insertBefore(banner, main.firstChild);

    const groupGrid = document.getElementById("groupGrid");
    if (groupGrid) {
      groupGrid.addEventListener("click", (e) => {
        if (e.target.closest(".community-group-card")) {
          e.stopPropagation();
          showJoinPrompt();
        }
      }, true);
    }
  }

  // ── Feed preview ────────────────────────────────────────────────────────────
  const feedViewport = document.getElementById("feedViewport");
  if (feedViewport) {
    feedViewport.addEventListener("click", (e) => {
      const hit = e.target.closest(
        ".action-btn, .btn-like, .btn-save, .btn-follow, .room-banner, [data-feed-action]"
      );
      if (hit) {
        e.stopPropagation();
        e.preventDefault();
        showJoinPrompt();
      }
    }, true);
  }
}

function syncHomepageRoleEntryLinks(auth) {
  document.querySelectorAll("[data-role-entry]").forEach((link) => {
    const targetRole = link.getAttribute("data-role-entry") || "";
    if (!targetRole) return;
    if (auth?.authenticated && auth.user?.role === targetRole) {
      link.setAttribute("href", dashboardPathForRole(targetRole));
      return;
    }
    link.setAttribute("href", `/enter/${encodeURIComponent(targetRole)}`);
  });
}

function setupMobileNav() {
  const button = document.querySelector("[data-mobile-toggle]");
  const drawer = document.querySelector("[data-mobile-drawer]");
  if (button && drawer) {
    button.addEventListener("click", () => {
      const isOpen = drawer.classList.toggle("open");
      document.body.classList.toggle("nav-open", isOpen);
    });
    drawer.addEventListener("click", (event) => {
      if (event.target instanceof HTMLElement && event.target.tagName === "A") {
        drawer.classList.remove("open");
        document.body.classList.remove("nav-open");
      }
    });
  }
  injectMobileBottomNav();
}

function injectMobileBottomNav() {
  // Feed page has its own full-screen mobile UI — skip
  if (document.querySelector("#feedViewport")) return;
  // Dashboard pages use dash-layout.css .bottom-nav — don't double-inject
  if (document.querySelector(".bottom-nav")) return;
  if (document.getElementById("mobile-bottom-nav")) return;

  const path = location.pathname.replace(/\/$/, "") || "/";

  const items = [
    { href: "/",          icon: "🏠", label: "Home",      match: ["/"] },
    { href: "/feed",      icon: "▶️",  label: "Feed",      match: ["/feed"] },
    { href: "/discover",  icon: "🗺️",  label: "Discover",  match: ["/discover"] },
    { href: "/community", icon: "💬",  label: "Community", match: ["/community", "/community-room"] },
    { href: "/dashboard", icon: "👤",  label: "Profile",   match: [
        "/dashboard", "/market-dashboard", "/shopper-dashboard",
        "/my-shop", "/profile", "/shop/",
      ]},
  ];

  const nav = document.createElement("nav");
  nav.id = "mobile-bottom-nav";
  nav.className = "mobile-bottom-nav";
  nav.setAttribute("aria-label", "Main navigation");
  nav.innerHTML = `<div class="mobile-bottom-nav-inner">${
    items.map(item => {
      const isActive = item.match.some(m =>
        m === "/" ? path === "" || path === "/" : path === m || path.startsWith(m)
      );
      return `<a href="${item.href}" class="mobile-bottom-nav-item${isActive ? " active" : ""}">
        <span class="mobile-bottom-nav-icon" aria-hidden="true">${item.icon}</span>
        <span class="nav-label">${item.label}</span>
      </a>`;
    }).join("")
  }</div>`;

  document.body.appendChild(nav);

  // Update Profile link once auth is known
  const profileItem = nav.querySelector(`a[href="/dashboard"]`);
  if (profileItem) {
    getAuthState().then(auth => {
      if (!auth || !auth.authenticated) {
        profileItem.href = "/signin";
        const label = profileItem.querySelector(".nav-label");
        if (label) label.textContent = "Sign In";
        const icon = profileItem.querySelector(".mobile-bottom-nav-icon");
        if (icon) icon.textContent = "🔑";
        return;
      }
      const role = auth.user?.role;
      const profilePath = role === "market" ? "/market-dashboard"
                        : role === "shopper" ? "/shopper-dashboard"
                        : "/dashboard";
      profileItem.href = profilePath;
      // Re-evaluate active state after resolving role path
      if (path === profilePath || path.startsWith(profilePath)) {
        profileItem.classList.add("active");
      }
    }).catch(() => {});
  }
}

function setupVendorScenarios() {
  const panel = document.querySelector("[data-scenario-panel]");
  if (!panel) return;

  document.querySelectorAll("[data-scenario]").forEach((button) => {
    button.addEventListener("click", () => {
      document.querySelectorAll("[data-scenario]").forEach((item) => item.classList.remove("active"));
      button.classList.add("active");
      const scenario = vendorScenarios[button.dataset.scenario];
      panel.innerHTML = `
        <h3>${scenario.title}</h3>
        <p class="muted">Example scenario</p>
        <p>${scenario.text}</p>
      `;
    });
  });
}

async function setupSignupPage() {
  const form = document.querySelector("[data-signup-form]");
  if (!form) return;
  const status = document.querySelector("[data-signup-status]");
  const usernameInput = form.querySelector('input[name="username"]');
  const roleInput = form.querySelectorAll('input[name="role"]');
  const usernameStatus = document.querySelector("[data-username-status]");
  const params = new URLSearchParams(window.location.search);
  const next = params.get("next");
  const roleFromQuery = params.get("role");
  let usernameCheckToken = 0;

  if (roleFromQuery && ["vendor", "market", "shopper"].includes(roleFromQuery)) {
    roleInput.forEach((input) => {
      input.checked = input.value === roleFromQuery;
    });
  }

  function setUsernameStatus(message, tone = "") {
    if (!usernameStatus) return;
    setStatus(usernameStatus, message, tone);
  }

  usernameInput?.addEventListener("input", async () => {
    const normalized = (usernameInput.value || "").trim().toLowerCase();
    usernameInput.value = normalized;
    if (!normalized) {
      setUsernameStatus("");
      return;
    }
    usernameCheckToken += 1;
    const currentToken = usernameCheckToken;
    setUsernameStatus("Checking username...");
    try {
      const result = await api(`/api/auth/username-availability?username=${encodeURIComponent(normalized)}`, { method: "GET" });
      if (currentToken !== usernameCheckToken) return;
      setUsernameStatus(result.message, result.available ? "success" : "error");
    } catch (error) {
      if (currentToken !== usernameCheckToken) return;
      setUsernameStatus("We couldn't check that username right now.", "error");
    }
  });

  form.addEventListener("submit", async (event) => {
    event.preventDefault();
    const payload = Object.fromEntries(new FormData(form).entries());
    payload.username = String(payload.username || "").trim().toLowerCase();
    setStatus(status, "Creating your account...");

    try {
      const response = await api("/api/auth/signup", {
        method: "POST",
        body: JSON.stringify(payload),
      });
      const destination = next || dashboardPathForRole(response.user?.role || payload.role || "vendor");
      setStatus(status, "Account created. Redirecting to your dashboard...", "success");
      window.location.href = destination;
    } catch (error) {
      setStatus(status, error.message, "error");
    }
  });
}

async function setupSigninPage() {
  const form = document.querySelector("[data-signin-form]");
  if (!form) return;
  const status = document.querySelector("[data-signin-status]");
  const next = new URLSearchParams(window.location.search).get("next");

  form.addEventListener("submit", async (event) => {
    event.preventDefault();
    const payload = Object.fromEntries(new FormData(form).entries());
    setStatus(status, "Signing you in...");

    try {
      const response = await api("/api/auth/signin", {
        method: "POST",
        body: JSON.stringify(payload),
      });
      const destination = next || dashboardPathForRole(response.user?.role || "vendor");
      setStatus(status, "Signed in. Redirecting...", "success");
      window.location.href = destination;
    } catch (error) {
      setStatus(status, error.message, "error");
    }
  });

  document.querySelectorAll("[data-dev-login]").forEach((button) => {
    button.addEventListener("click", async () => {
      const role = button.getAttribute("data-dev-login") || "vendor";
      setStatus(status, "Opening temporary test access...");
      try {
        const response = await api("/api/auth/dev-login", {
          method: "POST",
          body: JSON.stringify({ role }),
        });
        const destination = next || dashboardPathForRole(response.user?.role || role);
        setStatus(status, "Temporary account ready. Redirecting...", "success");
        window.location.href = destination;
      } catch (error) {
        setStatus(status, error.message || "We couldn't open temporary access right now.", "error");
      }
    });
  });
}

function renderMarketCard(event, authenticated) {
  const category = event.vendor_category || "general";
  const detailPath = eventDetailPath(event.id);
  return `
    <article class="result-card">
      <h3>${event.name}</h3>
      <p class="muted">${event.city}, ${event.state}${event.date ? ` | ${event.date}` : ""}</p>
      <div class="result-meta">
        <span class="pill">${formatMoney(event.booth_price)}</span>
        <span class="pill">${event.event_size || "unknown"} event</span>
        <span class="pill">${category}</span>
        ${renderRecurrencePill(event.recurrence)}
      </div>
      <p class="muted">Traffic: ${event.estimated_traffic || "TBD"} | Vendors: ${event.vendor_count || "TBD"}</p>
      <div class="stack-row">
        ${detailPath ? `<a class="btn btn-secondary" href="${detailPath}">View Details</a>` : ""}
        ${event.application_link ? `<a class="btn btn-secondary" href="${event.application_link}" target="_blank" rel="noreferrer">View Listing</a>` : ""}
        ${
          authenticated
            ? `<button class="btn btn-primary" type="button" data-save-market="${event.id}">Save to Dashboard</button>`
            : `<a class="btn btn-primary" href="/signup">Create Account to Save</a>`
        }
      </div>
    </article>
  `;
}

function renderDiscoveredMarketCard(event, authenticated) {
  const title = event.title || event.name || "Untitled Event";
  const link = event.url || event.application_link || event.source_url || "";
  const eventId = event.event_id || event.id || "";
  const detailPath = eventDetailPath(eventId);
  return `
    <article class="result-card">
      <h3>${title}</h3>
      <p class="muted">${event.city || ""}${event.city && event.state ? ", " : ""}${event.state || ""}${event.date ? ` | ${event.date}` : ""}</p>
      <div class="result-meta">
        <span class="pill">${event.source || "discovered"}</span>
        <span class="pill">new opportunity</span>
        ${renderRecurrencePill(event.recurrence)}
      </div>
      <div class="stack-row">
        ${detailPath ? `<a class="btn btn-secondary" href="${detailPath}">View Details</a>` : ""}
        ${link ? `<a class="btn btn-secondary" href="${link}" target="_blank" rel="noreferrer">Open Link</a>` : ""}
        ${
          authenticated && eventId
            ? `<button class="btn btn-primary" type="button" data-save-market="${eventId}">Save to Dashboard</button>`
            : ""
        }
      </div>
    </article>
  `;
}

function bindSaveButtons() {
  document.querySelectorAll("[data-save-market]").forEach((button) => {
    button.addEventListener("click", async () => {
      try {
        await api("/api/saved-markets", {
          method: "POST",
          body: JSON.stringify({ event_id: button.dataset.saveMarket }),
        });
        button.textContent = "Saved";
        button.disabled = true;
        showToast("Market saved to your dashboard", "success");
        button.closest(".result-card")?.setAttribute("data-saved", "true");
        window.dispatchEvent(new CustomEvent("vendor-atlas:saved-market", {
          detail: { eventId: button.dataset.saveMarket },
        }));
      } catch (error) {
        if (error.status === 401) {
          window.location.href = "/signup";
          return;
        }
        button.textContent = error.message;
        showToast(error.message || "We couldn't save that market right now.", "error");
      }
    });
  });
}

async function setupMarketFinder(auth) {
  const form = document.querySelector("[data-market-search-form]");
  if (!form) return;
  if (auth.authenticated && auth.user?.role === "shopper") {
    window.location.href = "/discover";
    return;
  }
  const results = document.querySelector("[data-market-results]");
  const status = document.querySelector("[data-market-status]");

  async function searchMarkets(params) {
    setStatus(status, "Searching markets...");
    results.innerHTML = "";
    try {
      const query = new URLSearchParams(params);
      const payload = await api(`/api/find-market?${query.toString()}`, { method: "GET" });
      const searchResults = payload.search_results || [];
      const discoveredResults = payload.discovered_results || [];
      if (!searchResults.length && !discoveredResults.length) {
        results.innerHTML = `<div class="empty-state"><strong>No markets matched yet.</strong><p class="muted">Try another city, widen the date range, or remove a filter to see more options.</p></div>`;
        setStatus(status, "No results yet.");
        return;
      }

      results.innerHTML = `
        ${
          (payload.recurring_series || []).length
            ? `
              <section class="results-grid">
                <div class="section-heading"><h2>Recurring event series</h2><p>Repeat markets and series detected from this search so you can plan further ahead.</p></div>
                <div class="recurring-summary">
                  ${payload.recurring_series
                    .map(
                      (series) => `
                        <article class="result-card">
                          <strong>${series.name}</strong>
                          <p class="muted">${series.city || ""}${series.city && series.state ? ", " : ""}${series.state || ""}${series.next_date ? ` | next known date ${series.next_date}` : ""}</p>
                          <div class="mini-meta">
                            <span class="pill pill-recurring">${series.label}</span>
                            <span class="pill">${series.repeat_count} known dates</span>
                          </div>
                        </article>
                      `,
                    )
                    .join("")}
                </div>
              </section>
            `
            : ""
        }
        <section class="results-grid">
          <div class="section-heading"><h2>From search_events</h2><p>Known event matches from the main event search tool.</p></div>
          ${searchResults.length ? searchResults.map((event) => renderMarketCard(event, auth.authenticated)).join("") : `<div class="empty-state"><strong>No direct search matches.</strong></div>`}
        </section>
        <section class="results-grid">
          <div class="section-heading"><h2>From discover_events</h2><p>Broader popup market and vendor event opportunities found by discovery.</p></div>
          ${discoveredResults.length ? discoveredResults.map((event) => renderDiscoveredMarketCard(event, auth.authenticated)).join("") : `<div class="empty-state"><strong>No extra discovered events.</strong></div>`}
        </section>
      `;

      setStatus(
        status,
        `${payload.search_count || 0} search results and ${payload.discover_count || 0} discovered events loaded.`,
        "success",
      );
      bindSaveButtons();
    } catch (error) {
      results.innerHTML = `<div class="empty-state"><strong>Search failed.</strong><p class="muted">${error.message}</p></div>`;
      setStatus(status, error.message, "error");
    }
  }

  form.addEventListener("submit", async (event) => {
    event.preventDefault();
    const payload = Object.fromEntries(new FormData(form).entries());
    await searchMarkets(payload);
  });

  const cityInput = form.querySelector('input[name="city"]');
  if (cityInput && cityInput.value) {
    await searchMarkets({
      city: cityInput.value,
      state: form.querySelector('input[name="state"]')?.value || "",
      vendor_category: form.querySelector('input[name="vendor_category"]')?.value || "",
      event_size: form.querySelector('select[name="event_size"]')?.value || "",
      distance_radius: form.querySelector('input[name="distance_radius"]')?.value || "",
    });
  }
}

function buildDiscoverFeedCard(event, authenticated, sourceLabel) {
  const title = event.title || event.name || "Untitled Event";
  const link = event.url || event.application_link || event.source_url || "";
  const eventId = event.event_id || event.id || "";
  const detailPath = eventDetailPath(eventId);
  const pinId = eventId || `${title}-${event.city || "city"}-${event.date || "date"}`.toLowerCase().replace(/[^a-z0-9]+/g, "-");
  const recurring = renderRecurrencePill(event.recurrence);
  return `
    <article class="result-card" data-discover-card data-pin-id="${pinId}">
      <div class="mini-meta">
        <span class="pill">${sourceLabel}</span>
        ${event.event_size ? `<span class="pill">${event.event_size}</span>` : ""}
        ${recurring}
      </div>
      <h3>${title}</h3>
      <p class="muted">${event.city || ""}${event.city && event.state ? ", " : ""}${event.state || ""}${event.date ? ` | ${event.date}` : ""}</p>
      <p class="muted">Booth: ${formatMoney(event.booth_price)}${event.estimated_traffic ? ` | Traffic ${event.estimated_traffic}` : ""}</p>
      <div class="stack-row">
        ${detailPath ? `<a class="btn btn-secondary" href="${detailPath}">Details</a>` : ""}
        ${link ? `<a class="btn btn-secondary" href="${link}" target="_blank" rel="noreferrer">View</a>` : ""}
        ${
          authenticated && eventId
            ? `<button class="btn btn-primary" type="button" data-save-market="${eventId}">Save</button>`
            : `<a class="btn btn-primary" href="/signup">Save</a>`
        }
      </div>
    </article>
  `;
}

function renderDiscoverMap(events) {
  const map = document.querySelector("[data-discover-map]");
  if (!map) return;

  if (!events.length) {
    map.innerHTML = `
      <div class="discover-map-grid"></div>
      <div class="discover-map-empty">
        <strong>No discover pins yet.</strong>
        <p class="muted">Run a city search to draw a synced board of results and recurring-series hotspots.</p>
      </div>
    `;
    return;
  }

  const pins = events.slice(0, 8).map((event, index) => {
    const top = 18 + ((index * 11) % 62);
    const left = 16 + ((index * 17) % 68);
    const title = event.title || event.name || "Untitled Event";
    const eventId = event.event_id || event.id || "";
    const pinId = eventId || `${title}-${event.city || "city"}-${event.date || "date"}`.toLowerCase().replace(/[^a-z0-9]+/g, "-");
    const recurringClass = event.recurrence?.is_recurring ? "recurring" : "";
    return `
      <div class="discover-map-pin ${recurringClass}" data-map-pin="${pinId}" style="top:${top}%; left:${left}%"></div>
      <div class="discover-map-label" data-map-label="${pinId}" style="top:${top}%; left:${left}%">
        <strong>${title}</strong>
        <div class="mini-meta">
          ${event.recurrence?.is_recurring ? `<span class="pill pill-recurring">${event.recurrence.label}</span>` : `<span class="pill pill-oneoff">One-off</span>`}
        </div>
      </div>
    `;
  }).join("");

  map.innerHTML = `
    <div class="discover-map-grid"></div>
    ${pins}
  `;
}

function bindDiscoverHoverSync() {
  const cards = document.querySelectorAll("[data-discover-card]");
  if (!cards.length) return;

  function setActive(pinId) {
    document.querySelectorAll("[data-discover-card]").forEach((card) => {
      card.classList.toggle("active", card.getAttribute("data-pin-id") === pinId);
    });
    document.querySelectorAll("[data-map-pin]").forEach((pin) => {
      pin.classList.toggle("active", pin.getAttribute("data-map-pin") === pinId);
    });
    document.querySelectorAll("[data-map-label]").forEach((label) => {
      label.classList.toggle("active", label.getAttribute("data-map-label") === pinId);
    });
  }

  function clearActive() {
    document.querySelectorAll("[data-discover-card], [data-map-pin], [data-map-label]").forEach((node) => {
      node.classList.remove("active");
    });
  }

  cards.forEach((card) => {
    card.addEventListener("mouseenter", () => setActive(card.getAttribute("data-pin-id")));
    card.addEventListener("mouseleave", clearActive);
  });

  document.querySelectorAll("[data-map-pin]").forEach((pin) => {
    const pinId = pin.getAttribute("data-map-pin");
    pin.addEventListener("mouseenter", () => setActive(pinId));
    pin.addEventListener("mouseleave", clearActive);
  });

  document.querySelectorAll("[data-map-label]").forEach((label) => {
    const pinId = label.getAttribute("data-map-label");
    label.addEventListener("mouseenter", () => setActive(pinId));
    label.addEventListener("mouseleave", clearActive);
  });
}

function buildMockDiscoverEvents() {
  const cities = [
    { city: "Kansas City", state: "MO" },
    { city: "Austin", state: "TX" },
    { city: "Chicago", state: "IL" },
    { city: "Nashville", state: "TN" },
    { city: "Denver", state: "CO" },
    { city: "Atlanta", state: "GA" },
  ];
  const eventTypes = ["Market", "Vintage", "Oddity", "Convention", "Craft", "Flea"];
  const audiences = ["Families", "Collectors", "Young professionals", "Tourists", "Local shoppers", "Festival crowd"];
  const trafficLevels = ["Low", "Medium", "High"];
  const settings = ["Indoor", "Outdoor"];
  const setupLevels = ["Light", "Moderate", "Heavy"];
  const accessLevels = ["Easy parking", "Limited parking", "Easy load-in", "ADA friendly", "Street parking only"];
  const featureSets = [
    ["Electricity", "Indoor", "Parking"],
    ["Parking", "Foot Traffic"],
    ["Indoor", "ADA friendly"],
    ["Electricity", "Foot Traffic"],
    ["Parking", "Outdoor space"],
  ];

  const events = [];
  for (let index = 0; index < 120; index += 1) {
    const city = cities[index % cities.length];
    const eventType = eventTypes[index % eventTypes.length];
    const traffic = trafficLevels[index % trafficLevels.length];
    const setting = settings[index % settings.length];
    const audience = audiences[index % audiences.length];
    const setup = setupLevels[index % setupLevels.length];
    const featureSet = featureSets[index % featureSets.length];
    const fee = 45 + ((index * 17) % 260);
    const distance = 12 + ((index * 9) % 220);
    const month = String(((index % 9) + 4)).padStart(2, "0");
    const day = String(((index * 3) % 27) + 1).padStart(2, "0");
    events.push({
      id: `mock-event-${index + 1}`,
      title: `${city.city} ${eventType} Showcase ${index + 1}`,
      location: `${city.city}, ${city.state}`,
      city: city.city,
      state: city.state,
      date: `2026-${month}-${day}`,
      vendor_fee: fee,
      event_type: eventType,
      estimated_traffic: traffic,
      audience_type: audience,
      indoor_outdoor: setting,
      electricity: featureSet.includes("Electricity"),
      setup_difficulty: setup,
      parking_accessibility: accessLevels[index % accessLevels.length],
      distance_miles: distance,
      features: featureSet,
      sourceLabel: "Vendor Atlas mock",
    });
  }
  return events;
}

function trafficBand(value) {
  if (typeof value === "string" && value) return value;
  const numeric = Number(value || 0);
  if (numeric >= 2500) return "High";
  if (numeric >= 1200) return "Medium";
  if (numeric > 0) return "Low";
  return "";
}

function normalizeDiscoverEventType(value) {
  const text = String(value || "").trim().toLowerCase();
  if (!text) return "Market";
  if (text.includes("vintage")) return "Vintage";
  if (text.includes("oddity")) return "Oddity";
  if (text.includes("convention")) return "Convention";
  if (text.includes("craft") || text.includes("art") || text.includes("handmade") || text.includes("maker")) return "Craft";
  if (text.includes("flea")) return "Flea";
  return "Market";
}

function normalizeDiscoverEvent(event, index = 0) {
  if (!event || typeof event !== "object") return null;
  const eventType = normalizeDiscoverEventType(event.event_type || event.vendor_category || event.category);
  const numericTraffic = Number(event.estimated_traffic || 0) || 0;
  const reasons = Array.isArray(event.score_reasons) ? event.score_reasons.filter(Boolean) : [];
  return {
    id: String(event.id || event.event_id || `discover-${index}`),
    title: event.title || event.name || "Untitled event",
    name: event.name || event.title || "Untitled event",
    location: event.location || [event.city, event.state].filter(Boolean).join(", "),
    city: event.city || "",
    state: event.state || "",
    date: event.date || "",
    vendor_fee: Number(event.vendor_fee ?? event.booth_price ?? 0) || 0,
    booth_price: Number(event.booth_price ?? event.vendor_fee ?? 0) || 0,
    fit_score: Number(event.fit_score ?? event.worth_it_score ?? 0) || 0,
    fit_reason: event.fit_reason || reasons.slice(0, 2).join(" "),
    bucket: event.bucket || "",
    score_label: event.score_label || "",
    score_reasons: reasons,
    score_breakdown: event.score_breakdown || null,
    distance_miles: Number(event.distance_miles ?? (12 + ((index * 17) % 180))) || 0,
    event_type: eventType,
    estimated_traffic: trafficBand(event.estimated_traffic),
    estimated_traffic_count: numericTraffic,
    audience_type: event.audience_type || (event.vendor_category ? `${event.vendor_category} shoppers` : "Local shoppers"),
    indoor_outdoor: event.indoor_outdoor || "Mixed",
    electricity: Boolean(event.electricity),
    setup_difficulty: event.setup_difficulty || "Moderate",
    parking_accessibility: event.parking_accessibility || "Check with organizer",
    application_link: event.application_link || event.apply_url || event.url || "",
    sourceLabel: event.sourceLabel || event.source || "Vendor Atlas",
  };
}

function parseCityStateInput(value) {
  const raw = String(value || "").trim();
  if (!raw) return { city: "", state: "" };
  const parts = raw.split(",").map((part) => part.trim()).filter(Boolean);
  if (parts.length >= 2) {
    return { city: parts[0], state: parts[1] };
  }
  return { city: raw, state: "" };
}

function mergeDiscoverEvents(searchResults = [], discoveredResults = []) {
  const merged = [];
  const seen = new Set();
  [...searchResults, ...discoveredResults].forEach((event) => {
    const normalized = normalizeDiscoverEvent(event, merged.length);
    if (!normalized) return;
    if (seen.has(normalized.id)) return;
    seen.add(normalized.id);
    merged.push(normalized);
  });
  return merged;
}

function categoryMatches(event, category) {
  if (category === "All") return true;
  if (category === "Markets") return event.event_type === "Market" || event.event_type === "Flea";
  if (category === "Vintage") return event.event_type === "Vintage";
  if (category === "Oddity") return event.event_type === "Oddity";
  if (category === "Conventions") return event.event_type === "Convention";
  if (category === "Craft") return event.event_type === "Craft";
  return true;
}

function buildLearningProfile() {
  const history = getEventHistory();
  if (!history.length) {
    return {
      preferredMonths: [],
      comfortableFeeCap: 200,
      averageProfit: 0,
      hasHistory: false,
    };
  }

  const profitable = history.filter((entry) => Number(entry.profit || 0) > 0);
  const monthCounts = new Map();
  profitable.forEach((entry) => {
    const date = String(entry.eventDate || entry.date || "");
    const month = date ? Number(date.slice(5, 7)) : 0;
    if (!month) return;
    monthCounts.set(month, (monthCounts.get(month) || 0) + 1);
  });
  const preferredMonths = [...monthCounts.entries()]
    .sort((a, b) => b[1] - a[1])
    .slice(0, 3)
    .map(([month]) => month);

  const avgProfitableFee = profitable.length
    ? profitable.reduce((sum, entry) => sum + (Number(entry.boothFee || 0) || 0), 0) / profitable.length
    : 0;
  const averageProfit = history.reduce((sum, entry) => sum + (Number(entry.profit || 0) || 0), 0) / history.length;

  return {
    preferredMonths,
    comfortableFeeCap: avgProfitableFee > 0 ? Math.max(100, Math.round(avgProfitableFee + 50)) : 200,
    averageProfit,
    hasHistory: true,
  };
}

function scoreDiscoverEvent(event, preferences) {
  let score = Number(event.fit_score || event.worth_it_score || 40) || 40;
  const reasons = Array.isArray(event.score_reasons) ? event.score_reasons.filter(Boolean).slice(0, 2) : [];
  const learning = buildLearningProfile();
  if (event.distance_miles <= preferences.distance) {
    score += 18;
    if (reasons.length < 4) reasons.push("Travel looks manageable.");
  } else {
    score -= 8;
    if (reasons.length < 4) reasons.push("This is a longer trip.");
  }
  if (preferences.travelMode === "Travel" && event.estimated_traffic === "High") {
    score += 10;
    if (reasons.length < 4) reasons.push("Travel mode favors bigger destination events.");
  }
  if (preferences.eventType === "All" || categoryMatches(event, preferences.eventType)) {
    score += 14;
    if (reasons.length < 4) reasons.push("Matches the kind of event you are browsing.");
  }
  if (event.vendor_fee <= preferences.maxFee) {
    score += 12;
    if (reasons.length < 4) reasons.push("The vendor fee fits your range.");
  } else {
    score -= 10;
    if (reasons.length < 4) reasons.push("The vendor fee is above your filter.");
  }
  if (preferences.features.includes("Electricity") && event.electricity) score += 10;
  if (preferences.features.includes("Indoor") && event.indoor_outdoor === "Indoor") score += 10;
  if (preferences.features.includes("Parking") && /parking|load-in/i.test(event.parking_accessibility)) score += 8;
  if (preferences.features.includes("Foot Traffic") && event.estimated_traffic === "High") score += 10;
  if (preferences.dateRange === "Soon" && Number(event.date.slice(5, 7)) <= 6) score += 6;
  if (preferences.dateRange === "Later" && Number(event.date.slice(5, 7)) >= 7) score += 6;
  if (learning.hasHistory) {
    const eventMonth = Number(String(event.date || "").slice(5, 7));
    if (learning.preferredMonths.includes(eventMonth)) {
      score += 8;
      if (reasons.length < 4) reasons.push("Past results suggest this time of year works for you.");
    }
    if (Number(event.vendor_fee || 0) <= learning.comfortableFeeCap) {
      score += 6;
      if (reasons.length < 4) reasons.push("This booth fee lines up with your stronger past results.");
    }
  }

  const fitScore = Math.max(1, Math.min(99, score));
  let bucket = "Worth Trying";
  if (fitScore >= 72) bucket = "Best Matches";
  else if (fitScore <= 45) bucket = "Not Ideal";
  return {
    ...event,
    fit_score: fitScore,
    fit_reason: reasons.slice(0, 2).join(" "),
    bucket,
  };
}

const PLAN_STORAGE_KEY = "vendorAtlasPlanningAnswers";
const PLAN_DRAFT_KEY = "vendorAtlasPlanningDraft";
const SELECTED_EVENTS_KEY = "vendorAtlasPlanSelectedEvents";
const SELECTED_IDS_KEY = "vendorAtlasPlanSelectedIds";
const PROFILES_KEY = "vendorAtlasProfiles";
const CURRENT_PROFILE_KEY = "vendorAtlasCurrentProfileId";
const EVENT_HISTORY_KEY = "vendorAtlasEventHistory";
const SHOPIFY_KEY = "vendorAtlasShopify";
const APP_STATE_KEY = "vendorAtlasAppState";
const APP_STATE_VERSION = 1;
const JOURNEY_PROGRESS_KEY = "vendorAtlasJourneyProgress";
const DISCOVER_STATE_KEY = "vendorAtlasDiscoverState";
const SHOPIFY_SNAPSHOT_KEY = "vendorAtlasShopifySnapshot";
const ORGANIZER_APPLICATIONS_KEY = "vendorAtlasOrganizerApplications";

function defaultAppState() {
  return {
    version: APP_STATE_VERSION,
    journey: {
      answers: {},
      draft: {},
      progress: {
        mode: "home",
        weekendStep: 0,
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
}

function parseJsonSafely(raw, fallback) {
  if (!raw) return fallback;
  try {
    return JSON.parse(raw);
  } catch (e) {
    return fallback;
  }
}

function loadAppState() {
  const fallback = defaultAppState();
  try {
    const parsed = parseJsonSafely(localStorage.getItem(APP_STATE_KEY), null);
    if (!parsed || typeof parsed !== "object") return fallback;
    return {
      ...fallback,
      ...parsed,
      journey: {
        ...fallback.journey,
        ...(parsed.journey || {}),
        progress: {
          ...fallback.journey.progress,
          ...((parsed.journey || {}).progress || parseJsonSafely(localStorage.getItem(JOURNEY_PROGRESS_KEY), {})),
        },
        discover: {
          ...fallback.journey.discover,
          ...((parsed.journey || {}).discover || parseJsonSafely(localStorage.getItem(DISCOVER_STATE_KEY), {})),
        },
      },
      profiles: Array.isArray(parsed.profiles) ? parsed.profiles : fallback.profiles,
      currentProfileId: parsed.currentProfileId || localStorage.getItem(CURRENT_PROFILE_KEY) || null,
      selectedEvents: Array.isArray(parsed.selectedEvents)
        ? parsed.selectedEvents
        : parseJsonSafely(localStorage.getItem(SELECTED_EVENTS_KEY), []),
      eventHistory: Array.isArray(parsed.eventHistory)
        ? parsed.eventHistory
        : parseJsonSafely(localStorage.getItem(EVENT_HISTORY_KEY), []),
      shopify: {
        ...fallback.shopify,
        ...(parsed.shopify || parseJsonSafely(localStorage.getItem(SHOPIFY_SNAPSHOT_KEY), {})),
      },
    };
  } catch (e) {
    return fallback;
  }
}

function syncLegacyStorage(state) {
  try {
    localStorage.setItem(PROFILES_KEY, JSON.stringify(state.profiles || []));
    if (state.currentProfileId == null) localStorage.removeItem(CURRENT_PROFILE_KEY);
    else localStorage.setItem(CURRENT_PROFILE_KEY, String(state.currentProfileId));
    localStorage.setItem(EVENT_HISTORY_KEY, JSON.stringify(state.eventHistory || []));
    localStorage.setItem(SELECTED_EVENTS_KEY, JSON.stringify(state.selectedEvents || []));
    localStorage.setItem(SELECTED_IDS_KEY, JSON.stringify((state.selectedEvents || []).map((event) => String(event.id))));
    localStorage.setItem(PLAN_STORAGE_KEY, JSON.stringify(state.journey?.answers || {}));
    localStorage.setItem(PLAN_DRAFT_KEY, JSON.stringify(state.journey?.draft || {}));
    localStorage.setItem(JOURNEY_PROGRESS_KEY, JSON.stringify(state.journey?.progress || {}));
    localStorage.setItem(DISCOVER_STATE_KEY, JSON.stringify(state.journey?.discover || {}));
    localStorage.setItem(SHOPIFY_KEY, state.shopify?.connected ? "true" : "false");
    localStorage.setItem(SHOPIFY_SNAPSHOT_KEY, JSON.stringify(state.shopify || {}));
    sessionStorage.setItem(PLAN_STORAGE_KEY, JSON.stringify(state.journey?.answers || {}));
  } catch (e) {}
}

function writeAppState(mutator) {
  const current = loadAppState();
  const next = typeof mutator === "function" ? mutator(current) : mutator;
  const normalized = {
    ...defaultAppState(),
    ...next,
    version: APP_STATE_VERSION,
  };
  try {
    localStorage.setItem(APP_STATE_KEY, JSON.stringify(normalized));
  } catch (e) {}
  syncLegacyStorage(normalized);
  return normalized;
}

function getAppState() {
  return loadAppState();
}

function getPlanningAnswers() {
  const state = getAppState();
  const answers = state.journey?.answers || {};
  if (Object.keys(answers).length) return answers;
  return parseJsonSafely(localStorage.getItem(PLAN_STORAGE_KEY), {});
}

function setPlanningAnswers(answers) {
  writeAppState((state) => ({
    ...state,
    journey: {
      ...state.journey,
      answers: { ...(answers || {}) },
    },
  }));
}

function getJourneyProgress() {
  return getAppState().journey?.progress || defaultAppState().journey.progress;
}

function setJourneyProgress(progress) {
  writeAppState((state) => ({
    ...state,
    journey: {
      ...state.journey,
      progress: {
        ...state.journey.progress,
        ...(progress || {}),
      },
    },
  }));
}

function getDiscoverState() {
  return getAppState().journey?.discover || {};
}

function setDiscoverState(patch) {
  writeAppState((state) => ({
    ...state,
    journey: {
      ...state.journey,
      discover: {
        ...state.journey.discover,
        ...(patch || {}),
      },
    },
  }));
}

function normalizeSelectedEvent(event) {
  if (!event || event.id == null) return null;
  return {
    id: String(event.id),
    title: event.title || event.name || "Untitled event",
    name: event.name || event.title || "Untitled event",
    location: event.location || [event.city, event.state].filter(Boolean).join(", "),
    city: event.city || "",
    state: event.state || "",
    date: event.date || "",
    vendor_fee: Number(event.vendor_fee ?? event.booth_price ?? 0) || 0,
    booth_price: Number(event.booth_price ?? event.vendor_fee ?? 0) || 0,
    fit_score: Number(event.fit_score ?? 0) || 0,
    fit_reason: event.fit_reason || "",
    distance_miles: Number(event.distance_miles ?? 0) || 0,
    event_type: event.event_type || "",
    estimated_traffic: event.estimated_traffic || "",
    audience_type: event.audience_type || "",
    indoor_outdoor: event.indoor_outdoor || "",
    electricity: Boolean(event.electricity),
    setup_difficulty: event.setup_difficulty || "",
    parking_accessibility: event.parking_accessibility || "",
    application_link: event.application_link || event.apply_url || event.url || "",
    sourceLabel: event.sourceLabel || event.source || "",
  };
}

function getSelectedEvents() {
  const legacyEvents = parseJsonSafely(localStorage.getItem(SELECTED_EVENTS_KEY), null);
  const events = Array.isArray(legacyEvents)
    ? legacyEvents
    : Array.isArray(getAppState().selectedEvents)
      ? getAppState().selectedEvents
      : [];
  return events.map((event) => normalizeSelectedEvent(event)).filter(Boolean);
}

function setSelectedEvents(events) {
  const deduped = [];
  const seen = new Set();
  (events || []).forEach((event) => {
    const normalized = normalizeSelectedEvent(event);
    if (!normalized || seen.has(normalized.id)) return;
    seen.add(normalized.id);
    deduped.push(normalized);
  });
  writeAppState((state) => ({
    ...state,
    selectedEvents: deduped,
  }));
  return deduped;
}

function getShopifySnapshot() {
  return getAppState().shopify || defaultAppState().shopify;
}

function setShopifySnapshot(snapshot) {
  writeAppState((state) => ({
    ...state,
    shopify: {
      ...state.shopify,
      ...(snapshot || {}),
    },
  }));
}

function getOrganizerApplicationState() {
  return parseJsonSafely(localStorage.getItem(ORGANIZER_APPLICATIONS_KEY), {});
}

function setOrganizerApplicationState(state) {
  try {
    localStorage.setItem(ORGANIZER_APPLICATIONS_KEY, JSON.stringify(state || {}));
  } catch (e) {}
}

function getProfiles() {
  return getAppState().profiles || [];
}

function getCurrentProfileId() {
  return getAppState().currentProfileId || null;
}

function setCurrentProfileId(id) {
  writeAppState((state) => ({
    ...state,
    currentProfileId: id == null ? null : String(id),
  }));
}

function saveProfile(profile) {
  const list = getProfiles();
  const id = profile.id || "pro-" + Date.now();
  const existing = list.findIndex((p) => p.id === id);
  const entry = { ...profile, id, updatedAt: new Date().toISOString() };
  if (!entry.name) entry.name = "My profile";
  if (!entry.createdAt) entry.createdAt = entry.updatedAt;
  if (existing >= 0) list[existing] = entry;
  else list.push(entry);
  writeAppState((state) => ({
    ...state,
    profiles: list,
  }));
  return id;
}

function deleteProfile(id) {
  const list = getProfiles().filter((p) => p.id !== id);
  writeAppState((state) => ({
    ...state,
    profiles: list,
    currentProfileId: state.currentProfileId === id ? null : state.currentProfileId,
  }));
}

function getEventHistory() {
  return getAppState().eventHistory || [];
}

function addEventToHistory(record) {
  const list = getEventHistory();
  const eventId = record.eventId != null ? String(record.eventId) : "";
  const eventDate = record.eventDate || record.date || "";
  const dateKey = String(eventDate || new Date().toISOString().slice(0, 10));
  const boothFee = Number(record.boothFee) || 0;
  const revenue = Number(record.revenue) || 0;
  const costs = Number(record.costs) || 0;
  const profit = revenue - boothFee - costs;

  const existingIndex = list.findIndex((e) => String(e.eventId || "") === eventId && String(e.eventDate || e.date || "") === dateKey);
  const base = existingIndex >= 0 ? list[existingIndex] : {};
  const entry = {
    ...base,
    id: base.id || "ev-" + Date.now(),
    eventId,
    eventTitle: record.eventTitle || base.eventTitle || "Event",
    eventDate: dateKey,
    date: base.date || new Date().toISOString().slice(0, 10),
    boothFee,
    revenue,
    costs,
    profit,
    rating: record.rating != null ? Number(record.rating) : base.rating ?? null,
    notes: record.notes != null ? String(record.notes) : base.notes || "",
    updatedAt: new Date().toISOString(),
    createdAt: base.createdAt || new Date().toISOString(),
  };

  if (existingIndex >= 0) {
    list.splice(existingIndex, 1);
    list.unshift(entry);
  } else {
    list.unshift(entry);
  }
  writeAppState((state) => ({
    ...state,
    eventHistory: list,
  }));
  return entry;
}

function getBudgetSummary() {
  const history = getEventHistory();
  const totalRevenue = history.reduce((s, e) => s + (e.revenue || 0), 0);
  const totalCosts = history.reduce((s, e) => s + (e.boothFee || 0) + (e.costs || 0), 0);
  const totalProfit = totalRevenue - totalCosts;
  const best = history.length ? history.reduce((a, b) => (a.profit > b.profit ? a : b)) : null;
  const worst = history.length ? history.reduce((a, b) => (a.profit < b.profit ? a : b)) : null;
  return { totalRevenue, totalCosts, totalProfit, count: history.length, best, worst };
}

function getShopifyConnected() {
  return Boolean(getShopifySnapshot().connected);
}

function setShopifyConnected(value) {
  setShopifySnapshot({ connected: Boolean(value) });
}

function getPlanSelectedFromStorage() {
  return new Set(getSelectedEvents().map((event) => String(event.id)));
}

function savePlanSelectedToStorage(ids, events) {
  const idSet = new Set([...(ids || [])].map((id) => String(id)));
  const eventList = Array.isArray(events) ? events : getSelectedEvents();
  const filtered = eventList
    .map((event) => normalizeSelectedEvent(event))
    .filter((event) => event && idSet.has(String(event.id)));
  setSelectedEvents(filtered);
  try {
    localStorage.setItem(SELECTED_EVENTS_KEY, JSON.stringify(filtered));
    localStorage.setItem(SELECTED_IDS_KEY, JSON.stringify(filtered.map((event) => String(event.id))));
  } catch (e) {}
}

function getPlanningDraft() {
  return getAppState().journey?.draft || null;
}

function savePlanningDraft(answers) {
  writeAppState((state) => ({
    ...state,
    journey: {
      ...state.journey,
      draft: { ...(answers || {}) },
    },
  }));
}

function clearPlanningDraft() {
  writeAppState((state) => ({
    ...state,
    journey: {
      ...state.journey,
      draft: {},
    },
  }));
}

async function setupDiscoverPage(auth) {
  const root = document.querySelector("[data-discover-app]");
  if (!root) return;

  root.innerHTML = `<div class="empty-state"><strong>Loading events...</strong></div>`;
  let allEvents = [];
  let discoverDataSource = "live";
  let discoverCity = "";
  let discoverSearching = false;

  async function runCitySearch(city) {
    if (!city || discoverSearching) return;
    discoverSearching = true;
    discoverCity = city;
    allEvents = [];
    requestRender();
    const location = parseCityStateInput(city);
    try {
      const query = new URLSearchParams();
      if (location.city) query.set("city", location.city);
      if (location.state) query.set("state", location.state);
      const payload = await api(`/api/find-market?${query.toString()}`, { method: "GET" });
      allEvents = mergeDiscoverEvents(payload.search_results || [], payload.discovered_results || []);
      discoverDataSource = "live";
      if (!allEvents.length) {
        const fallbackPayload = await api(`/api/events?limit=120`, { method: "GET" });
        allEvents = Array.isArray(fallbackPayload.events)
          ? fallbackPayload.events
            .filter((event) => {
              if (!location.city) return true;
              const eventCity = String(event.city || "").trim().toLowerCase();
              const eventState = String(event.state || "").trim().toLowerCase();
              return eventCity === location.city.trim().toLowerCase()
                && (!location.state || eventState === location.state.trim().toLowerCase());
            })
            .map((event, index) => normalizeDiscoverEvent(event, index))
            .filter(Boolean)
          : [];
      }
    } catch (_) {
      discoverDataSource = "fallback";
      allEvents = [];
    }
    discoverSearching = false;
    requestRender();
  }

  // Phase 1 — fast: stored events
  try {
    const payload = await api("/api/events?limit=120", { method: "GET" });
    allEvents = Array.isArray(payload.events)
      ? payload.events.map((event, index) => normalizeDiscoverEvent(event, index)).filter(Boolean)
      : [];
  } catch (error) {
    discoverDataSource = "fallback";
    allEvents = [];
  }
  // no mock fallback — real events only
  const planningAnswers = getPlanningAnswers();
  const persistedDiscoverState = getDiscoverState();
  const initialDistance = persistedDiscoverState.distance
    || (planningAnswers.travel === "30" ? 30 : planningAnswers.travel === "60" ? 60 : 120);
  const initialTravelMode = persistedDiscoverState.travelMode
    || (planningAnswers.travel === "flexible" ? "Travel" : "Local");
  const initialFee = persistedDiscoverState.maxFee
    || (planningAnswers.boothFeeComfort === "low" ? 100 : planningAnswers.boothFeeComfort === "higher" ? 300 : 200);
  const initialFeatures = Array.isArray(persistedDiscoverState.features) && persistedDiscoverState.features.length
    ? persistedDiscoverState.features
    : Array.isArray(planningAnswers.mustHaves)
      ? planningAnswers.mustHaves.map((item) => item === "foot traffic" ? "Foot Traffic" : item.charAt(0).toUpperCase() + item.slice(1))
      : [];
  const state = {
    travelMode: initialTravelMode,
    distance: initialDistance,
    eventType: persistedDiscoverState.eventType || "All",
    maxFee: initialFee,
    dateRange: persistedDiscoverState.dateRange || "Any",
    features: initialFeatures,
    mapOpen: Boolean(persistedDiscoverState.mapOpen),
    selectedIds: getPlanSelectedFromStorage(),
  };

  let renderQueued = false;
  function requestRender() {
    if (renderQueued) return;
    renderQueued = true;
    requestAnimationFrame(() => {
      renderQueued = false;
      render();
    });
  }

  function getWhySummary() {
    const params = new URLSearchParams(window.location.search);
    if (params.get("from") !== "planning") return null;
    try {
      const answers = getPlanningAnswers();
      if (!answers || !Object.keys(answers).length) return null;
      const parts = [];
      if (answers.travel) parts.push(`travel: ${answers.travel === "30" ? "~30 min" : answers.travel === "60" ? "~1 hour" : "flexible"}`);
      if (answers.boothFeeComfort) parts.push(`booth fees: ${answers.boothFeeComfort === "low" ? "keep it low" : answers.boothFeeComfort === "higher" ? "can pay more" : "depends on event"}`);
      if (answers.goal) parts.push(`goal: ${answers.goal}`);
      if (parts.length === 0) return null;
      return "We chose these events based on your planning answers: " + parts.join("; ") + ".";
    } catch (e) {
      return null;
    }
  }

  function persistDiscoverFilters() {
    setDiscoverState({
      travelMode: state.travelMode,
      distance: state.distance,
      eventType: state.eventType,
      maxFee: state.maxFee,
      dateRange: state.dateRange,
      features: state.features,
      mapOpen: state.mapOpen,
    });
  }

  function togglePlanSelection(eventId, eventObjFromScored) {
    const removing = state.selectedIds.has(eventId);
    let events = getSelectedEvents();
    if (state.selectedIds.has(eventId)) {
      state.selectedIds.delete(eventId);
      events = events.filter((e) => String(e.id) !== String(eventId));
    } else {
      const normalized = normalizeSelectedEvent(eventObjFromScored);
      if (normalized) {
        state.selectedIds.add(normalized.id);
        events = [...events.filter((e) => String(e.id) !== normalized.id), normalized];
      }
    }
    savePlanSelectedToStorage(state.selectedIds, events);
    showToast(removing ? "Removed from your plan" : "Added to your plan", "success");
    requestRender();
  }

  function render() {
    let scored = allEvents
      .filter((event) => categoryMatches(event, state.eventType))
      .filter((event) => discoverCity || event.distance_miles <= (state.travelMode === "Local" ? Math.min(state.distance, 75) : Math.max(state.distance, 120)))
      .filter((event) => event.vendor_fee <= state.maxFee)
      .filter((event) => state.dateRange === "Any" || (state.dateRange === "Soon" ? Number(event.date.slice(5, 7)) <= 6 : Number(event.date.slice(5, 7)) >= 7))
      .filter((event) => state.features.every((feature) => {
        if (feature === "Electricity") return event.electricity;
        if (feature === "Indoor") return event.indoor_outdoor === "Indoor";
        if (feature === "Parking") return /parking|load-in/i.test(event.parking_accessibility);
        if (feature === "Foot Traffic") return event.estimated_traffic === "High";
        return true;
      }))
      .map((event) => scoreDiscoverEvent(event, state))
      .sort((a, b) => b.fit_score - a.fit_score);

    const groups = {
      "Best Matches": scored.filter((event) => event.bucket === "Best Matches").slice(0, 8),
      "Worth Trying": scored.filter((event) => event.bucket === "Worth Trying").slice(0, 8),
      "Not Ideal": scored.filter((event) => event.bucket === "Not Ideal").slice(0, 8),
    };

    const whySummary = getWhySummary();
    const selectedCount = state.selectedIds.size;

    root.innerHTML = `
      <div class="discover-plus-shell">
        ${whySummary ? `<div class="discover-why-summary"><strong>Why these events?</strong> ${whySummary}</div>` : ""}
        <section class="discover-plus-filters">
          <div class="discover-plus-topbar">
            <div>
              <span class="eyebrow">Event discovery</span>
              <h2>${scored.length} events ranked for you</h2>
              <p class="muted">Use a few simple filters. Vendor Atlas will handle the sorting.</p>
            </div>
            <button class="btn btn-secondary" type="button" data-map-toggle>${state.mapOpen ? "Hide Map" : "Show Map"}</button>
          </div>
          <div class="discover-city-search" style="display:flex;gap:.5rem;margin-top:.75rem;align-items:center;">
            <input id="discover-city-input" class="mini-input" placeholder="Search events by city (e.g. Austin, TX)" style="flex:1;max-width:340px;" value="${escapeHtml(discoverCity)}">
            <button class="btn btn-primary" type="button" data-discover-search-btn ${discoverSearching ? "disabled" : ""}>${discoverSearching ? "Searching…" : "Find Events"}</button>
          </div>
          ${discoverSearching ? `<div class="empty-state" style="margin-top:1.5rem;"><strong>Searching for events…</strong><p class="muted">Scanning the web for popup markets and craft fairs near ${escapeHtml(discoverCity)}. This takes about 15 seconds.</p></div>` : scored.length === 0 ? `<div class="empty-state" style="margin-top:1.5rem;"><strong>No events found.</strong><p class="muted">Enter your city above and click Find Events to discover markets near you.</p></div>` : ""}
          ${discoverDataSource === "fallback" ? `<div class="discover-why-summary"><strong>Using backup event data.</strong> Live event ranking is temporarily unavailable, so we're keeping the page useful with a local sample set.</div>` : ""}
          <div class="discover-summary-strip">
            <div class="discover-summary-pill">
              <strong>${groups["Best Matches"].length}</strong>
              <span>best matches</span>
            </div>
            <div class="discover-summary-pill">
              <strong>${state.travelMode}</strong>
              <span>travel mode</span>
            </div>
            <div class="discover-summary-pill">
              <strong>${state.distance} mi</strong>
              <span>distance cap</span>
            </div>
          </div>
          <div class="discover-filter-group">
            <span class="discover-filter-label">Travel</span>
            <div class="discover-chip-row">
              ${["Local", "Travel"].map((mode) => `<button class="chip${state.travelMode === mode ? " active" : ""}" type="button" data-travel-mode="${mode}">${mode}</button>`).join("")}
            </div>
          </div>
          <div class="discover-filter-group">
            <span class="discover-filter-label">Distance</span>
            <div class="discover-chip-row">
              ${[
                { value: 30, label: "30 mi" },
                { value: 60, label: "60 mi" },
                { value: 120, label: "120 mi" },
                { value: 250, label: "250 mi" },
              ].map((item) => `<button class="chip${state.distance === item.value ? " active" : ""}" type="button" data-distance="${item.value}">${item.label}</button>`).join("")}
            </div>
          </div>
          <div class="discover-filter-group">
            <span class="discover-filter-label">Event type</span>
            <div class="discover-chip-row">
              ${["All", "Markets", "Vintage", "Oddity", "Conventions", "Craft"].map((category) => `<button class="chip${state.eventType === category ? " active" : ""}" type="button" data-event-type="${category}">${category}</button>`).join("")}
            </div>
          </div>
          ${auth.user?.role !== "shopper" ? `
          <div class="discover-filter-group">
            <span class="discover-filter-label">Booth fee</span>
            <div class="discover-chip-row">
              ${[
                { value: 100, label: "Up to $100" },
                { value: 200, label: "Up to $200" },
                { value: 300, label: "Up to $300" },
              ].map((item) => `<button class="chip${state.maxFee === item.value ? " active" : ""}" type="button" data-fee="${item.value}">${item.label}</button>`).join("")}
            </div>
          </div>
          ` : ""}
          <div class="discover-filter-group">
            <span class="discover-filter-label">Timing</span>
            <div class="discover-chip-row">
              ${["Any", "Soon", "Later"].map((range) => `<button class="chip${state.dateRange === range ? " active" : ""}" type="button" data-date-range="${range}">${range}</button>`).join("")}
            </div>
          </div>
          <div class="discover-filter-group">
            <span class="discover-filter-label">Must-have features</span>
            <div class="discover-chip-row">
              ${["Electricity", "Indoor", "Parking", "Foot Traffic"].map((feature) => `<button class="chip${state.features.includes(feature) ? " active" : ""}" type="button" data-feature="${feature}">${feature}</button>`).join("")}
            </div>
          </div>
        </section>
        <div class="discover-plus-layout${state.mapOpen ? " map-open" : ""}">
          <section class="discover-plus-results">
            ${Object.entries(groups).map(([label, events]) => `
              <div class="discover-group">
                <div class="section-heading compact">
                  <h2>${label}</h2>
                  <p>${label === "Best Matches" ? "Strong fit based on your current filters." : label === "Worth Trying" ? "Not perfect, but still promising." : "These miss too many of your preferences right now."}</p>
                </div>
                <div class="discover-card-grid">
                  ${(events.length ? events : [{ title: "No events in this group yet.", location: "", fit_reason: "Adjust a filter to reveal more options.", fit_score: 0, vendor_fee: 0, event_type: "", estimated_traffic: "", audience_type: "", indoor_outdoor: "", electricity: false, setup_difficulty: "", parking_accessibility: "", date: "" }]).map((event) => {
                    const isPlaceholder = !event.id;
                    const added = !isPlaceholder && state.selectedIds.has(event.id);
                    const detailPath = eventDetailPath(event.id);
                    return `
                    <article class="discover-event-card journey-card${added ? " added-to-plan" : ""}" ${event.id ? `data-event-id="${event.id}"` : ""}>
                      <div class="mini-meta">
                        <span class="pill">Fit ${event.fit_score}</span>
                        ${event.score_label ? `<span class="pill">${event.score_label}</span>` : ""}
                        ${event.event_type ? `<span class="pill">${event.event_type}</span>` : ""}
                        ${event.estimated_traffic ? `<span class="pill">${event.estimated_traffic} traffic</span>` : ""}
                      </div>
                      <h3>${event.title}</h3>
                      <p class="muted">${event.location}${event.date ? ` | ${event.date}` : ""}</p>
                      <p class="muted">${auth.user?.role !== "shopper" ? `Vendor fee ${formatMoney(event.vendor_fee || 0)} | ` : ""}${event.indoor_outdoor || "Mixed"} | ${event.distance_miles != null ? event.distance_miles + " mi away" : ""}</p>
                      <p class="muted">${event.fit_reason || ""}</p>
                      ${event.score_reasons?.length ? renderHighlightCard("Why it ranks here", event.score_reasons.slice(0, 2).join(" ")) : ""}
                      <div class="discover-detail-list">
                        <span>${event.audience_type || "General audience"}</span>
                        <span>${event.electricity ? "Electricity available" : "No electricity listed"}</span>
                        <span>${event.setup_difficulty || "Setup unknown"}</span>
                        <span>${event.parking_accessibility || "Access details not listed"}</span>
                      </div>
                      ${
                        !isPlaceholder
                          ? `
                            <div class="stack-row">
                              ${detailPath ? `<a class="btn btn-secondary" href="${detailPath}">View details</a>` : ""}
                              <button type="button" class="btn btn-add-plan${added ? " added" : ""}" data-add-plan="${event.id}">${added ? (auth.user?.role === "shopper" ? "Saved" : "Added to plan") : (auth.user?.role === "shopper" ? "Save Event" : "Add to My Plan")}</button>
                            </div>
                          `
                          : ""
                      }
                    </article>
                  `;
                  }).join("")}
                </div>
              </div>
            `).join("")}
          </section>
          ${
            state.mapOpen
              ? `
                <aside class="discover-plus-map">
                  <div class="discover-map-card">
                    <div class="discover-map-header">
                      <h3>Map view</h3>
                      <p class="muted">Interactive map of all events. Click a pin to see details.</p>
                    </div>
                    <div id="discover-leaflet-map" style="height:460px;border-radius:10px;overflow:hidden;"></div>
                    <div class="discover-map-filter-hint" style="margin-top:.6rem;font-size:.78rem;color:var(--muted);">
                      Showing all geo-tagged events · zoom and pan freely
                    </div>
                  </div>
                </aside>
              `
              : ""
          }
        </div>
        <div class="journey-float-bar${selectedCount > 0 ? " visible" : ""}" data-float-bar>
          <span class="float-bar-count">${selectedCount} event${selectedCount !== 1 ? "s" : ""} in your plan</span>
          <a class="btn" href="/shopper-plan">View My Plan</a>
        </div>
      </div>
    `;

    // Initialize Leaflet discover map after DOM update
    if (state.mapOpen && window.EventMap) {
      setTimeout(() => {
        if (document.getElementById("discover-leaflet-map")) {
          window.EventMap.initDiscover("discover-leaflet-map");
        }
      }, 0);
    }

    attachButtonPress(".btn", root);
    attachButtonPress(".chip", root);
    attachButtonPress(".btn-add-plan", root);

    root.querySelector("[data-discover-search-btn]")?.addEventListener("click", () => {
      const city = (root.querySelector("#discover-city-input")?.value || "").trim();
      if (city) runCitySearch(city);
    });
    root.querySelector("#discover-city-input")?.addEventListener("keydown", (e) => {
      if (e.key === "Enter") {
        const city = (e.target.value || "").trim();
        if (city) runCitySearch(city);
      }
    });

    root.querySelector("[data-map-toggle]")?.addEventListener("click", () => {
      state.mapOpen = !state.mapOpen;
      persistDiscoverFilters();
      requestRender();
    });
    root.querySelectorAll("[data-travel-mode]").forEach((button) => button.addEventListener("click", () => {
      state.travelMode = button.getAttribute("data-travel-mode");
      persistDiscoverFilters();
      requestRender();
    }));
    root.querySelectorAll("[data-distance]").forEach((button) => button.addEventListener("click", () => {
      state.distance = Number(button.getAttribute("data-distance"));
      persistDiscoverFilters();
      requestRender();
    }));
    root.querySelectorAll("[data-event-type]").forEach((button) => button.addEventListener("click", () => {
      state.eventType = button.getAttribute("data-event-type");
      persistDiscoverFilters();
      requestRender();
    }));
    root.querySelectorAll("[data-fee]").forEach((button) => button.addEventListener("click", () => {
      state.maxFee = Number(button.getAttribute("data-fee"));
      persistDiscoverFilters();
      requestRender();
    }));
    root.querySelectorAll("[data-date-range]").forEach((button) => button.addEventListener("click", () => {
      state.dateRange = button.getAttribute("data-date-range");
      persistDiscoverFilters();
      requestRender();
    }));
    root.querySelectorAll("[data-feature]").forEach((button) => button.addEventListener("click", () => {
      const feature = button.getAttribute("data-feature");
      state.features = state.features.includes(feature)
        ? state.features.filter((item) => item !== feature)
        : [...state.features, feature];
      persistDiscoverFilters();
      requestRender();
    }));
    root.querySelectorAll("[data-add-plan]").forEach((button) => {
      button.addEventListener("click", (e) => {
        e.preventDefault();
        const id = button.getAttribute("data-add-plan");
        const eventObj = scored.find((ev) => ev.id === id);
        if (id && eventObj) togglePlanSelection(id, eventObj);
      });
    });
  }

  requestRender();
}

function setupToggleGroup(selector, initialValues) {
  const selected = new Set(initialValues);
  document.querySelectorAll(selector).forEach((button) => {
    const value = button.dataset.weekday || button.dataset.month;
    button.classList.toggle("active", selected.has(value));
    button.addEventListener("click", () => {
      if (selected.has(value)) {
        selected.delete(value);
      } else {
        selected.add(value);
      }
      button.classList.toggle("active", selected.has(value));
    });
  });
  return selected;
}

function renderSavedMarketCard(event) {
  const detailPath = eventDetailPath(event.id);
  const fitScore = Number(event.fit_score ?? event.worth_it_score ?? event.schedule_fit_score ?? 0) || 0;
  const fitReason = event.fit_reason || (Array.isArray(event.score_reasons) ? event.score_reasons.slice(0, 1).join(" ") : "");
  return `
    <article class="result-card">
      <h3>${event.name}</h3>
      <p class="muted">${event.city}, ${event.state}${event.date ? ` | ${event.date}` : ""}</p>
      <div class="mini-meta">
        ${fitScore ? `<span class="pill">Fit ${fitScore}</span>` : ""}
        <span class="pill">${formatMoney(event.booth_price)}</span>
        <span class="pill">${event.event_size || "unknown"}</span>
        ${renderRecurrencePill(event.recurrence)}
      </div>
      ${fitReason ? `<p class="muted">${fitReason}</p>` : ""}
      <div class="stack-row">
        ${detailPath ? `<a class="btn btn-secondary" href="${detailPath}">Details</a>` : ""}
        ${event.application_link ? `<a class="btn btn-secondary" href="${event.application_link}" target="_blank" rel="noreferrer">Application</a>` : ""}
        <button class="btn btn-secondary" type="button" data-remove-market="${event.id}">Remove</button>
      </div>
    </article>
  `;
}

function renderRecommendationCard(event) {
  const detailPath = eventDetailPath(event.id);
  const fitScore = Number(event.schedule_fit_score ?? event.fit_score ?? event.worth_it_score ?? 0) || 0;
  const fitReason = (event.schedule_reasons || []).join(" ") || event.fit_reason || (Array.isArray(event.score_reasons) ? event.score_reasons.slice(0, 2).join(" ") : "");
  return `
    <article class="result-card">
      <h3>${event.name}</h3>
      <p class="muted">${event.city}, ${event.state}${event.date ? ` | ${event.date}` : ""}</p>
      <div class="mini-meta">
        ${fitScore ? `<span class="pill">Fit ${fitScore}</span>` : ""}
        <span class="pill">${formatMoney(event.booth_price)}</span>
        ${renderRecurrencePill(event.recurrence)}
      </div>
      ${fitReason ? `<p class="muted">${fitReason}</p>` : ""}
      ${detailPath ? `<a class="btn btn-secondary" href="${detailPath}">View details</a>` : ""}
      ${event.application_link ? `<a class="btn btn-secondary" href="${event.application_link}" target="_blank" rel="noreferrer">Open link</a>` : ""}
    </article>
  `;
}

function renderRecurringSeriesCard(series) {
  return `
    <article class="result-card">
      <strong>${series.name}</strong>
      <p class="muted">${series.city || ""}${series.city && series.state ? ", " : ""}${series.state || ""}${series.next_date ? ` | next known date ${series.next_date}` : ""}</p>
      <div class="mini-meta">
        <span class="pill pill-recurring">${series.label}</span>
        <span class="pill">${series.repeat_count} known dates</span>
      </div>
    </article>
  `;
}

function renderDashboardTracker() {
  const trackerRoot = document.querySelector("[data-dashboard-tracker]");
  if (!trackerRoot) return;

  function trackerHighlightClass(item) {
    if (item === "Apply Now") return "tracker-badge-primary";
    if (item === "Watch" || item === "Research") return "tracker-badge-secondary";
    return "tracker-badge-tertiary";
  }

  trackerRoot.innerHTML = `
    <section class="tracker-spotlight">
      <div class="tracker-spotlight-copy">
        <span class="eyebrow">${dashboardTracker.suggestedPlan.title}</span>
        <h4>${dashboardTracker.suggestedPlan.headline}</h4>
      </div>
      <div class="tracker-spotlight-list">
        ${dashboardTracker.suggestedPlan.items.map((item, index) => `
          <article class="tracker-plan-step">
            <span class="tracker-step-index">0${index + 1}</span>
            <p>${item}</p>
          </article>
        `).join("")}
      </div>
    </section>
    <div class="tracker-summary-bar">
      <div class="tracker-stat">
        <span class="tracker-stat-icon" aria-hidden="true">★</span>
        <strong>${dashboardTracker.summary.rankedMarkets}</strong>
        <span>Ranked markets</span>
      </div>
      <div class="tracker-stat">
        <span class="tracker-stat-icon" aria-hidden="true">◌</span>
        <strong>${dashboardTracker.summary.budgetEvents}</strong>
        <span>Pre-filled 2026 events</span>
      </div>
      <div class="tracker-stat">
        <span class="tracker-stat-icon" aria-hidden="true">✓</span>
        <strong>${dashboardTracker.summary.formulas}</strong>
        <span>Validated formulas</span>
      </div>
    </div>
    <div class="tracker-grid">
      ${dashboardTracker.tabs.map((tab) => `
        <article class="tracker-tab-card tracker-tab-card-${tab.tier}">
          <div class="tracker-tab-head">
            <span class="tracker-tab-icon" aria-hidden="true">${tab.icon}</span>
            <div>
              <h4>${tab.name}</h4>
              <p class="muted">${tab.blurb}</p>
            </div>
          </div>
          <div class="tracker-chip-row">
            ${tab.highlights.map((item) => `<span class="tracker-badge ${trackerHighlightClass(item)}">${item}</span>`).join("")}
          </div>
          <p class="tracker-footnote">${tab.footnote}</p>
        </article>
      `).join("")}
    </div>
    <div class="tracker-legend">
      <span class="tracker-key tracker-key-input">Blue cells: editable inputs</span>
      <span class="tracker-key tracker-key-post">Yellow cells: fill in after each market</span>
    </div>
  `;
}

function trackerMetrics(row) {
  const boothFee = Number(row.booth_fee || 0);
  const additionalCosts = Number(row.additional_costs || 0);
  const projectedRevenue = Number(row.projected_revenue || 0);
  const actualRevenue = Number(row.actual_revenue || 0);
  const revenueBasis = actualRevenue > 0 ? actualRevenue : projectedRevenue;
  const totalCost = boothFee + additionalCosts;
  const netProfit = revenueBasis - totalCost;
  const roi = totalCost > 0 ? (netProfit / totalCost) * 100 : 0;
  return {
    ...row,
    net_profit: Number(netProfit.toFixed(2)),
    roi: Number(roi.toFixed(1)),
  };
}

function buildLocalTrackerSummary(rows) {
  const total = (field) => rows.reduce((sum, row) => sum + Number(row[field] || 0), 0);
  return {
    total_booth_fees: Number(total("booth_fee").toFixed(2)),
    total_additional_costs: Number(total("additional_costs").toFixed(2)),
    total_projected_revenue: Number(total("projected_revenue").toFixed(2)),
    total_actual_revenue: Number(total("actual_revenue").toFixed(2)),
    total_net_profit: Number(rows.reduce((sum, row) => sum + Number(row.net_profit || 0), 0).toFixed(2)),
    average_roi: rows.length ? Number((rows.reduce((sum, row) => sum + Number(row.roi || 0), 0) / rows.length).toFixed(1)) : 0,
  };
}

function buildFallbackTracker(seedMarkets = []) {
  const appCalendar = (seedMarkets || []).slice(0, 5).map((market, index) => ({
    event_id: market.id || "",
    name: market.name || `Priority Market ${index + 1}`,
    city: market.city || "",
    state: market.state || "",
    date: market.date || "",
    status: index < 2 ? "Apply Now" : index < 4 ? "Watch" : "Research",
    booth_fee: Number(market.booth_price || 0),
    traffic: Number(market.estimated_traffic || 0),
    vendor_count: Number(market.vendor_count || 0),
    priority_stars: Math.max(1, 5 - index),
    notes: "",
    apply_url: market.application_link || "",
  }));

  while (appCalendar.length < 5) {
    const index = appCalendar.length;
    appCalendar.push({
      event_id: "",
      name: `Priority Market ${index + 1}`,
      city: "",
      state: "",
      date: "",
      status: index < 2 ? "Apply Now" : index < 4 ? "Watch" : "Research",
      booth_fee: 0,
      traffic: 0,
      vendor_count: 0,
      priority_stars: Math.max(1, 5 - index),
      notes: "",
      apply_url: "",
    });
  }

  const budgetRows = [];
  for (let index = 0; index < dashboardTracker.summary.budgetEvents; index += 1) {
    const market = seedMarkets[index] || {};
    const month = monthLabels[(index + 3) % monthLabels.length];
    budgetRows.push(trackerMetrics({
      event_id: market.id || "",
      month,
      date: market.date || "",
      event_name: market.name || "",
      booth_fee: Number(market.booth_price || 0),
      additional_costs: 0,
      projected_revenue: 0,
      actual_revenue: 0,
      units_sold: 0,
    }));
  }

  return {
    application_calendar: appCalendar,
    booth_budget: budgetRows,
    selection_criteria: {
      booth_price_guide: [
        "Under $125: strong low-risk test if traffic is credible.",
        "$125-$250: reasonable if fit and turnout are above average.",
        "$250+: only when traffic quality and organizer confidence are both strong.",
      ],
      traffic_benchmarks: [
        "2,500+ visitors: strong signal.",
        "1,000-2,499 visitors: viable if audience fit is tight.",
        "Under 1,000: test carefully unless niche alignment is excellent.",
      ],
      warning_signs: [
        "No clear organizer contact or setup instructions.",
        "High booth fee without turnout proof.",
        "Vague audience details or inconsistent market dates.",
      ],
      notes: "",
    },
    summary: buildLocalTrackerSummary(budgetRows),
    updated_at: "",
    local_only: true,
  };
}

function readLocalTracker(seedMarkets = []) {
  try {
    const raw = window.localStorage.getItem(LOCAL_TRACKER_STORAGE_KEY);
    if (!raw) return buildFallbackTracker(seedMarkets);
    const parsed = JSON.parse(raw);
    const boothBudget = (parsed.booth_budget || []).map((row) => trackerMetrics(row));
    return {
      ...buildFallbackTracker(seedMarkets),
      ...parsed,
      booth_budget: boothBudget,
      summary: buildLocalTrackerSummary(boothBudget),
      local_only: true,
    };
  } catch {
    return buildFallbackTracker(seedMarkets);
  }
}

function saveLocalTrackerDraft(payload) {
  const boothBudget = (payload.booth_budget || []).map((row) => trackerMetrics(row));
  const tracker = {
    ...payload,
    booth_budget: boothBudget,
    summary: buildLocalTrackerSummary(boothBudget),
    updated_at: new Date().toISOString(),
    local_only: true,
  };
  window.localStorage.setItem(LOCAL_TRACKER_STORAGE_KEY, JSON.stringify(tracker));
  return tracker;
}

function renderUsableDashboardTracker(tracker) {
  const trackerRoot = document.querySelector("[data-dashboard-tracker]");
  if (!trackerRoot) return;

  function trackerHighlightClass(item) {
    if (item === "Apply Now") return "tracker-badge-primary";
    if (item === "Watch" || item === "Research") return "tracker-badge-secondary";
    return "tracker-badge-tertiary";
  }

  const summary = tracker.summary || {};
  const updatedAt = tracker.updated_at ? new Date(tracker.updated_at.replace(" ", "T")).toLocaleString() : "Not saved yet";
  const saveLabel = tracker.local_only ? "Save Draft" : "Save Tracker";
  const saveHint = tracker.local_only ? "Local draft mode" : `Last saved: ${updatedAt}`;

  trackerRoot.innerHTML = `
    <section class="tracker-spotlight">
      <div class="tracker-spotlight-copy">
        <span class="eyebrow">${dashboardTracker.suggestedPlan.title}</span>
        <h4>${dashboardTracker.suggestedPlan.headline}</h4>
      </div>
      <div class="tracker-spotlight-list">
        ${dashboardTracker.suggestedPlan.items.map((item, index) => `
          <article class="tracker-plan-step">
            <span class="tracker-step-index">0${index + 1}</span>
            <p>${item}</p>
          </article>
        `).join("")}
      </div>
    </section>
    <div class="tracker-toolbar">
      <div class="tracker-tabs" role="tablist" aria-label="Vendor tracker sections">
        ${dashboardTracker.tabs.map((tab, index) => `<button class="tracker-tab-toggle${index === 0 ? " active" : ""}" type="button" data-tracker-tab="${index}">${tab.name}</button>`).join("")}
      </div>
      <div class="tracker-actions">
        <span class="muted">${saveHint}</span>
        <button class="btn btn-primary" type="button" data-save-tracker>${saveLabel}</button>
      </div>
    </div>
    <div class="tracker-summary-bar">
      <div class="tracker-stat">
        <span class="tracker-stat-icon" aria-hidden="true">A</span>
        <strong>${tracker.application_calendar.length}</strong>
        <span>Ranked markets</span>
      </div>
      <div class="tracker-stat">
        <span class="tracker-stat-icon" aria-hidden="true">B</span>
        <strong>${tracker.booth_budget.length}</strong>
        <span>Tracked events</span>
      </div>
      <div class="tracker-stat">
        <span class="tracker-stat-icon" aria-hidden="true">$</span>
        <strong>${formatMoney(summary.total_net_profit || 0)}</strong>
        <span>Net profit</span>
      </div>
    </div>
    <div class="tracker-grid">
      ${dashboardTracker.tabs.map((tab, index) => `
        <article class="tracker-tab-card tracker-tab-card-${tab.tier}${index === 0 ? " active" : ""}" data-tracker-panel="${index}">
          <div class="tracker-tab-head">
            <span class="tracker-tab-icon" aria-hidden="true">${tab.icon}</span>
            <div>
              <h4>${tab.name}</h4>
              <p class="muted">${tab.blurb}</p>
            </div>
          </div>
          <div class="tracker-chip-row">
            ${tab.highlights.map((item) => `<span class="tracker-badge ${trackerHighlightClass(item)}">${item}</span>`).join("")}
          </div>
          <p class="tracker-footnote">${tab.footnote}</p>
          ${
            index === 0
              ? `
                <div class="tracker-table-wrap">
                  <table class="tracker-table">
                    <thead>
                      <tr>
                        <th>Market</th>
                        <th>Status</th>
                        <th>Booth Fee</th>
                        <th>Traffic</th>
                        <th>Vendors</th>
                        <th>Priority</th>
                        <th>Notes</th>
                      </tr>
                    </thead>
                    <tbody>
                      ${(tracker.application_calendar || []).map((item, itemIndex) => `
                        <tr data-app-row="${itemIndex}">
                          <td>
                            <strong>${item.name || "Untitled Market"}</strong>
                            <div class="muted">${[item.city, item.state].filter(Boolean).join(", ")}${item.date ? ` | ${item.date}` : ""}</div>
                            ${item.apply_url ? `<a class="tracker-inline-link" href="${item.apply_url}" target="_blank" rel="noreferrer">Open listing</a>` : ""}
                          </td>
                          <td>
                            <select data-app-field="status">
                              ${["Apply Now", "Watch", "Research"].map((status) => `<option value="${status}"${status === item.status ? " selected" : ""}>${status}</option>`).join("")}
                            </select>
                          </td>
                          <td><input data-app-field="booth_fee" type="number" step="0.01" value="${item.booth_fee ?? 0}"></td>
                          <td><input data-app-field="traffic" type="number" step="1" value="${item.traffic ?? 0}"></td>
                          <td><input data-app-field="vendor_count" type="number" step="1" value="${item.vendor_count ?? 0}"></td>
                          <td>
                            <select data-app-field="priority_stars">
                              ${[5, 4, 3, 2, 1].map((stars) => `<option value="${stars}"${Number(item.priority_stars) === stars ? " selected" : ""}>${"*".repeat(stars)}</option>`).join("")}
                            </select>
                          </td>
                          <td><textarea data-app-field="notes" rows="2" placeholder="Deadline, fit, follow-up">${item.notes || ""}</textarea></td>
                          <input data-app-field="event_id" type="hidden" value="${item.event_id || ""}">
                          <input data-app-field="name" type="hidden" value="${item.name || ""}">
                          <input data-app-field="city" type="hidden" value="${item.city || ""}">
                          <input data-app-field="state" type="hidden" value="${item.state || ""}">
                          <input data-app-field="date" type="hidden" value="${item.date || ""}">
                          <input data-app-field="apply_url" type="hidden" value="${item.apply_url || ""}">
                        </tr>
                      `).join("")}
                    </tbody>
                  </table>
                </div>
              `
              : ""
          }
          ${
            index === 1
              ? `
                <div class="tracker-table-wrap">
                  <table class="tracker-table tracker-table-budget">
                    <thead>
                      <tr>
                        <th>Event</th>
                        <th>Month</th>
                        <th>Booth Fee</th>
                        <th>Additional Costs</th>
                        <th>Projected Revenue</th>
                        <th>Actual Revenue</th>
                        <th>Units Sold</th>
                        <th>Net Profit</th>
                        <th>ROI</th>
                      </tr>
                    </thead>
                    <tbody>
                      ${(tracker.booth_budget || []).map((row, rowIndex) => `
                        <tr data-budget-row="${rowIndex}">
                          <td>
                            <input data-budget-field="event_name" type="text" value="${row.event_name || ""}" placeholder="Event name">
                            <div class="muted">${row.date || ""}</div>
                            <input data-budget-field="event_id" type="hidden" value="${row.event_id || ""}">
                            <input data-budget-field="date" type="hidden" value="${row.date || ""}">
                          </td>
                          <td><input data-budget-field="month" type="text" value="${row.month || ""}" placeholder="Month"></td>
                          <td><input data-budget-field="booth_fee" class="tracker-input-input" type="number" step="0.01" value="${row.booth_fee ?? 0}"></td>
                          <td><input data-budget-field="additional_costs" class="tracker-input-input" type="number" step="0.01" value="${row.additional_costs ?? 0}"></td>
                          <td><input data-budget-field="projected_revenue" class="tracker-input-input" type="number" step="0.01" value="${row.projected_revenue ?? 0}"></td>
                          <td><input data-budget-field="actual_revenue" class="tracker-input-post" type="number" step="0.01" value="${row.actual_revenue ?? 0}"></td>
                          <td><input data-budget-field="units_sold" class="tracker-input-post" type="number" step="1" value="${row.units_sold ?? 0}"></td>
                          <td data-budget-output="net_profit">${formatMoney(row.net_profit || 0)}</td>
                          <td data-budget-output="roi">${Number(row.roi || 0).toFixed(1)}%</td>
                        </tr>
                      `).join("")}
                    </tbody>
                  </table>
                </div>
              `
              : ""
          }
          ${
            index === 2
              ? `
                <div class="tracker-criteria-grid">
                  <article class="tracker-criteria-card">
                    <h5>Booth Price Guide</h5>
                    <ul>${(tracker.selection_criteria?.booth_price_guide || []).map((item) => `<li>${item}</li>`).join("")}</ul>
                  </article>
                  <article class="tracker-criteria-card">
                    <h5>Traffic Benchmarks</h5>
                    <ul>${(tracker.selection_criteria?.traffic_benchmarks || []).map((item) => `<li>${item}</li>`).join("")}</ul>
                  </article>
                  <article class="tracker-criteria-card">
                    <h5>Warning Signs</h5>
                    <ul>${(tracker.selection_criteria?.warning_signs || []).map((item) => `<li>${item}</li>`).join("")}</ul>
                  </article>
                </div>
                <div class="field tracker-notes-field">
                  <label for="tracker_selection_notes">Decision notes</label>
                  <textarea id="tracker_selection_notes" data-criteria-notes rows="5" placeholder="Keep notes on organizer quality, red flags, or pricing rules here.">${tracker.selection_criteria?.notes || ""}</textarea>
                </div>
              `
              : ""
          }
        </article>
      `).join("")}
    </div>
    <div class="tracker-legend">
      <span class="tracker-key tracker-key-input">Blue cells: editable inputs</span>
      <span class="tracker-key tracker-key-post">Yellow cells: fill in after each market</span>
    </div>
    <div class="status" data-tracker-status></div>
  `;

  const tabButtons = trackerRoot.querySelectorAll("[data-tracker-tab]");
  const tabPanels = trackerRoot.querySelectorAll("[data-tracker-panel]");
  tabButtons.forEach((button) => {
    button.addEventListener("click", () => {
      const tabIndex = button.getAttribute("data-tracker-tab");
      tabButtons.forEach((item) => item.classList.toggle("active", item === button));
      tabPanels.forEach((panel) => panel.classList.toggle("active", panel.getAttribute("data-tracker-panel") === tabIndex));
    });
  });
}

function collectDashboardTrackerPayload() {
  const trackerRoot = document.querySelector("[data-dashboard-tracker]");
  if (!trackerRoot) return null;

  const application_calendar = Array.from(trackerRoot.querySelectorAll("[data-app-row]")).map((row) => {
    const data = {};
    row.querySelectorAll("[data-app-field]").forEach((field) => {
      data[field.getAttribute("data-app-field")] = field.value;
    });
    return data;
  });

  const booth_budget = Array.from(trackerRoot.querySelectorAll("[data-budget-row]")).map((row) => {
    const data = {};
    row.querySelectorAll("[data-budget-field]").forEach((field) => {
      data[field.getAttribute("data-budget-field")] = field.value;
    });
    return data;
  });

  return {
    application_calendar,
    booth_budget,
    selection_criteria: {
      notes: trackerRoot.querySelector("[data-criteria-notes]")?.value || "",
    },
  };
}

function bindTrackerBudgetCalculations() {
  const trackerRoot = document.querySelector("[data-dashboard-tracker]");
  if (!trackerRoot) return;

  function updateBudgetRow(row) {
    const boothFee = Number(row.querySelector('[data-budget-field="booth_fee"]')?.value || 0);
    const additionalCosts = Number(row.querySelector('[data-budget-field="additional_costs"]')?.value || 0);
    const projectedRevenue = Number(row.querySelector('[data-budget-field="projected_revenue"]')?.value || 0);
    const actualRevenue = Number(row.querySelector('[data-budget-field="actual_revenue"]')?.value || 0);
    const revenueBasis = actualRevenue > 0 ? actualRevenue : projectedRevenue;
    const totalCost = boothFee + additionalCosts;
    const netProfit = revenueBasis - totalCost;
    const roi = totalCost > 0 ? (netProfit / totalCost) * 100 : 0;
    row.querySelector('[data-budget-output="net_profit"]').textContent = formatMoney(netProfit);
    row.querySelector('[data-budget-output="roi"]').textContent = `${roi.toFixed(1)}%`;
  }

  trackerRoot.querySelectorAll("[data-budget-row]").forEach((row) => {
    row.querySelectorAll(".tracker-input-input, .tracker-input-post").forEach((input) => {
      input.addEventListener("input", () => updateBudgetRow(row));
    });
    updateBudgetRow(row);
  });
}

function renderKansasCityListingCard(event, authenticated, isDiscovered = false) {
  const title = event.title || event.name || "Untitled Event";
  const city = event.city || "Kansas City";
  const state = event.state || "MO";
  const date = event.date ? ` | ${event.date}` : "";
  const link = event.url || event.application_link || event.source_url || "";
  const eventId = event.event_id || event.id || "";
  const analysis = event.analysis;

  function ratingClass(value) {
    if (value >= 9) return "rating-top";
    if (value >= 7) return "rating-high";
    if (value >= 4) return "rating-mid";
    return "rating-low";
  }

  function ratingRow(label, value) {
    return `
      <div class="analysis-row">
        <div>
          <div class="analysis-label">${label}</div>
          <div class="rating-track"><div class="rating-fill" style="width:${Math.max(10, Number(value) * 10)}%"></div></div>
        </div>
        <div class="rating-badge ${ratingClass(Number(value))}">${value}</div>
      </div>
    `;
  }

  return `
    <article class="result-card">
      <h3>${title}</h3>
      <p class="muted">${city}, ${state}${date}</p>
      <div class="mini-meta">
        ${event.booth_price !== undefined && event.booth_price !== null ? `<span class="pill">${formatMoney(event.booth_price)}</span>` : ""}
        ${event.event_size ? `<span class="pill">${event.event_size}</span>` : ""}
        ${event.source ? `<span class="pill">${event.source}</span>` : ""}
        ${isDiscovered ? `<span class="pill">new</span>` : ""}
        ${renderRecurrencePill(event.recurrence)}
      </div>
      <p class="muted">
        ${event.vendor_count ? `Vendors: ${event.vendor_count}` : ""}
        ${event.vendor_count && event.estimated_traffic ? " | " : ""}
        ${event.estimated_traffic ? `Traffic: ${event.estimated_traffic}` : ""}
      </p>
      ${
        analysis
          ? `
            <div class="analysis-grid">
              ${ratingRow("Profit potential", analysis.ratings.profit_potential)}
              ${ratingRow("Traffic quality", analysis.ratings.traffic_quality)}
              ${ratingRow("Booth cost fairness", analysis.ratings.booth_cost_fairness)}
              ${ratingRow("Competition level", analysis.ratings.competition_level)}
              ${ratingRow("Overall worth-it", analysis.ratings.overall_worth_it)}
            </div>
            <p class="muted">Revenue: ${formatMoney(analysis.estimated_revenue)} | Cost: ${formatMoney(analysis.estimated_cost)} | Profit: ${formatMoney(analysis.estimated_profit)}</p>
            <p><strong>${analysis.recommendation}</strong></p>
            <p class="muted">${analysis.explanation}</p>
          `
          : ""
      }
      <div class="stack-row">
        ${link ? `<a class="btn btn-secondary" href="${link}" target="_blank" rel="noreferrer">Open Link</a>` : ""}
        ${
          authenticated && eventId
            ? `<button class="btn btn-primary" type="button" data-save-market="${eventId}">Save to Dashboard</button>`
            : ""
        }
      </div>
    </article>
  `;
}

function friendlyMarketName(event, index) {
  return event?.name || event?.title || `Market Option ${index + 1}`;
}

function moneyNumber(value) {
  const parsed = Number(value || 0);
  return Number.isFinite(parsed) ? parsed : 0;
}

function evaluateDecisionHelper(answers) {
  let score = 0;
  if (answers.boothFee === "low") score += 2;
  if (answers.boothFee === "medium") score += 1;
  if (answers.traffic === "high") score += 2;
  if (answers.traffic === "medium") score += 1;
  if (answers.organizer === "clear") score += 2;
  if (answers.organizer === "somewhat") score += 1;

  if (score >= 5) return { label: "Worth it", tone: "success", text: "This looks like a strong event to try." };
  if (score >= 3) return { label: "Risky", tone: "", text: "This might work, but you should ask a few more questions before paying." };
  return { label: "Skip", tone: "error", text: "This looks too risky for now. Save your money for a better fit." };
}

function buildMockProducts(interests) {
  const focus = interests || "your best sellers";
  return [
    { id: "prod-1", name: `${focus} Starter Set`, price: 24 },
    { id: "prod-2", name: "Weekend Best Seller", price: 38 },
    { id: "prod-3", name: "Gift Bundle", price: 52 },
  ];
}

function scorePlannerEvent(event, preferences) {
  let score = 0;
  const reasons = [];
  const boothFee = Number(event?.booth_price || 0);
  const traffic = Number(event?.estimated_traffic || 0);
  const eventSize = String(event?.event_size || "").toLowerCase();

  if (preferences.travel === "30") {
    score += 2;
    reasons.push("Best when you want to stay close to home.");
  } else if (preferences.travel === "60") {
    score += 1;
    reasons.push("A reasonable drive for a planned weekend.");
  } else {
    score += 1;
    reasons.push("Works if you are open to going farther for the right event.");
  }

  if (preferences.transportation === "difficult") {
    if (eventSize === "small" || eventSize === "medium") {
      score += 2;
      reasons.push("Feels easier for a business with tighter transportation limits.");
    } else {
      score -= 1;
      reasons.push("This may feel harder if loading and travel are tough right now.");
    }
  } else if (preferences.transportation === "some") {
    score += 1;
  }

  if (preferences.boothFeeComfort === "low") {
    if (boothFee <= 125) {
      score += 2;
      reasons.push("The booth fee stays in the lower-risk range.");
    } else {
      score -= 1;
      reasons.push("The booth fee may feel higher than you want right now.");
    }
  } else if (preferences.boothFeeComfort === "depends") {
    if (boothFee <= 225) score += 1;
  } else if (boothFee > 0) {
    score += 1;
    reasons.push("You said you can pay more when the fit is strong.");
  }

  if (preferences.setup === "light" && eventSize === "small") {
    score += 2;
    reasons.push("Looks like a lighter setup day.");
  } else if (preferences.setup === "heavy" && eventSize === "large") {
    score += 1;
    reasons.push("A larger event may be worth the bigger setup effort.");
  } else if (preferences.setup === "moderate") {
    score += 1;
  }

  if ((preferences.mustHaves || []).includes("foot traffic")) {
    if (traffic >= 2500) {
      score += 2;
      reasons.push("Traffic looks strong for getting seen.");
    } else if (traffic > 0) {
      score -= 1;
      reasons.push("Traffic may be lighter than you want.");
    }
  }

  if ((preferences.mustHaves || []).includes("indoor")) {
    reasons.push("Keep an eye on whether this event is indoor before booking.");
  }
  if ((preferences.mustHaves || []).includes("parking")) {
    reasons.push("Parking matters to you, so confirm load-in details first.");
  }
  if ((preferences.mustHaves || []).includes("electricity")) {
    reasons.push("Ask the organizer if power is available before you commit.");
  }

  if (preferences.goal === "practice") {
    if (boothFee <= 150) {
      score += 1;
      reasons.push("Good for getting reps without overcommitting.");
    }
  } else if (preferences.goal === "break_even") {
    if (boothFee <= 200) score += 1;
  } else if (preferences.goal === "profit") {
    if (traffic >= 2000) {
      score += 2;
      reasons.push("Better upside if your goal is real profit.");
    }
  }

  if (preferences.risk === "safe") {
    if (traffic >= 2000 && boothFee <= 200) {
      score += 1;
      reasons.push("This feels steadier for a play-it-safe weekend.");
    } else {
      score -= 1;
    }
  } else if (preferences.risk === "try_anything") {
    score += 1;
  }

  let bucket = "Worth Trying";
  if (score >= 6) bucket = "Best Matches";
  else if (score <= 1) bucket = "Probably Skip";

  return {
    bucket,
    score,
    explanation: reasons.slice(0, 3).join(" "),
  };
}

function renderGuidedDashboardApp(root, payload, auth) {
  const user = payload?.user || auth.user || { name: "friend", interests: "" };
  const savedMarkets = payload?.saved_markets || [];
  const recommendations = payload?.recommended_markets || savedMarkets.slice(0, 3);
  const shopify = payload?.shopify || null;
  const plannedEvents = getSelectedEvents();
  const eventChoices = (plannedEvents.length ? plannedEvents : recommendations.length ? recommendations : savedMarkets).slice(0, 3);
  const mockProducts = buildMockProducts(user.interests);

  const profiles = getProfiles();
  const currentProfileId = getCurrentProfileId();
  const currentProfile = currentProfileId ? profiles.find((p) => p.id === currentProfileId) : null;
  const draft = getPlanningDraft();
  const journeyProgress = getJourneyProgress();

  const state = {
    mode: journeyProgress.mode || "home",
    weekendStep: Number(journeyProgress.weekendStep || 0),
    profitStep: Number(journeyProgress.profitStep || 0),
    eventStep: Number(journeyProgress.eventStep || 0),
    weekend: {
      travel: "",
      transportation: "",
      boothFeeComfort: "",
      setup: "",
      mustHaves: [],
      goal: "",
      risk: "",
    },
    profit: {
      boothFee: draft?.profit?.boothFee || "",
      revenue: draft?.profit?.revenue || "",
      costs: draft?.profit?.costs || "",
    },
    helper: {
      boothFee: draft?.helper?.boothFee || "",
      traffic: draft?.helper?.traffic || "",
      organizer: draft?.helper?.organizer || "",
    },
    storeConnected: false,
    cart: [],
    profiles,
    currentProfileId,
  };
  if (currentProfile?.answers) {
    state.weekend = {
      travel: currentProfile.answers.travel || "",
      transportation: currentProfile.answers.transportation || "",
      boothFeeComfort: currentProfile.answers.boothFeeComfort || "",
      setup: currentProfile.answers.setup || "",
      mustHaves: Array.isArray(currentProfile.answers.mustHaves) ? currentProfile.answers.mustHaves : [],
      goal: currentProfile.answers.goal || "",
      risk: currentProfile.answers.risk || "",
    };
  } else if (draft) {
    state.weekend = {
      travel: draft.travel || "",
      transportation: draft.transportation || "",
      boothFeeComfort: draft.boothFeeComfort || "",
      setup: draft.setup || "",
      mustHaves: Array.isArray(draft.mustHaves) ? draft.mustHaves : [],
      goal: draft.goal || "",
      risk: draft.risk || "",
    };
  }

  function persistJourneyState() {
    savePlanningDraft({
      ...state.weekend,
      profit: { ...state.profit },
      helper: { ...state.helper },
    });
    setJourneyProgress({
      mode: state.mode,
      weekendStep: state.weekendStep,
      profitStep: state.profitStep,
      eventStep: state.eventStep,
    });
  }

  function cartTotal() {
    return state.cart.reduce((sum, item) => sum + item.price, 0);
  }

  function renderHome() {
    const hasDraftProgress = Boolean(
      Object.values(state.weekend || {}).filter((value) => Array.isArray(value) ? value.length : value).length
      || Object.values(state.profit || {}).filter(Boolean).length
      || Object.values(state.helper || {}).filter(Boolean).length
    );
    const savedPreview = (plannedEvents.length ? plannedEvents : savedMarkets).slice(0, 3);
    const profileOptions = state.profiles.length
      ? state.profiles
          .map(
            (p) =>
              `<option value="${p.id}" ${p.id === state.currentProfileId ? "selected" : ""}>${escapeHtml(p.name || "Profile")}</option>`
          )
          .join("")
      : "";
    root.innerHTML = `
      <div class="guided-shell journey-step">
        <section class="profile-bar" data-profile-bar>
          <label class="profile-label">Use profile:</label>
          <select class="profile-select" data-profile-select>
            <option value="">No profile</option>
            ${profileOptions}
            <option value="__new__">+ New profile</option>
          </select>
          <button type="button" class="btn btn-ghost btn-sm" data-profile-save title="Save current answers as profile">Save as profile</button>
        </section>
        <section class="journey-dashboard-cta">
          <span class="eyebrow">Your market assistant</span>
          <h2>Find your next best events in one flow.</h2>
          <p>Answer a few quick questions and we'll surface events that fit you—then add your favorites to your plan and see your profit picture.</p>
          <div class="stack-row">
            <button class="btn btn-primary" type="button" data-guided-start="weekend">${hasDraftProgress ? "Resume Planning" : "Start Planning"}</button>
            <a class="btn btn-secondary" href="/discover">Go to Discover</a>
            <a class="btn btn-secondary" href="/final-plan">Open Final Plan</a>
          </div>
        </section>
        <section class="journey-dashboard-secondary">
          <button class="btn btn-secondary" type="button" data-guided-start="profit">Track My Profit</button>
          <a class="btn btn-secondary" href="/business">My Business</a>
          <a class="btn btn-secondary" href="/profile">Profiles</a>
        </section>
        <section class="dashboard-card">
          <span class="eyebrow">Saved markets</span>
          <h3>Your shortlist and next moves</h3>
          ${
            savedPreview.length
              ? renderStreamList(savedPreview, (event) => `
                  <div class="atlas-stream-card">
                    <div class="atlas-stream-main">
                      <strong>${escapeHtml(event.name || event.title || "Event")}</strong>
                      <div class="atlas-stream-meta">${escapeHtml([event.city, event.state].filter(Boolean).join(", "))}${event.date ? ` | ${escapeHtml(event.date)}` : ""}</div>
                      <div class="atlas-stream-note">${event.fit_reason ? escapeHtml(event.fit_reason) : "Saved and ready to compare in your plan."}</div>
                    </div>
                    <div class="atlas-stream-aside">
                      <a class="btn btn-secondary" href="${event.id ? eventDetailPath(event.id) : "/discover"}">View</a>
                    </div>
                  </div>
                `)
              : `<div class="empty-state"><strong>No saved markets yet.</strong><p class="muted">Use Discover or Find Market to save a few events, then they’ll show up here for quick review.</p><div class="stack-row"><a class="btn btn-primary" href="/discover">Browse Discover</a></div></div>`
          }
        </section>
        <section class="dashboard-card">
          <span class="eyebrow">Vendor tools</span>
          <h3>Build your business page and selling setup</h3>
          <p class="muted">Use these tools to shape the public page shoppers see, connect your storefront, and keep your vendor presence feeling more like a real business hub.</p>
          <div class="tool-grid">
            <div class="tool-card">
              <strong>Business page studio</strong>
              <p class="muted">Manage profile copy, saved profiles, and the public page shoppers visit.</p>
              <div class="stack-row">
                <a class="btn btn-primary" href="/profile">Edit profile</a>
                ${auth.user?.username ? `<a class="btn btn-secondary" href="/u/${encodeURIComponent(auth.user.username)}">Preview page</a>` : ""}
              </div>
            </div>
            <div class="tool-card">
              <strong>Shopify store</strong>
              ${shopify?.connected
                ? `<p class="muted" style="display:flex;align-items:center;gap:.4rem;">
                    <span style="color:var(--success);font-weight:700;">✓ Connected</span>
                    <span>${escapeHtml(String(shopify.shop || "").replace(".myshopify.com", ""))}</span>
                  </p>
                  <div class="stack-row">
                    ${auth.user?.username ? `<a class="btn btn-primary" href="/shop/${encodeURIComponent(auth.user.username)}">View my shop</a>` : ""}
                    <button class="btn btn-secondary" type="button" data-shopify-sync-dash>Sync products</button>
                    <a class="btn btn-ghost" href="/integrations">Settings</a>
                  </div>`
                : `<p class="muted">Connect your Shopify store to show products on your public vendor page.</p>
                  <div class="stack-row" style="flex-wrap:wrap;gap:.5rem;">
                    <input class="mini-input" id="dash_shopify_store" placeholder="yourstore" style="max-width:160px;">
                    <button class="btn btn-primary" type="button" data-shopify-connect-dash>Connect Shopify</button>
                  </div>`
              }
            </div>
            <div class="tool-card">
              <strong>Event plan and route</strong>
              <p class="muted">Turn saved events into a real plan with route, inventory, and profit context before you commit.</p>
              <div class="stack-row">
                <a class="btn btn-primary" href="/final-plan">Open Final Plan</a>
                <a class="btn btn-secondary" href="/discover">Find more events</a>
              </div>
            </div>
            <div class="tool-card">
              <strong>Followers and event sharing</strong>
              <p class="muted">Choose which saved events followers can see and keep your public activity fresh.</p>
              <div class="stack-row">
                <a class="btn btn-primary" href="/history">View history</a>
                <a class="btn btn-secondary" href="/business">Open analytics</a>
              </div>
            </div>
          </div>
        </section>
        <section class="dashboard-card">
          <span class="eyebrow">Followers</span>
          <h3>Share events with your followers</h3>
          <div data-follower-events-panel>
            <div class="empty-state"><strong>Loading follower events…</strong></div>
          </div>
        </section>
      </div>
    `;

    attachButtonPress(".btn", root);
    attachButtonPress(".guided-action", root);

    root.querySelector("[data-shopify-connect-dash]")?.addEventListener("click", () => {
      const shop = (root.querySelector("#dash_shopify_store")?.value || "").trim();
      if (!shop) return;
      shopifyConnectFromInput("dash_shopify_store");
    });
    root.querySelector("[data-shopify-sync-dash]")?.addEventListener("click", async (e) => {
      const btn = e.currentTarget;
      btn.disabled = true;
      btn.textContent = "Syncing…";
      try {
        await fetch("/api/shopify/sync", { method: "POST", credentials: "include" });
        btn.textContent = "Synced ✓";
      } catch (_) { btn.textContent = "Sync products"; }
      setTimeout(() => { btn.disabled = false; btn.textContent = "Sync products"; }, 3000);
    });

    root.querySelector("[data-profile-select]")?.addEventListener("change", (e) => {
      const id = e.target.value || null;
      if (id === "__new__") {
        const name = window.prompt("Profile name?", "My vendor profile");
        if (!name) {
          e.target.value = state.currentProfileId || "";
          return;
        }
        const newId = saveProfile({ name, answers: { ...state.weekend } });
        state.profiles = getProfiles();
        state.currentProfileId = newId;
        setCurrentProfileId(newId);
        persistJourneyState();
        render();
        return;
      }
      setCurrentProfileId(id);
      state.currentProfileId = id;
      const prof = id ? state.profiles.find((p) => p.id === id) : null;
      if (prof?.answers) {
        state.weekend = {
          travel: prof.answers.travel || "",
          transportation: prof.answers.transportation || "",
          boothFeeComfort: prof.answers.boothFeeComfort || "",
          setup: prof.answers.setup || "",
          mustHaves: Array.isArray(prof.answers.mustHaves) ? prof.answers.mustHaves : [],
          goal: prof.answers.goal || "",
          risk: prof.answers.risk || "",
        };
      } else if (!id) {
        state.weekend = {
          travel: "",
          transportation: "",
          boothFeeComfort: "",
          setup: "",
          mustHaves: [],
          goal: "",
          risk: "",
        };
      }
      persistJourneyState();
      render();
    });
    root.querySelector("[data-profile-save]")?.addEventListener("click", () => {
      const name = window.prompt("Profile name?", "My vendor profile");
      if (!name) return;
      const id = saveProfile({ name, answers: { ...state.weekend } });
      state.profiles = getProfiles();
      state.currentProfileId = id;
      setCurrentProfileId(id);
      persistJourneyState();
      render();
    });

    root.querySelector("[data-guided-start='weekend']")?.addEventListener("click", () => {
      root.innerHTML = `
        <div class="guided-flow-card journey-step journey-loading">
          <div class="spinner"></div>
          <h2>Opening your planning flow…</h2>
          <p class="muted">Getting your first question ready.</p>
        </div>
      `;
      setTimeout(() => {
        state.mode = "weekend";
        if (!hasDraftProgress) state.weekendStep = 0;
        persistJourneyState();
        render();
      }, 180);
    });
    root.querySelector("[data-guided-start='profit']")?.addEventListener("click", () => {
      root.innerHTML = `
        <div class="guided-flow-card journey-step journey-loading">
          <div class="spinner"></div>
          <h2>Opening your profit check…</h2>
          <p class="muted">Pulling your revenue and cost inputs into place.</p>
        </div>
      `;
      setTimeout(() => {
        state.mode = "profit";
        persistJourneyState();
        render();
      }, 180);
    });

    const followerPanel = root.querySelector("[data-follower-events-panel]");
    if (followerPanel && auth.user?.role === "vendor") {
      api("/api/vendor/follower-events", { method: "GET" })
        .then((payload) => {
          const rows = payload.events || [];
          followerPanel.innerHTML = rows.length
            ? renderStreamList(rows.slice(0, 5), (event) => `
                <div class="atlas-stream-card">
                  <div class="atlas-stream-main">
                    <strong>${escapeHtml(event.name || "Event")}</strong>
                    <div class="atlas-stream-meta">${escapeHtml([event.city, event.state].filter(Boolean).join(", "))}${event.date ? ` | ${escapeHtml(event.date)}` : ""}</div>
                  </div>
                  <div class="atlas-stream-aside">
                    <button class="btn btn-secondary" type="button" data-follower-toggle="${event.id}">${event.visible_to_followers ? "Visible to followers" : "Share with followers"}</button>
                  </div>
                </div>
              `)
            : `<div class="empty-state"><strong>No saved events yet.</strong><p class="muted">Save events first, then choose which ones followers should see.</p></div>`;

          followerPanel.querySelectorAll("[data-follower-toggle]").forEach((button) => {
            button.addEventListener("click", async () => {
              const eventId = button.getAttribute("data-follower-toggle");
              const turningOff = button.textContent.includes("Visible");
              await api("/api/vendor/follower-events", {
                method: "POST",
                body: JSON.stringify({ event_id: eventId, visible_to_followers: !turningOff }),
              });
              showToast(turningOff ? "Event hidden from followers" : "Followers can now see this event", "success");
              render();
            });
          });
          attachButtonPress(".btn", followerPanel);
        })
        .catch(() => {
          followerPanel.innerHTML = `<div class="empty-state"><strong>We couldn't load follower sharing right now.</strong><p class="muted">Try refreshing this page in a moment.</p></div>`;
        });
    }
  }

  function renderWeekend() {
    const steps = [
      {
        question: "How far are you comfortable traveling for a market?",
        body: `
          <div class="guided-choice-grid">
            ${[
              { value: "30", label: "About 30 minutes" },
              { value: "60", label: "About 1 hour" },
              { value: "flexible", label: "I can be flexible" },
            ].map((item) => `<button class="guided-choice${state.weekend.travel === item.value ? " active" : ""}" type="button" data-weekend-travel="${item.value}">${item.label}</button>`).join("")}
          </div>
        `,
        ready: Boolean(state.weekend.travel),
      },
      {
        question: "How hard is transportation for you right now?",
        body: `
          <div class="guided-choice-grid">
            ${[
              { value: "none", label: "No big limits" },
              { value: "some", label: "Some limits" },
              { value: "difficult", label: "It is difficult" },
            ].map((item) => `<button class="guided-choice${state.weekend.transportation === item.value ? " active" : ""}" type="button" data-weekend-transportation="${item.value}">${item.label}</button>`).join("")}
          </div>
        `,
        ready: Boolean(state.weekend.transportation),
      },
      {
        question: "How do you feel about booth fees?",
        body: `
          <div class="guided-choice-grid">
            ${[
              { value: "low", label: "Keep it low" },
              { value: "depends", label: "Depends on the event" },
              { value: "higher", label: "I can pay more" },
            ].map((item) => `<button class="guided-choice${state.weekend.boothFeeComfort === item.value ? " active" : ""}" type="button" data-weekend-booth="${item.value}">${item.label}</button>`).join("")}
          </div>
        `,
        ready: Boolean(state.weekend.boothFeeComfort),
      },
      {
        question: "How much setup work feels realistic for you?",
        body: `
          <div class="guided-choice-grid">
            ${[
              { value: "light", label: "Light setup" },
              { value: "moderate", label: "Moderate setup" },
              { value: "heavy", label: "Heavy setup is okay" },
            ].map((item) => `<button class="guided-choice${state.weekend.setup === item.value ? " active" : ""}" type="button" data-weekend-setup="${item.value}">${item.label}</button>`).join("")}
          </div>
        `,
        ready: Boolean(state.weekend.setup),
      },
      {
        question: "What do you really need from an event?",
        body: `
          <div class="guided-choice-grid">
            ${["electricity", "parking", "indoor", "foot traffic"].map((item) => `<button class="guided-choice${state.weekend.mustHaves.includes(item) ? " active" : ""}" type="button" data-weekend-must="${item}">${item === "foot traffic" ? "Strong foot traffic" : item.charAt(0).toUpperCase() + item.slice(1)}</button>`).join("")}
          </div>
        `,
        ready: state.weekend.mustHaves.length > 0,
      },
      {
        question: "What is your goal for the event?",
        body: `
          <div class="guided-choice-grid">
            ${[
              { value: "practice", label: "Practice" },
              { value: "break_even", label: "Break even" },
              { value: "profit", label: "Make a profit" },
            ].map((item) => `<button class="guided-choice${state.weekend.goal === item.value ? " active" : ""}" type="button" data-weekend-goal="${item.value}">${item.label}</button>`).join("")}
          </div>
        `,
        ready: Boolean(state.weekend.goal),
      },
      {
        question: "How much risk feels okay right now?",
        body: `
          <div class="guided-choice-grid">
            ${[
              { value: "try_anything", label: "I will try almost anything" },
              { value: "sometimes", label: "Sometimes I can take a chance" },
              { value: "safe", label: "Safe options only" },
            ].map((item) => `<button class="guided-choice${state.weekend.risk === item.value ? " active" : ""}" type="button" data-weekend-risk="${item.value}">${item.label}</button>`).join("")}
          </div>
        `,
        ready: Boolean(state.weekend.risk),
      },
    ];

    if (state.weekendStep >= steps.length) {
      try {
        setPlanningAnswers(state.weekend);
        clearPlanningDraft();
        if (state.currentProfileId) {
          const prof = state.profiles.find((p) => p.id === state.currentProfileId);
          saveProfile({ id: state.currentProfileId, name: prof?.name, answers: state.weekend });
        }
        setJourneyProgress({
          mode: "home",
          weekendStep: steps.length,
          profitStep: state.profitStep,
          eventStep: state.eventStep,
        });
      } catch (e) {}
      root.innerHTML = `
        <div class="guided-flow-card journey-step journey-loading">
          <div class="spinner"></div>
          <h2>Finding your best events…</h2>
          <p class="muted">We're matching you with events based on your answers.</p>
        </div>
      `;
      setTimeout(() => {
        window.location.href = "/discover?from=planning";
      }, 900);
      return;
    }

    const step = steps[state.weekendStep];
    const weekendProgress = Math.round(((state.weekendStep + 1) / steps.length) * 100);
    root.innerHTML = `
      <div class="guided-flow-card journey-step">
        <button class="guided-back" type="button" data-go-home>Back</button>
        <div class="guided-progress-wrap">
          <div class="guided-progress">Question ${state.weekendStep + 1} of ${steps.length}</div>
          <div class="guided-progress-bar"><span style="width:${weekendProgress}%"></span></div>
        </div>
        <h2>${step.question}</h2>
        <p class="guided-step-note">Choose the answer that feels closest. You can always go back and change it.</p>
        ${step.body}
        <div class="guided-nav">
          <button class="btn btn-secondary" type="button" data-guided-prev ${state.weekendStep === 0 ? "disabled" : ""}>Back</button>
          <button class="btn btn-primary" type="button" data-guided-next ${!step.ready ? "disabled" : ""}>Next</button>
        </div>
      </div>
    `;

    root.querySelector("[data-go-home]")?.addEventListener("click", () => {
      state.mode = "home";
      persistJourneyState();
      render();
    });
    root.querySelector("[data-guided-prev]")?.addEventListener("click", () => {
      state.weekendStep = Math.max(0, state.weekendStep - 1);
      persistJourneyState();
      render();
    });
    root.querySelector("[data-guided-next]")?.addEventListener("click", () => {
      state.weekendStep += 1;
      persistJourneyState();
      render();
    });
    const autoAdvance = () => {
      const currentIndex = state.weekendStep;
      if (currentIndex < steps.length - 1) {
        setTimeout(() => {
          // Only advance if we're still on the same question
          if (state.weekendStep === currentIndex) {
            state.weekendStep += 1;
            persistJourneyState();
            render();
          }
        }, 260);
      }
    };

    root.querySelectorAll("[data-weekend-travel]").forEach((button) => button.addEventListener("click", () => {
      state.weekend.travel = button.getAttribute("data-weekend-travel");
      savePlanningDraft(state.weekend);
      persistJourneyState();
      render();
      autoAdvance();
    }));
    root.querySelectorAll("[data-weekend-transportation]").forEach((button) => button.addEventListener("click", () => {
      state.weekend.transportation = button.getAttribute("data-weekend-transportation");
      savePlanningDraft(state.weekend);
      persistJourneyState();
      render();
      autoAdvance();
    }));
    root.querySelectorAll("[data-weekend-booth]").forEach((button) => button.addEventListener("click", () => {
      state.weekend.boothFeeComfort = button.getAttribute("data-weekend-booth");
      savePlanningDraft(state.weekend);
      persistJourneyState();
      render();
      autoAdvance();
    }));
    root.querySelectorAll("[data-weekend-setup]").forEach((button) => button.addEventListener("click", () => {
      state.weekend.setup = button.getAttribute("data-weekend-setup");
      savePlanningDraft(state.weekend);
      persistJourneyState();
      render();
      autoAdvance();
    }));
    root.querySelectorAll("[data-weekend-goal]").forEach((button) => button.addEventListener("click", () => {
      state.weekend.goal = button.getAttribute("data-weekend-goal");
      savePlanningDraft(state.weekend);
      persistJourneyState();
      render();
      autoAdvance();
    }));
    root.querySelectorAll("[data-weekend-risk]").forEach((button) => button.addEventListener("click", () => {
      state.weekend.risk = button.getAttribute("data-weekend-risk");
      savePlanningDraft(state.weekend);
      persistJourneyState();
      render();
      autoAdvance();
    }));
    root.querySelectorAll("[data-weekend-must]").forEach((button) => button.addEventListener("click", () => {
      const value = button.getAttribute("data-weekend-must");
      if (state.weekend.mustHaves.includes(value)) {
        state.weekend.mustHaves = state.weekend.mustHaves.filter((item) => item !== value);
      } else {
        state.weekend.mustHaves = [...state.weekend.mustHaves, value];
      }
      savePlanningDraft(state.weekend);
      persistJourneyState();
      render();
    }));
  }

  function renderProfit() {
    const steps = [
      { key: "boothFee", question: "How much is the booth fee?", label: "Booth fee" },
      { key: "revenue", question: "How much money did you make?", label: "Sales" },
      { key: "costs", question: "What did you spend besides the booth fee?", label: "Extra costs" },
    ];

    if (state.profitStep >= steps.length) {
      const profit = moneyNumber(state.profit.revenue) - moneyNumber(state.profit.boothFee) - moneyNumber(state.profit.costs);
      root.innerHTML = `
        <div class="guided-flow-card guided-center-card">
          <button class="guided-back" type="button" data-go-home>Back</button>
          <span class="eyebrow">Your result</span>
          <h2>${profit >= 0 ? "You made a profit" : "You lost money"}</h2>
          <div class="guided-profit-number">${formatMoney(profit)}</div>
          <p>Sales ${formatMoney(state.profit.revenue)} minus booth fee ${formatMoney(state.profit.boothFee)} and costs ${formatMoney(state.profit.costs)}.</p>
          <div class="guided-profit-summary">
            <div class="guided-profit-stat">
              <span>Booth fee</span>
              <strong>${formatMoney(state.profit.boothFee)}</strong>
            </div>
            <div class="guided-profit-stat">
              <span>Sales</span>
              <strong>${formatMoney(state.profit.revenue)}</strong>
            </div>
            <div class="guided-profit-stat">
              <span>Other costs</span>
              <strong>${formatMoney(state.profit.costs)}</strong>
            </div>
          </div>
          <button class="btn btn-primary" type="button" data-restart-profit>Try another event</button>
        </div>
      `;
      root.querySelector("[data-go-home]")?.addEventListener("click", () => {
        state.mode = "home";
        persistJourneyState();
        render();
      });
      root.querySelector("[data-restart-profit]")?.addEventListener("click", () => {
        state.profitStep = 0;
        state.profit = { boothFee: "", revenue: "", costs: "" };
        persistJourneyState();
        render();
      });
      return;
    }

    const step = steps[state.profitStep];
    const profitProgress = Math.round(((state.profitStep + 1) / steps.length) * 100);
    root.innerHTML = `
      <div class="guided-flow-card">
        <button class="guided-back" type="button" data-go-home>Back</button>
        <div class="guided-progress-wrap">
          <div class="guided-progress">Question ${state.profitStep + 1} of ${steps.length}</div>
          <div class="guided-progress-bar"><span style="width:${profitProgress}%"></span></div>
        </div>
        <h2>${step.question}</h2>
        <p class="guided-step-note">Use a quick estimate if you do not know the exact number yet.</p>
        <div class="guided-input-wrap">
          <label for="guided_profit_input">${step.label}</label>
          <input id="guided_profit_input" class="guided-big-input" type="number" min="0" step="0.01" value="${state.profit[step.key]}">
        </div>
        <div class="guided-nav">
          <button class="btn btn-secondary" type="button" data-guided-prev ${state.profitStep === 0 ? "disabled" : ""}>Back</button>
          <button class="btn btn-primary" type="button" data-guided-next ${state.profit[step.key] === "" ? "disabled" : ""}>Next</button>
        </div>
      </div>
    `;
    root.querySelector("[data-go-home]")?.addEventListener("click", () => {
      state.mode = "home";
      persistJourneyState();
      render();
    });
    root.querySelector("[data-guided-prev]")?.addEventListener("click", () => {
      state.profitStep = Math.max(0, state.profitStep - 1);
      persistJourneyState();
      render();
    });
    root.querySelector("[data-guided-next]")?.addEventListener("click", () => {
      state.profitStep += 1;
      persistJourneyState();
      render();
    });
    root.querySelector("#guided_profit_input")?.addEventListener("input", (event) => {
      state.profit[step.key] = event.target.value;
      persistJourneyState();
      render();
    });
  }

  function renderEvents() {
    const steps = [
      {
        key: "boothFee",
        question: "Does the booth fee feel easy, okay, or expensive?",
        choices: [
          { value: "low", label: "Easy" },
          { value: "medium", label: "Okay" },
          { value: "high", label: "Expensive" },
        ],
      },
      {
        key: "traffic",
        question: "Do you expect a lot of shoppers?",
        choices: [
          { value: "high", label: "Yes, a lot" },
          { value: "medium", label: "Some" },
          { value: "low", label: "Not really" },
        ],
      },
      {
        key: "organizer",
        question: "Do the event details feel clear and trustworthy?",
        choices: [
          { value: "clear", label: "Yes" },
          { value: "somewhat", label: "Somewhat" },
          { value: "unclear", label: "No" },
        ],
      },
    ];

    if (state.eventStep >= steps.length) {
      const result = evaluateDecisionHelper(state.helper);
      root.innerHTML = `
        <div class="guided-flow-card guided-center-card">
          <button class="guided-back" type="button" data-go-home>Back</button>
          <span class="eyebrow">Event decision helper</span>
          <h2>${result.label}</h2>
          <div class="guided-decision ${result.tone}">${result.label}</div>
          <p>${result.text}</p>
          <div class="guided-result-grid">
            ${(eventChoices.length ? eventChoices : [{ name: "Search more events", city: "Near you" }]).map((event, index) => `
              <article class="guided-result-card">
                <div class="mini-meta">
                  <span class="pill">${result.label}</span>
                  ${Number(event.fit_score ?? event.worth_it_score ?? event.schedule_fit_score ?? 0) ? `<span class="pill">Fit ${Number(event.fit_score ?? event.worth_it_score ?? event.schedule_fit_score ?? 0)}</span>` : ""}
                </div>
                <strong>${friendlyMarketName(event, index)}</strong>
                <p>${[event.city, event.state].filter(Boolean).join(", ") || "Nearby area"}</p>
                ${(event.fit_reason || (event.schedule_reasons || []).join(" ")) ? `<p class="muted">${escapeHtml(event.fit_reason || (event.schedule_reasons || []).join(" "))}</p>` : ""}
                <a class="btn btn-secondary" href="${event.id ? eventDetailPath(event.id) : "/discover"}">${event.id ? "View event" : "See nearby events"}</a>
              </article>
            `).join("")}
          </div>
          <button class="btn btn-primary" type="button" data-restart-helper>Check another event</button>
        </div>
      `;
      root.querySelector("[data-go-home]")?.addEventListener("click", () => {
        state.mode = "home";
        persistJourneyState();
        render();
      });
      root.querySelector("[data-restart-helper]")?.addEventListener("click", () => {
        state.eventStep = 0;
        state.helper = { boothFee: "", traffic: "", organizer: "" };
        persistJourneyState();
        render();
      });
      return;
    }

    const step = steps[state.eventStep];
    const helperProgress = Math.round(((state.eventStep + 1) / steps.length) * 100);
    root.innerHTML = `
      <div class="guided-flow-card">
        <button class="guided-back" type="button" data-go-home>Back</button>
        <div class="guided-progress-wrap">
          <div class="guided-progress">Question ${state.eventStep + 1} of ${steps.length}</div>
          <div class="guided-progress-bar"><span style="width:${helperProgress}%"></span></div>
        </div>
        <h2>${step.question}</h2>
        <p class="guided-step-note">Go with your gut. This is here to help you sanity-check the event.</p>
        <div class="guided-choice-grid">
          ${step.choices.map((choice) => `<button class="guided-choice${state.helper[step.key] === choice.value ? " active" : ""}" type="button" data-helper-choice="${choice.value}">${choice.label}</button>`).join("")}
        </div>
        <div class="guided-nav">
          <button class="btn btn-secondary" type="button" data-guided-prev ${state.eventStep === 0 ? "disabled" : ""}>Back</button>
          <button class="btn btn-primary" type="button" data-guided-next ${!state.helper[step.key] ? "disabled" : ""}>Next</button>
        </div>
      </div>
    `;
    root.querySelector("[data-go-home]")?.addEventListener("click", () => {
      state.mode = "home";
      persistJourneyState();
      render();
    });
    root.querySelector("[data-guided-prev]")?.addEventListener("click", () => {
      state.eventStep = Math.max(0, state.eventStep - 1);
      persistJourneyState();
      render();
    });
    root.querySelector("[data-guided-next]")?.addEventListener("click", () => {
      state.eventStep += 1;
      persistJourneyState();
      render();
    });
    root.querySelectorAll("[data-helper-choice]").forEach((button) => button.addEventListener("click", () => {
      state.helper[step.key] = button.getAttribute("data-helper-choice");
      persistJourneyState();
      render();
    }));
  }

  function render() {
    if (state.mode === "home") return renderHome();
    if (state.mode === "weekend") return renderWeekend();
    if (state.mode === "profit") return renderProfit();
    return renderEvents();
  }

  render();
}

async function setupDashboard() {
  const root = document.querySelector("[data-dashboard-root]");
  if (!root) return;
  const welcome = document.querySelector("[data-dashboard-welcome]");
  const guidedRoot = document.querySelector("[data-guided-dashboard]");
  if (!guidedRoot) return;

  try {
    const [payload, shopify] = await Promise.all([
      api("/api/dashboard", { method: "GET" }),
      fetch("/api/shopify/me", { credentials: "include" }).then(r => r.ok ? r.json() : null).catch(() => null),
    ]);
    const user = payload.user || {};
    if (payload.dashboard_path && payload.dashboard_path !== "/dashboard") {
      window.location.href = payload.dashboard_path;
      return;
    }
    if (welcome) {
      welcome.textContent = `Hi ${user.name || "there"}, what would you like to do today?`;
    }
    renderGuidedDashboardApp(guidedRoot, { ...payload, shopify }, { user });
  } catch (error) {
    if (error.status === 401) {
      window.location.href = "/signin";
      return;
    }
    if (welcome) {
      welcome.textContent = "What would you like to do today?";
    }
    renderGuidedDashboardApp(guidedRoot, { user: { name: "friend", interests: "" }, saved_markets: [], recommended_markets: [], shopify: null }, { user: null });
  }
}

async function setupKansasCityListings(auth) {
  const currentGrid = document.querySelector("[data-kc-current-events]");
  const moreGrid = document.querySelector("[data-kc-more-events]");
  const status = document.querySelector("[data-kc-listings-status]");
  const refreshButton = document.querySelector("[data-refresh-kc-listings]");
  const form = document.querySelector("[data-kc-business-form]");
  if (!currentGrid || !moreGrid) return;

  async function loadListings() {
    setStatus(status, "Loading Kansas City events and ratings...");
    try {
      const inputs = form ? Object.fromEntries(new FormData(form).entries()) : {};
      const payload = await api("/api/listings/kansas-city/evaluate", {
        method: "POST",
        body: JSON.stringify(inputs),
      });
      const currentEvents = [...(payload.current_events || [])].sort(
        (a, b) => (b.analysis?.ratings?.overall_worth_it || 0) - (a.analysis?.ratings?.overall_worth_it || 0),
      );
      const moreEvents = [...(payload.more_events || [])].sort(
        (a, b) => (b.analysis?.ratings?.overall_worth_it || 0) - (a.analysis?.ratings?.overall_worth_it || 0),
      );

      currentGrid.innerHTML = currentEvents.length
        ? currentEvents.map((event) => renderKansasCityListingCard(event, auth.authenticated)).join("")
        : `<div class="empty-state"><strong>No current Kansas City events yet.</strong><p class="muted">Run discovery again to build up the local event set.</p></div>`;

      moreGrid.innerHTML = moreEvents.length
        ? moreEvents.map((event) => renderKansasCityListingCard(event, auth.authenticated, true)).join("")
        : `<div class="empty-state"><strong>No additional Kansas City events were found yet.</strong><p class="muted">Try refreshing to run the Kansas City discovery tool again.</p></div>`;

      bindSaveButtons();
      setStatus(status, `${payload.current_count || 0} current events and ${payload.more_count || 0} more events rated.`, "success");
    } catch (error) {
      currentGrid.innerHTML = `<div class="empty-state"><strong>Could not load Kansas City events.</strong><p class="muted">${error.message}</p></div>`;
      moreGrid.innerHTML = "";
      setStatus(status, error.message, "error");
    }
  }

  refreshButton?.addEventListener("click", loadListings);
  form?.addEventListener("submit", async (event) => {
    event.preventDefault();
    await loadListings();
  });
  await loadListings();
}

async function setupBusinessPage() {
  const root = document.querySelector("[data-business-app]");
  if (!root) return;
  try {
    const [payload, shopifyConn, shopifyProducts] = await Promise.all([
      api("/api/analytics", { method: "GET" }),
      fetch("/api/shopify/me", { credentials: "include" }).then(r => r.ok ? r.json() : null).catch(() => null),
      fetch("/api/shopify/products", { credentials: "include" }).then(r => r.ok ? r.json() : []).catch(() => []),
    ]);
    const role = payload.role || "vendor";
    if (role === "shopper") { window.location.href = "/shopper-dashboard"; return; }
    const summary = payload.summary || {};

    if (role === "vendor") {
      const vendor = payload.vendor || {};
      const events = Array.isArray(payload.events) ? payload.events : [];
      const summaryTiles = renderMetricGrid([
        { label: "Total revenue", value: formatMoney(summary.total_revenue || 0) },
        { label: "Total expenses", value: formatMoney(summary.total_expenses || 0) },
        { label: "Vendor fees", value: formatMoney(summary.total_vendor_fee || 0), tone: "warning" },
        { label: "Total profit", value: formatMoney(summary.total_profit || 0), tone: Number(summary.total_profit || 0) >= 0 ? "profit" : "danger" },
      ]);
      const snapshotTiles = renderMetricGrid([
        { label: "Events tracked", value: String(summary.event_count || 0) },
        { label: "Average profit", value: formatMoney(summary.average_profit_per_event || 0), tone: Number(summary.average_profit_per_event || 0) >= 0 ? "profit" : "danger" },
      ]);
      root.innerHTML = `
        <div class="dashboard-grid">
          <div class="dashboard-card">
            <span class="eyebrow">Vendor analytics</span>
            <h2>${escapeHtml(vendor.business_name || vendor.name || "Your business")}</h2>
            <p class="muted" style="margin-top:10px;">Answer the core question fast: was this event worth it?</p>
            ${summaryTiles}
          </div>

          <div class="dashboard-card">
            <span class="eyebrow">Performance snapshot</span>
            <h2>How your events are doing</h2>
            ${snapshotTiles}
            ${
              summary.best_event
                ? renderHighlightCard(
                  "Best performing event",
                  `${summary.best_event.event_title || "Event"} returned ${formatMoney(summary.best_event.profit || 0)}.`
                )
                : `<p class="muted" style="margin-top:12px;">No event stats yet. Add a few completed events to start learning what works.</p>`
            }
            ${
              summary.worst_event && summary.worst_event.event_id !== summary.best_event?.event_id
                ? renderHighlightCard(
                  "Needs another look",
                  `${summary.worst_event.event_title || "Event"} returned ${formatMoney(summary.worst_event.profit || 0)}. Review fee, traffic, and inventory fit before repeating it.`
                )
                : ``
            }
            <div class="stack-row" style="margin-top:16px;">
              <a class="btn btn-secondary" href="/final-plan">Profit hub</a>
              <a class="btn btn-secondary" href="/history">Event history</a>
            </div>
          </div>

          <div class="dashboard-card">
            <span class="eyebrow">Per-event breakdown</span>
            <h2>Event performance</h2>
            ${
              events.length
                ? renderStreamList(events, (item) => `
                    <div class="atlas-stream-card">
                      <div class="atlas-stream-main">
                        <strong>${escapeHtml(item.event_title || "Event")}</strong>
                        <div class="atlas-stream-meta">${escapeHtml(item.event_location || "")}${item.start_date ? ` | ${escapeHtml(item.start_date)}` : ""}</div>
                        <div class="atlas-stream-note">Revenue ${formatMoney(item.revenue || 0)} | Expenses ${formatMoney(item.expenses || 0)} | Fee ${formatMoney(item.vendor_fee || 0)}</div>
                        <div class="atlas-stream-note">ROI ${Number(item.roi || 0).toFixed(1)}%${item.notes ? ` | ${escapeHtml(item.notes)}` : ""}</div>
                      </div>
                      <div class="atlas-stream-aside">
                        <div class="${Number(item.profit || 0) >= 0 ? "atlas-profit" : "atlas-loss"}" style="font-weight:800;">${formatMoney(item.profit || 0)}</div>
                      </div>
                    </div>
                  `)
                : `<div class="empty-state"><strong>No event performance yet.</strong><p class="muted">Once revenue, expenses, and fees are logged, your profit breakdown will show up here.</p></div>`
            }
          </div>

          <div class="dashboard-card">
            <span class="eyebrow">Shopify store</span>
            <h2 style="display:flex;align-items:center;gap:.6rem;">
              Your shop
              ${shopifyConn?.connected
                ? `<span style="font-size:.75rem;font-weight:600;color:var(--success);background:rgba(2,122,72,.08);padding:.2rem .6rem;border-radius:99px;">✓ Connected</span>`
                : `<span style="font-size:.75rem;font-weight:600;color:var(--muted);background:rgba(19,38,35,.06);padding:.2rem .6rem;border-radius:99px;">Not connected</span>`}
            </h2>
            ${shopifyConn?.connected
              ? `<p class="muted" style="margin-bottom:.75rem;">${escapeHtml(String(shopifyConn.shop || "").replace(".myshopify.com", ""))}.myshopify.com · ${shopifyProducts.length} product${shopifyProducts.length === 1 ? "" : "s"} synced</p>
                <div class="stack-row" style="margin-bottom:1rem;">
                  ${shopifyConn.username ? `<a class="btn btn-primary" href="/shop/${encodeURIComponent(shopifyConn.username)}">View public shop</a>` : ""}
                  <button class="btn btn-secondary" type="button" id="biz-shopify-sync">Sync now</button>
                  <a class="btn btn-ghost" href="/integrations">Settings</a>
                </div>
                ${shopifyProducts.length
                  ? `<div style="display:grid;grid-template-columns:repeat(auto-fill,minmax(160px,1fr));gap:.75rem;">
                      ${shopifyProducts.slice(0, 6).map(p => `
                        <div style="background:var(--surface);border-radius:var(--radius-md);padding:.75rem;font-size:.88rem;">
                          <div style="font-weight:600;margin-bottom:.2rem;">${escapeHtml(p.name)}</div>
                          <div style="color:var(--brand);font-weight:700;">${p.price > 0 ? "$" + Number(p.price).toFixed(2) : "Free"}</div>
                          <div style="color:var(--muted);font-size:.78rem;">Stock: ${p.inventory_quantity ?? "—"}</div>
                        </div>`).join("")}
                    </div>`
                  : `<p class="muted">No products synced yet. Click Sync now to pull your Shopify inventory.</p>`}
              `
              : `<p class="muted">Connect your Shopify store to show products on your public vendor page and track inventory before events.</p>
                <a class="btn btn-primary" href="/integrations">Connect Shopify</a>`
            }
          </div>
        </div>
      `;
      root.querySelector("#biz-shopify-sync")?.addEventListener("click", async (e) => {
        const btn = e.currentTarget;
        btn.disabled = true; btn.textContent = "Syncing…";
        try {
          await fetch("/api/shopify/sync", { method: "POST", credentials: "include" });
          btn.textContent = "Synced ✓";
        } catch (_) { btn.textContent = "Sync now"; }
        setTimeout(() => { btn.disabled = false; btn.textContent = "Sync now"; }, 3000);
      });
    } else if (role === "market") {
      const events = Array.isArray(payload.events) ? payload.events : [];
      const organizerSummaryTiles = renderMetricGrid([
        { label: "Events hosted", value: String(summary.total_events_hosted || 0) },
        { label: "Applications", value: String(summary.total_applications_received || 0) },
        { label: "Avg vendors / event", value: Number(summary.avg_vendors_per_event || 0).toFixed(1) },
        { label: "Estimated fee revenue", value: formatMoney(summary.estimated_vendor_fee_revenue || 0), tone: "profit" },
      ]);
      root.innerHTML = `
        <div class="dashboard-grid">
          <div class="dashboard-card">
            <span class="eyebrow">Organizer analytics</span>
            <h2>How your events are performing</h2>
            ${organizerSummaryTiles}
            ${renderHighlightCard("What to watch", "Keep booth fee, application volume, and accepted vendor count moving together so each event grows without slowing down review.")}
          </div>
          <div class="dashboard-card">
            <span class="eyebrow">Per-event view</span>
            <h2>Applications and fee totals</h2>
            ${
              events.length
                ? renderStreamList(events, (item) => `
                    <div class="atlas-stream-card">
                      <div class="atlas-stream-main">
                        <strong>${escapeHtml(item.title || "Event")}</strong>
                        <div class="atlas-stream-meta">${escapeHtml(item.location || "")}${item.start_date ? ` | ${escapeHtml(item.start_date)}` : ""}</div>
                        <div class="atlas-stream-note">${item.applicant_count || 0} applicants | ${item.accepted_count || 0} accepted | Fee ${formatMoney(item.vendor_fee || 0)}</div>
                      </div>
                      <div class="atlas-stream-aside">
                        <div class="atlas-profit" style="font-weight:800;">${formatMoney(item.estimated_revenue || 0)}</div>
                      </div>
                    </div>
                  `)
                : `<div class="empty-state"><strong>No organizer analytics yet.</strong><p class="muted">Create an event and applications will start filling in these totals.</p></div>`
            }
          </div>
        </div>
      `;
    } else {
      const savedEvents = Array.isArray(payload.saved_events) ? payload.saved_events : [];
      const followedVendors = Array.isArray(payload.followed_vendors) ? payload.followed_vendors : [];
      const shopperSummaryTiles = renderMetricGrid([
        { label: "Events saved", value: String(summary.events_saved || 0) },
        { label: "Vendors followed", value: String(summary.followed_vendors || 0) },
        { label: "Upcoming events", value: String(summary.upcoming_events || 0), tone: "profit" },
      ]);
      root.innerHTML = `
        <div class="dashboard-grid">
          <div class="dashboard-card">
            <span class="eyebrow">Shopper analytics</span>
            <h2>Your event activity</h2>
            ${shopperSummaryTiles}
            ${renderHighlightCard("Keep momentum", "Save the events you want to visit and follow a few vendors so your next outing is easy to pick.")}
          </div>
          <div class="dashboard-card">
            <span class="eyebrow">Upcoming events</span>
            <h2>Your saved plans</h2>
            ${
              savedEvents.length
                ? renderStreamList(savedEvents, (item) => `
                    <div class="atlas-stream-card">
                      <div class="atlas-stream-main">
                        <strong>${escapeHtml(item.title || "Event")}</strong>
                        <div class="atlas-stream-meta">${escapeHtml(item.location || "")}${item.start_date ? ` | ${escapeHtml(item.start_date)}` : ""}</div>
                      </div>
                      <div class="atlas-stream-aside">
                        <a class="btn btn-secondary" href="/discover">Browse more</a>
                      </div>
                    </div>
                  `)
                : `<div class="empty-state"><strong>No saved events yet.</strong><p class="muted">Save a few events from Discover and they will show up here.</p></div>`
            }
          </div>
          <div class="dashboard-card">
            <span class="eyebrow">Followed vendors</span>
            <h2>Who you're tracking</h2>
            ${
              followedVendors.length
                ? renderStreamList(followedVendors, (item) => `
                    <div class="atlas-stream-card">
                      <div class="atlas-stream-main">
                        <strong>${escapeHtml(item.business_name || "Vendor")}</strong>
                        <div class="atlas-stream-meta">${escapeHtml(item.category || "Vendor")}${item.location ? ` | ${escapeHtml(item.location)}` : ""}</div>
                      </div>
                      <div class="atlas-stream-aside">
                        <a class="btn btn-secondary" href="/shopper-dashboard">View dashboard</a>
                      </div>
                    </div>
                  `)
                : `<div class="empty-state"><strong>No followed vendors yet.</strong><p class="muted">Follow a few vendors to keep track of where they will be selling.</p></div>`
            }
          </div>
        </div>
      `;
    }

    attachButtonPress(".btn", root);
  } catch (error) {
    if (error.status === 401) {
      window.location.href = "/signin";
      return;
    }
    root.innerHTML = `<div class="empty-state"><strong>We couldn't load analytics right now.</strong><p class="muted">${escapeHtml(error.message || "Please try again.")}</p></div>`;
  }
}

async function setupMarketDashboard() {
  const root = document.querySelector("[data-market-dashboard-app]");
  if (!root) return;
  const organizerView = root.getAttribute("data-organizer-view") || "workspace";

  try {
    const payload = await api("/api/market-dashboard", { method: "GET" });
    const initialEvents = payload.events || [];
    const analytics = payload.analytics || {};
    const baseApplications = payload.applications || [];
    const applicationOverrides = getOrganizerApplicationState();

    const state = {
      events: initialEvents,
      applications: baseApplications.map((application, index) => ({
        ...application,
        id: application.id || `app-${index + 1}`,
        ...(applicationOverrides[application.id || `app-${index + 1}`] || {}),
      })),
      statusMessage: "",
      editingEventId: "",
      eventDraft: {
        name: "",
        city: "",
        state: "",
        date: "",
        booth_price: "",
        vendor_category: "",
        application_link: "",
        latitude: "",
        longitude: "",
        location_name: "",
        address: "",
      },
    };

    function resetEventDraft() {
      state.editingEventId = "";
      state.eventDraft = {
        name: "",
        city: "",
        state: "",
        date: "",
        booth_price: "",
        vendor_category: "",
        application_link: "",
        latitude: "",
        longitude: "",
        location_name: "",
        address: "",
      };
    }

    function renderApplicationThread(application) {
      const messages = Array.isArray(application.messages) ? application.messages : [];
      if (!messages.length) {
        return `<div class="empty-state" style="margin-top:12px;"><strong>No conversation yet.</strong><p class="muted">Write a quick note, then accept, reject, or message the vendor to keep a visible thread here.</p></div>`;
      }
      return `
        <div class="message-thread">
          ${messages.map((message) => `
            <div class="message-thread-item">
              <strong>${escapeHtml(message.label || "Update")}</strong>
              <p>${escapeHtml(message.body || "")}</p>
            </div>
          `).join("")}
        </div>
      `;
    }

    function renderApplicationsPanel(isExpanded = false) {
      return `
        <div class="organizer-panel${isExpanded ? " organizer-panel-expanded" : ""}" data-organizer-tool="applications">
          <span class="eyebrow">Vendor applications</span>
          <h2>${isExpanded ? "Applications command center" : "Review and reply"}</h2>
          ${isExpanded ? `<p class="muted" style="margin-top:12px;">Work through the full application queue with room for notes, quick replies, and visible decision history.</p>` : ""}
          ${
            state.applications.length
              ? renderStreamList(state.applications, (application) => `
                  <div class="atlas-stream-card">
                    <div class="atlas-stream-main">
                      <strong>${escapeHtml(application.vendor_name || "Vendor application")}</strong>
                      <div class="atlas-stream-meta">${escapeHtml(application.vendor_category || application.category || "Category pending")}${application.event_name ? ` | ${escapeHtml(application.event_name)}` : ""}</div>
                      <div class="atlas-stream-note">${escapeHtml(application.notes || "No application note yet.")}</div>
                      <input class="mini-input" data-app-message="${application.id}" placeholder="Quick message" value="${escapeHtml(application.message || "")}" style="margin-top:10px;">
                      ${renderApplicationThread(application)}
                    </div>
                    <div class="atlas-stream-aside">
                      <span class="pill">${escapeHtml(application.status)}</span>
                      <div class="stack-row" style="justify-content:flex-end;">
                        <button class="btn btn-secondary" type="button" data-app-action="${application.id}:Accepted">Accept</button>
                        <button class="btn btn-secondary" type="button" data-app-action="${application.id}:Rejected">Reject</button>
                        <button class="btn btn-secondary" type="button" data-app-action="${application.id}:Messaged">Message</button>
                      </div>
                    </div>
                  </div>
                `)
              : `<div class="empty-state"><strong>No applications yet.</strong><p class="muted">Applications from vendors will appear here once your event is live.</p></div>`
          }
        </div>
      `;
    }

    function renderAnalyticsPanel(messageCount, isExpanded = false) {
      const acceptedCount = state.applications.filter((item) => item.status === "Accepted").length;
      return `
        <div class="organizer-panel${isExpanded ? " organizer-panel-expanded" : ""}" data-organizer-tool="analytics">
          <span class="eyebrow">Event analytics</span>
          <h2>${isExpanded ? "Organizer analytics overview" : "Performance at a glance"}</h2>
          ${renderMetricGrid([
            { label: "Listing views", value: String(analytics.views || 0) },
            { label: "Applications", value: String(state.applications.length || analytics.applications || 0) },
            { label: "Accepted vendors", value: String(acceptedCount || analytics.accepted_vendors || 0), tone: "profit" },
            { label: "Active conversations", value: String(messageCount) },
            { label: "Active events", value: String(state.events.length || analytics.active_events || 0) },
            { label: "Avg views / event", value: String(state.events.length ? Math.round((analytics.views || 0) / state.events.length) : 0) },
          ])}
          <p class="muted" style="margin-top:12px;">Your strongest next step is to keep applications moving fast and make sure each event has a clear booth fee and link.</p>
          <div data-ai-organizer-insights></div>
          ${
            isExpanded
              ? `
                <div class="organizer-analytics-grid">
                  <div class="organizer-panel organizer-panel-nested">
                    <span class="eyebrow">Event momentum</span>
                    <h3>Where the traffic is landing</h3>
                    ${
                      state.events.length
                        ? renderStreamList(state.events, (event) => `
                            <div class="atlas-stream-card compact">
                              <div class="atlas-stream-main">
                                <strong>${escapeHtml(event.name || "Event")}</strong>
                                <div class="atlas-stream-meta">${escapeHtml([event.city, event.state].filter(Boolean).join(", "))}${event.date ? ` | ${escapeHtml(event.date)}` : ""}</div>
                                <div class="atlas-stream-note">${formatMoney(event.booth_price)} booth fee | ${event.estimated_traffic || "Traffic TBD"} expected visitors</div>
                              </div>
                              <div class="atlas-stream-aside">
                                <span class="pill">${escapeHtml(event.vendor_category || "General")}</span>
                              </div>
                            </div>
                          `)
                        : `<div class="empty-state"><strong>No events yet.</strong><p class="muted">Create an event to start collecting analytics.</p></div>`
                    }
                  </div>
                  <div class="organizer-panel organizer-panel-nested">
                    <span class="eyebrow">What to watch</span>
                    <h3>Healthy organizer signals</h3>
                    ${renderHighlightCard("Volume vs quality", "Applications should rise alongside accepted vendors, not just raw listing views.")}
                    ${renderHighlightCard("Response speed", "If conversation count is climbing but accepted vendors are flat, the review queue may need attention.")}
                    ${renderHighlightCard("Listing clarity", "Events with clear booth fees and application links are easier for vendors to trust and act on.")}
                  </div>
                </div>
              `
              : ""
          }
        </div>
      `;
    }

    function render() {
      const messageCount = state.applications.filter((item) => item.message).length;
      const organizerTiles = renderMetricGrid([
        { label: "Active events", value: String(state.events.length || analytics.active_events || 0) },
        { label: "Applications", value: String(state.applications.length || analytics.applications || 0) },
        { label: "Accepted", value: String(state.applications.filter((item) => item.status === "Accepted").length || analytics.accepted_vendors || 0), tone: "profit" },
        { label: "Listing views", value: String(analytics.views || 0) },
      ]);
      if (organizerView === "applications") {
        root.innerHTML = `
          <div class="organizer-shell organizer-detail-shell">
            <div class="organizer-toolbar">
              <div>
                <div class="organizer-kicker">Applications workspace</div>
                <strong>Review vendors, send replies, and keep decisions moving.</strong>
              </div>
              <div class="organizer-chip-row">
                <span class="organizer-chip">${state.applications.length || analytics.applications || 0} applications</span>
                <span class="organizer-chip">${messageCount} active threads</span>
                <span class="organizer-chip">${state.events.length || analytics.active_events || 0} live listings</span>
              </div>
            </div>
            ${renderApplicationsPanel(true)}
          </div>
        `;
      } else if (organizerView === "analytics") {
        root.innerHTML = `
          <div class="organizer-shell organizer-detail-shell">
            <div class="organizer-toolbar">
              <div>
                <div class="organizer-kicker">Analytics workspace</div>
                <strong>See how your listings and application pipeline are performing.</strong>
              </div>
              <div class="organizer-chip-row">
                <span class="organizer-chip">${analytics.views || 0} listing views</span>
                <span class="organizer-chip">${state.applications.length || analytics.applications || 0} applications</span>
                <span class="organizer-chip">${state.events.length || analytics.active_events || 0} active events</span>
              </div>
            </div>
            ${renderAnalyticsPanel(messageCount, true)}
          </div>
        `;
      } else {
      root.innerHTML = `
        <div class="organizer-shell">
          <div class="organizer-toolbar">
            <div>
              <div class="organizer-kicker">Organizer workspace</div>
              <strong>Listings, applications, and event health stay here.</strong>
            </div>
            <div class="organizer-chip-row">
              <span class="organizer-chip">${state.events.length || analytics.active_events || 0} live listings</span>
              <span class="organizer-chip">${state.applications.length || analytics.applications || 0} vendor applications</span>
              <span class="organizer-chip">${messageCount} active threads</span>
            </div>
          </div>
          <div class="organizer-board">
            <div class="organizer-column">
              <div class="organizer-panel">
            <span class="eyebrow">Organizer overview</span>
            <h2>Run each event from one place</h2>
            ${organizerTiles}
            <p class="muted" style="margin-top:12px;">Create events, keep applications moving, and monitor which listings are getting attention.</p>
            <div class="status ${state.statusMessage ? "success" : ""}" style="${state.statusMessage ? "" : "display:none;"}">${escapeHtml(state.statusMessage)}</div>
              </div>

              <div class="organizer-panel">
            <span class="eyebrow">Organizer tools</span>
            <h2>Use the workspace that matches the job</h2>
            <p class="muted" style="margin-top:12px;">Organizer tools stay separate from vendor planning tools. Build listings here, review vendors here, and use Discover only when you want to compare the public event experience.</p>
            <div class="tool-grid">
              <div class="tool-card">
                <strong>Create and edit events</strong>
                <p class="muted">Publish a new market or update an existing one without leaving this dashboard.</p>
                <p class="muted" style="margin-top:12px;">The event form is part of this workspace just below, so you can start editing immediately without another click.</p>
              </div>
              <div class="tool-card">
                <strong>Review applications</strong>
                <p class="muted">Accept, reject, and message vendors with a visible thread attached to each application.</p>
                <div class="stack-row">
                  <a class="btn btn-primary" href="/market-applications">Open applications</a>
                </div>
              </div>
              <div class="tool-card">
                <strong>Watch listing health</strong>
                <p class="muted">See views, accepted vendors, and application volume without jumping into vendor-facing tools.</p>
                <div class="stack-row">
                  <a class="btn btn-primary" href="/market-analytics">Open analytics</a>
                </div>
              </div>
              <div class="tool-card">
                <strong>Check the public side</strong>
                <p class="muted">Open Discover to see how public event browsing feels after your listing goes live.</p>
                <div class="stack-row">
                  <a class="btn btn-secondary" href="/discover">Open Discover</a>
                </div>
              </div>
            </div>
              </div>

              <div class="organizer-panel" data-organizer-tool="create">
            <span class="eyebrow">Create event</span>
            <h2>${state.editingEventId ? "Edit market" : "Publish a new market"}</h2>
            <form class="form-grid" data-market-event-form>
              <div class="field"><label for="market_event_name">Event name</label><input id="market_event_name" name="name" value="${escapeHtml(state.eventDraft.name || "")}" required></div>
              <div class="stack-row">
                <div class="field" style="flex:1;"><label for="market_event_city">City</label><input id="market_event_city" name="city" value="${escapeHtml(state.eventDraft.city || "")}" required></div>
                <div class="field" style="width:120px;"><label for="market_event_state">State</label><input id="market_event_state" name="state" value="${escapeHtml(state.eventDraft.state || "")}" required></div>
              </div>
              <div class="stack-row">
                <div class="field" style="flex:1;"><label for="market_event_date">Date</label><input id="market_event_date" name="date" type="date" value="${escapeHtml(state.eventDraft.date || "")}" required></div>
                <div class="field" style="flex:1;"><label for="market_event_fee">Booth fee</label><input id="market_event_fee" name="booth_price" type="number" min="0" step="0.01" value="${escapeHtml(state.eventDraft.booth_price || "")}"></div>
              </div>
              <div class="stack-row">
                <div class="field" style="flex:1;"><label for="market_event_category">Category</label><input id="market_event_category" name="vendor_category" placeholder="Craft, vintage, food" value="${escapeHtml(state.eventDraft.vendor_category || "")}"></div>
                <div class="field" style="flex:1;"><label for="market_event_link">Application link</label><input id="market_event_link" name="application_link" placeholder="https://" value="${escapeHtml(state.eventDraft.application_link || "")}"></div>
              </div>
              <div class="field">
                <label>Event location <span class="muted" style="font-weight:400;">(optional — click map to pin)</span></label>
                <div id="planner-leaflet-map" style="height:320px;border-radius:10px;overflow:hidden;border:1px solid var(--border);margin-top:.4rem;"></div>
                <div style="display:flex;gap:.5rem;margin-top:.4rem;">
                  <input id="market_event_lat" name="latitude" type="hidden" value="${escapeHtml(String(state.eventDraft.latitude || ""))}">
                  <input id="market_event_lng" name="longitude" type="hidden" value="${escapeHtml(String(state.eventDraft.longitude || ""))}">
                  <input id="market_event_loc_name" name="location_name" class="mini-input" style="flex:1;" placeholder="Venue / location name" value="${escapeHtml(state.eventDraft.location_name || "")}">
                  <input id="market_event_address" name="address" class="mini-input" style="flex:2;" placeholder="Street address" value="${escapeHtml(state.eventDraft.address || "")}">
                </div>
                <p class="muted" style="margin-top:.35rem;font-size:.76rem;" id="planner-map-coords">${state.eventDraft.latitude ? `📍 ${Number(state.eventDraft.latitude).toFixed(4)}, ${Number(state.eventDraft.longitude).toFixed(4)}` : "No pin set yet — click the map above to place one."}</p>
              </div>
              <div class="stack-row">
                <button class="btn btn-primary btn-block" type="submit">${state.editingEventId ? "Save Changes" : "Create Event"}</button>
                ${state.editingEventId ? `<button class="btn btn-secondary" type="button" data-cancel-market-edit>Cancel</button>` : ""}
              </div>
            </form>
              </div>

              <div class="organizer-panel">
            <span class="eyebrow">Manage events</span>
            <h2>Your live listings</h2>
            ${
              state.events.length
                ? renderStreamList(state.events, (event) => `
                    <div class="atlas-stream-card">
                      <div class="atlas-stream-main">
                        <strong>${escapeHtml(event.name || "Event")}</strong>
                        <div class="atlas-stream-meta">${escapeHtml([event.city, event.state].filter(Boolean).join(", "))}${event.date ? ` | ${escapeHtml(event.date)}` : ""}</div>
                        <div class="atlas-stream-note">${formatMoney(event.booth_price)} booth fee | ${event.estimated_traffic || "Traffic TBD"} expected visitors</div>
                      </div>
                      <div class="atlas-stream-aside">
                        <div class="mini-meta">
                          <span class="pill">${escapeHtml(event.vendor_category || "General")}</span>
                        </div>
                        <button class="btn btn-secondary" type="button" data-edit-market="${escapeHtml(event.id || "")}">Edit</button>
                      </div>
                    </div>
                  `)
                : `<div class="empty-state"><strong>No events yet.</strong><p class="muted">Create your first event to start collecting applications.</p></div>`
            }
              </div>
            </div>

            <div class="organizer-column">
              ${renderApplicationsPanel(false)}
              ${renderAnalyticsPanel(messageCount, false)}
            </div>
          </div>
        </div>
      `;
      }

      // Initialize AI organizer insights (Feature 8)
      if (typeof AI !== "undefined" && document.querySelector("[data-ai-organizer-insights]")) {
        setTimeout(() => {
          AI.renderOrganizerInsights(
            "[data-ai-organizer-insights]",
            state.events,
            state.applications,
          );
        }, 0);
      }

      // Initialize planner map after DOM update (workspace view only)
      if (organizerView !== "applications" && organizerView !== "analytics" && window.EventMap) {
        setTimeout(() => {
          if (document.getElementById("planner-leaflet-map")) {
            window.EventMap.initPlanner("planner-leaflet-map", (lat, lng) => {
              const latInput = document.getElementById("market_event_lat");
              const lngInput = document.getElementById("market_event_lng");
              const hint = document.getElementById("planner-map-coords");
              if (latInput) latInput.value = lat.toFixed(6);
              if (lngInput) lngInput.value = lng.toFixed(6);
              if (hint) hint.textContent = `📍 ${lat.toFixed(4)}, ${lng.toFixed(4)}`;
            });
          }
        }, 0);
      }

      root.querySelector("[data-market-event-form]")?.addEventListener("submit", async (event) => {
        event.preventDefault();
        const payload = Object.fromEntries(new FormData(event.currentTarget).entries());
        const response = await api(state.editingEventId ? `/api/market/events/${encodeURIComponent(state.editingEventId)}` : "/api/market/events", {
          method: state.editingEventId ? "PUT" : "POST",
          body: JSON.stringify(payload),
        });
        if (state.editingEventId) {
          state.events = state.events.map((item) => String(item.id) === String(state.editingEventId) ? response.event : item);
          state.statusMessage = "Your event changes are live.";
        } else {
          state.events = [response.event, ...state.events];
          state.statusMessage = "Your event is live and ready for applications.";
        }
        resetEventDraft();
        render();
      });

      root.querySelector("[data-cancel-market-edit]")?.addEventListener("click", () => {
        resetEventDraft();
        state.statusMessage = "Edit canceled.";
        render();
      });

      root.querySelectorAll("[data-edit-market]").forEach((button) => {
        button.addEventListener("click", () => {
          const eventId = button.getAttribute("data-edit-market");
          const market = state.events.find((item) => String(item.id) === String(eventId));
          if (!market) return;
          state.editingEventId = String(market.id || "");
          state.eventDraft = {
            name: market.name || "",
            city: market.city || "",
            state: market.state || "",
            date: market.date || "",
            booth_price: market.booth_price ?? "",
            vendor_category: market.vendor_category || "",
            application_link: market.application_link || "",
            latitude: market.latitude ?? "",
            longitude: market.longitude ?? "",
            location_name: market.location_name || "",
            address: market.address || "",
          };
          state.statusMessage = `Editing ${market.name || "event"}.`;
          render();
        });
      });

      root.querySelectorAll("[data-app-message]").forEach((input) => {
        input.addEventListener("input", () => {
          const id = input.getAttribute("data-app-message");
          const application = state.applications.find((item) => item.id === id);
          if (!application) return;
          application.message = input.value || "";
          setOrganizerApplicationState(Object.fromEntries(state.applications.map((item) => [item.id, item])));
        });
      });

      root.querySelectorAll("[data-app-action]").forEach((button) => {
        button.addEventListener("click", () => {
          const [id, action] = String(button.getAttribute("data-app-action") || "").split(":");
          const application = state.applications.find((item) => item.id === id);
          if (!application) return;
          application.messages = Array.isArray(application.messages) ? application.messages : [];
          const typedMessage = String(application.message || "").trim();
          application.status = action;
          if (action === "Messaged" && !application.message) {
            application.message = "Sent a quick follow-up.";
          }
          if (typedMessage) {
            application.messages.push({
              label: action === "Messaged" ? "Organizer message" : "Organizer note",
              body: typedMessage,
            });
          }
          if (action === "Accepted" || action === "Rejected") {
            application.messages.push({
              label: `Application ${action.toLowerCase()}`,
              body: action === "Accepted"
                ? "This vendor was accepted for the event."
                : "This vendor was declined for the event.",
            });
          } else if (action === "Messaged" && !typedMessage) {
            application.messages.push({
              label: "Organizer message",
              body: "Sent a quick follow-up.",
            });
          }
          setOrganizerApplicationState(Object.fromEntries(state.applications.map((item) => [item.id, item])));
          state.statusMessage = `${application.vendor_name} marked as ${action.toLowerCase()}.`;
          render();
        });
      });

      attachButtonPress(".btn", root);
    }

    render();
  } catch (error) {
    if (error.status === 401) {
      window.location.href = "/signin";
      return;
    }
    if (error.status === 403) {
      window.location.href = "/dashboard";
      return;
    }
    root.innerHTML = `<div class="empty-state"><strong>We couldn't load the organizer dashboard.</strong><p class="muted">${escapeHtml(error.message)}</p></div>`;
  }
}

async function setupEventHistoryPage() {
  const root = document.querySelector("[data-history-app]");
  if (!root) return;

  const auth = await getAuthState();
  if (auth.authenticated && auth.user?.role === "shopper") {
    window.location.href = "/shopper-dashboard";
    return;
  }

  const state = {
    q: "",
    sort: "latest",
  };

  function sortHistory(list) {
    const rows = [...list];
    if (state.sort === "profit") {
      rows.sort((a, b) => (Number(b.profit) || 0) - (Number(a.profit) || 0));
    } else if (state.sort === "rating") {
      rows.sort((a, b) => (Number(b.rating) || 0) - (Number(a.rating) || 0));
    } else {
      rows.sort((a, b) => String(b.eventDate || b.date || "").localeCompare(String(a.eventDate || a.date || "")));
    }
    return rows;
  }

  function render() {
    const rows = sortHistory(
      getEventHistory().filter((entry) => !state.q || String(entry.eventTitle || "").toLowerCase().includes(state.q.toLowerCase())),
    );
    const ratedRows = rows.filter((entry) => entry.rating != null);
    const historySummary = renderMetricGrid([
      { label: "Events logged", value: String(rows.length) },
      { label: "Tracked profit", value: formatMoney(rows.reduce((sum, entry) => sum + (Number(entry.profit) || 0), 0)), tone: "profit" },
      { label: "Average rating", value: ratedRows.length ? (ratedRows.reduce((sum, entry) => sum + (Number(entry.rating) || 0), 0) / ratedRows.length).toFixed(1) : "0.0" },
    ]);

    root.innerHTML = `
      <div class="dashboard-card">
        <div class="stack-row" style="justify-content: space-between; align-items:flex-end;">
          <div>
            <span class="eyebrow">Event history</span>
            <h2 style="margin:8px 0 0;">Past events and performance</h2>
            <p class="muted" style="margin:10px 0 0;">Review what happened, spot patterns, and keep notes that make the next season easier.</p>
            ${historySummary}
          </div>
          <div class="stack-row" style="gap:10px;">
            <input class="mini-input" data-history-q placeholder="Search events..." value="${escapeHtml(state.q)}">
            <select class="mini-input" data-history-sort>
              <option value="latest" ${state.sort === "latest" ? "selected" : ""}>Latest</option>
              <option value="profit" ${state.sort === "profit" ? "selected" : ""}>Highest profit</option>
              <option value="rating" ${state.sort === "rating" ? "selected" : ""}>Highest rating</option>
            </select>
          </div>
        </div>
      </div>

      <div class="dashboard-card" style="margin-top:18px;">
        ${
          rows.length === 0
            ? `<div class="empty-state"><strong>No events logged yet.</strong><p class="muted">Go to Final Plan and mark an event complete after you sell, or log one from your business dashboard.</p></div>`
            : renderStreamList(rows, (entry) => `
                <div class="atlas-stream-card">
                  <div class="atlas-stream-main">
                    <strong>${escapeHtml(entry.eventTitle || "Event")}</strong>
                    <div class="atlas-stream-meta">${escapeHtml(entry.eventDate || entry.date || "")}${entry.rating != null ? ` | ${entry.rating}/5 stars` : ""}</div>
                    <div class="atlas-stream-note">Booth fee ${formatMoney(entry.boothFee)} | Costs ${formatMoney(entry.costs)} | Revenue ${formatMoney(entry.revenue)}</div>
                    ${entry.notes ? `<div class="atlas-stream-note">${escapeHtml(entry.notes)}</div>` : ""}
                  </div>
                  <div class="atlas-stream-aside">
                    <div class="${Number(entry.profit || 0) >= 0 ? "atlas-profit" : "atlas-loss"}" style="font-weight:800;">${formatMoney(entry.profit)}</div>
                    <a class="btn btn-secondary" href="/final-plan">Open plan</a>
                  </div>
                </div>
              `)
        }
      </div>
    `;

    root.querySelector("[data-history-q]")?.addEventListener("input", (event) => {
      state.q = event.target.value || "";
      render();
    });
    root.querySelector("[data-history-sort]")?.addEventListener("change", (event) => {
      state.sort = event.target.value || "latest";
      render();
    });
    attachButtonPress(".btn", root);
  }

  render();
}

async function setupShopperDashboard() {
  const root = document.querySelector("[data-shopper-dashboard-app]");
  if (!root) return;

  try {
    const payload = await api("/api/shopper-dashboard", { method: "GET" });
    const events = payload.events || [];
    const vendors = payload.featured_vendors || [];
    const savedPayload = await api("/api/saved-markets", { method: "GET" });
    const followingPayload = await api("/api/shopper/following", { method: "GET" });
    const state = {
      events,
      vendors,
      favorites: savedPayload.saved_markets || [],
      rsvps: payload.rsvped_events || [],
      followingVendors: followingPayload.vendors || [],
      followingEvents: followingPayload.events || [],
      notifications: followingPayload.notifications || [],
      statusMessage: "",
    };

    function favoriteIds() {
      return new Set((state.favorites || []).map((event) => String(event.id)));
    }

    function renderMapPreview(items) {
      if (!items.length) {
        return `<div class="empty-state"><strong>No map pins yet.</strong><p class="muted">Save a few favorites and they’ll appear here.</p></div>`;
      }
      return `
        <div class="discover-map">
          <div class="discover-map-grid"></div>
          ${items.slice(0, 8).map((event, index) => `
            <button class="discover-map-pin map-card-action ${event.recurrence?.is_recurring ? "recurring" : ""}" type="button" data-shopper-map-event="${escapeHtml(String(event.id || ""))}" style="top:${20 + ((index * 13) % 55)}%; left:${14 + ((index * 17) % 70)}%" aria-label="Open ${escapeHtml(event.name || "event")}"></button>
            <button class="discover-map-label map-card-action" type="button" data-shopper-map-event="${escapeHtml(String(event.id || ""))}" style="top:${20 + ((index * 13) % 55)}%; left:${14 + ((index * 17) % 70)}%">
              <strong>${escapeHtml(event.name || "Event")}</strong>
              <div class="mini-meta"><span class="pill">${escapeHtml(event.city || "")}</span></div>
            </button>
          `).join("")}
        </div>
      `;
    }

    async function toggleFavorite(id) {
      try {
        const existing = favoriteIds().has(String(id));
        if (existing) {
          await api(`/api/saved-markets/${encodeURIComponent(String(id))}`, { method: "DELETE" });
          state.favorites = state.favorites.filter((event) => String(event.id) !== String(id));
          state.statusMessage = "Removed from favorites.";
        } else {
          await api("/api/saved-markets", { method: "POST", body: JSON.stringify({ event_id: String(id) }) });
          const event = state.events.find((item) => String(item.id) === String(id));
          if (event) state.favorites = [event, ...state.favorites.filter((item) => String(item.id) !== String(id))];
          state.statusMessage = "Saved to favorites.";
        }
      } catch (error) {
        state.statusMessage = error.message || "We couldn't update your favorites right now.";
      }
      render();
    }

    function render() {
      const favoriteIdSet = favoriteIds();
      const socialSummaryTiles = renderMetricGrid([
        { label: "Favorites saved", value: String(state.favorites.length) },
        { label: "RSVPs", value: String(state.rsvps.length) },
        { label: "Vendors followed", value: String(state.followingVendors.length) },
        { label: "Feed events", value: String(state.followingEvents.length), tone: "profit" },
      ]);
      root.innerHTML = `
        <div class="dashboard-grid">
          <div class="dashboard-card">
            <span class="eyebrow">Shopper overview</span>
            <h2>Plan your next outing</h2>
            <p class="muted" style="margin-top:12px;">Find markets, save the ones you want to visit, and keep your favorite vendors in view.</p>
            ${socialSummaryTiles}
            <div class="stack-row" style="margin-top:16px;">
              <a class="btn btn-primary" href="/discover">Discover events</a>
              <a class="btn btn-secondary" href="/shopper-plan">View My Plan</a>
              <button class="btn btn-secondary" type="button" disabled>${state.favorites.length} favorites saved</button>
              <button class="btn btn-secondary" type="button" disabled>${state.followingVendors.length} vendors followed</button>
            </div>
            <div class="status ${state.statusMessage ? "success" : ""}" style="margin-top:14px; ${state.statusMessage ? "" : "display:none;"}">${escapeHtml(state.statusMessage)}</div>
          </div>

          <div class="dashboard-card">
            <span class="eyebrow">Discover events</span>
            <h2>Events worth checking out</h2>
            ${
              state.events.length
                ? renderStreamList(state.events.slice(0, 6), (event) => `
                    <div class="atlas-stream-card">
                      <div class="atlas-stream-main">
                        <strong>${escapeHtml(event.name || "Event")}</strong>
                        <div class="atlas-stream-meta">${escapeHtml([event.city, event.state].filter(Boolean).join(", "))}${event.date ? ` | ${escapeHtml(event.date)}` : ""}</div>
                        <div class="atlas-stream-note">${renderRecurrencePill(event.recurrence || null)}${event.fit_reason ? ` ${escapeHtml(event.fit_reason)}` : ""}</div>
                      </div>
                      <div class="atlas-stream-aside">
                        <a class="btn btn-secondary" href="${eventDetailPath(event.id)}">View</a>
                        <button class="btn btn-secondary" type="button" data-shopper-favorite="${event.id}">${favoriteIdSet.has(String(event.id)) ? "Saved" : "Save"}</button>
                      </div>
                    </div>
                  `)
                : `<div class="empty-state"><strong>No events loaded yet.</strong><p class="muted">Try refreshing later or browse Discover for the latest listings.</p></div>`
            }
          </div>

          <div class="dashboard-card">
            <span class="eyebrow">RSVPs</span>
            <h2>Events you're planning to attend</h2>
            ${
              state.rsvps.length
                ? renderStreamList(state.rsvps, (event) => `
                    <div class="atlas-stream-card">
                      <div class="atlas-stream-main">
                        <strong>${escapeHtml(event.name || "Event")}</strong>
                        <div class="atlas-stream-meta">${escapeHtml([event.city, event.state].filter(Boolean).join(", "))}${event.date ? ` | ${escapeHtml(event.date)}` : ""}</div>
                        <div class="atlas-stream-note">${event.vendor_count ? `${escapeHtml(String(event.vendor_count))} vendors expected` : "Vendor list coming soon."}${event.estimated_traffic ? ` | ${escapeHtml(String(event.estimated_traffic))} expected visitors` : ""}</div>
                      </div>
                      <div class="atlas-stream-aside">
                        <a class="btn btn-secondary" href="${eventDetailPath(event.id)}">View</a>
                      </div>
                    </div>
                  `)
                : `<div class="empty-state"><strong>No RSVPs yet.</strong><p class="muted">Open an event and tap RSVP when you know you want to go.</p></div>`
            }
          </div>

          <div class="dashboard-card">
            <span class="eyebrow">Following</span>
            <h2>Vendors you follow</h2>
            ${
              state.followingVendors.length
                ? renderStreamList(state.followingVendors, (vendor) => `
                    <div class="atlas-stream-card">
                      <div class="atlas-stream-main">
                        <strong>${escapeHtml(vendor.name || "Vendor")}</strong>
                        <div class="atlas-stream-meta">@${escapeHtml(vendor.username || "")}</div>
                        <div class="atlas-stream-note">${escapeHtml(vendor.bio || vendor.interests || "")}</div>
                      </div>
                      <div class="atlas-stream-aside">
                        <a class="btn btn-secondary" href="/u/${encodeURIComponent(vendor.username || "")}">View profile</a>
                      </div>
                    </div>
                  `)
                : `<div class="empty-state"><strong>You’re not following any vendors yet.</strong><p class="muted">Open a vendor profile and tap Follow to build your feed.</p></div>`
            }
          </div>

          <div class="dashboard-card">
            <span class="eyebrow">Following feed</span>
            <h2>Where your followed vendors will be</h2>
            ${
              state.followingEvents.length
                ? renderStreamList(state.followingEvents, (event) => `
                    <div class="atlas-stream-card">
                      <div class="atlas-stream-main">
                        <strong>${escapeHtml(event.name || "Event")}</strong>
                        <div class="atlas-stream-meta">${escapeHtml([event.city, event.state].filter(Boolean).join(", "))}${event.date ? ` | ${escapeHtml(event.date)}` : ""}</div>
                        <div class="atlas-stream-note">Vendors you follow attending: ${escapeHtml(event.vendor?.name || "Vendor")}</div>
                      </div>
                      <div class="atlas-stream-aside">
                        <div class="mini-meta">${renderRecurrencePill(event.recurrence || null)}</div>
                        <a class="btn btn-secondary" href="${eventDetailPath(event.id)}">View</a>
                      </div>
                    </div>
                  `)
                : `<div class="empty-state"><strong>No upcoming followed-vendor events yet.</strong><p class="muted">Once a followed vendor shares an event, it will show up here.</p></div>`
            }
          </div>

          <div class="dashboard-card">
            <span class="eyebrow">Notifications</span>
            <h2>Updates from followed vendors</h2>
            ${
              state.notifications.length
                ? renderStreamList(state.notifications, (notification) => `
                    <div class="atlas-stream-card">
                      <div class="atlas-stream-main">
                        <strong>${escapeHtml(notification.title)}</strong>
                        <div class="atlas-stream-note">${escapeHtml(notification.body)}</div>
                      </div>
                      <div class="atlas-stream-aside">
                        <div class="atlas-stream-meta">${escapeHtml(notification.created_at || "")}</div>
                      </div>
                    </div>
                  `)
                : `<div class="empty-state"><strong>No notifications yet.</strong><p class="muted">You’ll see new event shares and soon-upcoming reminders here.</p></div>`
            }
          </div>

          <div class="dashboard-card">
            <span class="eyebrow">Map</span>
            <h2>Favorites on the map</h2>
            ${renderMapPreview(state.favorites.length ? state.favorites : state.events.slice(0, 4))}
          </div>

          <div class="dashboard-card">
            <span class="eyebrow">Favorite events</span>
            <h2>Your saved shortlist</h2>
            ${
              state.favorites.length
                ? renderStreamList(state.favorites, (event) => `
                    <div class="atlas-stream-card">
                      <div class="atlas-stream-main">
                        <strong>${escapeHtml(event.name || "Event")}</strong>
                        <div class="atlas-stream-meta">${escapeHtml([event.city, event.state].filter(Boolean).join(", "))}${event.date ? ` | ${escapeHtml(event.date)}` : ""}</div>
                        <div class="atlas-stream-note">${event.fit_reason ? escapeHtml(event.fit_reason) : "Saved for your shortlist."}</div>
                      </div>
                      <div class="atlas-stream-aside">
                        <a class="btn btn-secondary" href="${eventDetailPath(event.id)}">View</a>
                        <button class="btn btn-secondary" type="button" data-shopper-favorite="${event.id}">Remove</button>
                      </div>
                    </div>
                  `)
                : `<div class="empty-state"><strong>No favorites yet.</strong><p class="muted">Save a few events and they’ll stay here for easy planning.</p></div>`
            }
          </div>

          <div class="dashboard-card">
            <span class="eyebrow">Featured vendors</span>
            <h2>Who to watch</h2>
            ${
              state.vendors.length
                ? renderStreamList(state.vendors, (vendor) => `
                    <div class="atlas-stream-card">
                      <div class="atlas-stream-main">
                        <strong>${escapeHtml(vendor.name)}</strong>
                        <div class="atlas-stream-meta">${escapeHtml(vendor.category)}</div>
                        <div class="atlas-stream-note">${escapeHtml(vendor.note)}</div>
                      </div>
                      <div class="atlas-stream-aside">
                        <a class="btn btn-secondary" href="/u/${encodeURIComponent(vendor.username || "")}">View vendor</a>
                        <button class="btn btn-secondary" type="button" data-featured-follow="${vendor.id}">${vendor.is_following ? "Following" : "Follow"}</button>
                      </div>
                    </div>
                  `)
                : `<div class="empty-state"><strong>No vendors featured yet.</strong><p class="muted">Check back after more vendors complete their profiles and share upcoming events.</p></div>`
            }
          </div>
        </div>
      `;

      root.querySelectorAll("[data-shopper-favorite]").forEach((button) => {
        button.addEventListener("click", () => {
          toggleFavorite(button.getAttribute("data-shopper-favorite"));
        });
      });
      root.querySelectorAll("[data-featured-follow]").forEach((button) => {
        button.addEventListener("click", async () => {
          const vendorId = button.getAttribute("data-featured-follow");
          const currentlyFollowing = button.textContent.includes("Following");
          try {
            await api(`/api/vendors/${vendorId}/follow`, {
              method: currentlyFollowing ? "DELETE" : "POST",
              body: JSON.stringify({}),
            });
            state.vendors = state.vendors.map((vendor) =>
              String(vendor.id) === String(vendorId)
                ? { ...vendor, is_following: !currentlyFollowing }
                : vendor
            );
            if (currentlyFollowing) {
              state.followingVendors = state.followingVendors.filter((vendor) => String(vendor.id) !== String(vendorId));
              state.statusMessage = "Vendor unfollowed.";
            } else {
              const vendor = state.vendors.find((item) => String(item.id) === String(vendorId));
              if (vendor && !state.followingVendors.some((item) => String(item.id) === String(vendorId))) {
                state.followingVendors = [vendor, ...state.followingVendors];
              }
              state.statusMessage = "Vendor followed.";
            }
          } catch (error) {
            state.statusMessage = error.message || "We couldn't update that follow right now.";
          }
          render();
        });
      });
      root.querySelectorAll("[data-shopper-map-event]").forEach((button) => {
        button.addEventListener("click", () => {
          const eventId = button.getAttribute("data-shopper-map-event");
          if (!eventId) return;
          window.location.href = eventDetailPath(eventId);
        });
      });
      attachButtonPress(".btn", root);
    }

    render();
  } catch (error) {
    if (error.status === 401) {
      window.location.href = "/signin";
      return;
    }
    if (error.status === 403) {
      window.location.href = "/dashboard";
      return;
    }
    root.innerHTML = `<div class="empty-state"><strong>We couldn't load the shopper dashboard.</strong><p class="muted">${escapeHtml(error.message)}</p></div>`;
  }
}

async function setupIntegrationsPage() {
  const root = document.querySelector("[data-integrations-app]");
  if (!root) return;

  const auth = await getAuthState();
  if (auth.authenticated && auth.user?.role === "shopper") {
    window.location.href = "/shopper-dashboard";
    return;
  }

  function render(snapshot = getShopifySnapshot()) {
    const connected = Boolean(snapshot.connected);
    const oauthAvailable = snapshot.oauthAvailable !== false && window.shopifyOauthAvailable !== false;
    const products = Array.isArray(snapshot.products) ? snapshot.products : [];
    const status = snapshot.status || "idle";
    const error = snapshot.error || "";

    root.innerHTML = `
      <div class="dashboard-grid">
        <div class="dashboard-card">
          <span class="eyebrow">Integrations</span>
          <h2>Connect your tools</h2>
          <p class="muted" style="margin-top:10px;">Keep your inventory and pricing close to your event plan so profit estimates feel less like guesswork.</p>
          <div class="mini-meta" style="margin-top:12px;">
            <span class="pill">${connected ? "Shopify connected" : "Shopify not connected"}</span>
            <span class="pill">${products.length} products cached</span>
          </div>
          <div id="shopify-inline-status" class="status" style="margin-top:14px; ${error ? "" : "display:none;"}">${escapeHtml(error)}</div>
          ${
            connected
              ? `
                <p class="muted" style="margin-top:14px;">Store: ${escapeHtml(snapshot.shop || "Connected store")}${snapshot.updatedAt ? ` · Last synced ${new Date(snapshot.updatedAt).toLocaleString()}` : ""}</p>
                <div class="stack-row" style="margin-top:14px;">
                  <button class="btn btn-primary" type="button" data-integrations-sync ${status === "loading" ? "disabled" : ""}>${status === "loading" ? "Syncing…" : "Sync products"}</button>
                  <button class="btn btn-secondary" type="button" data-integrations-disconnect>Disconnect</button>
                </div>
              `
              : oauthAvailable ? `
                <div class="field" style="margin-top:18px;">
                  <label for="integrations_shopify_store">Your store name</label>
                  <div style="display:flex;align-items:center;gap:0;">
                    <input id="integrations_shopify_store" class="mini-input" placeholder="yourstore" value="${escapeHtml((snapshot.shop || "").replace(".myshopify.com", ""))}" style="border-radius:6px 0 0 6px;border-right:none;flex:1;">
                    <span style="background:var(--surface-alt,#f8fafc);border:1px solid var(--border,#e2e8f0);border-radius:0 6px 6px 0;padding:0 10px;height:38px;display:flex;align-items:center;color:var(--muted,#64748b);font-size:.85rem;white-space:nowrap;">.myshopify.com</span>
                  </div>
                  <p class="muted" style="margin-top:5px;font-size:.8rem;">Find this in your Shopify admin URL: <em>admin.shopify.com/store/<strong>yourstore</strong></em></p>
                </div>
                <div class="stack-row" style="margin-top:14px;">
                  <button class="btn btn-primary" type="button" data-integrations-connect ${status === "loading" ? "disabled" : ""}>${status === "loading" ? "Connecting…" : "Connect with Shopify"}</button>
                </div>
                <p class="muted" style="margin-top:10px;font-size:.82rem;">You'll be redirected to Shopify to approve access, then brought right back.</p>
                <details style="margin-top:16px;">
                  <summary class="muted" style="cursor:pointer;font-size:.82rem;">Connect manually instead</summary>
                  <div class="field" style="margin-top:12px;">
                    <label for="integrations_shopify_token">Admin API access token</label>
                    <input id="integrations_shopify_token" class="mini-input" placeholder="shpat_…" type="password">
                    <p class="muted" style="margin-top:6px;">In your Shopify admin go to <strong>Settings → Apps and sales channels → Develop apps</strong>, create a custom app, then copy the Admin API access token.</p>
                  </div>
                  <div style="margin-top:10px;">
                    <button class="btn btn-secondary" type="button" data-token-connect ${status === "loading" ? "disabled" : ""}>${status === "loading" ? "Connecting…" : "Connect with token"}</button>
                  </div>
                </details>
              ` : `
                <div class="field" style="margin-top:18px;">
                  <label for="integrations_shopify_store">Store domain</label>
                  <input id="integrations_shopify_store" class="mini-input" placeholder="yourstore.myshopify.com" value="${escapeHtml(snapshot.shop || "")}">
                </div>
                <div class="field" style="margin-top:12px;">
                  <label for="integrations_shopify_token">Admin API access token</label>
                  <input id="integrations_shopify_token" class="mini-input" placeholder="shpat_…" type="password">
                  <p class="muted" style="margin-top:6px;">In your Shopify admin go to <strong>Settings → Apps and sales channels → Develop apps</strong>, create a custom app, then copy the Admin API access token.</p>
                </div>
                <div class="stack-row" style="margin-top:14px;">
                  <button class="btn btn-primary" type="button" data-token-connect ${status === "loading" ? "disabled" : ""}>${status === "loading" ? "Connecting…" : "Connect Shopify"}</button>
                </div>
              `
          }
          <div id="shopify-connect-error" class="status" style="display:none;margin-top:10px;color:var(--error,#dc2626);font-size:.85rem;"></div>
        </div>
        <div class="dashboard-card">
          <span class="eyebrow">CSV / Other platforms</span>
          <h2>Import inventory from a spreadsheet</h2>
          <p class="muted" style="margin-top:10px;">Works with Etsy, WooCommerce, Square, Faire, or any spreadsheet. Export your products as CSV, then upload here.</p>
          <p class="muted" style="margin-top:6px;font-size:.82rem;">Required column: <strong>name</strong> or <strong>title</strong>. Optional: <strong>price</strong>, <strong>quantity</strong>, <strong>category</strong>, <strong>description</strong>.</p>
          <div style="display:flex;gap:.5rem;align-items:center;margin-top:14px;flex-wrap:wrap;">
            <input type="file" id="csv-inventory-file" accept=".csv,text/csv" style="flex:1;min-width:0;font-size:.85rem;">
            <button class="btn btn-primary" type="button" id="csv-inventory-upload">Upload CSV</button>
          </div>
          <div id="csv-upload-status" style="display:none;margin-top:10px;font-size:.85rem;"></div>
        </div>
        <div class="dashboard-card">
          <span class="eyebrow">Inventory snapshot</span>
          <h2>What we can use right now</h2>
          ${
            status === "loading" && !products.length
              ? `<div class="empty-state"><strong>Loading your products…</strong><p class="muted">This usually takes a moment.</p></div>`
              : error && !products.length
                ? `<div class="empty-state"><strong>We couldn't load products right now.</strong><p class="muted">${escapeHtml(error)}</p></div>`
                : !products.length
                  ? `<div class="empty-state"><strong>No products cached yet.</strong><p class="muted">${connected ? "Run a sync to refresh your inventory snapshot." : "Connect Shopify to start bringing product data into Vendor Atlas."}</p></div>`
                  : renderStreamList(products.slice(0, 20), (product) => `
                      <div class="atlas-stream-card">
                        <div class="atlas-stream-main">
                          <strong>${escapeHtml(product.name || "Product")}</strong>
                          <div class="atlas-stream-meta">Price ${formatMoney(product.price)} | Inventory ${Number(product.inventory_quantity || 0)}</div>
                        </div>
                        <div class="atlas-stream-aside">
                          <div class="${Number(product.inventory_quantity || 0) <= 5 ? "atlas-loss" : "atlas-profit"}" style="font-weight:700;">${Number(product.inventory_quantity || 0) <= 5 ? "Low stock" : "Healthy stock"}</div>
                        </div>
                      </div>
                    `)
          }
        </div>
      </div>
    `;

    root.querySelector("[data-token-connect]")?.addEventListener("click", async () => {
      const btn = root.querySelector("[data-token-connect]");
      const errEl = root.querySelector("#shopify-connect-error");
      const shop = (root.querySelector("#integrations_shopify_store")?.value || "").trim();
      const token = (root.querySelector("#integrations_shopify_token")?.value || "").trim();
      if (!shop) { if (errEl) { errEl.textContent = "Enter your store domain."; errEl.style.display = ""; } return; }
      if (!token) { if (errEl) { errEl.textContent = "Enter your Admin API access token."; errEl.style.display = ""; } return; }
      if (errEl) errEl.style.display = "none";
      if (btn) { btn.disabled = true; btn.textContent = "Connecting…"; }
      try {
        const r = await fetch("/api/shopify/connect-token", {
          method: "POST",
          credentials: "include",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ shop_domain: shop, access_token: token }),
        });
        const d = await r.json();
        if (r.ok && d.ok) {
          await shopifyLoadData();
          render(getShopifySnapshot());
        } else {
          if (errEl) { errEl.textContent = d.error || "Connection failed — check your credentials."; errEl.style.display = ""; }
          if (btn) { btn.disabled = false; btn.textContent = "Connect Shopify"; }
        }
      } catch (_) {
        if (errEl) { errEl.textContent = "Network error — try again."; errEl.style.display = ""; }
        if (btn) { btn.disabled = false; btn.textContent = "Connect Shopify"; }
      }
    });
    root.querySelector("[data-integrations-connect]")?.addEventListener("click", () => {
      shopifyConnectFromInput("integrations_shopify_store");
    });
    root.querySelector("[data-integrations-sync]")?.addEventListener("click", () => {
      shopifySyncAndRefresh(() => render(getShopifySnapshot()));
    });
    root.querySelector("[data-integrations-disconnect]")?.addEventListener("click", () => {
      shopifyDisconnectSoft(() => render(getShopifySnapshot()));
    });

    root.querySelector("#csv-inventory-upload")?.addEventListener("click", async () => {
      const fileInput = root.querySelector("#csv-inventory-file");
      const statusEl = root.querySelector("#csv-upload-status");
      const btn = root.querySelector("#csv-inventory-upload");
      const file = fileInput?.files?.[0];
      if (!file) { showToast("Select a CSV file first.", "error"); return; }
      btn.disabled = true; btn.textContent = "Uploading…";
      if (statusEl) { statusEl.style.display = "none"; statusEl.textContent = ""; }
      const form = new FormData();
      form.append("file", file);
      try {
        const r = await fetch("/api/inventory/csv", { method: "POST", credentials: "include", body: form });
        const d = await r.json();
        if (r.ok && d.ok) {
          showToast(d.message || `Imported ${d.imported} products.`, "success");
          if (statusEl) { statusEl.style.display = ""; statusEl.style.color = "var(--success,#16a34a)"; statusEl.textContent = d.message; }
          if (fileInput) fileInput.value = "";
        } else {
          const msg = d.error || "Upload failed.";
          showToast(msg, "error");
          if (statusEl) { statusEl.style.display = ""; statusEl.style.color = "var(--error,#dc2626)"; statusEl.textContent = msg; }
        }
      } catch (_) {
        showToast("Network error — try again.", "error");
      } finally {
        btn.disabled = false; btn.textContent = "Upload CSV";
      }
    });

    attachButtonPress(".btn", root);
  }

  render({ ...getShopifySnapshot(), status: "loading", error: "" });
  await shopifyLoadData();
  render(getShopifySnapshot());

  const shopifyParam = new URLSearchParams(window.location.search).get("shopify");
  if (shopifyParam === "connected") {
    showToast("Shopify connected successfully!", "success");
    window.history.replaceState({}, "", window.location.pathname);
  } else if (shopifyParam === "error") {
    const reason = new URLSearchParams(window.location.search).get("reason") || "";
    const msgs = {
      state: "Session expired. Please sign out, sign back in, then try connecting again.",
      hmac: "Shopify security check failed — your store may have blocked the connection. Try again.",
      token: "Shopify rejected the connection. Make sure you entered the correct store name.",
      missing: "Shopify didn't complete the handshake. Please try connecting again.",
      no_token: "Shopify approved access but didn't return a token. Please try again.",
    };
    showToast(msgs[reason] || `Shopify connection failed (${reason || "unknown"}). Please try again.`, "error");
    window.history.replaceState({}, "", window.location.pathname);
  }
}

async function setupProfilePage() {
  const root = document.querySelector("[data-profile-app]");
  if (!root) return;

  const auth = await getAuthState();
  const viewer = auth?.user || null;
  const pathParts = window.location.pathname.split("/").filter(Boolean);
  const publicUsername = pathParts[0] === "u" ? decodeURIComponent(pathParts[1] || "") : "";
  const isPublicProfile = Boolean(publicUsername);
  const state = { q: "" };

function renderPublicProducts(productsState) {
    if (productsState.status === "loading") {
      return `<div class="empty-state"><strong>Loading products...</strong><p class="muted">Checking this vendor's Shopify storefront now.</p></div>`;
    }
    if (productsState.status === "error") {
      return `<div class="empty-state"><strong>Products are temporarily unavailable.</strong><p class="muted">${escapeHtml(productsState.message || productsState.error || "Please try again soon.")}</p></div>`;
    }
    if (!productsState.connected) {
      return `<div class="empty-state"><strong>No products connected yet.</strong><p class="muted">${escapeHtml(productsState.message || "This vendor has not added Shopify products to their public profile yet.")}</p></div>`;
    }
    if (!productsState.products.length) {
      return `<div class="empty-state"><strong>No products to show right now.</strong><p class="muted">${escapeHtml(productsState.message || "Check back soon for new inventory highlights from this vendor.")}</p></div>`;
    }
    return `
      <div class="vendor-product-grid">
        ${productsState.products.map((product) => `
          <article class="vendor-product-card">
            <div class="vendor-product-media">
              ${
                product.image
                  ? `<img src="${escapeHtml(product.image)}" alt="${escapeHtml(product.name || "Product")}">`
                  : `<div class="vendor-product-placeholder">Vendor pick</div>`
              }
            </div>
            <div class="vendor-product-copy">
              <h3>${escapeHtml(product.name || "Product")}</h3>
              <div class="vendor-product-price">${formatMoney(product.price || 0)}</div>
              <div class="atlas-stream-note">${product.handle ? `Shopify handle: ${escapeHtml(product.handle)}` : "Ready to buy on Shopify."}</div>
            </div>
            <div class="stack-row" style="margin-top:auto;">
              ${product.product_url ? `<a class="btn btn-primary" href="${escapeHtml(product.product_url)}" target="_blank" rel="noreferrer">Buy from Vendor</a>` : ""}
              ${product.product_url ? `<a class="btn btn-secondary" href="${escapeHtml(product.product_url)}" target="_blank" rel="noreferrer">View details</a>` : ""}
            </div>
          </article>
        `).join("")}
      </div>
    `;
  }

  function renderPublicVendorProfile(vendor, productsState) {
    root.innerHTML = `
      <div class="dashboard-grid">
        <div class="dashboard-card">
          <span class="eyebrow">Vendor profile</span>
          <h2>${escapeHtml(vendor.name || `@${vendor.username}`)}</h2>
          <p class="muted" style="margin-top:10px;">@${escapeHtml(vendor.username || "")}</p>
          <p class="muted" style="margin-top:10px;">${escapeHtml(vendor.bio || "This vendor hasn't added a bio yet.")}</p>
          <div class="mini-meta" style="margin-top:12px;">
            <span class="pill">${escapeHtml(vendor.interests || "Vendor")}</span>
            <span class="pill">${vendor.upcoming_events?.length || 0} upcoming events</span>
            <span class="pill">${productsState.connected ? "Shop products available" : "Products coming soon"}</span>
          </div>
          ${
            viewer?.role === "shopper"
              ? `<div class="stack-row" style="margin-top:16px;">
                  <button class="btn btn-primary" type="button" data-follow-vendor="${vendor.id}">${vendor.is_following ? "Following" : "Follow"}</button>
                  <a class="btn btn-secondary" href="/shopper-dashboard">Back to Following</a>
                </div>`
              : ""
          }
        </div>
        <div class="dashboard-card">
          <span class="eyebrow">Upcoming events</span>
          <h2>Where this vendor will be</h2>
          ${
            vendor.upcoming_events?.length
              ? renderStreamList(vendor.upcoming_events, (event) => `
                  <div class="atlas-stream-card">
                    <div class="atlas-stream-main">
                      <strong>${escapeHtml(event.name || "Event")}</strong>
                      <div class="atlas-stream-meta">${escapeHtml([event.city, event.state].filter(Boolean).join(", "))}${event.date ? ` | ${escapeHtml(event.date)}` : ""}</div>
                    </div>
                    <div class="atlas-stream-aside">
                      <div class="mini-meta">${renderRecurrencePill(event.recurrence || null)}</div>
                    </div>
                  </div>
                `)
              : `<div class="empty-state"><strong>No public events shared yet.</strong><p class="muted">Follow this vendor and check back when they share new events.</p></div>`
          }
        </div>
        <div class="dashboard-card" style="grid-column: 1 / -1;">
          <span class="eyebrow">Shop products</span>
          <h2>Inventory highlights</h2>
          <p class="muted" style="margin-top:10px;">Browse a few products from this vendor, then head to Shopify when you're ready to buy.</p>
          ${renderPublicProducts(productsState)}
        </div>
      </div>
    `;

    root.querySelector("[data-follow-vendor]")?.addEventListener("click", async () => {
      const following = Boolean(vendor.is_following);
      await api(`/api/vendors/${vendor.id}/follow`, {
        method: following ? "DELETE" : "POST",
        body: JSON.stringify({}),
      });
      showToast(following ? "Unfollowed vendor" : "Following vendor", "success");
      window.location.reload();
    });
    attachButtonPress(".btn", root);
  }

  function render() {
    if (isPublicProfile) {
      root.innerHTML = `<div class="dashboard-card"><div class="empty-state"><strong>Loading profile…</strong></div></div>`;
      return;
    }

    const profiles = getProfiles().filter((p) => !state.q || String(p.name || "").toLowerCase().includes(state.q.toLowerCase()));
    const currentId = getCurrentProfileId();
    root.innerHTML = `
      <div class="dashboard-card">
        <div class="stack-row" style="justify-content: space-between; align-items:center;">
          <div>
            <span class="eyebrow">Saved profiles</span>
            <h2 style="margin:8px 0 0;">Manage profiles</h2>
            <p class="muted" style="margin:10px 0 0;">Pick a default profile, rename, or delete old ones.${viewer?.username ? ` Your public link is @${escapeHtml(viewer.username)}.` : ""}</p>
          </div>
          <div class="stack-row" style="gap:10px;">
            <input class="mini-input" data-profile-q placeholder="Search profiles…" value="${escapeHtml(state.q)}">
            <button class="btn btn-primary" type="button" data-new-profile>Create profile</button>
          </div>
        </div>
      </div>

      <div class="dashboard-grid" style="margin-top:18px;">
        ${
          profiles.length === 0
            ? `<div class="dashboard-card"><div class="empty-state"><strong>No profiles yet.</strong><p class="muted">Create one, or go to Plan and Save as profile after answering questions.</p></div></div>`
            : profiles.map((p) => `
                <div class="dashboard-card">
                  <div class="mini-meta">
                    <span class="pill">${p.id === currentId ? "Default" : "Profile"}</span>
                    ${p.updatedAt ? `<span class="pill">Updated ${new Date(p.updatedAt).toLocaleDateString()}</span>` : ""}
                  </div>
                  <h3 style="margin:10px 0 6px;">${escapeHtml(p.name || "Profile")}</h3>
                  <p class="muted">Travel: ${escapeHtml(p.answers?.travel || "—")} · Goal: ${escapeHtml(p.answers?.goal || "—")}</p>
                  <div class="stack-row" style="margin-top:14px;">
                    <button class="btn btn-secondary" type="button" data-set-default="${p.id}">Set default</button>
                    <button class="btn btn-secondary" type="button" data-rename="${p.id}">Rename</button>
                    <button class="btn btn-ghost" type="button" data-delete="${p.id}">Delete</button>
                  </div>
                </div>
              `).join("")
        }
      </div>
    `;

    root.querySelector("[data-new-profile]")?.addEventListener("click", () => {
      const name = window.prompt("Profile name?", "My vendor profile");
      if (!name) return;
      const id = saveProfile({ name, answers: getPlanningDraft() || {} });
      setCurrentProfileId(id);
      showToast("Profile created", "success");
      render();
    });
    root.querySelectorAll("[data-set-default]").forEach((btn) => btn.addEventListener("click", () => {
      setCurrentProfileId(btn.getAttribute("data-set-default"));
      showToast("Default profile set", "success");
      render();
    }));
    root.querySelectorAll("[data-rename]").forEach((btn) => btn.addEventListener("click", () => {
      const id = btn.getAttribute("data-rename");
      const p = getProfiles().find((x) => x.id === id);
      const name = window.prompt("New name?", p?.name || "My profile");
      if (!name) return;
      saveProfile({ ...p, id, name });
      showToast("Profile renamed", "success");
      render();
    }));
    root.querySelectorAll("[data-delete]").forEach((btn) => btn.addEventListener("click", () => {
      const id = btn.getAttribute("data-delete");
      deleteProfile(id);
      showToast("Profile deleted", "success");
      render();
    }));

    root.querySelector("[data-profile-q]")?.addEventListener("input", (e) => {
      state.q = e.target.value || "";
      render();
    });

    attachButtonPress(".btn", root);
  }

  if (isPublicProfile) {
    try {
      const payload = await api(`/api/vendors/${encodeURIComponent(publicUsername.toLowerCase())}`, { method: "GET" });
      const vendor = payload.vendor;
      const productsState = { status: "loading", connected: false, products: [], error: "" };
      renderPublicVendorProfile(vendor, productsState);
      try {
        const productsPayload = await api(`/api/vendors/${encodeURIComponent(publicUsername.toLowerCase())}/products`, { method: "GET" });
        productsState.status = "ready";
        productsState.connected = Boolean(productsPayload.connected);
        productsState.products = Array.isArray(productsPayload.products) ? productsPayload.products : [];
        productsState.message = productsPayload.message || "";
      } catch (error) {
        const productsPayload = error?.data || {};
        productsState.status = "error";
        productsState.connected = Boolean(productsPayload.connected);
        productsState.products = [];
        productsState.error = productsPayload.error || error.message || "Products are unavailable right now.";
        productsState.message = productsPayload.message || "";
      }
      renderPublicVendorProfile(vendor, productsState);
      return;
    } catch (error) {
      root.innerHTML = `<div class="dashboard-card"><div class="empty-state"><strong>We couldn’t load that vendor profile.</strong><p class="muted">${escapeHtml(error.message)}</p></div></div>`;
      return;
    }
  }

  render();
}

async function setupEventDetailPage() {
  const root = document.querySelector("[data-event-detail-app]");
  if (!root) return;

  const pathParts = window.location.pathname.split("/").filter(Boolean);
  const eventId = decodeURIComponent(pathParts[pathParts.length - 1] || "");
  if (!eventId) {
    root.innerHTML = `<div class="empty-state"><strong>We couldn't find that event.</strong><p class="muted">Try heading back to Discover and opening another listing.</p></div>`;
    return;
  }

  const auth = await getAuthState();

  try {
    const [payload, attendeesPayload] = await Promise.all([
      api(`/api/events/${encodeURIComponent(eventId)}`, { method: "GET" }),
      fetch(`/api/events/${encodeURIComponent(eventId)}/attendees`, { credentials: "include" })
        .then(r => r.ok ? r.json() : { count: 0, attendees: [] })
        .catch(() => ({ count: 0, attendees: [] })),
    ]);
    const event = payload.event || {};
    const related = Array.isArray(payload.related_events) ? payload.related_events : [];
    const saved = Boolean(payload.is_saved);
    const rsvped = Boolean(payload.is_rsvped);
    const rsvpCount = typeof payload.rsvp_count === "number" ? payload.rsvp_count : (attendeesPayload.count || 0);
    const isShopper = auth.authenticated && auth.user?.role === "shopper";
    const isVendor = auth.authenticated && auth.user?.role === "vendor";

    function renderAttendeesSection(count, attendees, isRsvped) {
      if (!isShopper) return "";
      const avatars = (attendees || []).slice(0, 8).map(a => {
        const initials = (a.display_name || a.username || "?").slice(0, 2).toUpperCase();
        return `<span class="rsvp-avatar" title="${escapeHtml(a.display_name || a.username)}">${escapeHtml(initials)}</span>`;
      }).join("");
      const extra = count > 8 ? `<span class="rsvp-avatar rsvp-avatar-more">+${count - 8}</span>` : "";
      const countLabel = count === 0 ? "No one has RSVP\u2019d yet \u2014 be the first!" : count === 1 ? "1 person is going" : `${count} people are going`;
      return `
        <div class="rsvp-section" id="rsvp-section">
          <button class="btn rsvp-btn ${isRsvped ? "rsvp-btn-going" : "rsvp-btn-default"}" type="button" data-event-rsvp data-rsvped="${isRsvped ? "1" : "0"}">
            ${isRsvped ? "Going \u2713" : "RSVP to Attend"}
          </button>
          <p class="rsvp-count-text" id="rsvp-count-text">${escapeHtml(countLabel)}</p>
          ${count > 0 ? `<div class="rsvp-attendees-row" id="rsvp-attendees-row">${avatars}${extra}</div>` : ""}
        </div>
      `;
    }

    root.innerHTML = `
      <div class="dashboard-grid">
        <div class="dashboard-card">
          <span class="eyebrow">${escapeHtml(event.vendor_category || "Event")}</span>
          <h2>${escapeHtml(event.name || "Event")}</h2>
          <p class="muted" style="margin-top:10px;">${escapeHtml([event.city, event.state].filter(Boolean).join(", "))}${event.date ? ` | ${escapeHtml(event.date)}` : ""}</p>
          <div class="mini-meta" style="margin-top:14px;">
            ${event.fit_score && !isShopper ? `<span class="pill">Fit ${escapeHtml(String(event.fit_score))}</span>` : ""}
            ${event.score_label && !isShopper ? `<span class="pill">${escapeHtml(event.score_label)}</span>` : ""}
            ${!isShopper ? `<span class="pill">${formatMoney(event.booth_price)}</span>` : ""}
            <span class="pill">${escapeHtml(event.event_size || "unknown size")}</span>
            ${renderRecurrencePill(event.recurrence)}
          </div>
          <p class="muted" style="margin-top:14px;">${isShopper ? `Vendors: ${escapeHtml(String(event.vendor_count || "TBD"))}` : `Traffic: ${escapeHtml(String(event.estimated_traffic || "TBD"))} | Vendors: ${escapeHtml(String(event.vendor_count || "TBD"))}`}</p>
          ${!isShopper ? `<p class="muted" style="margin-top:8px;">Organizer: ${escapeHtml(event.organizer_contact || "Contact details not listed yet.")}</p>` : ""}
          <div class="stack-row" style="margin-top:18px;">
            ${
              auth.authenticated
                ? `<button class="btn btn-primary" type="button" data-event-save ${saved ? "disabled" : ""}>${saved ? "Saved to Dashboard" : "Save Event"}</button>`
                : `<a class="btn btn-primary" href="/signup">Create Account to Save</a>`
            }
            ${
              !isShopper && event.application_link && isVendor
                ? `<a class="btn btn-secondary" href="${escapeHtml(event.application_link)}" target="_blank" rel="noreferrer">Apply to Event</a>`
                : ""
            }
            <a class="btn btn-secondary" href="/discover">Back to Discover</a>
          </div>
          ${renderAttendeesSection(rsvpCount, attendeesPayload.attendees, rsvped)}
        </div>

        <div class="dashboard-card">
          ${isShopper ? `
          <span class="eyebrow">About this event</span>
          <h2>What to know before you go</h2>
          ${renderStreamList([
            {
              title: "Expected attendance",
              note: "Plan around the foot traffic estimate for a better experience.",
              value: escapeHtml(String(event.estimated_traffic || "TBD")),
            },
            {
              title: "Vendors attending",
              note: "Browse an assortment of makers, artists, and small businesses.",
              value: escapeHtml(String(event.vendor_count || "TBD")),
            },
            {
              title: "Format",
              note: "Indoor or outdoor — dress and plan accordingly.",
              value: escapeHtml(event.indoor_outdoor || "TBD"),
            },
          ], (item) => `
            <div class="atlas-stream-card">
              <div class="atlas-stream-main">
                <strong>${item.title}</strong>
                <div class="atlas-stream-note">${item.note}</div>
              </div>
              <div class="atlas-stream-aside">
                <div class="pill">${item.value}</div>
              </div>
            </div>
          `)}
          ` : `
          <span class="eyebrow">Quick fit check</span>
          <h2>What to review before applying</h2>
          ${renderStreamList([
            {
              title: "Worth-it score",
              note: event.fit_reason || "A quick blend of booth fee, turnout, and timing signals.",
              value: event.fit_score ? `${event.fit_score}/99` : "Review",
            },
            {
              title: "Foot traffic",
              note: "Use the traffic estimate as a planning signal, not a guarantee.",
              value: escapeHtml(String(event.estimated_traffic || "TBD")),
            },
            {
              title: "Application path",
              note: "Open the organizer link and confirm deadlines, setup rules, and booth details.",
              value: event.application_link ? "Ready" : "Ask organizer",
            },
          ], (item) => `
            <div class="atlas-stream-card">
              <div class="atlas-stream-main">
                <strong>${item.title}</strong>
                <div class="atlas-stream-note">${item.note}</div>
              </div>
              <div class="atlas-stream-aside">
                <div class="pill">${item.value}</div>
              </div>
            </div>
          `)}
          `}
        </div>

        <div class="dashboard-card">
          <span class="eyebrow">Related events</span>
          <h2>Similar options nearby</h2>
          ${
            related.length
              ? renderStreamList(related, (item) => `
                  <div class="atlas-stream-card">
                    <div class="atlas-stream-main">
                      <strong>${escapeHtml(item.name || "Event")}</strong>
                      <div class="atlas-stream-meta">${escapeHtml([item.city, item.state].filter(Boolean).join(", "))}${item.date ? ` | ${escapeHtml(item.date)}` : ""}</div>
                    </div>
                    <div class="atlas-stream-aside">
                      <a class="btn btn-secondary" href="${eventDetailPath(item.id)}">View</a>
                    </div>
                  </div>
                `)
              : `<div class="empty-state"><strong>No similar events yet.</strong><p class="muted">Try a broader browse in Discover to compare more options.</p></div>`
          }
        </div>
      </div>
    `;

    root.querySelector("[data-event-save]")?.addEventListener("click", async (buttonEvent) => {
      try {
        await api("/api/saved-markets", {
          method: "POST",
          body: JSON.stringify({ event_id: eventId }),
        });
        buttonEvent.currentTarget.textContent = "Saved to Dashboard";
        buttonEvent.currentTarget.disabled = true;
        showToast("Event saved to your dashboard", "success");
      } catch (error) {
        if (error.status === 401) {
          window.location.href = "/signup";
          return;
        }
        showToast(error.message || "We couldn't save that event right now.", "error");
      }
    });
    root.querySelector("[data-event-rsvp]")?.addEventListener("click", async (buttonEvent) => {
      const btn = buttonEvent.currentTarget;
      const currentlyRsvped = btn.dataset.rsvped === "1";
      btn.disabled = true;
      try {
        const result = await api(`/api/events/${encodeURIComponent(eventId)}/rsvp`, {
          method: currentlyRsvped ? "DELETE" : "POST",
          body: JSON.stringify({}),
        });
        const newRsvped = !currentlyRsvped;
        const newCount = typeof result.rsvp_count === "number" ? result.rsvp_count : null;
        btn.dataset.rsvped = newRsvped ? "1" : "0";
        btn.textContent = newRsvped ? "Going \u2713" : "RSVP to Attend";
        btn.className = `btn rsvp-btn ${newRsvped ? "rsvp-btn-going" : "rsvp-btn-default"}`;
        if (newCount !== null) {
          const countEl = root.querySelector("#rsvp-count-text");
          if (countEl) {
            const label = newCount === 0 ? "No one has RSVP\u2019d yet \u2014 be the first!" : newCount === 1 ? "1 person is going" : `${newCount} people are going`;
            countEl.textContent = label;
          }
        }
        showToast(currentlyRsvped ? "RSVP removed" : "You\u2019re on the list!", "success");
      } catch (error) {
        if (error.status === 401) {
          window.location.href = "/signup";
          return;
        }
        showToast(error.message || "We couldn't update your RSVP right now.", "error");
      } finally {
        btn.disabled = false;
      }
    });
    attachButtonPress(".btn", root);
  } catch (error) {
    root.innerHTML = `<div class="empty-state"><strong>We couldn't load that event.</strong><p class="muted">${escapeHtml(error.message || "Please try another event.")}</p></div>`;
  }
}

function setupBugReport() {
  const btn = document.createElement("button");
  btn.textContent = "Report a bug";
  btn.setAttribute("aria-label", "Report a bug");
  btn.style.cssText = "position:fixed;bottom:18px;right:18px;z-index:9999;background:var(--surface,#fff);border:1px solid var(--border,#e2e8f0);color:var(--muted,#64748b);font-size:.78rem;padding:6px 12px;border-radius:20px;cursor:pointer;box-shadow:0 2px 8px rgba(0,0,0,.12);";
  document.body.appendChild(btn);

  const overlay = document.createElement("div");
  overlay.style.cssText = "display:none;position:fixed;inset:0;z-index:10000;background:rgba(0,0,0,.45);align-items:center;justify-content:center;";
  overlay.innerHTML = `
    <div style="background:var(--surface,#fff);border-radius:12px;padding:28px 24px;max-width:420px;width:90%;box-shadow:0 8px 32px rgba(0,0,0,.18);">
      <h3 style="margin:0 0 6px;font-size:1.05rem;">Report a bug</h3>
      <p class="muted" style="margin:0 0 14px;font-size:.85rem;">Describe what happened and what you expected. We'll look into it.</p>
      <textarea id="bug-report-text" rows="4" class="mini-input" placeholder="e.g. Clicked 'Find Events' and nothing happened…" style="width:100%;resize:vertical;"></textarea>
      <div style="display:flex;gap:10px;margin-top:14px;justify-content:flex-end;">
        <button id="bug-cancel" class="btn btn-secondary">Cancel</button>
        <button id="bug-submit" class="btn btn-primary">Send report</button>
      </div>
    </div>`;
  document.body.appendChild(overlay);

  function open() { overlay.style.display = "flex"; setTimeout(() => overlay.querySelector("#bug-report-text")?.focus(), 50); }
  function close() { overlay.style.display = "none"; overlay.querySelector("#bug-report-text").value = ""; }

  btn.addEventListener("click", open);
  overlay.querySelector("#bug-cancel").addEventListener("click", close);
  overlay.addEventListener("click", (e) => { if (e.target === overlay) close(); });

  overlay.querySelector("#bug-submit").addEventListener("click", async () => {
    const text = (overlay.querySelector("#bug-report-text")?.value || "").trim();
    if (!text) { showToast("Please describe the bug first.", "error"); return; }
    const submitBtn = overlay.querySelector("#bug-submit");
    submitBtn.disabled = true;
    submitBtn.textContent = "Sending…";
    try {
      const r = await fetch("/api/feedback", {
        method: "POST",
        credentials: "include",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ message: text, page_url: window.location.href }),
      });
      if (!r.ok) {
        const d = await r.json().catch(() => ({}));
        showToast(d.error || "Couldn't send report. Try again.", "error");
      } else {
        close();
        showToast("Bug report sent — thanks!", "success");
      }
    } catch (_) {
      showToast("Couldn't send report. Try again.", "error");
    } finally {
      submitBtn.disabled = false;
      submitBtn.textContent = "Send report";
    }
  });
}

function setupAdminPanel(auth) {
  const role = auth?.user?.role || "";
  if (!["vendor", "market"].includes(role)) return;

  const btn = document.createElement("button");
  btn.textContent = "Admin";
  btn.style.cssText = "position:fixed;bottom:18px;right:130px;z-index:9999;background:var(--surface,#fff);border:1px solid var(--border,#e2e8f0);color:var(--muted,#64748b);font-size:.78rem;padding:6px 12px;border-radius:20px;cursor:pointer;box-shadow:0 2px 8px rgba(0,0,0,.12);";
  document.body.appendChild(btn);

  const panel = document.createElement("div");
  panel.style.cssText = "display:none;position:fixed;bottom:56px;right:120px;z-index:10000;background:var(--surface,#fff);border:1px solid var(--border,#e2e8f0);border-radius:10px;padding:16px;min-width:220px;box-shadow:0 4px 20px rgba(0,0,0,.15);";
  panel.innerHTML = `
    <p style="margin:0 0 10px;font-size:.8rem;font-weight:600;color:var(--muted,#64748b);text-transform:uppercase;letter-spacing:.05em;">Admin tools</p>
    <button id="admin-clear-events" class="btn btn-secondary" style="width:100%;font-size:.83rem;">Clear discovered events</button>
    <button id="admin-view-feedback" class="btn btn-secondary" style="width:100%;font-size:.83rem;margin-top:8px;">View bug reports</button>
  `;
  document.body.appendChild(panel);

  btn.addEventListener("click", () => {
    panel.style.display = panel.style.display === "none" ? "block" : "none";
  });
  document.addEventListener("click", (e) => {
    if (!panel.contains(e.target) && e.target !== btn) panel.style.display = "none";
  });

  panel.querySelector("#admin-clear-events").addEventListener("click", async () => {
    if (!confirm("Delete all discovered (pipeline) events from the DB?")) return;
    const el = panel.querySelector("#admin-clear-events");
    el.disabled = true; el.textContent = "Clearing…";
    try {
      const r = await fetch("/api/admin/events/discovered", { method: "DELETE", credentials: "include" });
      const d = await r.json();
      if (d.ok) showToast(`Cleared ${d.deleted} discovered events.`, "success");
      else showToast(d.error || "Failed to clear.", "error");
    } catch (_) { showToast("Network error.", "error"); }
    el.disabled = false; el.textContent = "Clear discovered events";
    panel.style.display = "none";
  });

  panel.querySelector("#admin-clear-events").insertAdjacentHTML("afterend", `<button id="admin-shopify-check" class="btn btn-secondary" style="width:100%;font-size:.83rem;margin-top:8px;">Shopify config check</button>`);
  panel.querySelector("#admin-shopify-check").addEventListener("click", async () => {
    const el = panel.querySelector("#admin-shopify-check");
    el.disabled = true; el.textContent = "Checking…";
    try {
      const r = await fetch("/api/shopify/config-check", { credentials: "include" });
      const d = await r.json();
      const lines = [
        `oauth_available: ${d.oauth_available}`,
        `api_key_set: ${d.api_key_set} (prefix: ${d.api_key_prefix || "none"})`,
        `api_secret_set: ${d.api_secret_set}`,
        `callback_url: ${d.callback_url}`,
        `scopes: ${d.scopes}`,
        "",
        "→ Register this callback URL in your Shopify Partners app:",
        d.callback_url,
      ];
      alert(lines.join("\n"));
    } catch (_) { showToast("Failed to check config.", "error"); }
    el.disabled = false; el.textContent = "Shopify config check";
    panel.style.display = "none";
  });

  panel.querySelector("#admin-view-feedback").addEventListener("click", async () => {
    const el = panel.querySelector("#admin-view-feedback");
    el.disabled = true; el.textContent = "Loading…";
    const abort = new AbortController();
    const timer = setTimeout(() => abort.abort(), 10000);
    try {
      const r = await fetch("/api/feedback", { credentials: "include", signal: abort.signal });
      clearTimeout(timer);
      if (!r.ok) { showToast("Not authorized to view reports.", "error"); el.disabled = false; el.textContent = "View bug reports"; return; }
      const d = await r.json();
      const items = d.feedback || [];
      if (!items.length) { showToast("No bug reports submitted yet.", "success"); el.disabled = false; el.textContent = "View bug reports"; return; }
      panel.style.display = "none";
      const existing = document.getElementById("_feedback-viewer");
      if (existing) existing.remove();
      const viewer = document.createElement("div");
      viewer.id = "_feedback-viewer";
      viewer.style.cssText = "position:fixed;inset:0;z-index:10001;background:rgba(0,0,0,.5);display:flex;align-items:center;justify-content:center;";
      const inner = items.map((f) =>
        `<div style="border-bottom:1px solid var(--line,#e2e8f0);padding:12px 0;font-size:.84rem;">` +
        `<div style="font-weight:600;">${new Date(f.created_at * 1000).toLocaleDateString()} — ${(f.user_email || "anonymous").replace(/</g,"&lt;")}</div>` +
        `<div style="color:var(--muted,#64748b);font-size:.78rem;margin:2px 0 6px;">${(f.page_url || "").replace(/</g,"&lt;")}</div>` +
        `<div style="white-space:pre-wrap;">${(f.message || "").replace(/</g,"&lt;")}</div></div>`
      ).join("");
      viewer.innerHTML = `<div style="background:var(--surface,#fff);border-radius:12px;padding:24px;max-width:560px;width:92%;max-height:80vh;overflow-y:auto;box-shadow:0 8px 32px rgba(0,0,0,.2);">` +
        `<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:14px;">` +
        `<strong>Bug Reports (${items.length})</strong>` +
        `<button id="_feedback-close" style="background:none;border:none;font-size:1.2rem;cursor:pointer;color:var(--muted,#64748b);">✕</button></div>` +
        inner + `</div>`;
      document.body.appendChild(viewer);
      const closeViewer = () => { viewer.remove(); el.disabled = false; el.textContent = "View bug reports"; };
      viewer.querySelector("#_feedback-close").addEventListener("click", closeViewer);
      viewer.addEventListener("click", (e) => { if (e.target === viewer) closeViewer(); });
    } catch (err) {
      clearTimeout(timer);
      const msg = err && err.name === "AbortError" ? "Request timed out. Try again." : "Failed to load reports.";
      showToast(msg, "error"); el.disabled = false; el.textContent = "View bug reports";
    }
  });
}

// ---------------------------------------------------------------------------
// Profit Dashboard
// ---------------------------------------------------------------------------

function _profitFmt(n) {
  const v = Number(n || 0);
  return v < 0 ? "-$" + Math.abs(v).toLocaleString("en-US", { minimumFractionDigits: 0, maximumFractionDigits: 0 }) : "$" + v.toLocaleString("en-US", { minimumFractionDigits: 0, maximumFractionDigits: 2 });
}

function _renderProfitCards(cards) {
  return `<div class="profit-cards">${cards.map(c => `
    <div class="profit-card">
      <div class="pc-label">${escapeHtml(c.label)}</div>
      <div class="pc-value${c.tone ? " " + c.tone : ""}">${escapeHtml(String(c.value))}</div>
      ${c.sub ? `<div class="pc-sub">${escapeHtml(c.sub)}</div>` : ""}
    </div>`).join("")}</div>`;
}

function _renderBarChart(chartData) {
  if (!chartData || !chartData.length) {
    return `<div class="chart-empty">No data for this period yet.</div>`;
  }
  const max = Math.max(...chartData.map(d => Number(d.revenue || 0)), 1);
  const bars = chartData.map(d => {
    const pct = Math.round((Number(d.revenue || 0) / max) * 120);
    const lbl = (d.label || d.date || "").slice(0, 12);
    return `<div class="chart-bar-col">
      <div class="chart-bar" style="height:${Math.max(pct, 3)}px" title="${escapeHtml(d.label || "")} — ${_profitFmt(d.revenue)}"></div>
      <div class="chart-bar-label">${escapeHtml(lbl)}</div>
    </div>`;
  }).join("");
  return `<div class="chart-wrap"><div class="chart-bars">${bars}</div></div>`;
}

function _renderProfitTable(columns, rows, emptyMsg) {
  if (!rows || !rows.length) {
    return `<div class="empty-state"><strong>${emptyMsg || "No data yet."}</strong></div>`;
  }
  const head = columns.map(c => `<th class="${c.num ? "num" : ""}">${escapeHtml(c.label)}</th>`).join("");
  const body = rows.map(row => {
    const cells = columns.map(c => {
      const val = c.render ? c.render(row) : escapeHtml(String(row[c.key] ?? ""));
      return `<td class="${c.num ? "num" : ""}">${val}</td>`;
    }).join("");
    return `<tr>${cells}</tr>`;
  }).join("");
  return `<table class="profit-table"><thead><tr>${head}</tr></thead><tbody>${body}</tbody></table>`;
}

async function setupProfitPage() {
  const root = document.querySelector("[data-profit-app]");
  if (!root) return;

  const auth = await getAuthState();
  if (!auth.authenticated) {
    window.location.href = "/signin?next=/profit";
    return;
  }
  const role = auth.user?.role || "vendor";

  // Update nav dashboard link based on role
  const navLink = document.getElementById("nav-dashboard-link");
  const mobileNavLink = document.getElementById("mobile-nav-dashboard-link");
  const dashPath = role === "market" ? "/market-dashboard" : role === "shopper" ? "/shopper-dashboard" : "/dashboard";
  if (navLink) { navLink.href = dashPath; navLink.textContent = role === "market" ? "Organizer" : role === "shopper" ? "Shopper" : "Dashboard"; }
  if (mobileNavLink) { mobileNavLink.href = dashPath; mobileNavLink.textContent = navLink ? navLink.textContent : "Dashboard"; }

  if (role === "shopper") {
    window.location.href = "/shopper-dashboard";
    return;
  } else if (role === "vendor") {
    await _setupVendorProfitDashboard(root);
  } else if (role === "market") {
    await _setupOrganizerProfitDashboard(root);
  } else {
    root.innerHTML = `<div class="empty-state"><strong>Profit dashboard is available for vendors and organizers.</strong><p class="muted"><a href="/signup">Create a vendor or organizer account</a> to access this dashboard.</p></div>`;
  }
}

async function _setupVendorProfitDashboard(root) {
  const titleEl = document.getElementById("profit-title");
  const eyebrowEl = document.getElementById("profit-eyebrow");
  const subtitleEl = document.getElementById("profit-subtitle");
  if (eyebrowEl) eyebrowEl.textContent = "Vendor profit dashboard";
  if (titleEl) titleEl.textContent = "Your revenue and market performance";
  if (subtitleEl) subtitleEl.textContent = "Track what's selling, which events deliver, and where your money goes.";

  root.innerHTML = `<div class="empty-state"><strong>Loading vendor data…</strong></div>`;

  let period = "30d";

  async function render() {
    const [revData, prodData, evtData] = await Promise.all([
      api(`/api/vendor/revenue?period=${period}`).catch(() => ({})),
      api("/api/vendor/product-performance").catch(() => ({})),
      api("/api/vendor/event-performance").catch(() => ({})),
    ]);

    const summary = revData.summary || {};
    const chart = Array.isArray(revData.chart) ? revData.chart : [];
    const products = Array.isArray(prodData.products) ? prodData.products : [];
    const events = Array.isArray(evtData.events) ? evtData.events : [];

    const summaryCards = _renderProfitCards([
      { label: "Total Revenue", value: _profitFmt(summary.total_revenue), tone: "profit" },
      { label: "Period Revenue", value: _profitFmt(summary.monthly_revenue), sub: period === "year" ? "This year" : `Last ${period}` },
      { label: "Total Orders", value: String(summary.total_orders || 0) },
      { label: "Avg Order Value", value: _profitFmt(summary.avg_order_value) },
      { label: "Markets Attended", value: String(summary.markets_attended || 0) },
    ]);

    const periodTabs = `<div class="period-tabs" id="vendor-period-tabs">
      ${["7d","30d","90d","year"].map(p => `<button class="period-tab${p === period ? " active" : ""}" data-period="${p}">${p === "year" ? "This year" : "Last " + p}</button>`).join("")}
    </div>`;

    // Product sort state
    let prodSort = "revenue";
    const sortedProducts = (by) => [...products].sort((a, b) => Number(b[by] || 0) - Number(a[by] || 0));

    const prodTableHTML = (by) => _renderProfitTable(
      [
        { label: "Product", key: "name" },
        { label: "Units Sold", key: "units_sold", num: true },
        { label: "Revenue", key: "revenue", num: true, render: r => _profitFmt(r.revenue) },
        { label: "Conv. Rate", key: "conversion_rate", num: true, render: r => (Number(r.conversion_rate || 0) * 100).toFixed(0) + "%" },
      ],
      sortedProducts(by),
      "No product data yet.",
    );

    const evtTableHTML = _renderProfitTable(
      [
        { label: "Event", key: "event_title" },
        { label: "Date", key: "start_date" },
        { label: "Revenue", key: "revenue", num: true, render: r => _profitFmt(r.revenue) },
        { label: "Expenses", key: "expenses", num: true, render: r => _profitFmt(r.expenses) },
        { label: "Fee", key: "vendor_fee", num: true, render: r => _profitFmt(r.vendor_fee) },
        { label: "Profit", key: "profit", num: true, render: r => `<span class="${Number(r.profit||0) >= 0 ? "profit-green" : "profit-red"}">${_profitFmt(r.profit)}</span>` },
      ],
      events,
      "No event performance data yet.",
    );

    // Insights
    const bestProd = products.length ? [...products].sort((a,b) => b.revenue - a.revenue)[0] : null;
    const bestEvt = events.length ? [...events].sort((a,b) => b.profit - a.profit)[0] : null;
    const insights = [
      bestProd ? { icon: "🏆", title: "Best selling product", sub: `${bestProd.name} — ${_profitFmt(bestProd.revenue)} revenue, ${bestProd.units_sold} units sold` } : null,
      bestEvt ? { icon: "📍", title: "Most profitable event", sub: `${bestEvt.event_title || "Event"} returned ${_profitFmt(bestEvt.profit)} profit` } : null,
      { icon: "📦", title: "Markets in tracker", sub: `You've attended ${summary.markets_attended || 0} tracked events so far` },
    ].filter(Boolean);

    root.innerHTML = `
      ${summaryCards}
      <div class="profit-section">
        <h2>Revenue over time</h2>
        ${periodTabs}
        <div id="vendor-chart-area">${_renderBarChart(chart)}</div>
      </div>
      <div class="profit-section">
        <h2>Product performance</h2>
        <div class="table-sort-bar">
          <button class="sort-btn${prodSort === "revenue" ? " active" : ""}" data-sort="revenue">Most revenue</button>
          <button class="sort-btn${prodSort === "units_sold" ? " active" : ""}" data-sort="units_sold">Most sold</button>
        </div>
        <div id="vendor-prod-table">${prodTableHTML(prodSort)}</div>
      </div>
      <div class="profit-section">
        <h2>Event performance</h2>
        ${evtTableHTML}
      </div>
      <div class="profit-section">
        <h2>Insights</h2>
        <ul class="insight-list">
          ${insights.map(i => `<li><div class="insight-icon">${i.icon}</div><div class="insight-text"><strong>${escapeHtml(i.title)}</strong><span>${escapeHtml(i.sub)}</span></div></li>`).join("")}
        </ul>
      </div>
    `;

    // Period tab clicks — re-fetch revenue & re-render
    root.querySelectorAll("[data-period]").forEach(btn => {
      btn.addEventListener("click", async () => {
        period = btn.getAttribute("data-period");
        root.querySelectorAll("[data-period]").forEach(b => b.classList.toggle("active", b === btn));
        const chartArea = root.querySelector("#vendor-chart-area");
        if (chartArea) chartArea.innerHTML = `<div class="chart-empty">Loading…</div>`;
        const fresh = await api(`/api/vendor/revenue?period=${period}`).catch(() => ({}));
        const freshChart = Array.isArray(fresh.chart) ? fresh.chart : [];
        if (chartArea) chartArea.innerHTML = _renderBarChart(freshChart);
      });
    });

    // Product sort clicks
    root.querySelectorAll("[data-sort]").forEach(btn => {
      btn.addEventListener("click", () => {
        prodSort = btn.getAttribute("data-sort");
        root.querySelectorAll("[data-sort]").forEach(b => b.classList.toggle("active", b === btn));
        const tbl = root.querySelector("#vendor-prod-table");
        if (tbl) tbl.innerHTML = prodTableHTML(prodSort);
      });
    });
  }

  await render();
}

async function _setupOrganizerProfitDashboard(root) {
  const titleEl = document.getElementById("profit-title");
  const eyebrowEl = document.getElementById("profit-eyebrow");
  const subtitleEl = document.getElementById("profit-subtitle");
  if (eyebrowEl) eyebrowEl.textContent = "Organizer profit dashboard";
  if (titleEl) titleEl.textContent = "Event revenue and vendor participation";
  if (subtitleEl) subtitleEl.textContent = "See how each event performed, what vendors are requesting, and where your fees add up.";

  root.innerHTML = `<div class="empty-state"><strong>Loading organizer data…</strong></div>`;

  let period = "year";

  async function render() {
    const [revData, evtData, demandData] = await Promise.all([
      api(`/api/organizer/revenue?period=${period}`).catch(() => ({})),
      api("/api/organizer/event-performance").catch(() => ({})),
      api("/api/organizer/vendor-stats").catch(() => ({})),
    ]);

    const summary = revData.summary || {};
    const chart = Array.isArray(revData.chart) ? revData.chart : [];
    const events = Array.isArray(evtData.events) ? evtData.events : [];
    const topCats = Array.isArray(demandData.top_categories) ? demandData.top_categories : [];
    const fastest = Array.isArray(demandData.fastest_selling_events) ? demandData.fastest_selling_events : [];
    const fillRate = Number(demandData.avg_fill_rate || 0);

    const summaryCards = _renderProfitCards([
      { label: "Total Event Revenue", value: _profitFmt(summary.total_revenue), tone: "profit" },
      { label: "Events Hosted", value: String(summary.events_hosted || 0) },
      { label: "Vendors Registered", value: String(summary.vendors_registered || 0) },
      { label: "Avg Booth Fee", value: _profitFmt(summary.avg_booth_fee) },
    ]);

    const periodTabs = `<div class="period-tabs" id="org-period-tabs">
      ${["30d","90d","year"].map(p => `<button class="period-tab${p === period ? " active" : ""}" data-period="${p}">${p === "year" ? "This year" : "Last " + p}</button>`).join("")}
    </div>`;

    const evtTableHTML = _renderProfitTable(
      [
        { label: "Event", key: "name" },
        { label: "Date", key: "date" },
        { label: "Vendors", key: "vendor_count", num: true },
        { label: "Booth Fees", key: "booth_fees_collected", num: true, render: r => _profitFmt(r.booth_fees_collected) },
        { label: "Profit", key: "profit", num: true, render: r => `<span class="profit-green">${_profitFmt(r.profit)}</span>` },
      ],
      events,
      "No event data yet. Create events to start tracking revenue.",
    );

    const catPills = topCats.length
      ? `<div class="cat-pills">${topCats.map(c => `<span class="cat-pill">${escapeHtml(c.category)} <strong>${c.count}</strong></span>`).join("")}</div>`
      : `<p class="muted" style="margin:.5rem 0 0;">No application data yet.</p>`;

    const fastestList = fastest.length
      ? fastest.map(e => `<li><div class="insight-icon">⚡</div><div class="insight-text"><strong>${escapeHtml(e.name)}</strong><span>${e.applicants} applicants${e.date ? " · " + escapeHtml(e.date) : ""}</span></div></li>`).join("")
      : `<li><div class="insight-text"><span class="muted">No event data yet.</span></div></li>`;

    root.innerHTML = `
      ${summaryCards}
      <div class="profit-section">
        <h2>Revenue per event</h2>
        ${periodTabs}
        <div id="org-chart-area">${_renderBarChart(chart)}</div>
      </div>
      <div class="profit-section">
        <h2>Event breakdown</h2>
        ${evtTableHTML}
      </div>
      <div class="profit-section">
        <h2>Vendor demand insights</h2>
        <ul class="insight-list">
          <li>
            <div class="insight-icon">📊</div>
            <div class="insight-text">
              <strong>Most requested vendor categories</strong>
              ${catPills}
            </div>
          </li>
          <li>
            <div class="insight-icon">📈</div>
            <div class="insight-text">
              <strong>Average vendor fill rate</strong>
              <span>${(fillRate * 100).toFixed(0)}% of applicants are accepted on average</span>
            </div>
          </li>
        </ul>
        <h2 style="margin-top:1.25rem;">Fastest filling events</h2>
        <ul class="insight-list">${fastestList}</ul>
      </div>
    `;

    // Period tab clicks
    root.querySelectorAll("[data-period]").forEach(btn => {
      btn.addEventListener("click", async () => {
        period = btn.getAttribute("data-period");
        root.querySelectorAll("[data-period]").forEach(b => b.classList.toggle("active", b === btn));
        const chartArea = root.querySelector("#org-chart-area");
        if (chartArea) chartArea.innerHTML = `<div class="chart-empty">Loading…</div>`;
        const fresh = await api(`/api/organizer/revenue?period=${period}`).catch(() => ({}));
        const freshChart = Array.isArray(fresh.chart) ? fresh.chart : [];
        if (chartArea) chartArea.innerHTML = _renderBarChart(freshChart);
      });
    });
  }

  await render();
}

document.addEventListener("DOMContentLoaded", async () => {
  setupMobileNav();
  setupVendorScenarios();
  setupBugReport();

  const auth = await getAuthState();
  setupAdminPanel(auth);
  renderAuthNav(auth);
  syncHomepageRoleEntryLinks(auth);
  setupAuthGuard(auth);
  setupPreviewGate(auth);

  await setupSignupPage();
  await setupSigninPage();
  await setupMarketFinder(auth);
  await setupDiscoverPage(auth);
  await setupDashboard();
  await setupMarketDashboard();
  await setupShopperDashboard();
  await setupKansasCityListings(auth);
  await setupBusinessPage();
  await setupEventHistoryPage();
  await setupIntegrationsPage();
  await setupProfilePage();
  await setupEventDetailPage();
  await setupProfitPage();
});
