# LEARNINGS.md — ops-dashboard
# Агент записывает сюда уроки после каждой ошибки или открытия

- nginx config at /srv/gateway/nginx.conf on HOST, not inside container
- docker exec gateway-nginx nginx -t before nginx -s reload
- message tool unavailable in cron context — use exec curl Bot API

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
- Frontend handles both old (array) and new (dict) formats for backward compat

## 2026-03-28 — Kanban Done count X/Y in header (Issue #160)
- Done column header shows 'DONE 10/143' when collapsed (10 visible of 143 total)
- Shows 'DONE 143' when expanded — clear UX improvement
- Previously showed just 'DONE 143' even when only 10 visible (misleading)

## 2026-03-28 — Kanban toolbar repo counts (Issue #159)
- Toolbar filter buttons now show card counts next to each repo name
- 'triangle (12)' 'ops-dashboard (5)' 'All repos (148)'
- Small but useful for quickly knowing which repos have most cards

## 2026-03-28 — Health endpoint: unhealthy containers (Issue #158)
- Health endpoint showed container count but not WHICH containers were unhealthy
- Fixed: added `checks.docker.unhealthy` list — name+status for any container not in 'running'/'up' state
- When unhealthy containers exist, overall health status becomes 'degraded'
- All 27 containers currently healthy — no unhealthy field shown

## 2026-03-28 — Network I/O rate (Issue #157)
- Cumulative bytes_sent/bytes_recv since boot — not actionable for monitoring
- Fixed: track previous poll values + monotonic time, compute sent_rate/recv_rate in bytes/sec
- Had Python `UnboundLocalError` bug: `global _network_rate` needed inside function
- Frontend: shows "NET ↑↓ XKB/s↑ YKB/s↓" format
- Verified: sent_rate=952 B/s, recv_rate=102 B/s (2nd poll)

## 2026-03-28 — Fix misleading 'mac' duplicate in /api/system (Issue #156)
- `/api/system` had `"mac": server` — literally echoing Hetzner metrics under a `mac` key
- Root cause: legacy code from when a real Mac was monitored; `mac_remote` is the real Mac field, `mac` was dead data
- Fix: removed `"mac": server` from system_metrics() return dict in main.py
- Also renamed `#system-mac` → `#system-server` in HTML/CSS to fix misleading panel ID
- Frontend falls back to `data.server || data.hetzner` so no JS changes needed

## 2026-03-28 — lain:patrol-1h cron anomaly
- Cron shows next_run=03:30 (24m in past) but last_run=null (never run)
- Appears to be a new cron that hasn't fired yet, or scheduler timing edge case
- 0 consecutive_errors — not failing, just not yet executed
- Dashboard otherwise fully operational
