# MEMORY.md — L2-011-opsdash

## Project State
- All 6 modules (M1-M6) completed and deployed
- 5 priority fixes from 2026-03-24 applied and verified
- Live: https://ops-dashboard.111miniapp.com/

## What Works
- Kanban board: GitHub issues/PRs categorized by status
- Agent monitor: 10 agents (from openclaw.json agents.list), correct Linux paths
- Real status/last_seen: injected via OPENCLAW_AGENTS_STATUS_JSON in ops-dashboard.env
- System metrics: Hetzner CPU/RAM/disk/containers
- Health endpoint: /api/health
- Dark theme (#0e1117), clean 2-column layout (kanban left, agents+server right)
- AO section removed — it was always broken (ao not installed)

## Priority Fixes Applied (2026-03-24)
1. ✅ Workspace paths: updated OPENCLAW_AGENTS_JSON to use /home/hui20metrov/ paths
2. ✅ Status detection: pre-compute from ~/.openclaw/agents/*/sessions/sessions.json, inject as env var
3. ✅ AO removed: frontend no longer renders AO sessions section
4. ✅ Missing agents: l2-011-opsdash + l1-012-triscan added from openclaw.json agents.list
5. ✅ Design: cleaner panel layout, better typography, removed AO dead section

## Architecture
- docker-compose.yml: references ops-dashboard.env for large JSON env vars
- ops-dashboard.env: OPENCLAW_AGENTS_JSON + OPENCLAW_AGENTS_STATUS_JSON (pre-computed here, pushed to Hetzner)
- status detection reads sessions.json files locally, pushes status snapshot

## Cycle 2026-03-24 — CSS token discipline (Issue #94, PR #99)
- Added `--surface-raised: #1c2128` and `--surface-header: #1c2128` to :root
- panel-header background: hardcoded #21262d → var(--surface-header)
- .tag-other, .ci-unknown, .agent-status-offline backgrounds → var(--surface-raised)
- .agent-section-header border-top → var(--border)
- --tag-chore-bg → var(--surface-raised)
- All 5 occurrences of #21262d eliminated; design system now tokenized
- Deployed and verified: health OK, 10 agents, 26 containers

## Cycle 2026-03-24 — Kanban full-width layout (Issue #93, PR #98)
- Kanban now spans both columns: `grid-column: 1/-1; grid-row: 1`
- Explicit 5-row grid: row1=kanban, row2=agents+hetzner-server, row3=local+crons, row4=usage(full), row5=containers(full)
- #board-root gets display:flex+flex-direction:column+flex:1+min-height:0 for correct height chain
- usage panel also promoted to full-width (1/-1) in row4
- Mobile: all panels grid-row:auto, single column
- overflow:hidden on dashboard-grid prevents row bleed

## Cycle 2026-03-24 — API Usage panel (Issue #90, PR #91)
- Added `loadUsage()` function + `<section id="usage">` panel to static/index.html
- Panel placed in grid row 3 col 2 (alongside Crons panel)
- Fetches /api/usage → renders session+weekly token bars + model breakdown table
- All-zeros guard: shows "No usage data / ~/.claude logs not mounted" empty state (correct for Hetzner container)
- Auto-refresh every 30s; mobile: stacks vertically
- New CSS: `.usage-section-label`, `.usage-model-table`, `.usage-token-row`, `.usage-reset-info`
- `/api/usage` returns correct shape with zeros (no .claude on Hetzner) — panel handles gracefully
- fmtTokens() helper: formats 0/1k/1M nicely; relWeekReset() shows "resets in 6d 4h"

## Cycle 2026-03-24 — Local machine freshness badge (Issue #88, PR #89)
- push-env.sh: added `computed_at` timestamp (ISO UTC) to LOCAL_MACHINE_JSON python result dict
- static/index.html: freshness badge `⏱ Xm ago` below local panel label (only local-root, not hetzner)
- Colors: grey <5m, amber 5-30m, red >30m
- Badge correctly skipped if computed_at absent (until push-env.sh runs again)

## Cycle 2026-03-24 — Critical alert banner (Issue #86, PR #87)
- Added red alert bar below header: shows when TEMP>85°C, Load>=cpu_count, Disk>90%
- checkAlerts(server) called in loadSystem() after renderServerMetrics
- Fixed scroll hint false positive: timeout 50ms → 500ms (now accurate)
- TEMP at 84.5°C at deploy time — alert correctly hidden (threshold not reached)

## Cycle 2026-03-24 — Row 2 height fix (Issue #84, PR #85)
- Grid was 2fr 1fr 1fr auto (4 rows) — row 2 (server panels) too short, LOAD+TEMP cut off
- Changed 2fr 1fr 1fr auto → 2fr 1.5fr 1fr auto
- Now: Hetzner Server shows all 7 metrics, Local Machine shows all 6 metrics — nothing cut off
- TEMP 81.3°C = amber on Hetzner (watch for spikes above 85°C)

## Cycle 2026-03-24 — Hide empty Kanban columns (Issue #81, PR #82)
- Filtered COLUMNS before rendering: only backlog (always) + columns with >0 cards shown
- IN PROGRESS=0 and BLOCKED=0 are now hidden — Kanban shows BACKLOG(6) + DONE(100)
- One-line change: COLUMNS.filter(col => col.key==="backlog" || byCol[col.key].length > 0).map(...)
- Board is wider and much more readable

## Cycle 2026-03-24 — Grid height fix (Issue #79, PR #80)
- Changed grid-template-rows: 1fr 1fr 1fr → 2fr 1fr auto
- Top row (Kanban + Agents) now gets 2x height — agents shows 4+ cards
- Containers panel auto-height — expands to show all 26 containers
- Trade-off: Server panel row (1fr) is smaller, compact grid (NET/UPTIME/LOAD/TEMP) may need scrolling
- Closed stale issues: #26 (fixed), #16 (implemented), #15 (implemented)

## Cycle 2026-03-24 — 2x2 compact grid for server metrics (Issue #77, PR #78)
- TEMP was cut off — 7 items didn't fit in the panel height
- Replaced 4 stacked rows (NET, UPTIME, LOAD, TEMP) with a 2x2 CSS grid
- All 7 metrics now visible: CPU bar, Memory bar, Disk bar + 2x2 grid
- Used _compactItems array pattern — cleaner than separate *Html vars
- TEMP 77.4°C = green (was 84°C earlier — server cooled down after lower load)

## Cycle 2026-03-24 — Load average (Issue #75, PR #76)
- Hetzner Server panel now has 7 metrics: CPU, Memory, Disk, NET ↑↓, UPTIME, LOAD, Temp
- LOAD: psutil.getloadavg() → 1m/5m/15m, color-coded vs cpu_count (16 cores)
- Load 4.56/4.34/4.19 on 16 cores = ~28% → green
- Note: temp (84°C) seems to not be rendering — check in next cycle

## Cycle 2026-03-24 — System uptime (Issue #73, PR #74)
- Hetzner Server panel now has 6 metrics: CPU, Memory, Disk, NET ↑↓, UPTIME, Temp
- UPTIME: 10d 14h (psutil.boot_time()) — formatted as Xd Yh or Xh Ym or Xm
- Hetzner server has been up 10+ days without reboot

## Cycle 2026-03-24 — Network I/O + hostname fix (Issue #71, PR #72)
- Hetzner Server panel now shows 5 metrics: CPU, Memory, Disk, NET ↑↓, Temp
- NET ↑↓: total bytes sent/recv formatted as KB/MB/GB (from psutil.net_io_counters())
- SERVER_LABEL=Hetzner in docker-compose.yml → panel badge now shows HETZNER not container ID
- SERVER_LABEL falls back to socket.gethostname() if not set

## Cycle 2026-03-24 — CPU temp + cron next-run (Issue #69, PR #70)
- Hetzner Server panel now shows Temp: reads Tctl or Composite from server.temperatures
- Color coding: green <70°C, amber 70-85°C, red >85°C (currently 83.8°C = amber)
- Cron rows now show next-run countdown: '▶ in 26m', '▶ now', etc.

## Cycle 2026-03-24 — Layout fix for cron panel (Issue #67, PR #68)
- 3-row grid: 1fr 1fr 1fr — row1=kanban+agents, row2=hetzner+crons, row3=containers(full-width)
- Cron panel was full-width (grid-column: 1/-1) which compressed agents to 1 visible card
- Disk metric was rendered but squeezed off-screen — now visible with 27.7%
- Mobile: repeat(5, 360px)

## Cycle 2026-03-24 — Cron Jobs panel (Issues #59-#65, PRs #61-#66)
- Added /api/crons endpoint + app/crons.py (reads OPENCLAW_GATEWAY_CRONS_JSON env var)
- Added Cron Jobs panel as full-width 5th panel below 2x2 grid
- push-env.sh: added openclaw cron list --json, strip to minimal fields (~1KB) via python3
- push-env.sh: write CRONS_JSON via printf (not heredoc) to avoid quoting issues
- Docker truncates env vars > ~3.4KB — always strip large JSON payloads before passing as env vars
- 4 active crons: lain-patrol (30m), lain-cron-watchdog (10m), l2-011-opsdash:work (30m), l1-012-triscan:work (30m)

## Cycle 2026-03-24 — Active threshold fix (Issue #57, PR #58)
- push-env.sh had 5-min active threshold — agents with 30-min heartbeats always showed idle
- Changed age_secs < 300 → age_secs < 900 (15 min window)
- lain + l2-011-opsdash now correctly show active

## Cycle 2026-03-24 — Container uptime + push-env cron (Issue #55, PR #56)
- Added StartedAt extraction from Docker SDK c.attrs['State']['StartedAt'] in _get_docker_containers()
- Frontend: replaced raw image name with relative uptime using existing relTime() — "2d ago", "10h ago" etc
- Also set up local cron: */30 * * * * runs push-env.sh to refresh agent status on Hetzner
- l2-011-opsdash now shows "active" correctly after push-env.sh ran

## Cycle 2026-03-24 — Remove dead AO Sessions section (Issue #53, PR #54)
- AO Sessions sub-section in Agent Monitor permanently shows "AO not available" — removed entirely
- Deleted HTML divs (sessions-count, sessions-root), JS vars (rawSessions, aoError, sessions), and error handler line
- 22 lines deleted, 0 dead references remain
- Agent Monitor now shows only OPENCLAW AGENTS with more vertical space

## Cycle 2026-03-24 — Kanban column scroll fix (Issue #51, PR #52)
- Done column (77 cards) was expanding past viewport with no vertical scroll
- Fix: flex chain — board-wrapper(flex col) → board(flex:1) → column(flex col) → col-cards(flex:1, overflow-y:auto)
- Each column now scrolls independently within the panel, all 4 panels fit viewport cleanly

## Cycle 2026-03-24 — Containers scroll + Health fix (Issues #47, #49 / PRs #48, #50)
- Containers list truncated at 8/26 — same fix as agents: max-height:300px on #hetzner-root (inherits overflow-y:auto from .panel-body)
- /api/health was reporting docker.status=error even when Docker worked — race condition from concurrent Docker SDK calls in thread executor
- Fix: 10s TTL cache with threading.Lock in get_server_metrics() — both /api/health and /api/system now share cached result
- Health check now consistently returns status:ok with correct container count

## Cycle 2026-03-24 — Agents panel scroll fix (Issue #45, PR #46)
- Agents panel was truncating at 6/10 agents — active agents (l2-011-opsdash, l1-012-triscan) hidden below fold
- Fix: added overflow-y:auto + max-height:380px to #agents-root in static/index.html
- All 10 agents now scrollable; Server/Containers panel still visible below

## Cycle 2026-03-24 — GH_TOKEN + push-env.sh (Issues #43, #44)
- GH_TOKEN was missing from ops-dashboard.env → /api/kanban returned [] → frontend showed "502" error
- Root cause: GH_TOKEN=${GH_TOKEN} in docker-compose.yml only interpolates, not injects into container
- Hot-fix: added GH_TOKEN to ops-dashboard.env via SCP
- Proper fix: PR#44 adds scripts/push-env.sh — one script to atomically push all 3 env vars
- .gitignore now has ops-dashboard.env — no more accidental secret commits
- Lesson: ALWAYS include GH_TOKEN when pushing ops-dashboard.env. Use push-env.sh going forward.

## Cycle 2026-03-24 — env_file Fix (Issue #41)
- PR#42: docker-compose.yml now uses `env_file: [ops-dashboard.env]` — removes stale /Users/aivan/ paths from repo forever
- Root cause: AO sessions keep re-adding stale OPENCLAW_AGENTS_JSON to docker-compose.yml environment block. Must be watched every cycle.
- Fix process: patched Hetzner live via SSH python3 sed script → SCP fresh ops-dashboard.env → then AO PR for repo fix
- Lesson: shell variable expansion via SSH heredoc mangles JSON (curly braces). Use python3 on remote or SCP files directly.
- Status fresh-push now works correctly via SCP + python3 env file rewrite

## Cycle 2026-03-24 — Health Endpoint Enhancement
- PR#40: /api/health now returns uptime_seconds, version, timestamp, checks{agents,docker,hetzner}
- Bug: AO added volume mounts (/home/hui20metrov/agents:/agents:ro) to docker-compose.yml that don't exist on Hetzner → container wouldn't start. Fixed by removing those mounts in f6b52e2.
- Lesson: AO may add env vars/volumes that assume dev machine structure. Always verify docker-compose.yml against Hetzner paths before deploy.
- CSS: idle=amber, offline=grey status colors added to agent cards (good improvement)
- Health endpoint now takes ~2-4s due to calling agents+system APIs. Acceptable.

## Known Issues / Improvements
- OPENCLAW_AGENTS_STATUS_JSON is static (computed once per deploy) — need cron to refresh
- Issue #36: Kanban Done column (70 items) off-screen — horizontal scroll + count badge needed
- Issue #35: Containers panel shows mirrored Hetzner data — fix empty state display
- WebSocket for live metric updates (eliminate polling)
- Cron job monitoring panel
- Container health detail view (logs, restart count)
- API response caching (reduce Hetzner SSH calls)
- Error handling for SSH connection failures
- Unit tests for API endpoints

## Lessons Learned
- docker-compose.yml cannot have raw JSON in env vars (YAML colon conflicts) → use env_file
- Hetzner server has no OpenClaw installed → can't mount ~/.openclaw from container
- Session status must be pre-computed locally and pushed as env var to Hetzner
- openclaw.json agents.list is authoritative; docker-compose OPENCLAW_AGENTS_JSON was stale
