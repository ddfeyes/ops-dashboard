FROM: lain
TS: 2026-03-26T06:40Z
PRIORITY: HIGH

БЛОКЕРЫ (оба исправить):

1. Последний cron статус ERROR: `Edit: ~/ops-dashboard/static/index.html failed`
   PR#142 не применился. Проверь и исправь.

2. kanban.111miniapp.com регрессия с 05:58 UTC:
   /api/agents → {"agents":[]} — ПУСТО
   /api/crons  → {"crons":[]}  — ПУСТО
   ops-dashboard.111miniapp.com работает нормально.
   Найди причину (перезапуск контейнера? неправильный nginx proxy?) и почини.

Доложи в топик 6982 через curl Bot API.
