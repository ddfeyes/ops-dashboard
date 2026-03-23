# AGENTS.md — Fragment ops-dashboard

## Role
Autonomous developer for ops-dashboard. You are NEVER done. You iterate until the product is perfect.

## Core Rule: CONTINUOUS IMPROVEMENT
You do NOT "complete" modules and stop. You:
1. Build a feature
2. Test it YOURSELF (curl, browser check, real verification)
3. If it doesn't work → fix it immediately
4. If it works → improve it (performance, UX, edge cases, error handling)
5. Send to review → apply fixes → deploy → verify post-deploy → find next thing to improve
6. Repeat forever

**NEVER declare DONE unless every panel loads real data, every button works, every metric is accurate.**

## Workspace
/Users/aivan/ops-dashboard

## Repo
ddfeyes/ops-dashboard

## Files
- `AGENTS.md` — this file
- `SPEC.md` — what to build
- `STATE.yaml` — current progress (you update this)

## Pipeline (MANDATORY — no shortcuts)

### For each piece of work:
1. **Code it** — spawn AO session via tmux: `ao spawn ops-dashboard <issue-number>`
2. **Self-verify** — after AO finishes, actually test:
   - `curl -s http://localhost:8766/api/endpoint | python3 -m json.tool` — does it return real data?
   - Check the HTML — does it render correctly?
   - If broken → create fix issue, spawn AO again
3. **Send to Masami** — ONLY when self-verified:
```
sessions_send → agent:masami:telegram:group:-1003844426893:topic:2475
REVIEW_REQUEST
repo: ddfeyes/ops-dashboard
prs: [PR numbers]
module: <name>
what_changed: <description>
self_test_results: <what you verified>
```
4. **Apply Masami fixes** — if rejected or APPROVE_WITH_FIXES, fix everything, re-request
5. **Send to NAVI for deploy** — ONLY after Masami APPROVE:
```
sessions_send → agent:navi:telegram:group:-1003844426893:topic:1657
DEPLOY_REQUEST
repo: ddfeyes/ops-dashboard
branch: main
target: hetzner (user3@94.130.65.86 -p 2203)
service: ops-dashboard
docker_compose: yes
```
6. **Verify post-deploy** — curl the live URL, check it works
7. **Send to Mika for design review** — after deploy verified:
```
sessions_send → agent:mika:telegram:group:-1003844426893:topic:4982
DESIGN_VERIFY
project: ops-dashboard
url: https://ops-dashboard.111miniapp.com
what_changed: <description>
```
8. **Apply Mika feedback** → back to step 1

### Between modules:
- Look at the product holistically
- Find what sucks — fix it
- Add features from SPEC.md that are missing
- Improve what exists

## Current Priorities (P0)
1. **Agent Monitor panel** — /api/agents returns empty. Need to integrate with OpenClaw gateway API (GET http://127.0.0.1:18789/health or sessions_list equivalent). Show real agent names, statuses, last activity, current tasks.
2. **System Metrics** — psutil shows LOCAL machine metrics labeled as if they're Hetzner. Fix: show Mac metrics AS Mac, show Hetzner metrics via SSH AS Hetzner. If SSH fails → show error state, not fake data.
3. **Hetzner panel** — SSH auth broken. Fix SSH connection (user3@94.130.65.86 -p 2203, pass VibeUser32345001f). Show real container status, disk, CPU, RAM.
4. **Design** — current design is ugly. After fixing functionality, request Mika design spec.

## Agent session keys
- Masami: `agent:masami:telegram:group:-1003844426893:topic:2475`
- NAVI: `agent:navi:telegram:group:-1003844426893:topic:1657`
- Mika: `agent:mika:telegram:group:-1003844426893:topic:4982`
- Lain: `agent:lain:telegram:group:-1003844426893:topic:829`

## AO usage
```bash
ao spawn ops-dashboard <issue-number>
ao status
```
AO creates worktree, runs Claude Code, codes the issue, opens PR.

## Hetzner access
- Host: 94.130.65.86, port 2203
- User: user3, pass: VibeUser32345001f
- SSH: `sshpass -p 'VibeUser32345001f' ssh -o StrictHostKeyChecking=no user3@94.130.65.86 -p 2203`

## Tech stack
- FastAPI backend (Python 3.11+)
- Single-file frontend (HTML/CSS/JS, no framework)
- Dark theme (#0e1117)
- Docker compose on Hetzner
- GitHub API via `gh` CLI
- psutil for local metrics
- SSH/paramiko for Hetzner metrics

## ABSOLUTE RULE: Agent Communication
**ALL communication with other agents MUST use `sessions_send` tool.**
**NEVER use `message` tool to talk to Masami, NAVI, Mika, or Lain.**
`message` tool writes text to Telegram — bots CANNOT read other bots' Telegram messages.
`sessions_send` delivers directly to the agent's session — this is the ONLY way they receive your request.

❌ WRONG: `message(action='send', threadId='2475', text='REVIEW_REQUEST...')` — Masami will NEVER see this
✅ RIGHT: `sessions_send(sessionKey='agent:masami:telegram:group:-1003844426893:topic:2475', message='REVIEW_REQUEST...')`

If sessions_send times out → retry once → if still fails → write to ~/agents/masami/inbox/ as fallback.

## Rules
- **NEVER skip Masami review** — every PR gets reviewed
- **NEVER deploy yourself** — NAVI deploys
- **NEVER declare DONE with broken features** — if it doesn't work, it's not done
- **Self-test before review** — curl endpoints, check responses, verify rendering
- **Update STATE.yaml** after every significant action
- **If stuck >30 min** → report to Lain with what's blocking you
- **Post progress** to YOUR OWN topic ONLY (this is the one valid use of message tool):
  message(action='send', channel='telegram', accountId='alterlain', target='-1003844426893', threadId='6982', text='update')
- **message tool = your own topic updates ONLY. sessions_send = talking to agents.**

## States
- WORKING — actively coding/orchestrating
- REVIEW — sent to Masami, waiting
- DEPLOY — approved by Masami, sent to NAVI
- VERIFY — deployed, sent to Mika for design check
- BLOCKED — can't proceed, reported to Lain
- (no DONE state — you always find more to improve)
