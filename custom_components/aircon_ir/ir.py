"""IR encoder for UTOR-RKY20-N7-1 — Home Assistant native infrared only."""

from __future__ import annotations

import abc

try:
    from infrared_protocols.commands import Command as InfraredCommand
except ImportError:

    class InfraredCommand(abc.ABC):  # type: ignore[no-redef]
        def __init__(self, *, modulation: int, repeat_count: int = 0) -> None:
            self.modulation = modulation
            self.repeat_count = repeat_count

        @abc.abstractmethod
        def get_raw_timings(self) -> list[int]:
            ...

COMMAND_POWER_OFF = "power_off"
COMMAND_SET = "set"

MODE_COOL = "cool"
MODE_DRY = "dry"

SWING_BYTE = 3
SWING_BIT = 0x10

# Dry has no temperature or fan on the remote: it sends this fixed temperature byte and low fan.
DRY_TEMPERATURE_BYTE = 0xBC

_BROADLINK_TICK_US = 269 / 8192 * 1000


def logical_bytes(
    command: str, temperature: int, power: str, swing: str = "off", mode: str = MODE_COOL
) -> list[int]:
    if mode == MODE_DRY:
        encoded_temperature = DRY_TEMPERATURE_BYTE
        power = "low"
    elif mode == MODE_COOL:
        encoded_temperature = 0xEF - temperature
        if not 0 <= encoded_temperature <= 0xFF:
            raise ValueError("temperature is outside the encodable range")
    else:
        raise ValueError("mode must be cool or dry")

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
    output: list[int] = []
    for byte in logical:
        output.extend([byte, byte ^ 0xFF])
    return output


def _ticks(ticks: int) -> int:
    return int(round(ticks * _BROADLINK_TICK_US))


def infrared_timings(logical: list[int]) -> list[int]:
    seq: list[int] = []
    seq.append(_ticks(0xC6))
    seq.append(-_ticks(0xF2))
    for byte in wire_bytes(logical):
        for bit_index in range(8):
            bit = (byte >> bit_index) & 1
            seq.append(_ticks(0x12))
            seq.append(-_ticks(0x34 if bit else 0x11))
    seq.append(_ticks(0x12))
    seq.append(-_ticks(0xF2))
    seq.append(_ticks(0x12))
    return seq


class UtorCommand(InfraredCommand):
    def __init__(
        self,
        command: str,
        temperature: int,
        power: str,
        swing: str = "off",
        mode: str = MODE_COOL,
        *,
        modulation: int = 38000,
        repeat_count: int = 0,
    ) -> None:
        super().__init__(modulation=modulation, repeat_count=repeat_count)
        self._logical = logical_bytes(command, temperature, power, swing, mode)
        self._timings = infrared_timings(self._logical)

    def get_raw_timings(self) -> list[int]:
        return list(self._timings)


def make_utor_command(
    command: str, temperature: int, power: str, swing: str = "off", mode: str = MODE_COOL
) -> UtorCommand:
    return UtorCommand(command, temperature, power, swing, mode)
