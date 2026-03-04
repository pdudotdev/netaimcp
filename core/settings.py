"""Runtime configuration — credentials, TLS flags, and transport timeout constants.

Loaded once at import time. All transport modules import from here.
"""
import os
from dotenv import load_dotenv

load_dotenv()

USERNAME = os.getenv("ROUTER_USERNAME")
PASSWORD = os.getenv("ROUTER_PASSWORD")

if not USERNAME or not PASSWORD:
    raise RuntimeError("ROUTER_USERNAME and ROUTER_PASSWORD must be set in .env")

# TLS / SSH security settings — defaults are lab-safe; set to 'true' in .env for production.
VERIFY_TLS     = os.getenv("VERIFY_TLS",           "false").lower() == "true"
ROUTEROS_HTTPS = os.getenv("ROUTEROS_USE_HTTPS",   "false").lower() == "true"
SSH_STRICT_KEY = os.getenv("SSH_STRICT_HOST_KEY",  "false").lower() == "true"

# Scrapli SSH timeout (seconds) applied to all SSH connections.
SSH_TIMEOUT_TRANSPORT = 30
SSH_TIMEOUT_OPS       = 30

# SSH retry settings — applied to transient connection failures only.
SSH_RETRIES     = 2   # Max retry attempts after initial failure (3 total)
SSH_RETRY_DELAY = 2   # Seconds between retries
