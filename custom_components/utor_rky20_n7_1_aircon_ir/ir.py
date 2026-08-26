"""IR packet encoder for the supported air conditioner cool-mode protocol.

Supports both legacy Broadlink ``remote.send_command`` (b64 packet) and
official Home Assistant 2026.4 ``infrared`` entity platform (raw timings).
"""

from __future__ import annotations

import abc
import base64

try:  # HA core provides infrared-protocols; fallback shim for tests/offline
    from infrared_protocols.commands import Command as InfraredCommand
except ImportError:  # ponytail: shim so custom component loads without dep

    class InfraredCommand(abc.ABC):  # type: ignore[no-redef]
        def __init__(self, *, modulation: int, repeat_count: int = 0) -> None:
            self.modulation = modulation
            self.repeat_count = repeat_count

        @abc.abstractmethod
        def get_raw_timings(self) -> list[int]:
            ...

COMMAND_POWER_OFF = "power_off"
COMMAND_SET = "set"

# swing confirmed 2026-05-28 via learn_swing at 22C high: byte3 0x10 (C5->D5)
SWING_BYTE = 3
SWING_BIT = 0x10

_BROADLINK_TICK_US = 269 / 8192 * 1000  # ~32.84 µs per Broadlink tick


def logical_bytes(command: str, temperature: int, power: str, swing: str = "off") -> list[int]:
    """Return the six logical bytes for a command."""
    encoded_temperature = 0xEF - temperature
    if not 0 <= encoded_temperature <= 0xFF:
        raise ValueError("temperature is outside the encodable range")

    if command == COMMAND_SET:
        state = 0xFD
        command_byte = 0x85
    elif command == COMMAND_POWER_OFF:
        state = 0xFF
        command_byte = 0x87
    else:
        raise ValueError("command must be set or power_off")

    if power == "high":
        command_byte |= 0x40
    elif power != "low":
        raise ValueError("power must be low or high")

    logical = [0xFF, 0xFE, state, command_byte, encoded_temperature, 0x5A]
    if swing == "on":
        logical[SWING_BYTE] |= SWING_BIT
    elif swing != "off":
        raise ValueError("swing must be on or off")
    return logical


def wire_bytes(logical: list[int]) -> list[int]:
    """Duplicate each logical byte with its bitwise inverse."""
    output: list[int] = []
    for byte in logical:
        output.extend([byte, byte ^ 0xFF])
    return output


def encode_broadlink_packet(logical: list[int]) -> bytes:
    """Encode logical bytes as a Broadlink learned IR packet."""
    packet = bytearray([0x26, 0x00, 0xC8, 0x00])
    durations = bytearray([0xC6, 0xF2])

    for byte in wire_bytes(logical):
        for bit_index in range(8):
            bit = (byte >> bit_index) & 1
            durations.extend([0x12, 0x34 if bit else 0x11])

    durations.extend([0x12, 0xF2, 0x12, 0x00])
    packet.extend(durations)
    packet.extend([0x0D, 0x05])
    return bytes(packet)


def encode_broadlink_base64(command: str, temperature: int, power: str, swing: str = "off") -> str:
    """Return a Home Assistant Broadlink remote b64 command string."""
    packet = encode_broadlink_packet(logical_bytes(command, temperature, power, swing))
    return f"b64:{base64.b64encode(packet).decode('ascii')}"


# -- Official infrared entity platform (HA 2026.4+) --


def _ticks(ticks: int) -> int:
    return int(round(ticks * _BROADLINK_TICK_US))


def infrared_timings(logical: list[int]) -> list[int]:
    """Return signed microsecond timings (mark +, space -) for infrared emitter."""
    # durations as in Broadlink packet but as signed timings
    seq: list[int] = []
    # lead
    seq.append(_ticks(0xC6))
    seq.append(-_ticks(0xF2))
    for byte in wire_bytes(logical):
        for bit_index in range(8):
            bit = (byte >> bit_index) & 1
            seq.append(_ticks(0x12))  # mark
            seq.append(-_ticks(0x34 if bit else 0x11))  # space
    # trailer: mark, long space, mark (no trailing space)
    seq.append(_ticks(0x12))
    seq.append(-_ticks(0xF2))
    seq.append(_ticks(0x12))
    return seq


class UtorCommand(InfraredCommand):
    """HA infrared-protocols Command for UTOR-RKY20-N7-1."""

    def __init__(
        self,
        command: str,
        temperature: int,
        power: str,
        swing: str = "off",
        *,
        modulation: int = 38000,
        repeat_count: int = 0,
    ) -> None:
        super().__init__(modulation=modulation, repeat_count=repeat_count)
        self._logical = logical_bytes(command, temperature, power, swing)
        self._timings = infrared_timings(self._logical)

    def get_raw_timings(self) -> list[int]:
        base = list(self._timings)
        # handle repeats as gap + repeat of base without lead? Keep simple: HA helper handles repeat via repeat_count gap.
        # For ponytail: repeats via manual gap extension if needed.
        if self.repeat_count:
            gap = 41000
            out = list(base)
            for i in range(self.repeat_count):
                out.append(-gap)
                out.extend(base)
                gap = 96000
            return out
        return base


def make_utor_command(command: str, temperature: int, power: str, swing: str = "off") -> UtorCommand:
    return UtorCommand(command, temperature, power, swing)
