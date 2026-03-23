/**
 * Vendor Atlas — Dashboard Layout JS
 * Handles sidebar collapse, active route detection, and mobile drawer.
 * Include on all dashboard pages after app.js.
 */
(function () {
  'use strict';

  // ── Sidebar collapse ────────────────────────────────────────────────────
  const sidebar = document.getElementById('dash-sidebar');
  const collapseBtn = document.getElementById('dash-collapse-btn');
  const COLLAPSED_KEY = 'va_sidebar_collapsed';

  function initSidebar() {
    if (!sidebar) return;

    // Restore collapsed state from localStorage
    if (localStorage.getItem(COLLAPSED_KEY) === '1') {
      sidebar.classList.add('collapsed');
    }

    if (collapseBtn) {
      collapseBtn.addEventListener('click', function () {
        sidebar.classList.toggle('collapsed');
        localStorage.setItem(COLLAPSED_KEY, sidebar.classList.contains('collapsed') ? '1' : '0');
      });
    }
  }

  // ── Active nav highlighting ─────────────────────────────────────────────
  function highlightActive() {
    const currentPath = window.location.pathname;

    // Sidebar nav items
    document.querySelectorAll('.dash-nav-item, .bottom-nav-link, .mobile-drawer-nav .dash-nav-item').forEach(function (link) {
      const href = link.getAttribute('href');
      if (!href) return;
      // Exact match or starts-with for sub-paths
      if (href === currentPath || (href !== '/' && currentPath.startsWith(href))) {
        link.classList.add('active');
      } else {
        link.classList.remove('active');
      }
    });

    // Update topbar page title
    const titleEl = document.getElementById('dash-page-title');
    if (titleEl) {
      const activeLink = document.querySelector('.dash-nav-item.active');
      if (activeLink) {
        const textEl = activeLink.querySelector('.dash-nav-text');
        if (textEl) titleEl.textContent = textEl.textContent.trim();
      }
    }
  }

  // ── Mobile drawer ───────────────────────────────────────────────────────
  const mobileMenuBtn = document.getElementById('dash-mobile-menu-btn');
  const drawer = document.getElementById('mobile-slide-drawer');
  const drawerOverlay = document.getElementById('mobile-drawer-overlay');
  const drawerClose = document.getElementById('mobile-drawer-close');

  function openDrawer() {
    if (!drawer || !drawerOverlay) return;
    drawer.classList.add('open');
    drawerOverlay.classList.add('open');
    document.body.style.overflow = 'hidden';
  }

  function closeDrawer() {
    if (!drawer || !drawerOverlay) return;
    drawer.classList.remove('open');
    drawerOverlay.classList.remove('open');
    document.body.style.overflow = '';
  }

  function initMobileDrawer() {
    if (mobileMenuBtn) mobileMenuBtn.addEventListener('click', openDrawer);
    if (drawerOverlay) drawerOverlay.addEventListener('click', closeDrawer);
    if (drawerClose) drawerClose.addEventListener('click', closeDrawer);

    // Close drawer when a link inside it is tapped
    if (drawer) {
      drawer.querySelectorAll('a').forEach(function (a) {
        a.addEventListener('click', function () {
          // Small delay so the navigation feels intentional
          setTimeout(closeDrawer, 80);
        });
      });
    }
  }

  // ── Bottom nav "More" button ─────────────────────────────────────────────
  const moreBtn = document.getElementById('bottom-nav-more');
  if (moreBtn) {
    moreBtn.addEventListener('click', openDrawer);
  }

  // ── Touch swipe to close drawer ─────────────────────────────────────────
  let touchStartX = 0;
  if (drawer) {
    drawer.addEventListener('touchstart', function (e) {
      touchStartX = e.touches[0].clientX;
    }, { passive: true });

    drawer.addEventListener('touchend', function (e) {
      const dx = e.changedTouches[0].clientX - touchStartX;
      if (dx < -60) closeDrawer(); // swipe left to close
    }, { passive: true });
  }

  // ── Keyboard: Escape closes drawer ──────────────────────────────────────
  document.addEventListener('keydown', function (e) {
    if (e.key === 'Escape') closeDrawer();
  });

  // ── Init ────────────────────────────────────────────────────────────────
  function init() {
    initSidebar();
    highlightActive();
    initMobileDrawer();
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();
