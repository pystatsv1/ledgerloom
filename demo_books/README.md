# demo_books

This folder is a LedgerLoom project.

## Quickstart

1) Put your CSVs in `inputs/2026-01/`
2) Edit `ledgerloom.yaml` and `config/chart_of_accounts.yaml`
3) Run the gatekeeper:

```bash
ledgerloom check --project .
```

Outputs:

* `outputs/check/2026-01/checks.md`
* `outputs/check/2026-01/staging.csv`
* `outputs/check/2026-01/staging_issues.csv`
