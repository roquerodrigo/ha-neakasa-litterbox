# CLAUDE.md

Guidance for Claude Code (claude.ai/code) agents working in this repository.

## Always read `CODE_STYLE.md` first

Before creating, renaming or restructuring any file/class/function, **read [`CODE_STYLE.md`](./CODE_STYLE.md)**. It is the single source of truth for conventions: language, file organisation, naming, typing, properties vs `__init__`, imports, docstrings, comments, coordinator pattern, repairs/diagnostics layout, translations, lint workflow.

For user-facing topics (what's included, how to fork, rename steps, layout diagram, useful commands, CI list), see [`README.md`](./README.md).

This file deliberately avoids restating those rules — it only adds:

1. The verification workflow agents must run after every change.
2. The architectural reasoning that is not obvious from `CODE_STYLE.md` alone.

## Verification workflow

**After every code change, always run lint then tests, in that order, before declaring the task done:**

```bash
uv run ruff format . && uv run ruff check . --fix && uv run mypy custom_components/neakasa_litterbox && uv run pytest
```

- The lint commands run `ruff format`, `ruff check --fix` and `mypy` (config in `pyproject.toml`). Fix any failure and re-run before moving on.
- `pytest` enforces a **90 % coverage gate** (`pyproject.toml`).

Both gates mirror CI (`.github/workflows/ci.yml`). Skip this only when the change literally cannot affect lint or tests (e.g., README-only edits).

## Bumping the Home Assistant version

The Home Assistant version is pinned in three places and **must be updated together**, otherwise CI, HACS and the test harness drift apart:

1. `pyproject.toml` — `homeassistant==<X.Y.Z>` in `[dependency-groups] dev` (runtime/CI lint + mypy).
2. `hacs.json` — `"homeassistant": "<X.Y.Z>"` (minimum HA core enforced by HACS).
3. `pyproject.toml` — `pytest-homeassistant-custom-component==<matching release>` in `[dependency-groups] dev` (the test harness ships its own pinned `homeassistant`; the two pins must come from the same HA release, otherwise lint and tests resolve different cores).

Verify the pairing on PyPI before committing: the `requires_dist` of `pytest-homeassistant-custom-component` must list the same `homeassistant==<X.Y.Z>` you pinned in `pyproject.toml`.

## Bumping `neakasa-litterbox-sdk`

This integration is a thin wrapper around the [`neakasa-litterbox-sdk`](https://pypi.org/project/neakasa-litterbox-sdk/) PyPI package (companion repo `neakasa-litterbox-sdk`). The pin lives in two places that **must move together**, same failure mode as the HA version above:

1. `custom_components/neakasa_litterbox/manifest.json` — `requirements: ["neakasa-litterbox-sdk==<X.Y.Z>"]` (what HA installs at runtime).
2. `pyproject.toml` — `neakasa-litterbox-sdk==<X.Y.Z>` in `[dependency-groups] dev` (what lint/mypy/pytest resolve against).

Past bumps landed as `fix(deps)`/`build(deps)` commits touching both files plus `uv.lock` in the same commit (e.g. `a120c7a`, `8eb34e9`) — copy that pattern rather than editing only one.

The integration only imports from the SDK's public surface, so an SDK release is safe as long as it doesn't rename/remove these:

- `api.py` — `NeakasaClient` (wrapped by `NeakasaApiClient`) and its `watch_status()` method, which returns the `StatusStream` used by `push.py`.
- `push.py` — `StatusStream`, `StatusUpdate`, `DeviceStatus`.
- `coordinator.py` — `Cat`, `Device`, `DeviceStatus`, `ToiletRecord`, `RecordType`.
- `exceptions/` — `_translate_errors` in `api.py` catches the SDK's `NeakasaError`, `ApiError` (branching on its `.code`), `TransportError`, `InvalidCredentialsError`, `SessionExpiredError`, `AuthenticationError`. If the SDK adds/renames an exception class or changes an error code (e.g. the `29003` "device busy" code), update this mapping or the integration will surface the wrong HA exception (or none).

## Architecture

The integration follows the HA `DataUpdateCoordinator` pattern, plus an MQTT push channel:

```
config_flow.py   → validates credentials and creates the ConfigEntry
__init__.py      → instantiates ApiClient + DataUpdateCoordinator + PushClient, performs the first refresh
coordinator.py   → polls every scan_interval seconds; returns the typed payload
push.py          → subscribes to the SDK's MQTT status stream, merges deltas into coordinator data in real time
sensor/, binary_sensor/, button/, number/, switch/
                 → one package per platform; each reads coordinator.data and creates its entities.
                   `<platform>/__init__.py` holds async_setup_entry + dynamic device/cat discovery,
                   one file per entity class otherwise.
```

### Entry typing

`data.py` defines `NeakasaConfigEntry = ConfigEntry[NeakasaData]` and the `NeakasaData(client, coordinator, integration, push)` dataclass. State lives on `entry.runtime_data` (auto-discarded on unload), never on `hass.data`.

### Config flow surface

`config_flow.py` implements four user-facing steps; all share one `_validate` helper and one `_credentials_schema` builder:

- `async_step_user` — initial setup; sets unique_id from username, aborts on duplicate.
- `async_step_reauth` / `async_step_reauth_confirm` — fired when the coordinator raises `ConfigEntryAuthFailed`. `async_update_reload_and_abort` rotates credentials in place.
- `async_step_reconfigure` — lets the user edit credentials via the integration's three-dot menu, no delete-and-re-add cycle.
- `async_get_options_flow` — returns `NeakasaOptionsFlow` from `options_flow.py` (one class per file).

### Options flow

`options_flow.py` (`NeakasaOptionsFlow`) exposes two options:

- `scan_interval` (seconds; min 60, default 600) — the coordinator's polling fallback cadence.
- `statistics_lookback_days` (days; min 1, max 30, default 7) — the coordinator's `ToiletRecord` lookback window for per-cat last-visit/visits-today sensors.

Changing either triggers `async_reload_entry`, which re-instantiates the coordinator with the new `update_interval`/lookback.

### Push client

`push.py` (`NeakasaPushClient`) opens the SDK's `StatusStream` (MQTT, `watch_status()`) and merges each `StatusUpdate` delta into coordinator data as it arrives. A supervisor task polls the SDK's underlying dispatch task for liveness (the SDK doesn't surface disconnects on its public API) and respawns the stream with exponential backoff (5 s → up to 300 s cap) when it dies, resetting the backoff once a connection has been stable for 60 s. `async_setup_entry` starts it right after the coordinator's first refresh and registers `push.async_stop` via `entry.async_on_unload`.

### API client

`api.py` exposes `NeakasaApiClient`, a thin async wrapper around the SDK's `NeakasaClient`. The `_translate_errors` context manager maps SDK exceptions to the integration's own hierarchy (`exceptions/`):

- `NeakasaApiClientError` (base) ← `NeakasaError`, or `ApiError` for any code other than the one below
- `NeakasaApiClientCommunicationError` ← `TransportError`
- `NeakasaApiClientAuthenticationError` ← `InvalidCredentialsError`, `SessionExpiredError`, `AuthenticationError`
- `NeakasaApiClientDeviceBusyError` ← `ApiError` with code `29003` — the cloud rejects a property readback while the box is mid-cycle (cleaning/restoring/leveling); this is expected and transient, so the coordinator can keep-last on it instead of surfacing an error.

### Diagnostics

`diagnostics.py` returns `NeakasaDiagnosticsPayload`. `username`/`password` are redacted via `async_redact_data` (driven by `TO_REDACT: frozenset[str]`). `.github/ISSUE_TEMPLATE/bug.yml` asks users to attach the dump.

### Repairs

`repairs.py` is the entry point HA calls when the user clicks **Fix** on an issue:

- `async_create_fix_flow(hass, issue_id, data)` returns a `RepairsFlow`. Branch on `issue_id` for multiple kinds; the default returns `ConfirmRepairFlow`.
- `async_raise_deprecated_api_issue(hass)` is the sample helper that registers an issue. Call helpers like this from the coordinator/setup when you detect a recoverable problem.

Issue strings live under `issues.<issue_id>` in the translation files.
