# BACKLOG.md — ops-dashboard
# Агент обновляет этот файл каждый цикл. Новые задачи добавляются снизу.
# [x] = done, [ ] = todo, P0-P4 = priority

## Active
- [x] P2: docker.containers=0 в health endpoint — fixed 2026-03-24 (теперь показывает 27)
- [ ] P3: agent last_seen timestamps (issue #29)

## Ideas (агент пополняет)
- [x] P2: misleading 'mac' key duplicate in /api/system (issue #156) — fixed 2026-03-28
- [x] P2: network I/O as rate not cumulative bytes (issue #157) — fixed 2026-03-28
- [x] P2: health endpoint shows unhealthy containers (issue #158) — fixed 2026-03-28
- [x] P3: kanban toolbar repo counts (issue #159) — fixed 2026-03-28
- [x] P3: kanban Done column header shows X/Y count when collapsed (issue #160) — fixed 2026-03-28
- [x] P3: /api/kanban returns {cards,total} with filtered count badge (issue #161) — fixed 2026-03-28
- [x] P3: network rate shows — not 0B/s on first poll post-restart (issue #162) — fixed 2026-03-28
- [x] P3: done column age footer showing oldest card age (issue #163) — fixed 2026-03-28
- [x] P3: done cards >7d old get visual stale marker (opacity+strikethrough) (issue #164) — fixed 2026-03-28
- [x] P3: container restart count badge — only shown when >0 (issue #165) — fixed 2026-03-28
- [x] P3: kanban cards link to PR when available, title hover hint (issue #166) — fixed 2026-03-28
- [x] P3: header shows version + deploy date (issue #167) — fixed 2026-03-28
