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

function formatMoney(value) {
  if (value === null || value === undefined || value === "") return "TBD";
  return new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: "USD",
    maximumFractionDigits: 0,
  }).format(Number(value));
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

function renderAuthNav(auth) {
  const desktop = document.querySelector("[data-auth-nav]");
  const mobile = document.querySelector("[data-mobile-auth-nav]");
  const nodes = [desktop, mobile].filter(Boolean);

  nodes.forEach((node) => {
    if (auth.authenticated && auth.user) {
      node.innerHTML = `
        <a href="/dashboard">Dashboard</a>
        <button class="linklike" data-logout-button type="button">Logout</button>
      `;
    } else {
      node.innerHTML = `
        <a href="/signin">Sign In</a>
        <a class="btn btn-primary" href="/signup">Sign Up</a>
      `;
    }
  });

  document.querySelectorAll("[data-logout-button]").forEach((button) => {
    button.addEventListener("click", async () => {
      await api("/api/auth/logout", { method: "POST", body: JSON.stringify({}) });
      window.location.href = "/";
    });
  });
}

function setupMobileNav() {
  const button = document.querySelector("[data-mobile-toggle]");
  const drawer = document.querySelector("[data-mobile-drawer]");
  if (!button || !drawer) return;

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

  form.addEventListener("submit", async (event) => {
    event.preventDefault();
    const payload = Object.fromEntries(new FormData(form).entries());
    setStatus(status, "Creating your account...");

    try {
      await api("/api/auth/signup", {
        method: "POST",
        body: JSON.stringify(payload),
      });
      setStatus(status, "Account created. Redirecting to your dashboard...", "success");
      window.location.href = "/dashboard";
    } catch (error) {
      setStatus(status, error.message, "error");
    }
  });
}

async function setupSigninPage() {
  const form = document.querySelector("[data-signin-form]");
  if (!form) return;
  const status = document.querySelector("[data-signin-status]");

  form.addEventListener("submit", async (event) => {
    event.preventDefault();
    const payload = Object.fromEntries(new FormData(form).entries());
    setStatus(status, "Signing you in...");

    try {
      await api("/api/auth/signin", {
        method: "POST",
        body: JSON.stringify(payload),
      });
      setStatus(status, "Signed in. Redirecting to your dashboard...", "success");
      window.location.href = "/dashboard";
    } catch (error) {
      setStatus(status, error.message, "error");
    }
  });
}

function renderMarketCard(event, authenticated) {
  const category = event.vendor_category || "general";
  return `
    <article class="result-card">
      <h3>${event.name}</h3>
      <p class="muted">${event.city}, ${event.state}${event.date ? ` | ${event.date}` : ""}</p>
      <div class="result-meta">
        <span class="pill">${formatMoney(event.booth_price)}</span>
        <span class="pill">${event.event_size || "unknown"} event</span>
        <span class="pill">${category}</span>
      </div>
      <p class="muted">Traffic: ${event.estimated_traffic || "TBD"} | Vendors: ${event.vendor_count || "TBD"}</p>
      <div class="stack-row">
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
  return `
    <article class="result-card">
      <h3>${title}</h3>
      <p class="muted">${event.city || ""}${event.city && event.state ? ", " : ""}${event.state || ""}${event.date ? ` | ${event.date}` : ""}</p>
      <div class="result-meta">
        <span class="pill">${event.source || "discovered"}</span>
        <span class="pill">new opportunity</span>
      </div>
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
      } catch (error) {
        if (error.status === 401) {
          window.location.href = "/signup";
          return;
        }
        button.textContent = error.message;
      }
    });
  });
}

