/**
 * EventMap — Leaflet.js interactive map for Vendor Atlas
 *
 * Provides two modes:
 *   EventMap.initDiscover(containerId)  — shopper/vendor event discovery map
 *   EventMap.initPlanner(containerId, onLocationSet)  — organizer location picker
 *
 * Requires: Leaflet CSS+JS and Leaflet.markercluster CSS+JS loaded before this file.
 */
(function (global) {
  "use strict";

  // ─── Icon lookup ────────────────────────────────────────────────────────────

  var TYPE_ICON = {
    "craft fair":     "🛍",
    "art market":     "🎨",
    "makers market":  "🧶",
    "vintage fair":   "👗",
    "oddities market":"💀",
    "pop-up market":  "🎪",
    "pop-up":         "🎪",
    "festival":       "🎪",
    "food market":    "🍜",
    "flea market":    "🛒",
    craft:            "🛍",
    art:              "🎨",
    handmade:         "🧶",
    vintage:          "👗",
    oddities:         "💀",
    gift:             "🎁",
    food:             "🍜",
  };

  function getIcon(event) {
    var t = (event.event_type || event.vendor_category || "").toLowerCase();
    return TYPE_ICON[t] || "📍";
  }

  // ─── Marker factory ─────────────────────────────────────────────────────────

  function makeMarker(event) {
    var icon = getIcon(event);
    var divIcon = L.divIcon({
      html: '<div class="va-map-pin" data-etype="' + escAttr(event.event_type || "market") + '">' + icon + "</div>",
      className: "va-map-pin-wrapper",
      iconSize: [38, 38],
      iconAnchor: [19, 38],
      popupAnchor: [0, -40],
    });
    var marker = L.marker([event.latitude, event.longitude], { icon: divIcon });
    marker.bindPopup(buildPopupHTML(event), { maxWidth: 300, className: "va-map-popup-wrap" });
    return marker;
  }

  function buildPopupHTML(event) {
    var date = "Date TBD";
    if (event.date) {
      try {
        date = new Date(event.date + "T12:00:00").toLocaleDateString("en-US", {
          weekday: "short", month: "short", day: "numeric", year: "numeric",
        });
      } catch (_) {}
    }
    var loc = [event.location_name, event.city && event.state ? event.city + ", " + event.state : (event.city || event.state || "")]
      .filter(Boolean).join(" · ");

    return [
      '<div class="va-popup">',
      event.banner_image
        ? '<img src="' + escAttr(event.banner_image) + '" alt="" class="va-popup-img">'
        : "",
      '<div class="va-popup-body">',
      '<p class="va-popup-type">' + esc(event.event_type || event.vendor_category || "Market") + "</p>",
      '<h4 class="va-popup-title">' + esc(event.name || "Untitled Event") + "</h4>",
      '<div class="va-popup-meta">',
      '<span>📅 ' + esc(date) + "</span>",
      loc ? '<span>📍 ' + esc(loc) + "</span>" : "",
      event.vendor_count ? '<span>🛍 ' + event.vendor_count + " vendors</span>" : "",
      "</div>",
      '<div class="va-popup-actions">',
      '<a href="/event-details/' + esc(String(event.id)) + '" class="btn btn-primary btn-sm">View Event</a>',
      '<button type="button" class="btn btn-secondary btn-sm" onclick="EventMap.saveEvent(\'' + esc(String(event.id)) + '\', this)">Save Event</button>',
      '<button type="button" class="btn btn-secondary btn-sm" onclick="EventMap.predictEvent(' + JSON.stringify(event).replace(/</g,'\\u003c').replace(/>/g,'\\u003e') + ', this)">Predict</button>',
      "</div>",
      "</div>",
      "</div>",
    ].join("");
  }

  function esc(str) {
    return String(str || "").replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
  }
  function escAttr(str) {
    return String(str || "").replace(/"/g, "&quot;").replace(/'/g, "&#39;");
  }

  // ─── Tile layer ─────────────────────────────────────────────────────────────

  function addTiles(map) {
    L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
      attribution: '© <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>',
      maxZoom: 19,
    }).addTo(map);
  }

  // ─── Data fetch ─────────────────────────────────────────────────────────────

  async function fetchMapEvents() {
    try {
      var resp = await fetch("/api/events/map");
      if (!resp.ok) return [];
      var data = await resp.json();
      return Array.isArray(data.events) ? data.events : [];
    } catch (_) {
      return [];
    }
  }

  // ─── Module state ───────────────────────────────────────────────────────────

  var _discoverMap = null;
  var _discoverCluster = null;
  var _plannerMap = null;
  var _plannerPin = null;

  // ─── Discover map ───────────────────────────────────────────────────────────

  async function initDiscover(containerId) {
    var el = document.getElementById(containerId);
    if (!el) return;

    if (_discoverMap) {
      _discoverMap.remove();
      _discoverMap = null;
      _discoverCluster = null;
    }

    var events = await fetchMapEvents();

    _discoverMap = L.map(containerId, { zoomControl: true });
    addTiles(_discoverMap);

    _discoverCluster = L.markerClusterGroup({
      showCoverageOnHover: false,
      maxClusterRadius: 55,
      iconCreateFunction: function (cluster) {
        return L.divIcon({
          html: '<div class="va-cluster">' + cluster.getChildCount() + "</div>",
          className: "va-cluster-wrapper",
          iconSize: [40, 40],
        });
      },
    });

    events.forEach(function (ev) {
      if (ev.latitude != null && ev.longitude != null) {
        _discoverCluster.addLayer(makeMarker(ev));
      }
    });
    _discoverMap.addLayer(_discoverCluster);

    // Try to center on user; fall back to event bounds or USA center
    if (navigator.geolocation) {
      navigator.geolocation.getCurrentPosition(
        function (pos) {
          _discoverMap.setView([pos.coords.latitude, pos.coords.longitude], 10);
        },
        function () { fitToBounds(events); },
        { timeout: 5000 }
      );
    } else {
      fitToBounds(events);
    }

    // Resize fix for hidden → visible transition
    setTimeout(function () {
      if (_discoverMap) _discoverMap.invalidateSize();
    }, 200);
  }

  function fitToBounds(events) {
    if (!_discoverMap) return;
    var coords = events.filter(function (e) { return e.latitude != null; })
      .map(function (e) { return [e.latitude, e.longitude]; });
    if (coords.length) {
      _discoverMap.fitBounds(L.latLngBounds(coords), { padding: [40, 40] });
    } else {
      _discoverMap.setView([39.5, -98.35], 4); // USA center
    }
  }

  /**
   * Replace markers with a filtered subset (called when discover filters change).
   * Pass an array of event objects that include latitude/longitude.
   */
  function updateDiscoverMarkers(filteredEvents) {
    if (!_discoverMap || !_discoverCluster) return;
    _discoverCluster.clearLayers();
    (filteredEvents || []).forEach(function (ev) {
      if (ev.latitude != null && ev.longitude != null) {
        _discoverCluster.addLayer(makeMarker(ev));
      }
    });
  }

  // ─── Planner map ────────────────────────────────────────────────────────────

  async function initPlanner(containerId, onLocationSet) {
    var el = document.getElementById(containerId);
    if (!el) return;

    if (_plannerMap) {
      _plannerMap.remove();
      _plannerMap = null;
      _plannerPin = null;
    }

    var events = await fetchMapEvents();

    _plannerMap = L.map(containerId, { zoomControl: true });
    addTiles(_plannerMap);

    // Show existing events as non-interactive reference pins
    events.forEach(function (ev) {
      if (ev.latitude != null && ev.longitude != null) {
        makeMarker(ev).addTo(_plannerMap);
      }
    });

    fitToPlannerBounds(events);

    // Click-to-place new event location
    _plannerMap.on("click", function (e) {
      placePlannerPin(e.latlng.lat, e.latlng.lng, onLocationSet);
    });

    setTimeout(function () {
      if (_plannerMap) _plannerMap.invalidateSize();
    }, 200);
  }

  function fitToPlannerBounds(events) {
    if (!_plannerMap) return;
    var coords = events.filter(function (e) { return e.latitude != null; })
      .map(function (e) { return [e.latitude, e.longitude]; });
    if (coords.length) {
      _plannerMap.fitBounds(L.latLngBounds(coords), { padding: [60, 60] });
    } else {
      _plannerMap.setView([39.5, -98.35], 4);
    }
  }

  function placePlannerPin(lat, lng, onLocationSet) {
    if (!_plannerMap) return;
    if (_plannerPin) _plannerMap.removeLayer(_plannerPin);

    _plannerPin = L.marker([lat, lng], {
      draggable: true,
      icon: L.divIcon({
        html: '<div class="va-map-pin va-map-pin-new">📌</div>',
        className: "va-map-pin-wrapper",
        iconSize: [38, 38],
        iconAnchor: [19, 38],
      }),
    })
      .addTo(_plannerMap)
      .bindPopup("New event location<br><small>Drag to adjust</small>")
      .openPopup();

    _plannerPin.on("dragend", function () {
      var pos = _plannerPin.getLatLng();
      if (onLocationSet) onLocationSet(pos.lat, pos.lng);
    });

    if (onLocationSet) onLocationSet(lat, lng);
  }

  /** Programmatically set the planner pin (e.g. when city field changes). */
  function setPlannerLocation(lat, lng, onLocationSet) {
    if (!_plannerMap) return;
    _plannerMap.setView([lat, lng], 13);
    placePlannerPin(lat, lng, onLocationSet);
  }

  // ─── Save event ─────────────────────────────────────────────────────────────

  async function saveEvent(eventId, btn) {
    try {
      var resp = await fetch("/api/saved-markets", {
        method: "POST",
        credentials: "include",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ event_id: eventId }),
      });
      if (resp.ok) {
        if (btn) { btn.textContent = "Saved ✓"; btn.disabled = true; }
      } else {
        if (btn) btn.textContent = "Sign in to save";
      }
    } catch (_) {}
  }

  // ─── Event prediction modal ─────────────────────────────────────────────

  async function predictEvent(event, btn) {
    if (btn) { btn.textContent = "Loading…"; btn.disabled = true; }

    var prediction = null;
    try {
      var resp = await fetch("/api/ai/event-prediction", {
        method: "POST",
        credentials: "include",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ event: event }),
      });
      if (resp.ok) prediction = await resp.json();
    } catch (_) {}

    if (btn) { btn.textContent = "Predict"; btn.disabled = false; }
    if (!prediction) return;

    // Build and show modal
    var colorMap = { green: "#22c55e", amber: "#f59e0b", teal: "#14b8a6" };
    var badgeColor = colorMap[prediction.risk_color] || "#6b7280";
    var tips = Array.isArray(prediction.tips) && prediction.tips.length
      ? "<ul style='margin:.5rem 0 0;padding-left:1.25rem;'>" +
          prediction.tips.map(function (t) { return "<li style='margin:.25rem 0;font-size:.85rem;'>" + esc(t) + "</li>"; }).join("") +
        "</ul>"
      : "";

    var html = [
      '<div id="va-predict-overlay" style="position:fixed;inset:0;background:rgba(0,0,0,.55);z-index:9999;display:flex;align-items:center;justify-content:center;">',
      '<div style="background:#fff;border-radius:12px;padding:1.5rem;max-width:380px;width:92%;box-shadow:0 8px 32px rgba(0,0,0,.25);position:relative;">',
      '<button onclick="document.getElementById(\'va-predict-overlay\').remove()" style="position:absolute;top:.75rem;right:.75rem;background:none;border:none;font-size:1.25rem;cursor:pointer;line-height:1;">×</button>',
      '<p style="margin:0 0 .25rem;font-size:.8rem;color:#6b7280;text-transform:uppercase;letter-spacing:.05em;">Event Prediction</p>',
      '<h4 style="margin:0 0 .75rem;font-size:1rem;">' + esc(event.name || "Event") + '</h4>',
      '<div style="display:inline-block;background:' + badgeColor + ';color:#fff;border-radius:999px;padding:.2rem .75rem;font-size:.8rem;font-weight:600;margin-bottom:.75rem;">' + esc(prediction.risk_level || "") + '</div>',
      '<div style="display:grid;grid-template-columns:1fr 1fr;gap:.5rem;margin-bottom:.75rem;">',
      '<div style="background:#f9fafb;border-radius:8px;padding:.6rem;text-align:center;"><div style="font-size:.72rem;color:#6b7280;">Est. Revenue</div><div style="font-weight:700;font-size:.95rem;">$' + (prediction.revenue_low || 0).toLocaleString() + '–$' + (prediction.revenue_high || 0).toLocaleString() + '</div></div>',
      '<div style="background:#f9fafb;border-radius:8px;padding:.6rem;text-align:center;"><div style="font-size:.72rem;color:#6b7280;">Est. Traffic</div><div style="font-weight:700;font-size:.95rem;">' + esc(prediction.traffic_estimate || "—") + '</div></div>',
      '</div>',
      prediction.summary ? '<p style="font-size:.85rem;color:#374151;margin:0 0 .5rem;">' + esc(prediction.summary) + '</p>' : '',
      prediction.competition_note ? '<p style="font-size:.8rem;color:#6b7280;margin:0 0 .5rem;">' + esc(prediction.competition_note) + '</p>' : '',
      tips,
      '<p style="font-size:.7rem;color:#9ca3af;margin:.75rem 0 0;text-align:right;">' + esc(prediction.confidence || "") + '</p>',
      '</div></div>',
    ].join("");

    // Remove any existing overlay first
    var existing = document.getElementById("va-predict-overlay");
    if (existing) existing.remove();

    var wrapper = document.createElement("div");
    wrapper.innerHTML = html;
    document.body.appendChild(wrapper.firstChild);
  }

  // ─── Cleanup ────────────────────────────────────────────────────────────────

  function destroyAll() {
    if (_discoverMap) { _discoverMap.remove(); _discoverMap = null; _discoverCluster = null; }
    if (_plannerMap)  { _plannerMap.remove();  _plannerMap = null;  _plannerPin = null; }
  }

  // ─── Public API ─────────────────────────────────────────────────────────────

  global.EventMap = {
    initDiscover:           initDiscover,
    updateDiscoverMarkers:  updateDiscoverMarkers,
    initPlanner:            initPlanner,
    setPlannerLocation:     setPlannerLocation,
    saveEvent:              saveEvent,
    predictEvent:           predictEvent,
    destroyAll:             destroyAll,
  };

})(window);
