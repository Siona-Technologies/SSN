# SIONA Deploy Layout (Phase 3)

Multi-deployment: same codebase, different law + state + knowledge per tenant.

## Samson home (deployment #1)

```bash
cp deploy/samson.home/.env.example .env
# edit SSN_MASTER_KEY locally — never commit
export SSN_AUTO_DOTENV=1
python -m ssn.runtime.http_server --port 8080
```

Law: `ssn/policy/home_law_samson.yaml` (OWNER ultimate authority)

## Example organization (deployment #2)

```bash
export SSN_HOME_LAW_PATH=deploy/tenant.example/home_law_org.yaml
export SSN_STATE_DIR=.ssn_state/tenants/org-example
export SSN_TENANT_ID=org-example
python -m ssn.runtime.http_server --port 8081
```

Or use HTTP tenant header (state isolation only):

```bash
curl -X POST http://127.0.0.1:8080/v1/chat \
  -H "Content-Type: application/json" \
  -H "X-SSN-Tenant-ID: org-example" \
  -d '{"message":"hello","role":"GUEST","offline":true}'
```

Sessions for tenant `org-example` persist under:
`.ssn_state/tenants/org-example/sessions/`

## Environment variables

| Variable | Purpose |
|----------|---------|
| `SSN_HOME_LAW_PATH` | OWNER home law YAML |
| `SSN_WORLD_LAW_PATH` | Global world law YAML |
| `SSN_SYSTEM_LAW_PATH` | System law YAML |
| `SSN_STATE_DIR` | Runtime state root |
| `SSN_KNOWLEDGE_PATH` | Curated knowledge JSONL |
| `SSN_TENANT_ID` | Default tenant id (optional) |

## Law modes

| `owner_authority` | Behavior |
|-------------------|----------|
| `ultimate` (Samson default) | OWNER allowed unless explicitly restricted |
| `bounded` (tenant example) | OWNER only if action in `permissions.allowed_actions` |

Guest allowlist: optional `guest_permissions.allowed_actions` in home law YAML.
