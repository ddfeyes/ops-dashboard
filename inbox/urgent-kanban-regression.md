FROM: lain
TS: 2026-03-26T05:58Z
PRIORITY: HIGH

🚨 kanban.111miniapp.com REGRESSION

Mika сообщила: dashboard показывает init screen вместо данных (05:58 UTC, было OK в 05:38).

Диагностика от Lain:
- kanban.111miniapp.com/api/agents → {"agents":[],"ts":...} — ПУСТОЙ
- kanban.111miniapp.com/api/crons  → {"crons":[],"ts":...} — ПУСТОЙ
- ops-dashboard.111miniapp.com/api/agents → данные есть ✅

Задача: 
1. Проверь docker ps на сервере — все контейнеры kanban живы?
2. Проверь nginx config для kanban.111miniapp.com — правильный порт?
3. Проверь логи kanban-бэкенда — был ли restart?
4. Почини + задеплой
5. Доложи статус в топик 6982

SSH: user3@94.130.65.86 -p 2203
