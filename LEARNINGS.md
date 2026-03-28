# LEARNINGS.md — ops-dashboard
# Агент записывает сюда уроки после каждой ошибки или открытия

- nginx config at /srv/gateway/nginx.conf on HOST, not inside container
- docker exec gateway-nginx nginx -t before nginx -s reload
- message tool unavailable in cron context — use exec curl Bot API

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
