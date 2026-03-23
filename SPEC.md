# SPEC — Unified Operations Dashboard

## Project
Single-page web dashboard that combines: Kanban board, AO agent monitor, system metrics, and API usage tracking.

## Stack
- Frontend: vanilla HTML/CSS/JS (single file, dark theme, responsive)
- Backend: FastAPI + Python
- Data sources: GitHub API, AO CLI, system metrics (psutil), Anthropic API usage
- Deploy: Docker on Hetzner (same server as svc-dash)

## Modules

### M1: Backend API
- `GET /api/kanban` — fetch GitHub issues/PRs for configured repos, categorize by status (backlog/progress/review/done/blocked)
- `GET /api/agents` — run `ao status --json` and parse output (sessions, branches, PRs, activity)
- `GET /api/system` — local Mac metrics (CPU, RAM, temp via psutil) + Hetzner server metrics (SSH + parse top/df/docker ps)
- `GET /api/usage` — Anthropic API usage (scrape from console.anthropic.com or use billing API if available)
- `GET /api/health` — health check
- CORS enabled, auto-refresh friendly (no auth needed, local only)

### M2: Frontend — Kanban
- Columns: Backlog, In Progress, Review/PR, Done, Blocked
- Cards show: title, tags (feat/fix/infra), PR link, assigned agent, timestamp
- Auto-categorize from GitHub issue labels + PR status
- Repos configurable (start with ddfeyes/svc-dash)
- Real-time: poll every 30 seconds

### M3: Frontend — Agent Monitor
- Show all AO sessions: session name, branch, PR#, CI status, activity (running/exited), age
- Show OpenClaw agents: name, status (last seen), current task
- Visual: card grid or table, color-coded by status

### M4: Frontend — System Metrics
- Mac: CPU %, RAM %, disk %, temperature
- Hetzner: CPU %, RAM %, disk %, container count, container health
- Progress bars like the screenshot (blue bars, dark bg)
- API usage: current session %, weekly limits %, model breakdown
- Auto-refresh every 60 seconds

### M5: Integration & Deploy
- Docker compose (single service)
- Nginx reverse proxy on Hetzner gateway-nginx
- Domain: ops.111miniapp.com or localhost:8090
- CI: GitHub Actions (lint + build + push)

## Acceptance Criteria
- Dashboard loads in <2s
- All 4 panels visible on one page (grid layout)
- Dark theme matching svc-dash style (#0e1117 bg)
- Mobile-responsive (stack panels vertically)
- Auto-refresh without full page reload
- Works 24/7 without manual intervention
