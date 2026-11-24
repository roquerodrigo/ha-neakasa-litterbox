# Contributing

Bug reports, ideas and pull requests are welcome.

## Reporting a bug

Open an [issue](https://github.com/roquerodrigo/ha-neakasa-litterbox/issues/new/choose)
with:

- the integration version and the system information from
  **Settings → System → Repairs → ⋮ → System information**;
- what you did, what you expected and what happened;
- the debug log of the problem and the diagnostics downloaded from the
  integration's menu (the email and password are redacted).

## Development setup

The project uses [uv](https://docs.astral.sh/uv/) and Python 3.14.2 or newer.

```bash
scripts/setup      # install the dev and lint dependencies into .venv
scripts/develop    # run Home Assistant at http://localhost:8123 with this integration loaded
```

`scripts/develop` uses the configuration in [`config/`](config/) and loads
the integration from `custom_components/` through `PYTHONPATH`, without
symlinks. Both scripts use `.venv` on their own, so there is no need to
activate it. On macOS Python builds without a trusted CA bundle,
`scripts/develop` points TLS at the `certifi` bundle so the Neakasa cloud can
be verified.

To start again with fresh entity and device IDs, stop Home Assistant and
delete `config/.storage/core.entity_registry` and
`config/.storage/core.device_registry`.

## Checks

Run these before opening a pull request. CI runs the same ones, and
`uv run pre-commit install` runs the first three on every commit.

```bash
uv run ruff format .                               # format
uv run ruff check . --fix                          # lint
uv run mypy custom_components/neakasa_litterbox    # type-check
uv run pytest                                      # tests, coverage must stay at 90 % or more
```

CI also validates the integration against the Home Assistant Marketplace
requirements and runs a CodeQL scan.

Read [CODE_STYLE.md](CODE_STYLE.md) before adding or restructuring code.

## Pull requests

1. Fork the repository and branch from `main`.
2. Write commit messages as [Conventional Commits](https://www.conventionalcommits.org/).
   Releases and their notes are generated from them. Mark breaking changes
   with `!` or a `BREAKING CHANGE:` footer.
3. Update `translations/en.json`, `translations/pt-BR.json` and
   `translations/es.json` together when you change user-facing strings.
   `tests/test_translations.py` fails when their keys differ.
4. Update the README when behaviour, configuration or entities change.
5. Fill in the pull request template.

## License

Contributions are released under the project's [MIT License](LICENSE).
