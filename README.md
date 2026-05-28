# Go-On UTOR-RKY20-N7-1 Aircon IR

Home Assistant custom climate integration for a Go-On UTOR-RKY20-N7-1 cool-only air conditioner controlled by generated Broadlink IR commands.

This integration does not import or use the Python `broadlink` package. It sends generated Broadlink learned-code payloads through Home Assistant's existing `remote.send_command` service, so it works with the proper Broadlink remote entity created by Home Assistant.

## Features

- Climate entity with `cool` and `off` HVAC modes.
- Target temperature commands generated from `0xEF - temperature`.
- Fan mode used as low/high power mode.
- Stateful off command using the last restored or selected temperature and fan mode.
- HACS-compatible custom repository layout.

## Installation

### HACS custom repository

1. Add this repository to HACS as a custom repository.
2. Choose category `Integration`.
3. Install `Go-On UTOR-RKY20-N7-1 Aircon IR`.
4. Restart Home Assistant.

### Manual

Copy `custom_components/utor_rky20_n7_1_aircon_ir` into your Home Assistant `custom_components` directory and restart Home Assistant.

## Configuration

Before adding this integration, configure your Broadlink device in Home Assistant so you have a `remote.*` entity, for example `remote.rm4c_pro`.

Then go to:

`Settings` -> `Devices & services` -> `Add integration` -> `Go-On UTOR-RKY20-N7-1 Aircon IR`

Choose the Broadlink remote entity and defaults:

- Default temperature: used after first setup and as the off context until state is restored.
- Default fan mode: `low` or `high`.
- Repeats: number of times to send each generated command.

## Protocol

Logical command bytes:

```text
[0xFF, 0xFE, state, command, temperature, 0x5A]
```

Field values:

```text
state:
  0xFD = cool set
  0xFF = power off

command:
  0x85 = low set
  0xC5 = high set
  0x87 = low power off
  0xC7 = high power off

temperature:
  encoded_temp = 0xEF - temperature_celsius
```

Each logical byte is transmitted followed by its bitwise inverse. The final packet is encoded as a Broadlink learned IR container and sent to Home Assistant as a `b64:` command.

## Notes

The off command is stateful. Home Assistant restores the previous climate state after restart when possible. If no previous state exists, the integration uses the configured default temperature and fan mode for `off`.
