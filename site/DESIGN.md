# Vendor Atlas UI — Design & Color Scheme

The Vendor Atlas app is **built into this repo** and **served by the same MCP server** that runs `server.py`. There is no separate frontend app or build step.

- **Location:** `site/` (HTML pages + `assets/styles.css`, `assets/app.js`)
- **Served at:** `GET /`, `/discover`, `/dashboard`, `/find-my-next-market`, `/final-plan`, `/features`, `/pricing`, `/about`, `/signin`, `/signup`, etc.
- **Assets:** `GET /assets/styles.css`, `GET /assets/app.js`

## Official color scheme

Use these values so the app matches the original Vendor Atlas look. They are defined in `site/assets/styles.css` as CSS custom properties.

| Token   | Value              | Usage           |
|---------|--------------------|-----------------|
| `--bg`  | `#f4efe6`          | Page background (cream) |
| `--surface` | `rgba(255,255,255,0.78)` | Cards, panels |
| `--surface-strong` | `#fffdf8` | Stronger surfaces |
| `--surface-dark`   | `#132623` | Dark teal (footer, contrast) |
| `--text`   | `#132623` | Body text |
| `--muted`  | `#54645d` | Secondary text |
| `--brand`  | `#0f766e` | Primary teal (buttons, links) |
| `--brand-deep` | `#0b5b55` | Darker teal (hover, emphasis) |
| `--accent` | `#e89f47` | Amber accent (highlights) |
| `--danger` | `#b42318` | Errors, destructive |
| `--success` | `#027a48` | Success states |

Any “final” or alternate UI that should represent Vendor Atlas must use this palette and should be served from this `site/` via the MCP server so there is one canonical experience.
