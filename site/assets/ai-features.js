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
    post: _post,          // escape hatch for custom AI calls
    checkEnabled: _checkEnabled,
  };
})();
