# NetBox Setup

aiNOC uses NetBox as the source of truth for device inventory (replacing `NETWORK.json`).
NetBox is optional — the system falls back to `inventory/NETWORK.json` when not configured.

---

## Install NetBox (Docker)

```bash
git clone -b release https://github.com/netbox-community/netbox-docker.git
cd netbox-docker
```

## Configure Port Mapping

Rename the existing test override file (it's empty) and edit it to expose port 8080:

```bash
sudo mv docker-compose.test.override.yml docker-compose.override.yml
```

Edit `docker-compose.override.yml` to contain:
```yaml
services:
  netbox:
    ports:
      - "127.0.0.1:8000:8080"
```

## Start Containers

```bash
docker compose up -d
```

First start takes ~2 minutes to run database migrations. All containers will show `healthy` when ready.

## Create Superuser

```bash
docker compose exec -e DJANGO_SUPERUSER_PASSWORD=<password> netbox \
  python /opt/netbox/netbox/manage.py createsuperuser \
  --username admin --email admin@ainoc.local --noinput
```

Then restart to apply the port mapping:
```bash
docker compose down && docker compose up -d
```

## Create API Token

1. Log in at `http://localhost:8000` with admin / <your_password>
2. Go to the user menu (top right) → **Profile** → **API Tokens** → **Add Token**
3. Under **Version**, select **v1** — v2 tokens are hashed and incompatible with pynetbox
4. Copy the generated token value (shown once at creation)

## Configure aiNOC

Add to `.env`:
```
NETBOX_URL=http://localhost:8000
NETBOX_TOKEN=<your_api_token>
```

## Populate Devices

Run the population script — it creates all prerequisite objects and 9 devices automatically:

```bash
cd /home/mcp/aiNOC
python metadata/netbox/populate_netbox.py
```

The script is idempotent — safe to run multiple times. Verify the result:

```bash
PYTHONPATH=/home/mcp/aiNOC python -c "
from core.netbox import load_devices
d = load_devices()
print(f'{len(d)} devices loaded from NetBox')
for name, info in sorted(d.items()):
    print(f'  {name}: {info[\"host\"]} ({info[\"transport\"]})')
"
```

## Device Reference

| Device | Platform slug | Transport | cli_style | Management IP | Site |
|--------|--------------|-----------|-----------|---------------|------|
| A1C | cisco_iosxe | asyncssh | ios | 172.20.20.205 | Access |
| A2C | cisco_iosxe | asyncssh | ios | 172.20.20.206 | Access |
| C1C | cisco_iosxe | restconf | ios | 172.20.20.207 | Core |
| C2C | cisco_iosxe | restconf | ios | 172.20.20.208 | Core |
| E1C | cisco_iosxe | restconf | ios | 172.20.20.209 | Edge |
| E2C | cisco_iosxe | restconf | ios | 172.20.20.210 | Edge |
| IAN | cisco_iosxe | asyncssh | ios | 172.20.20.220 | ISP A |
| IBN | cisco_iosxe | asyncssh | ios | 172.20.20.230 | ISP B |
| X1C | cisco_iosxe | restconf | ios | 172.20.20.240 | Remote |

---

## Production: Boot Persistence

### Step 1 — Enable Docker to start on boot

```bash
sudo systemctl enable docker
```

### Step 2 — Add restart policies to the compose stack

Edit `docker-compose.override.yml` to add `restart: unless-stopped` to each service so Docker restarts the containers automatically when it starts:

```yaml
services:
  netbox:
    ports:
      - "127.0.0.1:8000:8080"
    restart: unless-stopped
  netbox-worker:
    restart: unless-stopped
  postgres:
    restart: unless-stopped
  redis:
    restart: unless-stopped
  redis-cache:
    restart: unless-stopped
```

Apply the change:
```bash
docker compose down && docker compose up -d
```

### Alternative: systemd unit (production-grade)

For tighter integration — dependency ordering, journal logging, `systemctl status netbox`:

```bash
sudo tee /etc/systemd/system/netbox.service > /dev/null <<'EOF'
[Unit]
Description=NetBox Docker Compose Stack
Requires=docker.service
After=docker.service

[Service]
Type=oneshot
RemainAfterExit=yes
WorkingDirectory=/home/mcp/netbox-docker
ExecStart=/usr/bin/docker compose up -d --remove-orphans
ExecStop=/usr/bin/docker compose down
TimeoutStartSec=120

[Install]
WantedBy=multi-user.target
EOF

sudo systemctl daemon-reload
sudo systemctl enable --now netbox
```

This approach also allows ordering Vault before NetBox: add `After=vault.service` to `[Unit]` if needed.

### Verify

After a reboot, confirm all containers are running:
```bash
docker ps --format "table {{.Names}}\t{{.Status}}"
```
Expected: all 5 `netbox-docker-*` containers show `Up`.

---

## Troubleshooting

### Containers exited after reboot (NetBox unreachable)

**Symptom**: `docker ps` shows all `netbox-docker-*` containers as `Exited`. Browser can't connect to `localhost:8000`. Dashboard SOURCE shows `NETWORK.json` instead of `NetBox`.

**Cause**: Docker was re-enabled on boot but the containers lack a restart policy — they were stopped and never restarted.

**Fix**:
1. Add `restart: unless-stopped` to each service in `docker-compose.override.yml` (see "Boot Persistence" above — this is a one-time change).
2. Start the containers: `cd ~/netbox-docker && docker compose up -d`

### aiNOC shows NETWORK.json after NetBox is restored

If NetBox is brought back up while the watcher is already running, the watcher process has cached `inventory_source = "NETWORK.json"` from startup. Restart the watcher to pick up the new state:
```bash
sudo systemctl restart oncall-watcher
```
