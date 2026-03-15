"""Device inventory — loads from NetBox (if configured) or NETWORK.json as fallback.

Exposes the 'devices' dict: {name: {host, platform, transport, cli_style, location}}
All tools that need to look up a device by name import 'devices' from here.
"""
import json
import logging
import os

from core.netbox import load_devices

_INVENTORY_FILE = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "inventory", "NETWORK.json"
)
_log = logging.getLogger("ainoc.inventory")


def _load_json_fallback() -> dict:
    if not os.path.exists(_INVENTORY_FILE):
        raise RuntimeError(f"Inventory file not found: {_INVENTORY_FILE}")
    with open(_INVENTORY_FILE) as f:
        return json.load(f)


_netbox_result = load_devices()
if _netbox_result:
    devices: dict = _netbox_result
    inventory_source: str = "NetBox"
    _log.info("Inventory: loaded %d device(s) from NetBox", len(devices))
else:
    devices: dict = _load_json_fallback()
    inventory_source: str = "NETWORK.json"
    _log.info("Inventory: loaded %d device(s) from NETWORK.json (NetBox not available)", len(devices))
