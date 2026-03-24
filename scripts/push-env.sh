#!/usr/bin/env bash
# push-env.sh — Compute and push ops-dashboard.env to Hetzner
set -euo pipefail

HETZNER_HOST="user3@94.130.65.86"
HETZNER_PORT="2203"
HETZNER_PASS="VibeUser32345001f"
REMOTE_DIR="/home/user3/ops-dashboard"
ENV_FILE="/tmp/ops-dashboard-push.env"

echo "==> Computing agent status..."
AGENTS_STATUS=$(python3 - << 'PYEOF'
import json, os
from datetime import datetime, timezone
sessions_base = os.path.expanduser("~/.openclaw/agents")
result = {}
now = datetime.now(timezone.utc).timestamp()
for agent_dir in os.listdir(sessions_base):
    sessions_file = os.path.join(sessions_base, agent_dir, "sessions", "sessions.json")
    if not os.path.exists(sessions_file):
        continue
    try:
        with open(sessions_file) as f:
            data = json.load(f)
        sessions = data.values() if isinstance(data, dict) else data
        last_ms = max((s.get("updatedAt", 0) or s.get("lastMessageAt", 0) for s in sessions), default=0)
        if last_ms:
            last_iso = datetime.fromtimestamp(last_ms/1000, tz=timezone.utc).isoformat()
            age_secs = now - last_ms/1000
            result[agent_dir] = {"status": "active" if age_secs < 900 else "idle", "last_seen_iso": last_iso}
    except Exception:
        pass
print(json.dumps(result, separators=(',', ':')))
PYEOF
)

echo "==> Getting cron jobs..."
CRONS_JSON=$(openclaw cron list --json 2>/dev/null || echo '[]')

echo "==> Getting GH_TOKEN..."
GH_TOKEN=$(gh auth token)

echo "==> Getting current OPENCLAW_AGENTS_JSON from Hetzner..."
AGENTS_JSON=$(sshpass -p "$HETZNER_PASS" ssh -o StrictHostKeyChecking=no -p "$HETZNER_PORT" "$HETZNER_HOST" \
  "grep '^OPENCLAW_AGENTS_JSON=' $REMOTE_DIR/ops-dashboard.env | head -1")

echo "==> Writing env file..."
cat > "$ENV_FILE" << EOF
${AGENTS_JSON}
OPENCLAW_AGENTS_STATUS_JSON=${AGENTS_STATUS}
GH_TOKEN=${GH_TOKEN}
OPENCLAW_GATEWAY_CRONS_JSON=${CRONS_JSON}
EOF

echo "==> Pushing to Hetzner..."
sshpass -p "$HETZNER_PASS" scp -P "$HETZNER_PORT" -o StrictHostKeyChecking=no \
  "$ENV_FILE" "${HETZNER_HOST}:${REMOTE_DIR}/ops-dashboard.env"

echo "==> Restarting container..."
sshpass -p "$HETZNER_PASS" ssh -o StrictHostKeyChecking=no -p "$HETZNER_PORT" "$HETZNER_HOST" \
  "cd $REMOTE_DIR && docker compose --env-file ops-dashboard.env up -d"

echo "==> Done! ops-dashboard.env pushed and container restarted."
