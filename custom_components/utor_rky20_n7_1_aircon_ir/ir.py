"""IR packet encoder for the supported air conditioner cool-mode protocol."""

from __future__ import annotations

import base64

COMMAND_POWER_OFF = "power_off"
COMMAND_SET = "set"


def logical_bytes(command: str, temperature: int, power: str) -> list[int]:
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

    return [0xFF, 0xFE, state, command_byte, encoded_temperature, 0x5A]


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


def encode_broadlink_base64(command: str, temperature: int, power: str) -> str:
    """Return a Home Assistant Broadlink remote b64 command string."""
    packet = encode_broadlink_packet(logical_bytes(command, temperature, power))
    return f"b64:{base64.b64encode(packet).decode('ascii')}"
