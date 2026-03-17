# Vendor Atlas QA Checklist

Use this quick smoke test before shipping UI or backend changes that affect the dashboard.

## Core Flows

- Load `GET /` and confirm the homepage renders without console-breaking errors.
- Confirm `GET /config.json` returns `api_base_url` and the page still works with the default same-origin fallback.
- Run a market search and confirm results, empty states, and error states render cleanly.
- Open `View Details` from a result card and confirm the modal content, focus handling, and close actions work.
- Save a market, then confirm it appears in the saved list and can still be compared or opened.
- Run `Help me choose` and confirm the compare modal shows a ranked recommendation list.
- Complete the vendor profile quiz and confirm the profile saves without breaking later ranking.

## Responsive + Accessibility

- Test the mobile menu on a narrow viewport and confirm it opens, closes, and returns focus correctly.
- Confirm `Escape` closes the quiz, details, compare, and mobile-menu overlays.
- Tab through primary actions and confirm visible focus is present on major buttons and dialog controls.

## Backend + Data

- Check `GET /health` and confirm the tool count is non-zero.
- Check `GET /markets/search?city=Austin` and confirm `ok`, `results_count`, and `events` are present.
- Confirm seeded demo data appears on a fresh database path.

## Known Follow-Up

- The dashboard already calls `GET /markets/search`, but some frontend code still tolerates the older compatibility payload. That cleanup remains a safe follow-up task.
- `site/index.html` still contains a few visible text-encoding artifacts that should be normalized in a dedicated polish pass.