async function setupMarketFinder(auth) {
  const form = document.querySelector("[data-market-search-form]");
  if (!form) return;
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
        results.innerHTML = `<div class="empty-state"><strong>No markets matched yet.</strong><p class="muted">Try another city, widen the date range, or run discover_events in Cursor to add more candidates.</p></div>`;
        setStatus(status, "No results yet.");
        return;
      }

      results.innerHTML = `
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
  return `
    <article class="result-card">
      <h3>${event.name}</h3>
      <p class="muted">${event.city}, ${event.state}${event.date ? ` | ${event.date}` : ""}</p>
      <div class="mini-meta">
        <span class="pill">${formatMoney(event.booth_price)}</span>
        <span class="pill">${event.event_size || "unknown"}</span>
      </div>
      <div class="stack-row">
        ${event.application_link ? `<a class="btn btn-secondary" href="${event.application_link}" target="_blank" rel="noreferrer">Application</a>` : ""}
        <button class="btn btn-secondary" type="button" data-remove-market="${event.id}">Remove</button>
      </div>
    </article>
  `;
}

function renderRecommendationCard(event) {
  return `
    <article class="result-card">
      <h3>${event.name}</h3>
      <p class="muted">${event.city}, ${event.state}${event.date ? ` | ${event.date}` : ""}</p>
      <div class="mini-meta">
        <span class="pill">Fit ${event.schedule_fit_score}</span>
        <span class="pill">${formatMoney(event.booth_price)}</span>
      </div>
      <p class="muted">${(event.schedule_reasons || []).join(" ")}</p>
      ${event.application_link ? `<a class="btn btn-secondary" href="${event.application_link}" target="_blank" rel="noreferrer">Open link</a>` : ""}
    </article>
  `;
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

async function setupDashboard() {
  const root = document.querySelector("[data-dashboard-root]");
  if (!root) return;

  const welcome = document.querySelector("[data-dashboard-welcome]");
  const profileForm = document.querySelector("[data-profile-form]");
  const profileStatus = document.querySelector("[data-profile-status]");
  const savedGrid = document.querySelector("[data-saved-markets]");
  const availabilityForm = document.querySelector("[data-availability-form]");
  const availabilityStatus = document.querySelector("[data-availability-status]");
  const recommendedGrid = document.querySelector("[data-recommended-markets]");

  let weekdaySet = new Set();
  let monthSet = new Set();

  function renderRecommendations(items) {
    if (!recommendedGrid) return;
    recommendedGrid.innerHTML = (items || []).length
      ? items.map(renderRecommendationCard).join("")
      : `<div class="empty-state"><strong>No recommendations yet.</strong><p class="muted">Save your availability and shortlist a few markets to improve schedule-fit suggestions.</p></div>`;
  }

  try {
    const payload = await api("/api/dashboard", { method: "GET" });
    const user = payload.user;
    welcome.textContent = `Welcome back, ${user.name}.`;

    if (profileForm) {
      profileForm.name.value = user.name || "";
      profileForm.interests.value = user.interests || "";
      profileForm.bio.value = user.bio || "";
    }

    if (savedGrid) {
      const items = payload.saved_markets || [];
      savedGrid.innerHTML = items.length
        ? items.map(renderSavedMarketCard).join("")
        : `<div class="empty-state"><strong>No saved markets yet.</strong><p class="muted">Save markets from the Find My Next Market page and they will show up here.</p></div>`;

      document.querySelectorAll("[data-remove-market]").forEach((button) => {
        button.addEventListener("click", async () => {
          await api(`/api/saved-markets/${button.dataset.removeMarket}`, { method: "DELETE" });
          window.location.reload();
        });
      });
    }

    if (availabilityForm) {
      const availability = payload.availability || {};
      availabilityForm.weekly_capacity.value = availability.weekly_capacity || 2;
      availabilityForm.monthly_goal.value = availability.monthly_goal || 6;
      availabilityForm.notes.value = availability.notes || "";
      weekdaySet = setupToggleGroup("[data-weekday]", availability.weekdays || []);
      monthSet = setupToggleGroup("[data-month]", availability.preferred_months || []);
    }

    renderRecommendations(payload.recommended_markets || []);
  } catch (error) {
    if (error.status === 401) {
      window.location.href = "/signin";
      return;
    }
    root.innerHTML = `<div class="empty-state"><strong>Could not load dashboard.</strong><p class="muted">${error.message}</p></div>`;
    return;
  }

  if (profileForm) {
    profileForm.addEventListener("submit", async (event) => {
      event.preventDefault();
      const payload = Object.fromEntries(new FormData(profileForm).entries());
      setStatus(profileStatus, "Saving profile...");
      try {
        await api("/api/profile", {
          method: "POST",
          body: JSON.stringify(payload),
        });
        setStatus(profileStatus, "Profile updated.", "success");
      } catch (error) {
        setStatus(profileStatus, error.message, "error");
      }
    });
  }

  if (availabilityForm) {
    if (!weekdaySet.size) {
      weekdaySet = setupToggleGroup("[data-weekday]", []);
    }
    if (!monthSet.size) {
      monthSet = setupToggleGroup("[data-month]", []);
    }

    availabilityForm.addEventListener("submit", async (event) => {
      event.preventDefault();
      setStatus(availabilityStatus, "Saving your planner...");

      try {
        const payload = {
          weekdays: weekdayLabels.filter((label) => weekdaySet.has(label)),
          preferred_months: monthLabels.filter((label) => monthSet.has(label)),
          weekly_capacity: availabilityForm.weekly_capacity.value,
          monthly_goal: availabilityForm.monthly_goal.value,
          notes: availabilityForm.notes.value,
        };
        const response = await api("/api/availability", {
          method: "POST",
          body: JSON.stringify(payload),
        });
        renderRecommendations(response.recommended_markets || []);
        setStatus(availabilityStatus, "Availability updated.", "success");
      } catch (error) {
        setStatus(availabilityStatus, error.message, "error");
      }
    });
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

document.addEventListener("DOMContentLoaded", async () => {
  setupMobileNav();
  setupVendorScenarios();

  const auth = await getAuthState();
  renderAuthNav(auth);

  await setupSignupPage();
  await setupSigninPage();
  await setupMarketFinder(auth);
  await setupDashboard();
  await setupKansasCityListings(auth);
});
