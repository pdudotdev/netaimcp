"""NetBox device inventory loader.

Fetches device inventory from a NetBox instance and maps it to the schema
expected by core/inventory.py. Falls back gracefully to NETWORK.json if
NetBox is not configured (NETBOX_URL/NETBOX_TOKEN absent) or unreachable.

NetBox custom fields required on the Device model:
  transport  — 'asyncssh' or 'restconf'
  cli_style  — 'ios'

The 'location' field is read from device.site.name.
"""
import logging
import os

from dotenv import load_dotenv

load_dotenv()

log = logging.getLogger("ainoc.netbox")


def load_devices() -> dict | None:
    """Load device inventory from NetBox.

    Returns a dict matching the NETWORK.json schema:
        {device_name: {host, platform, transport, cli_style, location}}

    Returns None if NetBox is not configured, unreachable, or returns no devices,
    so the caller can fall back to NETWORK.json.
    """
    url = os.getenv("NETBOX_URL", "").strip()
    token = os.getenv("NETBOX_TOKEN", "").strip()

    if not url or not token:
        return None

    try:
        import pynetbox
        nb = pynetbox.api(url, token=token)
        nb.http_session.timeout = (5, 15)  # (connect_timeout, read_timeout) in seconds
        raw_devices = list(nb.dcim.devices.all())
    except Exception as exc:
        log.warning("NetBox unavailable: %s — falling back to NETWORK.json", exc)
        return None

    if not raw_devices:
        log.warning("NetBox returned no devices — falling back to NETWORK.json")
        return None

    devices: dict = {}
    for dev in raw_devices:
        name = dev.name
        if not name:
            continue

        # primary_ip comes back as an IPAddress object with .address = "x.x.x.x/mask"
        if not dev.primary_ip:
            log.warning("NetBox device %s has no primary IP — skipping", name)
            continue
        host = dev.primary_ip.address.split("/")[0]

        platform = dev.platform.slug if dev.platform else ""
        transport = (dev.custom_fields or {}).get("transport", "")
        cli_style = (dev.custom_fields or {}).get("cli_style", "")
        location = dev.site.name if dev.site else ""

        if not platform or not transport or not cli_style:
            log.warning(
                "NetBox device %s missing required fields "
                "(platform=%r, transport=%r, cli_style=%r) — skipping",
                name, platform, transport, cli_style,
            )
            continue

        devices[name] = {
            "host":      host,
            "platform":  platform,
            "transport": transport,
            "cli_style": cli_style,
            "location":  location,
        }

    if not devices:
        log.warning("NetBox: no valid devices after mapping — falling back to NETWORK.json")
        return None

    log.info("Loaded %d device(s) from NetBox", len(devices))
    return devices
