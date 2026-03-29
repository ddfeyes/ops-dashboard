# AGENTS.md — L2-011-opsdash

Solo developer. Project: ops-dashboard. Model: minimax-m2.7-highspeed, thinking: high.

## Bootstrap (EVERY wake)
0. Check mailbox: ls /home/hui20metrov/agents/mailbox/<my-agent-id>/*.msg — process and delete
1. cat STATE.yaml → определи текущий state
2. Выполни ОДНУ state transition (см. State Machine)
3. Обнови STATE.yaml
4. Пост прогресс в топик 6982

## Project
- Repo: ddfeyes/ops-dashboard
- Live: https://ops-dashboard.111miniapp.com/
- Topic: 6982
- Workspace: /home/hui20metrov/ops-dashboard/
- Hetzner: source ~/.lain-secrets/hetzner.env → sshpass -p $HETZNER_PASS ssh -o StrictHostKeyChecking=no $HETZNER_USER@$HETZNER_HOST -p $HETZNER_PORT
- Hetzner path: /home/user3/ops-dashboard
- NEVER use 82.165.193.123 — WRONG IP. Always use hetzner.env vars.

## State Machine
INIT → PLANNING → CODING → TESTING → SELF_REVIEW → DEPLOYING → VERIFYING → DONE → INIT
BLOCKED = любой state → sessions_send к Lain

## Pipeline
Читай /home/hui20metrov/agents/lain/shared/PIPELINE.md

## Verification
Читай /home/hui20metrov/agents/lain/shared/VERIFICATION.md перед VERIFYING

## Communication
Читай /home/hui20metrov/agents/lain/shared/COMMUNICATION.md
- Топик: 6982
- BLOCKED/DONE → sessions_send к Lain

## Rules
Читай /home/hui20metrov/agents/lain/shared/RULES.md
Один цикл = одна state transition. Без пропусков. Без shortcuts.

## Agent Session Keys (для sessions_send)
- Mika (design): agent:mika:telegram:group:-1003844426893:topic:4982
- Masami (review): agent:masami:telegram:group:-1003844426893:topic:2475
- NAVI (deploy): agent:navi:telegram:group:-1003844426893:topic:1657
- Lain (orchestrator): agent:lain:telegram:group:-1003844426893:topic:829
НЕ используй agents_list tool — он показывает только subagents, не всех агентов.
Все агенты выше ЖИВЫЕ и просыпаются каждые 20 мин.

