#!/usr/bin/env bash
# push-env.sh — Compute and push ops-dashboard.env to Hetzner
set -euo pipefail

HETZNER_HOST="user3@94.130.65.86"
HETZNER_PORT="2203"
HETZNER_PASS="VibeUser32345001f"
REMOTE_DIR="/home/user3/ops-dashboard"
ENV_FILE="/tmp/ops-dashboard-push.env"

echo "==> Computing local machine metrics..."
LOCAL_MACHINE_JSON=$(python3 - << 'PYEOF'
import json, time, os

with open('/proc/stat') as f:
    cpu_line = f.readline()
vals = list(map(int, cpu_line.split()[1:]))
idle, total = vals[3], sum(vals)
time.sleep(0.3)
with open('/proc/stat') as f:
    cpu_line2 = f.readline()
vals2 = list(map(int, cpu_line2.split()[1:]))
idle2, total2 = vals2[3], sum(vals2)
cpu_pct = round(100 * (1 - (idle2-idle)/(total2-total)), 1)

mem = {}
with open('/proc/meminfo') as f:
    for line in f:
        k, v = line.split(':')
        mem[k.strip()] = int(v.split()[0])
mem_total = round(mem['MemTotal']/1024**2, 2)
mem_avail = round(mem['MemAvailable']/1024**2, 2)
mem_used = round((mem['MemTotal']-mem['MemAvailable'])/1024**2, 2)
mem_pct = round(100*mem_used/mem_total, 1)

import shutil
disk = shutil.disk_usage('/')
disk_total = round(disk.total/1024**3, 2)
disk_used = round(disk.used/1024**3, 2)
disk_pct = round(100*disk_used/disk_total, 1)

with open('/proc/loadavg') as f:
    la = f.read().split()
load1, load5, load15 = float(la[0]), float(la[1]), float(la[2])
cpu_count = os.cpu_count() or 1

with open('/proc/uptime') as f:
    uptime_sec = int(float(f.read().split()[0]))

net_sent, net_recv = 0, 0
with open('/proc/net/dev') as f:
    for line in f:
        parts = line.split()
        if len(parts) < 10 or ':' not in parts[0]:
            continue
        iface = parts[0].rstrip(':')
        if iface == 'lo':
            continue
        net_recv += int(parts[1])
        net_sent += int(parts[9])

hostname = open('/etc/hostname').read().strip() if os.path.exists('/etc/hostname') else 'local'

result = {
    'cpu_percent': cpu_pct, 'cpu_count': cpu_count,
    'memory': {'total_gb': mem_total, 'used_gb': mem_used, 'percent': mem_pct},
    'disk': {'total_gb': disk_total, 'used_gb': disk_used, 'percent': disk_pct},
    'network': {'bytes_sent': net_sent, 'bytes_recv': net_recv},
    'load_avg': {'load1': load1, 'load5': load5, 'load15': load15, 'cpu_count': cpu_count},
    'uptime_seconds': uptime_sec,
    'hostname': hostname,
    'label': 'Local Machine'
}
print(json.dumps(result, separators=(',', ':')))
PYEOF
)

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
CRONS_JSON=$(openclaw cron list --json 2>/dev/null | python3 -c 'import sys,json; d=json.load(sys.stdin); jobs=d if isinstance(d,list) else d.get("jobs",[]); m=[{"id":j.get("id",""),"name":j.get("name",""),"agentId":j.get("agentId",""),"enabled":j.get("enabled",True),"schedule":{"everyMs":j.get("schedule",{}).get("everyMs",0)},"state":{"lastRunAtMs":j.get("state",{}).get("lastRunAtMs",0),"nextRunAtMs":j.get("state",{}).get("nextRunAtMs",0),"lastRunStatus":j.get("state",{}).get("lastRunStatus","unknown"),"lastDurationMs":j.get("state",{}).get("lastDurationMs",0),"consecutiveErrors":j.get("state",{}).get("consecutiveErrors",0)}} for j in jobs]; print(json.dumps({"jobs":m},separators=(",",":")))' 2>/dev/null || echo '{"jobs":[]}')

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
EOF
printf 'OPENCLAW_GATEWAY_CRONS_JSON=%s\n' "$CRONS_JSON" >> "$ENV_FILE"
printf 'LOCAL_MACHINE_JSON=%s\n' "$LOCAL_MACHINE_JSON" >> "$ENV_FILE"

echo "==> Pushing to Hetzner..."
sshpass -p "$HETZNER_PASS" scp -P "$HETZNER_PORT" -o StrictHostKeyChecking=no \
  "$ENV_FILE" "${HETZNER_HOST}:${REMOTE_DIR}/ops-dashboard.env"

echo "==> Restarting container..."
sshpass -p "$HETZNER_PASS" ssh -o StrictHostKeyChecking=no -p "$HETZNER_PORT" "$HETZNER_HOST" \
  "cd $REMOTE_DIR && docker compose --env-file ops-dashboard.env up -d"

echo "==> Done! ops-dashboard.env pushed and container restarted."
