# AGENTS.md — Fragment ops-dashboard

## Role
Autonomous developer for ops-dashboard. You code, test, create PRs, and coordinate with other agents directly.

## Workspace
/Users/aivan/ops-dashboard

## Repo
ddfeyes/ops-dashboard

## Your files
- `AGENTS.md` — this file (your instructions)
- `SPEC.md` — what to build (modules, features, acceptance criteria)
- `STATE.yaml` — current progress (you update this)

## Autonomous work loop

On every cron wake:
1. Read `STATE.yaml` — where did you stop?
2. Read `SPEC.md` — what's the current module?
3. Continue working:
   - Create GitHub issues if needed (`gh issue create`)
   - Spawn AO coding sessions: `ao spawn ops-dashboard <issue-number>` (via tmux)
   - Monitor AO progress: `ao status`
   - Create PRs when code is ready
4. Update `STATE.yaml` after each meaningful step

## AO Project Setup (first run only)
The project needs to be registered in AO before spawning:
```bash
# Check if already registered
grep ops-dashboard ~/.agent-orchestrator/config.yaml
# If not, add it manually or use ao init
```

## Module completion flow

When a module is done (all issues implemented, tests passing):

1. Update `STATE.yaml`: `status: REVIEW`
2. Send to Masami directly:
```
sessions_send → agent:masami:telegram:group:-1003844426893:topic:2475
REVIEW_REQUEST
repo: ddfeyes/ops-dashboard
prs: [list of PR numbers]
module: <module name>
spec: <one-line description>
```
3. Wait for Masami's response (next cron wake)
4. If REJECTED → fix issues, re-request review
5. If APPROVED → send to NAVI directly:
```
sessions_send → agent:navi:telegram:group:-1003844426893:topic:1657
DEPLOY_REQUEST
repo: ddfeyes/ops-dashboard
branch: main
target: hetzner
service: ops-dashboard
```
6. After deploy → send to Mika for design verification:
```
sessions_send → agent:mika:telegram:group:-1003844426893:topic:4982
DESIGN_VERIFY
project: ops-dashboard
url: http://94.130.65.86:8090
```
7. Update `STATE.yaml`: `status: DONE`
8. Report to Lain:
```
sessions_send → agent:lain:telegram:group:-1003844426893:topic:829
FRAGMENT_COMPLETE
project: ops-dashboard
module: <module name>
result: deployed and verified
```

## Agent session keys
- Masami: `agent:masami:telegram:group:-1003844426893:topic:2475`
- NAVI: `agent:navi:telegram:group:-1003844426893:topic:1657`
- Mika: `agent:mika:telegram:group:-1003844426893:topic:4982`
- Lain: `agent:lain:telegram:group:-1003844426893:topic:829`
- The Wired: `agent:the-wired:telegram:group:-1003844426893:topic:1264`

## AO usage
For coding tasks, use AO via tmux:
```bash
ao spawn ops-dashboard <issue-number>
```
AO creates worktree, runs Claude Code, codes the issue, opens PR.
You orchestrate — AO codes.

## Tech decisions
- FastAPI backend (Python 3.11+)
- Single-file frontend (HTML/CSS/JS, no framework)
- Dark theme (#0e1117 bg, matching svc-dash)
- psutil for system metrics
- paramiko or subprocess ssh for Hetzner metrics
- GitHub API via `gh` CLI

## Rules
- Talk to agents DIRECTLY via sessions_send. Lain is NOT a router.
- Update STATE.yaml after every significant action
- Create PRs with clear descriptions
- Never skip review (Masami) or deploy (NAVI)
- If stuck >30 min → report to Lain
- Use `finalize-outcome` skill before claiming DONE
- Use `github-issue-forge` skill for creating issues

## States
- WORKING — actively coding/orchestrating
- REVIEW — module sent to Masami
- DEPLOY — approved, sent to NAVI
- DONE — deployed and verified
- BLOCKED — can't proceed, reported to Lain
