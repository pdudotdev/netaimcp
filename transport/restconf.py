"""RESTCONF executor: httpx AsyncClient, GET for reads.

Used by Cisco c8000v devices (C1C, C2C, E1C, E2C, X1C) as the primary transport tier.
Paired with SSH (fallback) in the 2-tier ActionChain.

Action format (from ios_restconf platform map):
  {"url": "Cisco-IOS-XE-ospf-oper:ospf-oper-data", "method": "GET"}
"""
import logging

try:
    import httpx
    _HTTPX_AVAILABLE = True
except ImportError:
    _HTTPX_AVAILABLE = False

from core.settings import USERNAME, PASSWORD, RESTCONF_PORT, RESTCONF_VERIFY_TLS

log = logging.getLogger("ainoc.transport.restconf")

_RESTCONF_BASE = "/restconf/data/"
_HEADERS = {
    "Accept": "application/yang-data+json",
    "Content-Type": "application/yang-data+json",
}


async def execute_restconf(device: dict, action: dict) -> dict:
    """Execute a RESTCONF read operation.

    action format: {"url": "module:container/path", "method": "GET"}
    Returns the parsed JSON dict or {"error": "..."} on failure.
    """
    if not _HTTPX_AVAILABLE:
        return {"error": "httpx not installed. Run: pip install httpx"}

    host = device["host"]
    url = f"https://{host}:{RESTCONF_PORT}{_RESTCONF_BASE}{action['url']}"

    try:
        async with httpx.AsyncClient(verify=RESTCONF_VERIFY_TLS, timeout=30.0) as client:
            log.debug("RESTCONF → %s: GET %s", host, url)
            response = await client.get(url, headers=_HEADERS, auth=(USERNAME, PASSWORD))

        if response.status_code == 200:
            return response.json()
        elif response.status_code == 204:
            return {}  # No content — feature not configured on device
        elif response.status_code == 404:
            return {"error": f"RESTCONF 404: resource not found: {action['url']}"}
        else:
            return {"error": f"RESTCONF HTTP {response.status_code}: {response.text[:200]}"}

    except Exception as e:
        log.error("RESTCONF execute error %s: %s", device["host"], e)
        return {"error": str(e)}
