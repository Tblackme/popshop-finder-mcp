/**
 * ai-features.js — Vendor Atlas AI Add-on Layer
 *
 * Drop this script into any page that needs AI buttons.
 * It never replaces core functionality — it only adds optional AI calls
 * on top of what the core UI already does.
 *
 * Usage: <script src="/assets/ai-features.js"></script>
 *
 * Then call:
 *   AI.injectBioButton(containerSelector, formFields)
 *   AI.injectProductDescButton(containerSelector, formFields)
 *   AI.injectSocialPostButton(containerSelector, formFields)
 *   AI.injectMatchButton(containerSelector, vendorFn, eventFn)
 */

const AI = (() => {
  // ------------------------------------------------------------------
  // Config
  // ------------------------------------------------------------------
  const BASE = "/api/ai";

  // ------------------------------------------------------------------
  // Internal helpers
  // ------------------------------------------------------------------

  async function _checkEnabled() {
    try {
      const res = await fetch(`${BASE}/status`);
      const data = await res.json();
      return data.features || {};
    } catch {
      return {};
    }
  }

  async function _post(path, body) {
    const res = await fetch(`${BASE}${path}`, {
      method: "POST",
      credentials: "include",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({ error: res.statusText }));
      throw new Error(err.error || `HTTP ${res.status}`);
    }
    return res.json();
  }

  function _btn(label, onClick) {
    const btn = document.createElement("button");
    btn.type = "button";
    btn.className = "ai-btn";
    btn.innerHTML = `✦ ${label}`;
    btn.style.cssText = [
      "display:inline-flex", "align-items:center", "gap:6px",
      "padding:6px 14px", "border-radius:6px", "font-size:13px",
      "font-weight:600", "cursor:pointer", "border:1.5px solid #7c3aed",
      "background:#f5f3ff", "color:#7c3aed", "transition:all .15s",
    ].join(";");
    btn.addEventListener("mouseenter", () => {
      btn.style.background = "#7c3aed";
      btn.style.color = "#fff";
    });
    btn.addEventListener("mouseleave", () => {
      btn.style.background = "#f5f3ff";
      btn.style.color = "#7c3aed";
    });
    btn.addEventListener("click", onClick);
    return btn;
  }

  function _setLoading(btn, loading) {
    btn.disabled = loading;
    btn.innerHTML = loading ? "✦ Generating…" : btn._originalLabel;
    btn.style.opacity = loading ? "0.7" : "1";
  }

  function _toast(msg, type = "info") {
    const colors = { info: "#7c3aed", error: "#dc2626", success: "#16a34a" };
    const el = document.createElement("div");
    el.style.cssText = [
      "position:fixed", "bottom:20px", "right:20px", "z-index:9999",
      `background:${colors[type] || colors.info}`, "color:#fff",
      "padding:10px 16px", "border-radius:8px", "font-size:13px",
      "box-shadow:0 4px 12px rgba(0,0,0,.15)", "max-width:320px",
    ].join(";");
    el.textContent = msg;
    document.body.appendChild(el);
    setTimeout(() => el.remove(), 4000);
  }

  function _modal(title, content) {
    const overlay = document.createElement("div");
    overlay.style.cssText = [
      "position:fixed", "inset:0", "background:rgba(0,0,0,.5)",
      "z-index:10000", "display:flex", "align-items:center", "justify-content:center",
    ].join(";");
    const box = document.createElement("div");
    box.style.cssText = [
      "background:#fff", "border-radius:12px", "padding:24px",
      "max-width:560px", "width:90%", "max-height:80vh", "overflow-y:auto",
      "box-shadow:0 20px 60px rgba(0,0,0,.2)",
    ].join(";");
    box.innerHTML = `
      <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:16px">
        <h3 style="margin:0;font-size:16px;color:#1e1b4b">✦ ${title}</h3>
        <button id="_ai_close" style="border:none;background:none;font-size:20px;cursor:pointer;color:#6b7280">×</button>
      </div>
      <div id="_ai_modal_body">${content}</div>
    `;
    overlay.appendChild(box);
    document.body.appendChild(overlay);
    box.querySelector("#_ai_close").addEventListener("click", () => overlay.remove());
    overlay.addEventListener("click", (e) => { if (e.target === overlay) overlay.remove(); });
    return { overlay, body: box.querySelector("#_ai_modal_body") };
  }

  // ------------------------------------------------------------------
  // Public: Vendor Bio Button
  // ------------------------------------------------------------------

  /**
   * injectBioButton(containerSelector, getFields)
   *
   * getFields() should return:
   *   { business_name, category, products[], location, tone, existing_bio }
   *
   * The button will append to the container and open a modal with the result.
   * The user can then click "Use This Bio" to apply it to a target textarea.
   *
   * @param {string} containerSelector  — CSS selector for the button container
   * @param {Function} getFields        — returns field values from the form
   * @param {string} [targetSelector]   — CSS selector for bio textarea (optional)
   */
  function injectBioButton(containerSelector, getFields, targetSelector = "") {
    const container = document.querySelector(containerSelector);
    if (!container) return;
    const btn = _btn("Generate Bio with AI", async () => {
      btn._originalLabel = btn.innerHTML;
      _setLoading(btn, true);
      try {
        const fields = getFields();
        const data = await _post("/content/vendor-bio", fields);
        _setLoading(btn, false);
        const { overlay, body } = _modal("AI-Generated Bio", `
          <p style="margin:0 0 8px;font-size:13px;color:#6b7280">Tagline</p>
          <p style="margin:0 0 16px;font-style:italic;color:#1e1b4b">"${_esc(data.tagline)}"</p>
          <p style="margin:0 0 8px;font-size:13px;color:#6b7280">Bio</p>
          <p style="margin:0 0 16px;line-height:1.6">${_esc(data.bio)}</p>
          <p style="margin:0 0 8px;font-size:13px;color:#6b7280">Keywords</p>
          <p style="margin:0 0 20px;color:#7c3aed">${data.keywords.map(_esc).join(" · ")}</p>
          ${targetSelector ? `<button id="_ai_use_bio" style="width:100%;padding:10px;background:#7c3aed;color:#fff;border:none;border-radius:8px;font-weight:600;cursor:pointer">Use This Bio</button>` : ""}
        `);
        if (targetSelector) {
          body.querySelector("#_ai_use_bio")?.addEventListener("click", () => {
            const el = document.querySelector(targetSelector);
            if (el) el.value = data.bio;
            overlay.remove();
            _toast("Bio applied!", "success");
          });
        }
      } catch (e) {
        _setLoading(btn, false);
        _toast(e.message.includes("disabled") ? "AI content is not enabled." : `Error: ${e.message}`, "error");
      }
    });
    btn._originalLabel = btn.innerHTML;
    container.appendChild(btn);
  }

  // ------------------------------------------------------------------
  // Public: Product Description Button
  // ------------------------------------------------------------------

  function injectProductDescButton(containerSelector, getFields, targetSelector = "") {
    const container = document.querySelector(containerSelector);
    if (!container) return;
    const btn = _btn("Generate Description with AI", async () => {
      btn._originalLabel = btn.innerHTML;
      _setLoading(btn, true);
      try {
        const fields = getFields();
        const data = await _post("/content/product-description", fields);
        _setLoading(btn, false);
        const { overlay, body } = _modal("AI-Generated Description", `
          <p style="margin:0 0 8px;font-size:13px;color:#6b7280">Short</p>
          <p style="margin:0 0 16px;font-style:italic">"${_esc(data.short_description)}"</p>
          <p style="margin:0 0 8px;font-size:13px;color:#6b7280">Full Description</p>
          <p style="margin:0 0 16px;line-height:1.6">${_esc(data.description)}</p>
          ${data.suggested_price_note ? `<p style="margin:0 0 20px;font-size:13px;background:#fef3c7;padding:8px 12px;border-radius:6px">💡 ${_esc(data.suggested_price_note)}</p>` : ""}
          ${targetSelector ? `<button id="_ai_use_desc" style="width:100%;padding:10px;background:#7c3aed;color:#fff;border:none;border-radius:8px;font-weight:600;cursor:pointer">Use This Description</button>` : ""}
        `);
        if (targetSelector) {
          body.querySelector("#_ai_use_desc")?.addEventListener("click", () => {
            const el = document.querySelector(targetSelector);
            if (el) el.value = data.description;
            overlay.remove();
            _toast("Description applied!", "success");
          });
        }
      } catch (e) {
        _setLoading(btn, false);
        _toast(e.message.includes("disabled") ? "AI content is not enabled." : `Error: ${e.message}`, "error");
      }
    });
    btn._originalLabel = btn.innerHTML;
    container.appendChild(btn);
  }

  // ------------------------------------------------------------------
  // Public: Social Post Generator Button
  // ------------------------------------------------------------------

  function injectSocialPostButton(containerSelector, getFields) {
    const container = document.querySelector(containerSelector);
    if (!container) return;
    const btn = _btn("Generate Social Posts with AI", async () => {
      btn._originalLabel = btn.innerHTML;
      _setLoading(btn, true);
      try {
        const fields = getFields();
        const data = await _post("/marketing/social-posts", fields);
        _setLoading(btn, false);
        _modal("AI Social Posts", `
          <div style="margin-bottom:16px">
            <p style="margin:0 0 6px;font-size:13px;font-weight:600;color:#6b7280">INSTAGRAM</p>
            <div style="background:#f9fafb;border-radius:8px;padding:12px;white-space:pre-wrap;font-size:13px;line-height:1.6">${_esc(data.instagram)}</div>
            <button onclick="navigator.clipboard.writeText(${JSON.stringify(data.instagram)})" style="margin-top:6px;font-size:12px;color:#7c3aed;background:none;border:none;cursor:pointer">Copy</button>
          </div>
          <div style="margin-bottom:16px">
            <p style="margin:0 0 6px;font-size:13px;font-weight:600;color:#6b7280">FACEBOOK</p>
            <div style="background:#f9fafb;border-radius:8px;padding:12px;white-space:pre-wrap;font-size:13px;line-height:1.6">${_esc(data.facebook)}</div>
            <button onclick="navigator.clipboard.writeText(${JSON.stringify(data.facebook)})" style="margin-top:6px;font-size:12px;color:#7c3aed;background:none;border:none;cursor:pointer">Copy</button>
          </div>
          <div style="margin-bottom:16px">
            <p style="margin:0 0 6px;font-size:13px;font-weight:600;color:#6b7280">X / TWITTER</p>
            <div style="background:#f9fafb;border-radius:8px;padding:12px;white-space:pre-wrap;font-size:13px;line-height:1.6">${_esc(data.twitter)}</div>
            <button onclick="navigator.clipboard.writeText(${JSON.stringify(data.twitter)})" style="margin-top:6px;font-size:12px;color:#7c3aed;background:none;border:none;cursor:pointer">Copy</button>
          </div>
          <p style="margin:0;font-size:12px;color:#9ca3af"># ${data.hashtags.map(_esc).join("  #")}</p>
        `);
      } catch (e) {
        _setLoading(btn, false);
        _toast(e.message.includes("disabled") ? "AI marketing is not enabled." : `Error: ${e.message}`, "error");
      }
    });
    btn._originalLabel = btn.innerHTML;
    container.appendChild(btn);
  }

  // ------------------------------------------------------------------
  // Public: Smart Match Button (vendor ↔ event)
  // ------------------------------------------------------------------

  /**
   * injectMatchButton(containerSelector, getVendor, getEvent)
   * getVendor() → vendor dict, getEvent() → event dict
   */
  function injectMatchButton(containerSelector, getVendor, getEvent) {
    const container = document.querySelector(containerSelector);
    if (!container) return;
    const btn = _btn("Find Matches with AI", async () => {
      btn._originalLabel = btn.innerHTML;
      _setLoading(btn, true);
      try {
        const data = await _post("/match/vendor-event", {
          vendor: getVendor(),
          event: getEvent(),
        });
        _setLoading(btn, false);
        const scoreColor = data.score >= 70 ? "#16a34a" : data.score >= 45 ? "#d97706" : "#dc2626";
        _modal("AI Match Analysis", `
          <div style="display:flex;align-items:center;gap:12px;margin-bottom:20px">
            <div style="width:64px;height:64px;border-radius:50%;background:${scoreColor};display:flex;align-items:center;justify-content:center;color:#fff;font-size:20px;font-weight:700">${data.score}</div>
            <div>
              <div style="font-weight:700;font-size:15px">${_esc(data.verdict)}</div>
              <div style="font-size:13px;color:#6b7280">out of 100</div>
            </div>
          </div>
          ${data.reasons_for.length ? `
            <p style="margin:0 0 6px;font-size:13px;font-weight:600;color:#16a34a">Why it works</p>
            <ul style="margin:0 0 16px;padding-left:20px;font-size:13px;line-height:1.8">
              ${data.reasons_for.map(r => `<li>${_esc(r)}</li>`).join("")}
            </ul>` : ""}
          ${data.reasons_against.length ? `
            <p style="margin:0 0 6px;font-size:13px;font-weight:600;color:#dc2626">Things to consider</p>
            <ul style="margin:0 0 16px;padding-left:20px;font-size:13px;line-height:1.8">
              ${data.reasons_against.map(r => `<li>${_esc(r)}</li>`).join("")}
            </ul>` : ""}
          <p style="margin:0;padding:12px;background:#f5f3ff;border-radius:8px;font-size:13px;line-height:1.6">${_esc(data.recommendation)}</p>
        `);
      } catch (e) {
        _setLoading(btn, false);
        _toast(e.message.includes("disabled") ? "AI matching is not enabled." : `Error: ${e.message}`, "error");
      }
    });
    btn._originalLabel = btn.innerHTML;
    container.appendChild(btn);
  }

  // ------------------------------------------------------------------
  // Public: Caption Generator Button (Feature 3)
  // ------------------------------------------------------------------

  /**
   * injectCaptionButton(containerSelector, getFields, targetSelector)
   * getFields() → { product_name, event_name, description, tone }
   */
  function injectCaptionButton(containerSelector, getFields, targetSelector = "") {
    const container = document.querySelector(containerSelector);
    if (!container) return;
    const btn = _btn("Generate Caption with AI", async () => {
      btn._originalLabel = btn.innerHTML;
      _setLoading(btn, true);
      try {
        const fields = getFields();
        const data = await _post("/generate-caption", fields);
        _setLoading(btn, false);
        const { overlay, body } = _modal("AI-Generated Caption", `
          <p style="margin:0 0 8px;font-size:13px;color:#6b7280">Caption</p>
          <div style="background:#f9fafb;border-radius:8px;padding:12px;white-space:pre-wrap;font-size:13px;line-height:1.6;margin-bottom:12px">${_esc(data.caption)}</div>
          <p style="margin:0 0 8px;font-size:12px;color:#9ca3af"># ${(data.hashtags || []).map(_esc).join("  #")}</p>
          ${targetSelector ? `<button id="_ai_use_caption" style="width:100%;padding:10px;background:#7c3aed;color:#fff;border:none;border-radius:8px;font-weight:600;cursor:pointer;margin-top:12px">Use This Caption</button>` : ""}
        `);
        if (targetSelector) {
          body.querySelector("#_ai_use_caption")?.addEventListener("click", () => {
            const el = document.querySelector(targetSelector);
            if (el) el.value = data.caption + (data.hashtags?.length ? "\n\n" + data.hashtags.map(t => "#" + t).join(" ") : "");
            overlay.remove();
            _toast("Caption applied!", "success");
          });
        }
      } catch (e) {
        _setLoading(btn, false);
        _toast(e.message.includes("disabled") ? "AI content is not enabled." : `Error: ${e.message}`, "error");
      }
    });
    btn._originalLabel = btn.innerHTML;
    container.appendChild(btn);
  }

  // ------------------------------------------------------------------
  // Public: Event Predictor (Feature 4)
  // ------------------------------------------------------------------

  /**
   * injectEventPredictor(containerSelector, getEvent, getVendor)
   * getEvent() → event dict, getVendor() → vendor dict (optional)
   */
  function injectEventPredictor(containerSelector, getEvent, getVendor = () => ({})) {
    const container = document.querySelector(containerSelector);
    if (!container) return;
    const btn = _btn("Predict Event Success", async () => {
      btn._originalLabel = btn.innerHTML;
      _setLoading(btn, true);
      try {
        const data = await _post("/event-prediction", { event: getEvent(), vendor: getVendor() });
        _setLoading(btn, false);
        const colors = { teal: "#0f766e", amber: "#d97706", green: "#16a34a" };
        const bg = colors[data.risk_color] || "#6b7280";
        _modal("Event Success Prediction", `
          <div style="display:flex;align-items:center;gap:12px;margin-bottom:20px">
            <div style="background:${bg};color:#fff;border-radius:10px;padding:8px 18px;font-weight:700;font-size:15px">${_esc(data.risk_level)}</div>
          </div>
          <div style="display:grid;grid-template-columns:1fr 1fr;gap:10px;margin-bottom:16px">
            <div style="background:#f9fafb;border-radius:8px;padding:12px;text-align:center">
              <div style="font-size:11px;color:#6b7280;margin-bottom:4px">REVENUE RANGE</div>
              <div style="font-weight:700;font-size:16px">$${data.revenue_low}–$${data.revenue_high}</div>
            </div>
            <div style="background:#f9fafb;border-radius:8px;padding:12px;text-align:center">
              <div style="font-size:11px;color:#6b7280;margin-bottom:4px">FOOT TRAFFIC</div>
              <div style="font-weight:700;font-size:16px">${_esc(data.traffic_estimate)}</div>
            </div>
          </div>
          <p style="margin:0 0 12px;font-size:13px;line-height:1.6">${_esc(data.summary)}</p>
          <p style="margin:0 0 12px;font-size:13px;color:#6b7280;font-style:italic">${_esc(data.competition_note)}</p>
          ${data.tips?.length ? `
            <p style="margin:0 0 6px;font-size:13px;font-weight:600;color:#374151">Tips</p>
            <ul style="margin:0;padding-left:18px;font-size:13px;line-height:1.8">
              ${data.tips.map(t => `<li>${_esc(t)}</li>`).join("")}
            </ul>` : ""}
          <p style="margin:12px 0 0;font-size:11px;color:#9ca3af">Confidence: ${_esc(data.confidence)}</p>
        `);
      } catch (e) {
        _setLoading(btn, false);
        _toast(`Error: ${e.message}`, "error");
      }
    });
    btn._originalLabel = btn.innerHTML;
    container.appendChild(btn);
  }

  // ------------------------------------------------------------------
  // Public: Product Tag Suggester (Feature 7)
  // ------------------------------------------------------------------

  /**
   * injectProductTagger(containerSelector, getFields, tagsContainerSelector)
   * getFields() → { product_name, category, description }
   * tagsContainerSelector → element to inject tag pills into
   */
  function injectProductTagger(containerSelector, getFields, tagsContainerSelector = "") {
    const container = document.querySelector(containerSelector);
    if (!container) return;
    const btn = _btn("Suggest Tags with AI", async () => {
      btn._originalLabel = btn.innerHTML;
      _setLoading(btn, true);
      try {
        const fields = getFields();
        const data = await _post("/product-tags", fields);
        _setLoading(btn, false);
        if (tagsContainerSelector) {
          const tagsEl = document.querySelector(tagsContainerSelector);
          if (tagsEl) {
            tagsEl.innerHTML = (data.tags || []).map(tag =>
              `<button type="button" class="ai-tag-pill" style="display:inline-block;margin:3px;padding:4px 10px;background:#f5f3ff;color:#7c3aed;border:1px solid #ddd6fe;border-radius:99px;font-size:12px;cursor:pointer" data-tag="${_esc(tag)}">${_esc(tag)}</button>`
            ).join("");
            tagsEl.querySelectorAll(".ai-tag-pill").forEach(pill => {
              pill.addEventListener("click", () => {
                pill.style.background = "#7c3aed";
                pill.style.color = "#fff";
                _toast(`Tag "${pill.dataset.tag}" selected`, "success");
              });
            });
          }
        } else {
          _modal("Suggested Tags", `
            <p style="margin:0 0 12px;font-size:13px;color:#6b7280">Click to copy any tag</p>
            <div style="display:flex;flex-wrap:wrap;gap:8px">
              ${(data.tags || []).map(tag =>
                `<span onclick="navigator.clipboard.writeText('${_esc(tag)}'); this.style.background='#7c3aed'; this.style.color='#fff';"
                  style="padding:5px 12px;background:#f5f3ff;color:#7c3aed;border:1px solid #ddd6fe;border-radius:99px;font-size:13px;cursor:pointer">${_esc(tag)}</span>`
              ).join("")}
            </div>
          `);
        }
      } catch (e) {
        _setLoading(btn, false);
        _toast(`Error: ${e.message}`, "error");
      }
    });
    btn._originalLabel = btn.innerHTML;
    container.appendChild(btn);
  }

  // ------------------------------------------------------------------
  // Public: AI Insights Panel (Feature 2 — dashboard)
  // ------------------------------------------------------------------

  /**
   * renderInsightsPanel(containerSelector, vendor, products, savedEvents)
   * Fetches vendor insights and renders a card panel.
   */
  async function renderInsightsPanel(containerSelector, vendor = {}, products = [], savedEvents = []) {
    const container = document.querySelector(containerSelector);
    if (!container) return;
    container.innerHTML = `<div style="font-size:13px;color:#6b7280;padding:8px 0">✦ Loading insights…</div>`;
    try {
      const data = await _post("/vendor-insights", {
        vendor_id: vendor.id || null,
        products,
        saved_events: savedEvents,
        vendor_category: vendor.vendor_category || vendor.category || "",
      });
      const insights = data.insights || [];
      if (!insights.length) {
        container.innerHTML = "";
        return;
      }
      container.innerHTML = `
        <div class="ai-insights-panel" style="margin-top:1rem;">
          <div style="display:flex;align-items:center;gap:6px;margin-bottom:10px">
            <span style="font-size:12px;font-weight:700;letter-spacing:.04em;color:#7c3aed;text-transform:uppercase">✦ AI Insights</span>
          </div>
          ${insights.map(i => `
            <div style="display:flex;gap:10px;align-items:flex-start;padding:8px 0;border-bottom:1px solid #f3f4f6;">
              <span style="font-size:1.1rem;line-height:1.4">${i.icon || "✦"}</span>
              <span style="font-size:13px;line-height:1.55;color:#374151">${_esc(i.text)}</span>
            </div>`).join("")}
        </div>`;
    } catch (_) {
      container.innerHTML = "";
    }
  }

  // ------------------------------------------------------------------
  // Public: Event Recommendations Panel (Feature 1 — dashboard)
  // ------------------------------------------------------------------

  /**
   * renderRecommendedEvents(containerSelector, vendor)
   * Renders "Recommended Events For You" cards.
   */
  async function renderRecommendedEvents(containerSelector, vendor = {}) {
    const container = document.querySelector(containerSelector);
    if (!container) return;
    container.innerHTML = `<div style="font-size:13px;color:#6b7280;padding:8px 0">✦ Finding events for you…</div>`;
    try {
      const data = await _post("/recommend-events", {
        vendor,
        vendor_category: vendor.vendor_category || "",
        limit: 4,
      });
      const recs = data.recommendations || [];
      if (!recs.length) {
        container.innerHTML = `<p class="muted" style="font-size:.88rem;">No recommendations yet — add products and event preferences to get personalized matches.</p>`;
        return;
      }
      container.innerHTML = `
        <div style="display:flex;align-items:center;gap:6px;margin-bottom:10px">
          <span style="font-size:12px;font-weight:700;letter-spacing:.04em;color:#7c3aed;text-transform:uppercase">✦ Recommended For You</span>
          <span style="font-size:11px;color:#9ca3af;font-style:italic">${_esc(data.source)}</span>
        </div>
        ${recs.map(r => `
          <div style="display:flex;justify-content:space-between;align-items:center;padding:8px 0;border-bottom:1px solid #f3f4f6;">
            <div>
              <div style="font-weight:600;font-size:13px">${_esc(r.event_title || "Event")}</div>
              <div style="font-size:12px;color:#6b7280">${_esc(r.verdict)}</div>
            </div>
            <div style="background:#f5f3ff;color:#7c3aed;border-radius:99px;padding:3px 10px;font-size:12px;font-weight:700;white-space:nowrap">${r.score}%</div>
          </div>`).join("")}
        <a href="/discover" style="display:block;text-align:center;margin-top:10px;font-size:13px;color:#7c3aed;font-weight:600;">Browse all events →</a>`;
    } catch (_) {
      container.innerHTML = `<p class="muted" style="font-size:.88rem;">Could not load recommendations.</p>`;
    }
  }

  // ------------------------------------------------------------------
  // Public: Community Assistant (Feature 6)
  // ------------------------------------------------------------------

  /**
   * injectCommunityAssistant(containerSelector)
   * Renders a compact Q&A chat widget.
   */
  function injectCommunityAssistant(containerSelector) {
    const container = document.querySelector(containerSelector);
    if (!container) return;

    const widget = document.createElement("div");
    widget.className = "ai-community-widget";
    widget.style.cssText = "background:#f5f3ff;border:1.5px solid #ddd6fe;border-radius:12px;padding:16px;margin-top:16px;";
    widget.innerHTML = `
      <div style="display:flex;align-items:center;gap:8px;margin-bottom:12px">
        <span style="font-size:16px">✦</span>
        <strong style="font-size:14px;color:#7c3aed">Ask the AI Assistant</strong>
      </div>
      <div id="_ai_chat_history" style="max-height:220px;overflow-y:auto;margin-bottom:10px;font-size:13px;line-height:1.6"></div>
      <div style="display:flex;gap:6px">
        <input id="_ai_chat_input" type="text" placeholder="e.g. Best markets for jewelry vendors?" style="flex:1;padding:8px 12px;border:1.5px solid #ddd6fe;border-radius:8px;font-size:13px;background:#fff;outline:none;" />
        <button id="_ai_chat_send" style="padding:8px 14px;background:#7c3aed;color:#fff;border:none;border-radius:8px;font-size:13px;font-weight:600;cursor:pointer">Ask</button>
      </div>
      <div id="_ai_follow_ups" style="margin-top:8px;display:flex;flex-wrap:wrap;gap:6px"></div>`;
    container.appendChild(widget);

    const history = widget.querySelector("#_ai_chat_history");
    const input   = widget.querySelector("#_ai_chat_input");
    const sendBtn = widget.querySelector("#_ai_chat_send");
    const followUps = widget.querySelector("#_ai_follow_ups");

    function appendMsg(text, role) {
      const div = document.createElement("div");
      div.style.cssText = role === "user"
        ? "margin-bottom:8px;text-align:right"
        : "margin-bottom:8px;background:#fff;border-radius:8px;padding:8px 10px;border:1px solid #ede9fe";
      div.innerHTML = role === "user"
        ? `<span style="background:#7c3aed;color:#fff;border-radius:8px;padding:5px 10px;font-size:13px">${_esc(text)}</span>`
        : _esc(text);
      history.appendChild(div);
      history.scrollTop = history.scrollHeight;
    }

    function renderFollowUps(prompts) {
      followUps.innerHTML = prompts.map(p =>
        `<button type="button" style="background:#fff;border:1px solid #ddd6fe;color:#7c3aed;border-radius:99px;padding:3px 10px;font-size:12px;cursor:pointer" data-q="${_esc(p)}">${_esc(p)}</button>`
      ).join("");
      followUps.querySelectorAll("button").forEach(b => {
        b.addEventListener("click", () => { input.value = b.dataset.q; doAsk(); });
      });
    }

    async function doAsk() {
      const q = input.value.trim();
      if (!q) return;
      input.value = "";
      followUps.innerHTML = "";
      appendMsg(q, "user");
      sendBtn.disabled = true; sendBtn.textContent = "…";
      try {
        const data = await _post("/community/ask", { question: q });
        appendMsg(data.answer || "Sorry, I couldn't answer that right now.", "ai");
        if (data.follow_up_prompts?.length) renderFollowUps(data.follow_up_prompts);
      } catch (e) {
        appendMsg("Sorry, I'm unavailable right now. Try the Community groups for peer advice!", "ai");
      } finally {
        sendBtn.disabled = false; sendBtn.textContent = "Ask";
      }
    }

    sendBtn.addEventListener("click", doAsk);
    input.addEventListener("keydown", e => { if (e.key === "Enter") doAsk(); });

    // Seed follow-up prompt chips
    renderFollowUps(["Best markets for my category?", "How to price my products?", "How to apply to events?"]);
  }

  // ------------------------------------------------------------------
  // Public: Organizer Insights Panel (Feature 8)
  // ------------------------------------------------------------------

  /**
   * renderOrganizerInsights(containerSelector, events, applications, organizerName)
   */
  async function renderOrganizerInsights(containerSelector, events = [], applications = [], organizerName = "") {
    const container = document.querySelector(containerSelector);
    if (!container) return;
    container.innerHTML = `<div style="font-size:13px;color:#6b7280;padding:8px 0">✦ Analyzing your events…</div>`;
    try {
      const data = await _post("/organizer-insights", { events, applications, organizer_name: organizerName });
      const insights = data.insights || [];
      if (!insights.length) { container.innerHTML = ""; return; }
      container.innerHTML = `
        <div class="ai-insights-panel" style="margin-top:.5rem;">
          <div style="display:flex;align-items:center;gap:6px;margin-bottom:10px">
            <span style="font-size:12px;font-weight:700;letter-spacing:.04em;color:#7c3aed;text-transform:uppercase">✦ AI Demand Insights</span>
          </div>
          ${insights.map(i => `
            <div style="display:flex;gap:10px;align-items:flex-start;padding:8px 0;border-bottom:1px solid #f3f4f6;">
              <span style="font-size:1.1rem;line-height:1.4">${i.icon || "✦"}</span>
              <span style="font-size:13px;line-height:1.55;color:#374151">${_esc(i.text)}</span>
            </div>`).join("")}
        </div>`;
    } catch (_) {
      container.innerHTML = "";
    }
  }

  // ------------------------------------------------------------------
  // Helpers
  // ------------------------------------------------------------------

  function _esc(str) {
    return String(str || "")
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;");
  }

  // ------------------------------------------------------------------
  // Exports
  // ------------------------------------------------------------------

  return {
    injectBioButton,
    injectProductDescButton,
    injectSocialPostButton,
    injectMatchButton,
    injectCaptionButton,
    injectEventPredictor,
    injectProductTagger,
    renderInsightsPanel,
    renderRecommendedEvents,
    injectCommunityAssistant,
    renderOrganizerInsights,
    post: _post,
    checkEnabled: _checkEnabled,
  };
})();
