# AGENTS.md — L2-011-opsdash

Solo developer. Project: ops-dashboard. Model: minimax-m2.7-highspeed, thinking: high.

## Bootstrap (EVERY wake)
1. cat STATE.yaml → определи текущий state
2. Выполни ОДНУ state transition (см. State Machine)
3. Обнови STATE.yaml
4. Пост прогресс в топик 6982

## Project
- Repo: ddfeyes/ops-dashboard
- Live: https://ops-dashboard.111miniapp.com/
- Topic: 6982
- Workspace: /home/hui20metrov/ops-dashboard/
- Hetzner path: /home/user3/ops-dashboard

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
