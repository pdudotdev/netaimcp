# HashiCorp Vault Setup

aiNOC uses Vault to store 4 secrets (router credentials, Jira API token, Discord bot token).
Vault is optional — the system falls back to `.env` values when not configured.

---

## Install Vault

```bash
wget -O - https://apt.releases.hashicorp.com/gpg | sudo gpg --dearmor -o /usr/share/keyrings/hashicorp-archive-keyring.gpg
echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/hashicorp-archive-keyring.gpg] https://apt.releases.hashicorp.com $(grep -oP '(?<=UBUNTU_CODENAME=).*' /etc/os-release || lsb_release -cs) main" | sudo tee /etc/apt/sources.list.d/hashicorp.list
sudo apt update && sudo apt install vault
```

## Start Vault (dev mode — lab only)

```bash
vault server -dev -dev-root-token-id="dev-root-token" &
export VAULT_ADDR='http://127.0.0.1:8200'
export VAULT_TOKEN='dev-root-token'
```

> For production: use persistent storage backend + AppRole auth + audit logging.

## Store Secrets

```bash
vault kv put secret/ainoc/router username=<router_username> password=<router_password>
vault kv put secret/ainoc/jira api_token=<jira_api_token>
vault kv put secret/ainoc/discord bot_token=<discord_bot_token>
```

## Verify

```bash
vault kv get secret/ainoc/router
vault kv get secret/ainoc/jira
vault kv get secret/ainoc/discord
```

## Configure aiNOC

Add to `.env`:
```
VAULT_ADDR=http://127.0.0.1:8200
VAULT_TOKEN=dev-root-token
```

When these are set, `core/vault.py` reads secrets from Vault instead of `.env`.
If Vault is unreachable, it falls back to `ROUTER_USERNAME`/`ROUTER_PASSWORD`/etc. in `.env`.

## Vault Paths Reference

| Path | Keys | Used by |
|------|------|---------|
| `secret/ainoc/router` | `username`, `password` | `core/settings.py` |
| `secret/ainoc/jira` | `api_token` | `core/jira_client.py` |
| `secret/ainoc/discord` | `bot_token` | `core/discord_approval.py` |

---

## Production: Boot Persistence

The `vault` apt package installs a systemd unit. Enable it so Vault starts automatically on every boot:

```bash
sudo systemctl enable vault
sudo systemctl start vault
```

Verify:
```bash
systemctl is-enabled vault   # should output: enabled
systemctl status vault        # should show: active (running)
```

> **Dev mode vs production**: `vault server -dev` (shown above) is ephemeral — all secrets are lost on restart and it binds to localhost only. For production, configure `/etc/vault.d/vault.hcl` with a persistent storage backend (e.g., `storage "file" { path = "/opt/vault/data" }`) and a proper listener with TLS. The systemd unit then starts the production server, not dev mode.

---

## Production: Initialization (one-time setup)

The `vault` apt package starts Vault in production mode (using `/etc/vault.d/vault.hcl`). Unlike dev mode, production Vault requires a one-time initialization and must be unsealed after every restart.

### Step 1 — Switch to HTTP listener (lab)

The default `vault.hcl` uses HTTPS with a self-signed cert that won't work with `http://localhost:8200`. Edit `/etc/vault.d/vault.hcl` to use the HTTP listener instead:

```hcl
# Uncomment this block:
listener "tcp" {
  address = "127.0.0.1:8200"
  tls_disable = 1
}

# Comment out the HTTPS block (tls_cert_file / tls_key_file)
```

Then restart:
```bash
sudo systemctl restart vault
export VAULT_ADDR='http://127.0.0.1:8200'
```

### Step 2 — Initialize Vault (run once, ever)

```bash
vault operator init -key-shares=1 -key-threshold=1
```

**Save the output** — it contains the unseal key and root token. These are shown only once.
For production, use more key shares (e.g., `-key-shares=5 -key-threshold=3`).

### Step 3 — Unseal Vault

```bash
vault operator unseal <unseal-key>
```

Vault must be unsealed after every restart. Verify:
```bash
vault status   # Sealed: false
```

### Step 4 — Enable KV engine and store secrets

```bash
export VAULT_TOKEN='<root-token-from-init>'
vault secrets enable -path=secret kv-v2
vault kv put secret/ainoc/router username=<router_username> password=<router_password>
vault kv put secret/ainoc/jira api_token=<jira_api_token>
vault kv put secret/ainoc/discord bot_token=<discord_bot_token>
```

### Step 5 — Update `.env`

```
VAULT_ADDR=http://127.0.0.1:8200
VAULT_TOKEN=<root-token-from-init>
```

> **Note**: Dev mode secrets are ephemeral and are NOT carried over to production mode. If you previously used `vault server -dev`, you must re-store all secrets in the production instance.
>
> **Unseal on reboot**: Production Vault is sealed on every restart by design (the master key is never persisted to disk). You must run `vault operator unseal` after each reboot before aiNOC can read secrets. Automation options: cloud KMS auto-unseal, transit auto-unseal, or a local unseal script (less secure).

---

## Troubleshooting

### Vault running but inaccessible (browser / curl returns nothing)

**Symptom**: `systemctl status vault` shows active, but `http://localhost:8200` is unreachable. `vault status` fails with TLS/certificate error.

**Cause**: The default `/etc/vault.d/vault.hcl` configures an HTTPS listener on `0.0.0.0:8200` with a self-signed TLS cert that lacks localhost IP SANs. The `.env` file uses `http://` (not `https://`) — protocol mismatch. Also, the production Vault requires initialization before it can serve any requests.

**Fix**: Switch to the HTTP listener (see "Production: Initialization → Step 1" above) and initialize Vault (`vault operator init`).

### Vault sealed after reboot

**Symptom**: `vault status` shows `Sealed: true`. aiNOC falls back to `.env` credentials.

**Cause**: By design — production Vault seals itself on restart. The unseal key is never written to disk.

**Fix**: `vault operator unseal <unseal-key>` (requires the key saved during `vault operator init`).

### aiNOC shows .env after Vault is restored

If Vault is brought back up while the watcher is running, the credential_source probe in `core/vault.py` will pick up the live Vault on the next call. However, if the watcher's cached `_VAULT_FAILED` sentinel is already set from a failed attempt during startup, restart the watcher:
```bash
sudo systemctl restart oncall-watcher
```

### Dev mode secrets not available in production

Dev mode (`vault server -dev`) stores everything in RAM — all secrets are lost when the process exits. After switching to production mode, re-run all `vault kv put` commands to re-store the secrets.
