#!/usr/bin/env python3
"""Decode dry_signals.json and diff each capture's logical bytes against the cool baseline and the integration's own encoder."""
import json
import sys
from pathlib import Path

from broadlink_decode import decode_broadlink_ir

BASELINE = "cool_22_high"


def logical(sig):
    d = decode_broadlink_ir(sig["name"], sig["broadlink_base64"])
    valid = all(p["valid"] for p in d["inverse_pairs"]) and len(d["inverse_pairs"]) == 6
    return [p["value"] for p in d["inverse_pairs"]], valid


def diff(a, b):
    return [(i, x, y, x ^ y) for i, (x, y) in enumerate(zip(a, b)) if x != y]


def fmt(bs):
    return " ".join(f"{b:02X}" for b in bs)


def report(signals):
    lines = []
    decoded = {s["name"]: logical(s) for s in signals}
    for name, (bs, valid) in decoded.items():
        lines.append(f"{name:22} {fmt(bs)}  {'valid' if valid else 'INVALID (recapture)'}")
    if BASELINE not in decoded:
        lines.append(f"\nMissing {BASELINE}; can't diff.")
        return lines
    base = decoded[BASELINE][0]
    lines.append(f"\nDiffs vs {BASELINE}:")
    for name, (bs, _) in decoded.items():
        if name == BASELINE:
            continue
        changes = ", ".join(f"byte{i} {x:02X}->{y:02X} xor{z:02X}" for i, x, y, z in diff(base, bs)) or "identical"
        lines.append(f"  {name:22} {changes}")
    return lines


def main():
    src = Path(sys.argv[1] if len(sys.argv) > 1 else "dry_signals.json")
    print("\n".join(report(json.loads(src.read_text())["signals"])))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
