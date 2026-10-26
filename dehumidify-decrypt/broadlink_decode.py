#!/usr/bin/env python3
import argparse
import base64
import json

BROADLINK_TICK_US = 269 / 8192 * 1000


def classify_bit(mark, space):
    if mark > 100 or space > 100 or space == 0:
        return None
    return 1 if space > 30 else 0


def decode_broadlink_ir(name, code):
    raw = base64.b64decode(code)
    if len(raw) < 6 or raw[0] != 0x26:
        raise ValueError(f"{name}: not a Broadlink learned IR packet")

    duration_bytes = list(raw[4:-2])
    pairs = list(zip(duration_bytes[::2], duration_bytes[1::2]))

    bits = []
    events = []
    for index, (mark, space) in enumerate(pairs):
        event = {
            "index": index,
            "mark": mark,
            "space": space,
            "mark_us": round(mark * BROADLINK_TICK_US),
            "space_us": round(space * BROADLINK_TICK_US),
        }
        bit = classify_bit(mark, space)
        if bit is not None:
            event["bit"] = bit
            bits.append(bit)
        events.append(event)

    # For these samples, pair 0 is a lead-in and the final two pairs are gap/stop.
    data_bits = [classify_bit(*pair) for pair in pairs[1:97]]
    data_bits = [bit for bit in data_bits if bit is not None]
    bit_string = "".join(str(bit) for bit in data_bits)
    lsb_bytes = [
        int("".join(str(bit) for bit in data_bits[i : i + 8][::-1]), 2)
        for i in range(0, len(data_bits), 8)
    ]

    inverse_pairs = [
        {
            "value": lsb_bytes[i],
            "inverse": lsb_bytes[i + 1],
            "valid": (lsb_bytes[i] ^ lsb_bytes[i + 1]) == 0xFF,
        }
        for i in range(0, len(lsb_bytes) - 1, 2)
    ]

    return {
        "name": name,
        "raw_length": len(raw),
        "header_hex": raw[:4].hex(" "),
        "terminator_hex": raw[-2:].hex(" "),
        "lead_in_us": events[0] if events else None,
        "data_bits_lsb_first": bit_string,
        "data_bytes_lsb_hex": [f"{byte:02X}" for byte in lsb_bytes],
        "logical_bytes_hex": [f"{pair['value']:02X}" for pair in inverse_pairs],
        "inverse_pairs": inverse_pairs,
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("name")
    parser.add_argument("code")
    args = parser.parse_args()
    print(json.dumps(decode_broadlink_ir(args.name, args.code), indent=2))


if __name__ == "__main__":
    main()
