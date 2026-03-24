/**
 * Vendor Atlas — Dashboard Layout JS
 * Handles sidebar collapse, active route detection, mobile drawer,
 * and role-based dynamic nav rendering.
 * Include on all dashboard pages after app.js.
 */
(function () {
  'use strict';

  // ── SVG icon library ────────────────────────────────────────────────────
  var ICONS = {
    dashboard: '<svg viewBox="0 0 24 24"><rect x="3" y="3" width="7" height="7" rx="1"/><rect x="14" y="3" width="7" height="7" rx="1"/><rect x="14" y="14" width="7" height="7" rx="1"/><rect x="3" y="14" width="7" height="7" rx="1"/></svg>',
    home:      '<svg viewBox="0 0 24 24"><path d="M3 9l9-7 9 7v11a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z"/><polyline points="9 22 9 12 15 12 15 22"/></svg>',
    feed:      '<svg viewBox="0 0 24 24"><polyline points="22 12 18 12 15 21 9 3 6 12 2 12"/></svg>',
    community: '<svg viewBox="0 0 24 24"><path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/></svg>',
    discover:  '<svg viewBox="0 0 24 24"><circle cx="12" cy="12" r="10"/><polygon points="16.24 7.76 14.12 14.12 7.76 16.24 9.88 9.88 16.24 7.76"/></svg>',
    shop:      '<svg viewBox="0 0 24 24"><path d="M6 2L3 6v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2V6l-3-4z"/><line x1="3" y1="6" x2="21" y2="6"/><path d="M16 10a4 4 0 0 1-8 0"/></svg>',
    profit:    '<svg viewBox="0 0 24 24"><line x1="18" y1="20" x2="18" y2="10"/><line x1="12" y1="20" x2="12" y2="4"/><line x1="6" y1="20" x2="6" y2="14"/></svg>',
    messages:  '<svg viewBox="0 0 24 24"><path d="M4 4h16c1.1 0 2 .9 2 2v12c0 1.1-.9 2-2 2H4c-1.1 0-2-.9-2-2V6c0-1.1.9-2 2-2z"/><polyline points="22,6 12,13 2,6"/></svg>',
    events:    '<svg viewBox="0 0 24 24"><rect x="3" y="4" width="18" height="18" rx="2"/><line x1="16" y1="2" x2="16" y2="6"/><line x1="8" y1="2" x2="8" y2="6"/><line x1="3" y1="10" x2="21" y2="10"/><polyline points="9 16 11 18 15 14"/></svg>',
    analytics: '<svg viewBox="0 0 24 24"><line x1="18" y1="20" x2="18" y2="10"/><line x1="12" y1="20" x2="12" y2="4"/><line x1="6" y1="20" x2="6" y2="14"/></svg>',
    settings:  '<svg viewBox="0 0 24 24"><circle cx="12" cy="12" r="3"/><path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1-2.83 2.83l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-4 0v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83-2.83l.06-.06A1.65 1.65 0 0 0 4.68 15a1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1 0-4h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 2.83-2.83l.06.06A1.65 1.65 0 0 0 9 4.68a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 4 0v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 2.83l-.06.06A1.65 1.65 0 0 0 19.4 9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 0 4h-.09a1.65 1.65 0 0 0-1.51 1z"/></svg>',
    saved:     '<svg viewBox="0 0 24 24"><path d="M19 21l-7-5-7 5V5a2 2 0 0 1 2-2h10a2 2 0 0 1 2 2z"/></svg>',
    more:      '<svg viewBox="0 0 24 24"><circle cx="12" cy="12" r="1"/><circle cx="19" cy="12" r="1"/><circle cx="5" cy="12" r="1"/></svg>',
  };

  // ── Role nav configurations ──────────────────────────────────────────────
  var NAV_CONFIGS = {
    vendor: {
      sections: [
        { label: 'Main', items: [
          { icon: 'dashboard', text: 'Dashboard',  href: '/dashboard' },
          { icon: 'feed',      text: 'Feed',        href: '/feed' },
          { icon: 'community', text: 'Community',   href: '/community' },
          { icon: 'discover',  text: 'Discover',    href: '/discover' },
        ]},
        { label: 'Vendor', items: [
          { icon: 'shop',      text: 'My Shop',     href: '/my-shop' },
          { icon: 'profit',    text: 'Profit',      href: '/profit' },
          { icon: 'messages',  text: 'Messages',    href: '/messages' },
        ]},
        { label: 'Account', items: [
          { icon: 'settings',  text: 'Settings',    href: '/settings' },
        ]},
      ],
      bottomNav: [
        { icon: 'dashboard', text: 'Home',      href: '/dashboard' },
        { icon: 'feed',      text: 'Feed',      href: '/feed' },
        { icon: 'discover',  text: 'Discover',  href: '/discover' },
        { icon: 'community', text: 'Community', href: '/community' },
      ],
    },
    market: {
      sections: [
        { label: 'Main', items: [
          { icon: 'dashboard', text: 'Dashboard',   href: '/market-dashboard' },
          { icon: 'feed',      text: 'Feed',         href: '/feed' },
          { icon: 'community', text: 'Community',    href: '/community' },
          { icon: 'discover',  text: 'Discover',     href: '/discover' },
        ]},
        { label: 'Organizer', items: [
          { icon: 'events',    text: 'My Events',    href: '/market-applications' },
          { icon: 'analytics', text: 'Analytics',    href: '/market-analytics' },
          { icon: 'messages',  text: 'Messages',     href: '/messages' },
        ]},
        { label: 'Account', items: [
          { icon: 'settings',  text: 'Settings',     href: '/settings' },
        ]},
      ],
      bottomNav: [
        { icon: 'dashboard', text: 'Home',      href: '/market-dashboard' },
        { icon: 'feed',      text: 'Feed',      href: '/feed' },
        { icon: 'discover',  text: 'Discover',  href: '/discover' },
        { icon: 'community', text: 'Community', href: '/community' },
      ],
    },
    shopper: {
      sections: [
        { label: 'Browse', items: [
          { icon: 'home',      text: 'Home',       href: '/shopper-dashboard' },
          { icon: 'feed',      text: 'Feed',        href: '/feed' },
          { icon: 'discover',  text: 'Discover',    href: '/discover' },
          { icon: 'community', text: 'Community',   href: '/community' },
          { icon: 'saved',     text: 'Saved',       href: '/shopper-dashboard' },
          { icon: 'messages',  text: 'Messages',    href: '/messages' },
        ]},
        { label: 'Account', items: [
          { icon: 'settings',  text: 'Settings',    href: '/settings' },
        ]},
      ],
      bottomNav: [
        { icon: 'home',      text: 'Home',      href: '/shopper-dashboard' },
        { icon: 'feed',      text: 'Feed',      href: '/feed' },
        { icon: 'discover',  text: 'Discover',  href: '/discover' },
        { icon: 'community', text: 'Community', href: '/community' },
      ],
    },
  };

  // ── Build HTML ────────────────────────────────────────────────────────────
  function buildNavSectionsHtml(sections) {
    return sections.map(function (section) {
      return '<div class="dash-nav-section">' +
        '<div class="dash-nav-label">' + section.label + '</div>' +
        section.items.map(function (item) {
          return '<a class="dash-nav-item" href="' + item.href + '">' +
            '<span class="dash-nav-icon">' + ICONS[item.icon] + '</span>' +
            '<span class="dash-nav-text">' + item.text + '</span>' +
            '</a>';
        }).join('') +
        '</div>';
    }).join('');
  }

  function buildBottomNavHtml(items) {
    return items.map(function (item) {
      return '<li class="bottom-nav-item">' +
        '<a class="bottom-nav-link" href="' + item.href + '">' +
        ICONS[item.icon] + item.text +
        '</a></li>';
    }).join('') +
    '<li class="bottom-nav-item">' +
    '<button class="bottom-nav-more-btn" id="bottom-nav-more">' +
    ICONS.more + 'More' +
    '</button></li>';
  }

  function applyRoleNav(role) {
    var config = NAV_CONFIGS[role] || NAV_CONFIGS.vendor;
    var sectionsHtml = buildNavSectionsHtml(config.sections);

    // Desktop sidebar nav
    var sidebarNav = document.querySelector('#dash-sidebar .dash-nav');
    if (sidebarNav) sidebarNav.innerHTML = sectionsHtml;

    // Mobile drawer nav
    var drawerNav = document.querySelector('.mobile-drawer-nav');
    if (drawerNav) drawerNav.innerHTML = sectionsHtml;

    // Bottom nav items
    var bottomNavItems = document.querySelector('.bottom-nav .bottom-nav-items');
    if (bottomNavItems) bottomNavItems.innerHTML = buildBottomNavHtml(config.bottomNav);

    // Reattach "More" button listener (rebuilt above)
    var newMoreBtn = document.getElementById('bottom-nav-more');
    if (newMoreBtn) newMoreBtn.addEventListener('click', openDrawer);

    // Re-highlight active after nav rebuild
    highlightActive();
  }

  async function loadRoleNav() {
    try {
      var res = await fetch('/api/auth/me', { credentials: 'include' });
      if (!res.ok) return;
      var data = await res.json();
      var user = data.user || data;
      var role = (user.role || 'vendor').toLowerCase();
      // Normalise role aliases
      if (role === 'organizer') role = 'market';
      if (!NAV_CONFIGS[role]) role = 'vendor';
      applyRoleNav(role);
    } catch (_) {
      // Silently fail — keep the static nav already in HTML
    }
  }

  // ── Sidebar collapse ──────────────────────────────────────────────────────
  var sidebar = document.getElementById('dash-sidebar');
  var collapseBtn = document.getElementById('dash-collapse-btn');
  var COLLAPSED_KEY = 'va_sidebar_collapsed';

  function initSidebar() {
    if (!sidebar) return;
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

  // ── Active nav highlighting ───────────────────────────────────────────────
  function highlightActive() {
    var currentPath = window.location.pathname;
    document.querySelectorAll('.dash-nav-item, .bottom-nav-link, .mobile-drawer-nav .dash-nav-item').forEach(function (link) {
      var href = link.getAttribute('href');
      if (!href) return;
      if (href === currentPath || (href !== '/' && currentPath.startsWith(href))) {
        link.classList.add('active');
      } else {
        link.classList.remove('active');
      }
    });

    // Update topbar page title
    var titleEl = document.getElementById('dash-page-title');
    if (titleEl) {
      var activeLink = document.querySelector('.dash-nav-item.active');
      if (activeLink) {
        var textEl = activeLink.querySelector('.dash-nav-text');
        if (textEl) titleEl.textContent = textEl.textContent.trim();
      }
    }
  }

  // ── Mobile drawer ─────────────────────────────────────────────────────────
  var mobileMenuBtn = document.getElementById('dash-mobile-menu-btn');
  var drawer = document.getElementById('mobile-slide-drawer');
  var drawerOverlay = document.getElementById('mobile-drawer-overlay');
  var drawerClose = document.getElementById('mobile-drawer-close');

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
    if (drawer) {
      drawer.querySelectorAll('a').forEach(function (a) {
        a.addEventListener('click', function () {
          setTimeout(closeDrawer, 80);
        });
      });
    }
  }

  // ── Bottom nav "More" button (initial attach) ─────────────────────────────
  var moreBtn = document.getElementById('bottom-nav-more');
  if (moreBtn) moreBtn.addEventListener('click', openDrawer);

  // ── Touch swipe to close drawer ───────────────────────────────────────────
  var touchStartX = 0;
  if (drawer) {
    drawer.addEventListener('touchstart', function (e) {
      touchStartX = e.touches[0].clientX;
    }, { passive: true });
    drawer.addEventListener('touchend', function (e) {
      var dx = e.changedTouches[0].clientX - touchStartX;
      if (dx < -60) closeDrawer();
    }, { passive: true });
  }

  // ── Keyboard: Escape closes drawer ───────────────────────────────────────
  document.addEventListener('keydown', function (e) {
    if (e.key === 'Escape') closeDrawer();
  });

  // ── Init ─────────────────────────────────────────────────────────────────
  function init() {
    initSidebar();
    highlightActive();
    initMobileDrawer();
    loadRoleNav(); // async — replaces nav once role is known
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();
