#!/usr/bin/env python3
"""Check the integration's dry encoding against the captured remote packets in dry_signals.json."""
import json
import sys
from pathlib import Path

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE.parent / "custom_components" / "aircon_ir"))
from ir import COMMAND_POWER_OFF, COMMAND_SET, MODE_DRY, logical_bytes  # noqa: E402

from decode_dry import logical  # noqa: E402

signals = {s["name"]: s for s in json.loads((HERE / "dry_signals.json").read_text())["signals"]}
cases = {
    "dry_swing_off": logical_bytes(COMMAND_SET, 23, "high", "off", MODE_DRY),
    "dry_swing_on": logical_bytes(COMMAND_SET, 23, "high", "on", MODE_DRY),
    "off_from_dry": logical_bytes(COMMAND_POWER_OFF, 23, "high", "off", MODE_DRY),
}
for name, ours in cases.items():
    captured, valid = logical(signals[name])
    assert valid, name
    # ponytail: bytes 1-2 skipped; the remote puts the pressed button there, the integration keeps its FE FD/FF convention.
    assert ours[3:] == captured[3:], (name, ours, captured)
    assert ours[2] == captured[2] or name != "off_from_dry", (name, ours, captured)
print("dry encoding ok")
