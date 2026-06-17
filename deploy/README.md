# SIONA Deploy Layout (Phase 3–6)

Multi-deployment: same codebase, different law + state + knowledge per tenant.

## Quick start (development)

```bash
cp deploy/samson.home/.env.example .env
# edit SSN_MASTER_KEY locally — never commit
export SSN_AUTO_DOTENV=1
python -m ssn.runtime.http_server --port 8080
```

Health check:

```bash
curl http://127.0.0.1:8080/v1/health
```

## Samson home (deployment #1)

Law: `ssn/policy/home_law_samson.yaml` (OWNER ultimate authority)

```bash
cp deploy/samson.home/.env.example .env
python -m ssn.runtime.http_server --port 8080
```

## Example organization (deployment #2)

```bash
export SSN_HOME_LAW_PATH=deploy/tenant.example/home_law_org.yaml
export SSN_STATE_DIR=.ssn_state/tenants/org-example
export SSN_TENANT_ID=org-example
python -m ssn.runtime.http_server --port 8081
```

Tenant header (state isolation):

```bash
curl -X POST http://127.0.0.1:8080/v1/chat \
  -H "Content-Type: application/json" \
  -H "X-SSN-Tenant-ID: org-example" \
  -d '{"message":"hello","role":"GUEST","offline":true}'
```

---

## Production install (Ubuntu / Jarvis box)

### 1. Install code and venv

```bash
sudo useradd --system --home /opt/siona --shell /usr/sbin/nologin siona || true
sudo mkdir -p /opt/siona /var/lib/siona/state /etc/siona
sudo git clone https://github.com/samsonnjaji/SSN.git /opt/siona
cd /opt/siona
sudo python3 -m venv .venv
sudo .venv/bin/pip install -r requirements.txt
sudo chown -R siona:siona /opt/siona /var/lib/siona
```

Optional editable install with console scripts:

```bash
sudo -u siona /opt/siona/.venv/bin/pip install -e /opt/siona
# then: siona-http, siona-cli
```

### 2. Configure environment

```bash
sudo cp deploy/siona.env.example /etc/siona/siona.env
sudo chmod 600 /etc/siona/siona.env
sudo nano /etc/siona/siona.env   # set SSN_MASTER_KEY, LLM endpoints, etc.
```

Initialize OWNER master key hash (one-time):

```bash
sudo -u siona bash -lc 'set -a && source /etc/siona/siona.env && set +a && /opt/siona/.venv/bin/python /opt/siona/scripts/init_master_key.py'
```

### 3. Install systemd service

```bash
sudo cp deploy/siona.service /etc/systemd/system/siona.service
sudo systemctl daemon-reload
sudo systemctl enable siona
sudo systemctl start siona
sudo systemctl status siona
```

Logs (structured JSON when `SSN_STRUCTURED_LOG=1`):

```bash
journalctl -u siona -f
```

Health:

```bash
curl http://127.0.0.1:8080/v1/health
```

---

## Backup and restore

### Backup

```bash
SSN_STATE_DIR=/var/lib/siona/state ./scripts/backup_state.sh
# default output: ./backups/siona-state-YYYYMMDD-HHMMSS.tar.gz
```

Includes sessions, rate limits, master key hash, memory proposals, etc.

### Restore

```bash
sudo systemctl stop siona
sudo tar -xzf backups/siona-state-YYYYMMDD-HHMMSS.tar.gz -C /var/lib/siona
# archive contains top-level "state/" directory when SSN_STATE_DIR=/var/lib/siona/state
sudo chown -R siona:siona /var/lib/siona
sudo systemctl start siona
```

Verify with `/v1/health` and a test chat request.

---

## Environment variables

| Variable | Purpose |
|----------|---------|
| `SSN_HOME_LAW_PATH` | OWNER home law YAML |
| `SSN_WORLD_LAW_PATH` | Global world law YAML |
| `SSN_SYSTEM_LAW_PATH` | System law YAML |
| `SSN_STATE_DIR` | Runtime state root |
| `SSN_KNOWLEDGE_PATH` | Curated knowledge JSONL |
| `SSN_TENANT_ID` | Default tenant id (optional) |
| `SSN_STRUCTURED_LOG` | `1` = JSON audit/access logs to stdout |
| `SSN_HTTP_QUIET` | `1` = suppress plain HTTP access logs |

See `ENVIRONMENT.md` for full reference.

## Law modes

| `owner_authority` | Behavior |
|-------------------|----------|
| `ultimate` (Samson default) | OWNER allowed unless explicitly restricted |
| `bounded` (tenant example) | OWNER only if action in `permissions.allowed_actions` |

Guest allowlist: optional `guest_permissions.allowed_actions` in home law YAML.
