## Summary

<!-- 1-3 bullets describing what changed and why. -->

## Type of change

- [ ] Bug fix
- [ ] New feature
- [ ] Refactor / cleanup
- [ ] Documentation
- [ ] Tooling / CI

## Test plan

- [ ] `uv run ruff format .`, `uv run ruff check . --fix` and `uv run mypy custom_components/neakasa_litterbox` pass (ruff + mypy)
- [ ] `pytest` passes with the 90 % coverage gate
- [ ] All translation locales updated (if user-facing strings changed)

## Checklist

- [ ] Code is in English (only `translations/<locale>.json` follows the locale)
- [ ] One top-level class per file
- [ ] CLAUDE.md / README updated if architecture or workflow changed
- [ ] `manifest.json` version bumped if releasing
