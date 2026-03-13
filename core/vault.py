"""HashiCorp Vault client — reads secrets from KV v2 engine with env var fallback.

Falls back to os.getenv() if Vault is not configured (VAULT_ADDR/VAULT_TOKEN absent)
or if Vault is unreachable. This makes Vault fully optional — the system works without
it by reading secrets from .env as before.

Vault paths used by aiNOC:
  ainoc/router   → username, password
  ainoc/jira     → api_token
  ainoc/discord  → bot_token
"""
import logging
import os

log = logging.getLogger("ainoc.vault")

# Module-level cache: path → {key: value} dict from Vault KV data
# _VAULT_FAILED is a sentinel for "Vault unreachable for this path" — distinct from an
# empty-but-valid secret dict. When set, env var fallback is still used on every call.
_VAULT_FAILED = object()
_cache: dict[str, object] = {}


def get_secret(path: str, key: str, fallback_env: str = "") -> str | None:
    """Read a secret from Vault KV v2, falling back to an env var if Vault is unavailable.

    Args:
        path:         KV path without the 'secret/' prefix, e.g. 'ainoc/router'
        key:          Key within the KV secret, e.g. 'username'
        fallback_env: Env var name to use when Vault is not configured or unreachable

    Returns:
        Secret value string, or None if neither Vault nor the fallback env var has a value.
    """
    vault_addr = os.getenv("VAULT_ADDR", "").strip()
    vault_token = os.getenv("VAULT_TOKEN", "").strip()

    if not vault_addr or not vault_token:
        log.debug("Vault not configured — using env var %s", fallback_env)
        return os.getenv(fallback_env) if fallback_env else None

    # Return from cache if already fetched this path
    if path in _cache:
        cached = _cache[path]
        if cached is _VAULT_FAILED:
            # Previous attempt failed — preserve env var fallback on every call
            return os.getenv(fallback_env) if fallback_env else None
        return cached.get(key)

    try:
        import hvac
        client = hvac.Client(url=vault_addr, token=vault_token)
        response = client.secrets.kv.v2.read_secret_version(
            path=path, mount_point="secret", raise_on_deleted_version=True
        )
        data: dict = response["data"]["data"]
        _cache[path] = data
        log.info("Vault: loaded secret path '%s'", path)
        return data.get(key)
    except Exception as exc:
        log.warning(
            "Vault unavailable (path=%s): %s — falling back to env var %s",
            path, exc, fallback_env or "(none)",
        )
        _cache[path] = _VAULT_FAILED  # sentinel: Vault unavailable, use env var fallback
        return os.getenv(fallback_env) if fallback_env else None
