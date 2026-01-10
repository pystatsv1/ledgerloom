# Changelog

LedgerLoom follows semantic versioning.

## 0.2.0 (Unreleased)

### Added
- Practical Tool example project: `examples/real_world_scenario/` (runnable COA + config + sample CSV).
- Deterministic build smoke test for the example (manifest hash stability).
- Audience-focused Practical Tool docs: accountant quickstart, developer view, data professional view.

### Changed
- Trust/manifest + run metadata writing centralized and made deterministic across runs.

## 0.1.5 (2026-01-05)

### Added
- Initial engine MVP: signed-money model + debits/credits encoding, COA validation, and statement derivations.
- CLI commands: `ledgerloom init`, `ledgerloom check`, and `ledgerloom build` (foundations for the Practical Tool).

### Changed
- Documentation overhaul: clearer engine narrative and practical tooling section scaffolding.
