#!/usr/bin/env python3
"""Live reachability dashboard — pings all lab devices every 5 seconds."""

import asyncio
import json
import os
from datetime import datetime
from pathlib import Path

INVENTORY = Path(__file__).resolve().parent.parent / "inventory" / "NETWORK.json"
REFRESH = 5  # seconds

ANSI_RESET  = "\033[0m"
ANSI_GREEN  = "\033[32m"
ANSI_RED    = "\033[31m"
ANSI_BOLD   = "\033[1m"
ANSI_CLEAR  = "\033[2J\033[H"


async def ping(ip: str) -> bool:
    proc = await asyncio.create_subprocess_exec(
        "ping", "-c", "1", "-W", "1", ip,
        stdout=asyncio.subprocess.DEVNULL,
        stderr=asyncio.subprocess.DEVNULL,
    )
    await proc.wait()
    return proc.returncode == 0


async def ping_all(devices: list[dict]) -> dict[str, bool]:
    results = await asyncio.gather(*(ping(d["host"]) for d in devices))
    return {d["name"]: ok for d, ok in zip(devices, results)}


def load_devices() -> list[dict]:
    with open(INVENTORY) as f:
        inv = json.load(f)
    devices = []
    for name, meta in inv.items():
        devices.append({
            "name": name,
            "host": meta.get("host", ""),
            "location": meta.get("location", ""),
        })
    return sorted(devices, key=lambda d: d["name"])


def render(devices: list[dict], status: dict[str, bool], ts: str) -> None:
    col_name = max(len(d["name"]) for d in devices)
    col_ip   = max(len(d["host"]) for d in devices)
    col_loc  = max(len(d["location"]) for d in devices)
    col_st   = 6

    w = col_name + col_ip + col_loc + col_st + 13  # separators
    sep = "+" + "-" * (col_name + 2) + "+" + "-" * (col_ip + 2) + \
          "+" + "-" * (col_loc + 2) + "+" + "-" * (col_st + 2) + "+"

    up   = sum(1 for v in status.values() if v)
    down = len(status) - up

    print(ANSI_CLEAR, end="")
    print(f"{ANSI_BOLD}aiNOC — Reachability Dashboard{ANSI_RESET}  "
          f"Last refresh: {ts}  "
          f"{ANSI_GREEN}{up} UP{ANSI_RESET}  {ANSI_RED}{down} DOWN{ANSI_RESET}")
    print()
    print(sep)
    print(f"| {ANSI_BOLD}{'Dev.':<{col_name}}{ANSI_RESET} "
          f"| {ANSI_BOLD}{'IP':<{col_ip}}{ANSI_RESET} "
          f"| {ANSI_BOLD}{'Location':<{col_loc}}{ANSI_RESET} "
          f"| {ANSI_BOLD}{'Status':<{col_st}}{ANSI_RESET} |")
    print(sep)
    for d in devices:
        ok = status.get(d["name"])
        if ok is None:
            st_str = "  ----"
        elif ok:
            st_str = f"{ANSI_GREEN}  UP  {ANSI_RESET}"
        else:
            st_str = f"{ANSI_RED}  DOWN{ANSI_RESET}"
        print(f"| {d['name']:<{col_name}} | {d['host']:<{col_ip}} "
              f"| {d['location']:<{col_loc}} | {st_str} |")
    print(sep)
    print(f"\n  Ctrl+C to exit  |  refresh every {REFRESH}s")


async def main() -> None:
    devices = load_devices()
    status: dict[str, bool] = {}
    print(f"{ANSI_CLEAR}Loading inventory ({len(devices)} devices)…")

    try:
        while True:
            status = await ping_all(devices)
            ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            render(devices, status, ts)
            await asyncio.sleep(REFRESH)
    except KeyboardInterrupt:
        print("\nDashboard stopped.")


if __name__ == "__main__":
    asyncio.run(main())
