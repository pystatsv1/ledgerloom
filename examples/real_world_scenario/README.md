# LedgerLoom example: real_world_scenario

This folder is a fully runnable **LedgerLoom project** meant to prove the v0.2.0 “practical tool” workflow:

- no Python required
- CSV → staging/check → build → trust + accounting artifacts
- unmapped rows go to a suspense account and generate `unmapped.csv` + `reclass_template.csv`

## Run it

From the repo root:

```bash
ledgerloom check --project examples/real_world_scenario
ledgerloom build --project examples/real_world_scenario --run-id run-a
ledgerloom build --project examples/real_world_scenario --run-id run-b
```

Verify determinism (same inputs/config ⇒ same manifest hash):

```bash
sha256sum examples/real_world_scenario/outputs/run-a/trust/manifest.json \
         examples/real_world_scenario/outputs/run-b/trust/manifest.json
```

## What to look at

- `outputs/<run_id>/check/checks.md` — human-readable validation report
- `outputs/<run_id>/artifacts/postings.csv` — the postings fact table
- `outputs/<run_id>/artifacts/trial_balance.csv` — trial balance
- `outputs/<run_id>/artifacts/income_statement.csv` — income statement
- `outputs/<run_id>/artifacts/balance_sheet.csv` — balance sheet
- `outputs/<run_id>/artifacts/unmapped.csv` — rows that hit suspense + suggested mapping YAML
- `outputs/<run_id>/artifacts/reclass_template.csv` — optional helper to reclass suspense postings

This example intentionally contains one “mystery” vendor that does **not** match any mapping rule, so you can see the exception workflow end-to-end.
