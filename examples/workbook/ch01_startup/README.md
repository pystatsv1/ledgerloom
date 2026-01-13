# Workbook example — Chapter 1 (Startup)

This is a minimal, runnable **workbook-profile** project.

It demonstrates the end-to-end workbook build artifacts:

- `entries.csv`
- `trial_balance_unadjusted.csv`
- `trial_balance_adjusted.csv`
- `closing_entries.csv`
- `trial_balance_post_close.csv`

## Run it

From this folder:

```bash
python -m ledgerloom check --project .
python -m ledgerloom build --project . --run-id demo
```

Outputs will be written under:

- `outputs/check/2026-01/` (from `check`)
- `outputs/demo/` (from `build`)
