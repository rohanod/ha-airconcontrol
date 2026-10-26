#!/usr/bin/env python3
"""Capture dry (dehumidify) mode packets from the remote via a Broadlink RM4C, with a cool baseline from the same session."""
import argparse
import base64
import json
import struct
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

try:
    import broadlink
    from broadlink import exceptions as broadlink_exceptions
except ImportError:
    print("Missing dependency: pip install broadlink", file=sys.stderr)
    raise SystemExit(1)

from broadlink_decode import decode_broadlink_ir

DEFAULT_OUTPUT = "dry_signals.json"
DEFAULT_HOST = "10.24.6.65"
# Dry mode on the remote only exposes swing (no temp/fan), so: cool baseline, dry swing off/on, and off-from-dry.
# "start" is the remote state before Enter; "press" is the one button pressed after it (RM4C keeps only the first packet).
CAPTURE_PLAN = [
    {"name": "cool_22_high", "command": "set", "mode": "cool", "temperature_c": 22, "power": "high", "swing": "off",
     "start": "COOL 23C fan high, swing off", "press": "TEMP DOWN (to 22C)"},
    {"name": "dry_swing_off", "command": "set", "mode": "dry", "swing": "off",
     "start": "DRY, swing on", "press": "SWING (turns it off)"},
    {"name": "dry_swing_on", "command": "set", "mode": "dry", "swing": "on",
     "start": "DRY, swing off", "press": "SWING (turns it on)"},
    {"name": "off_from_dry", "command": "power_off", "mode": "dry", "swing": "off",
     "start": "DRY, swing off, AC on", "press": "POWER (turns it off)"},
]


def mac_to_bytes(mac):
    compact = mac.replace(":", "").replace("-", "").strip()
    if len(compact) != 12:
        raise ValueError("MAC must be 12 hex chars")
    return bytes.fromhex(compact)


def connect_device(args):
    if args.mac:
        dev = broadlink.gendevice(args.devtype, (args.host, 80), mac_to_bytes(args.mac))
    else:
        dev = broadlink.hello(args.host, timeout=args.discovery_timeout)
    if not dev.auth():
        raise RuntimeError("Broadlink auth failed")
    return dev


def _manual_check_data(device):
    mro = {c.__name__.lower() for c in type(device).__mro__}
    if {"rm4pro", "rm4mini", "rmminib"} & mro:
        resp = device.send_packet(0x6A, struct.pack("<HI", 4, 0x04))
        code = struct.unpack("h", resp[0x22:0x24])[0]
        if code not in (0, -5):
            broadlink_exceptions.check_error(resp[0x22:0x24])
        payload = device.decrypt(resp[0x38:])
        plen = struct.unpack("<H", payload[:0x2])[0]
        return payload[0x6 : plen + 2]
    resp = device.send_packet(0x6A, struct.pack("<I", 0x04))
    code = struct.unpack("h", resp[0x22:0x24])[0]
    if code not in (0, -5):
        broadlink_exceptions.check_error(resp[0x22:0x24])
    return device.decrypt(resp[0x38:])[0x4:]


def check_data(dev):
    try:
        return dev.check_data()
    except Exception as e:
        if getattr(e, "errno", None) != -5:
            raise
        return _manual_check_data(dev)


def learn_packet(dev, timeout, sig):
    input(f"\n>>> [{sig['name']}] Set remote to {sig['start']}, then press Enter to start learning...")
    dev.enter_learning()
    print(f"  -> Press {sig['press']} ONCE NOW, pointing at the RM4C...")
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        pkt = check_data(dev)
        if pkt:
            return pkt
        time.sleep(0.5)
    raise TimeoutError(f"No packet in {timeout}s")


def build_entry(pkt, sig):
    code = base64.b64encode(pkt).decode("ascii")
    entry = {**sig, "learned_at": datetime.now(timezone.utc).isoformat(), "broadlink_base64": code}
    try:
        dec = decode_broadlink_ir(sig["name"], code)
        entry["decoded"] = {
            "logical_bytes_hex": dec["logical_bytes_hex"],
            "data_bytes_lsb_hex": dec["data_bytes_lsb_hex"],
            "valid": all(p["valid"] for p in dec["inverse_pairs"]),
        }
    except Exception as err:
        entry["decode_error"] = str(err)
    return entry


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--output", default=DEFAULT_OUTPUT)
    p.add_argument("--host", default=DEFAULT_HOST)
    p.add_argument("--mac")
    p.add_argument("--devtype", type=lambda v: int(v, 0), default=0x5F36)
    p.add_argument("--discovery-timeout", type=float, default=5)
    p.add_argument("--learn-timeout", type=float, default=30)
    args = p.parse_args()

    out = Path(args.output)
    entries = json.loads(out.read_text())["signals"] if out.exists() else []
    dev = connect_device(args)
    for sig in CAPTURE_PLAN:
        if any(e["name"] == sig["name"] and e.get("decoded", {}).get("valid") for e in entries):
            print(f"Already have a valid {sig['name']}, skipping (remove it from {out} to recapture)")
            continue
        entry = build_entry(learn_packet(dev, args.learn_timeout, sig), sig)
        entries = [e for e in entries if e["name"] != sig["name"]] + [entry]
        print(f"Learned {sig['name']}: {entry.get('decoded') or entry.get('decode_error')}")
        out.write_text(json.dumps({"schema": "rm4c-dry-v1", "updated_at": datetime.now(timezone.utc).isoformat(), "signals": entries}, indent=2) + "\n")
    print(f"\nDone. Now run: python3 decode_dry.py {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
