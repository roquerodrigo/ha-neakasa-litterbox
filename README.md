# Neakasa Litterbox for Home Assistant

[![HACS Validate](https://github.com/roquerodrigo/ha-neakasa-litterbox/actions/workflows/validate.yml/badge.svg)](https://github.com/roquerodrigo/ha-neakasa-litterbox/actions/workflows/validate.yml)
[![Lint](https://github.com/roquerodrigo/ha-neakasa-litterbox/actions/workflows/lint.yml/badge.svg)](https://github.com/roquerodrigo/ha-neakasa-litterbox/actions/workflows/lint.yml)
[![CodeQL](https://github.com/roquerodrigo/ha-neakasa-litterbox/actions/workflows/codeql.yml/badge.svg)](https://github.com/roquerodrigo/ha-neakasa-litterbox/actions/workflows/codeql.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![hacs_badge](https://img.shields.io/badge/HACS-Custom-orange.svg)](https://github.com/hacs/integration)

Home Assistant integration for the [Neakasa M1](https://www.neakasa.com/) self-cleaning litter box. Talks to the Neakasa cloud through the [`neakasa-litterbox-sdk`](https://pypi.org/project/neakasa-litterbox-sdk/), so it works without LAN-side setup: one config entry per account exposes every litter box bound to it, plus a sub-device per cat profile registered in the Neakasa app.

The integration is **cloud push**: an MQTT status stream keeps state in real time, with a longer polling cadence as a safety net.

## Add to Home Assistant

[![Open your Home Assistant instance and open a repository inside the Home Assistant Community Store.](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=roquerodrigo&repository=ha-neakasa-litterbox&category=integration)

## Features

- Multiple litter boxes per account, discovered dynamically.
- Sub-device per cat (with `via_device` pointing at the litter box).
- Real-time updates via MQTT push, with polling fallback (default 10 min).
- Optimistic UI: switches, the calibration slider and buttons reflect new state immediately; the device confirms via push within seconds.
- Bucket-full sensor debounced: only flips on after **5 consecutive minutes** of the device reporting it full.
- Per-region (US / EU / AP) login, reauth and reconfigure flows.
- Translations: English and Brazilian Portuguese.

## Entities

Per litter box (`device_name → "Neakasa M1"`):

| Platform | Entity | Notes |
|---|---|---|
| `sensor` | Sand level | percentage |
| `sensor` | Visits today | count since local midnight |
| `sensor` | Last visit | timestamp of the most recent `CAT_VISIT` |
| `binary_sensor` | Needs cleaning | `device_class=problem` |
| `binary_sensor` | Waste bucket full | `device_class=problem`, debounced 5 min |
| `switch` | Auto clean | `EntityCategory.CONFIG` |
| `switch` | Auto level | `EntityCategory.CONFIG` |
| `switch` | Silent mode | `EntityCategory.CONFIG` |
| `switch` | Child lock | `EntityCategory.CONFIG` |
| `button` | Clean now | one-shot trigger |
| `button` | Level now | one-shot trigger |
| `number` | Sand calibration | 0–100 % in 10 % steps, `EntityCategory.CONFIG` |

Per cat (sub-device of the litter box):

| Platform | Entity | Notes |
|---|---|---|
| `sensor` | Weight | weight measured on the cat's most recent visit (kg) |
| `sensor` | Last visit | timestamp |
| `sensor` | Visits today | count since local midnight |

## Setup

1. Install via HACS (recommended) or copy `custom_components/neakasa_litterbox/` into your config.
2. **Settings → Devices & Services → Add Integration → Neakasa Litterbox**.
3. Enter the **email and password** you use in the Neakasa app and pick the **region** (US / EU / AP) that matches your account.
4. The integration logs in, opens the MQTT push stream and registers every device + cat the account has.

If the credentials become invalid later, Home Assistant raises the standard reauth dialog. To change the region or rotate the password without removing the entry, use the integration's three-dot menu → **Reconfigure**.

## Options

Via the integration's **⚙ Configure** dialog:

| Option | Default | Range | Effect |
|---|---|---|---|
| `Polling interval (seconds)` | 600 | ≥ 60 | How often the coordinator falls back to a poll. MQTT push usually delivers updates well before the next poll. |
| `Statistics lookback (days)` | 7 | 1–30 | Window used by the coordinator when pulling `ToiletRecord`s for per-cat last-visit / visits-today sensors. |

## How real-time updates work

The integration keeps two channels open against the Neakasa cloud:

- **MQTT push** (`cloud_push`): subscribes via `watch_status()` on the SDK and merges deltas into coordinator data as they arrive (sand percent, switch flips, presence flags…).
- **Polling fallback**: every `scan_interval` seconds the coordinator re-fetches `list_devices` + `get_status` + `list_cats` + `get_toilet_records` in parallel per device, so state stays correct even if the MQTT stream drops.

The MQTT client uses `tls_insecure=True` because Aliyun-fronted brokers don't always present a chain that the bundled Python OpenSSL trusts; the broker URL still uses TLS, only certificate validation is skipped on the push channel.

## Optimistic state

Switches, the sand-calibration slider and buttons run an **optimistic update**: after the SDK call returns, the integration patches the local `DeviceStatus` snapshot so the UI reflects the new state immediately. The MQTT push that follows (typically within 1–2 s) confirms the change. The previous design called `coordinator.async_request_refresh()` right after each command and then snapped the UI back to the cloud's pre-command state — that race is gone.

## Bucket-full debounce

`binary_sensor.<device>_waste_bucket_full` only goes **on** after the device reports `bucket_full=True` for **300 consecutive seconds** (5 min). Any reading of `False` clears the dwell timer immediately and resets the sensor. This filters out the brief flap that happens during clean cycles.

## Compatibility

| Component | Version |
|---|---|
| Home Assistant | ≥ 2026.5.1 (matches `requirements.txt`, `hacs.json`, and `requirements_test.txt`) |
| Python | 3.14 |
| `neakasa-litterbox-sdk` | 0.1.1 |

The integration targets the **Platinum** tier of Home Assistant's [Integration Quality Scale](https://developers.home-assistant.io/docs/core/integration-quality-scale/) — see [`custom_components/neakasa_litterbox/quality_scale.yaml`](./custom_components/neakasa_litterbox/quality_scale.yaml).

## Diagnostics

Use **⚙ Configure → Download diagnostics** to get a redacted dump (email and password are stripped) of the config entry and the currently-registered devices. Attach the file when opening an issue.

## Known limitations

- The Neakasa cloud occasionally drops the MQTT dispatcher (`Disconnected during message iteration`). The integration currently does **not** auto-reconnect; restart the entry to bring push back. Polling fallback keeps working in the meantime.
- The Neakasa SDK does not expose a way to disable HTTPS verification, so the integration assumes the local Python install can validate `*.neakasa.com` (most distributions can; on macOS Python builds the helper script auto-injects `certifi`'s bundle — see [`scripts/develop`](./scripts/develop)).
- Firmware version is surfaced as **device metadata** (visible on the device card) rather than as a dedicated sensor.

## Development

```bash
scripts/setup      # install requirements.txt
scripts/develop    # start Home Assistant in debug mode with this integration loaded
scripts/lint       # ruff format + check + mypy
pytest             # run the test suite (95 % coverage gate enforced)
```

Each script auto-detects `./.venv` and prepends it to `PATH` — no `source .venv/bin/activate` needed. For ad-hoc commands the same trick works: `.venv/bin/pytest`, `.venv/bin/ruff …`.

HA runs with config in `config/` and `PYTHONPATH` pointing at `custom_components/` — no symlinks. To recreate entity/device IDs during development:

```bash
rm config/.storage/core.entity_registry config/.storage/core.device_registry
```

Conventions for contributors live in [`CODE_STYLE.md`](./CODE_STYLE.md); architectural notes for AI agents in [`CLAUDE.md`](./CLAUDE.md).

## CI

- **`lint.yml`** — ruff (check + format) and mypy (Python 3.14)
- **`validate.yml`** — `hassfest` + HACS validation; push/PR to `main` and a daily cron
- **`codeql.yml`** — GitHub CodeQL security scan; push/PR to `main` and a weekly cron

## Acknowledgements

Bootstrapped from [ludeeus/integration_blueprint](https://github.com/ludeeus/integration_blueprint). Powered by the [`neakasa-litterbox-sdk`](https://pypi.org/project/neakasa-litterbox-sdk/).

## License

[MIT](LICENSE)
