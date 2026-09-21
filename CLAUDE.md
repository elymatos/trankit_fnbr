# Trankit FNBr agent instructions

## Project direction

This repository implements the self-contained FNBr pipeline described in:

- `docs/00-project-direction.md` — boundaries and build order;
- `docs/01-specification.md` — normative behavior and work packages;
- `docs/02-upstream-trankit.md` — pinned upstream source and fork changes.

Read the applicable documents before changing pipeline behavior, lexical processing, dataset conversion, or the Trankit fork.

## Development environment

Use the `trankit-fnbr` Conda environment for every Python install, test, type-check, training, and runtime command. Create it from `environment.yml` when absent. Keep credentials in environment variables or `.env`; `.env.example` documents the supported configuration.

The FNBr database is read-only from this project. Keep SQL and schema mapping inside `trankit_fnbr/database.py`.

## Verification

Run focused tests during development, then complete both checks before finishing:

```bash
conda run -n trankit-fnbr python -m pytest
conda run -n trankit-fnbr mypy trankit_fnbr
```

## Agent skills

### Issue tracker

Issues are tracked in this repository's GitHub Issues. See `docs/agents/issue-tracker.md`.

### Triage labels

The repository uses the default Matt Pocock triage-label vocabulary. See `docs/agents/triage-labels.md`.

### Domain docs

This repository uses a single-context domain-documentation layout. See `docs/agents/domain.md`.
