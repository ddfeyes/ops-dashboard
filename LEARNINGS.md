# LEARNINGS.md — ops-dashboard
# Агент записывает сюда уроки после каждой ошибки или открытия

- nginx config at /srv/gateway/nginx.conf on HOST, not inside container
- docker exec gateway-nginx nginx -t before nginx -s reload
- message tool unavailable in cron context — use exec curl Bot API

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

## 2026-03-28 — Network I/O rate (Issue #157)
