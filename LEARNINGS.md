# LEARNINGS.md — ops-dashboard
# Агент записывает сюда уроки после каждой ошибки или открытия

- nginx config at /srv/gateway/nginx.conf on HOST, not inside container
- docker exec gateway-nginx nginx -t before nginx -s reload
- message tool unavailable in cron context — use exec curl Bot API

## 2026-03-28 — Header shows version + deploy date (Issue #167)
- Backend: added `_get_deployed_at()` using Docker SDK image.attrs['Created']
- Frontend: calls `/api/health` on load, shows "v0.1.0 · deployed 28 Mar" in header
- `deployed_at` = image build time, updates on each new deploy

## 2026-03-28 — Kanban cards link to PR when available (Issue #166)
- Cards with `pr_url` now link to the PR (not the issue) — merged PRs open directly
- Card title gets subtle underline on hover to hint the card is clickable

## 2026-03-28 — Container restart count badge (Issue #165)
- Backend: added `RestartCount` to container data from Docker SDK c.attrs.get("RestartCount", 0)
- Frontend: shows ↺N badge only when restart_count > 0; hidden when 0 (clean)
- bananas31-frontend currently shows ↺53 — high restart count, worth investigating
- Tooltip on hover: "Restart count"

## 2026-03-28 — Done cards older than 7 days get visual marker (Issue #164)
- Done cards with timestamp >7 days old: opacity:0.55 + strikethrough on title
- Makes the done column scannable — stale items visually distinct at a glance
- Pure CSS class + JS timestamp check in cardHtml()

## 2026-03-28 — Done column age footer (Issue #163)
- Shows "oldest 13d" or "oldest 13d · 47 >7d" (count of cards >7 days old) below done column
- Helps spot stale done items at a glance
- Computed in JS from card timestamps — no backend change needed

## 2026-03-28 — Network rate shows — on first poll (Issue #162)
- Backend returned 0 when _prev_net was None (no previous data after restart)
- Fix: return null; frontend shows — instead of misleading 0B/s
- API now: sent_rate=null, recv_rate=null on first poll; real values after second poll

## 2026-03-28 — /api/kanban returns {cards,total} (Issue #161)
- Changed return type from `list[dict]` to `dict{cards,total}`
- Badge now shows "5/148 issues" when filtered, "148 issues" when showing all

## 2026-03-28 — Kanban Done count X/Y in header (Issue #160)
- Collapsed done column now shows "10/143" instead of just "10"
- Only applies when done column is collapsed (more cards than DONE_PREVIEW=10)

## 2026-03-28 — Kanban toolbar repo counts (Issue #159)
- Filter buttons show per-repo card counts: "triangle (12)" "ops-dashboard (5)" "All repos (148)"

## 2026-03-28 — Health endpoint: unhealthy containers (Issue #158)
- Added `unhealthy` field to container objects from Docker health status
- `docker ps --format '{{.Names}} {{.Status}}'` — parse health from Status field
- Frontend: no change (health endpoint was for backend/API use)

## 2026-03-28 — Cron panel summary row (Issue #174)
- Added summary row at top of crons panel: "N crons · X errors · next HH:MM"
- Shows total count, error count (red when >0), and next fire time
- Monospace font, subtle separator line from the rest of the list

## 2026-03-28 — Kanban toolbar shows card count with total when filtered (Issue #176)
- When viewing all repos: toolbar shows "148 cards" after the sort dropdown
- When a repo filter is active: toolbar shows "12 · 148 total" (filtered count + total)
- Helps users understand scope when viewing a filtered subset of the board

## 2026-03-28 — Kanban sort dropdown focus ring (Issue #175)
- Sort dropdown (#sort-select) had outline:none inline — no keyboard focus indicator
- Removed outline:none from inline style; added #sort-select:focus CSS with 2px accent outline
- Fixes keyboard accessibility for the sort control

## 2026-03-28 — Kanban sort control (Issue #173)
- Added sort dropdown to kanban toolbar: "newest" (default) or "oldest" — sorts by card created_at timestamp
- Purely frontend sort — no backend changes needed, instant response
- Sort persists during session (client-side only)

## 2026-03-28 — High-restart container row highlight (Issue #172)
- Containers with >5 restarts now get a red left border + tinted red background
- Makes the bananas31-frontend (↺53) row immediately visible in the container list
- Threshold kept at >5 (same as restart warning badge threshold)

## 2026-03-28 — Kanban keyboard shortcuts (Issue #171)
- Press "/" anywhere on the page to focus the kanban search bar
- Press "Escape" while in the search bar to clear the search and unfocus
- Self-contained: only fires when not already in an input/textarea

## 2026-03-28 — Container image tooltip (Issue #170)
- Added image name as hover tooltip on every container row
- Tooltip shows full image tag (e.g., `image: triangle-scanner-scanner:latest`)
- Helps ops identify which image a named container is running without guessing

## 2026-03-28 — Container restart warning badge (Issue #169)
- Added ⚠N warning badge to containers panel label when any container has >5 restarts
- Currently catches bananas31-frontend (↺53 restarts) — service is unstable
- Tooltip shows container names with high restart counts

## 2026-03-28 — Container search/filter bar (Issue #168)
- Added search input to containers panel body (🔍 filter containers… placeholder)
- Filters container list by name in real-time as user types
- Shows "X of 27" count when filtered; "no match" empty state if none match
- Uses separate #container-list-root innerHTML target to preserve search bar on re-render
- Container search state stored in `containerSearch` global var; lastServerData cached for re-filter

## 2026-03-28 — Network I/O rate (Issue #157)
