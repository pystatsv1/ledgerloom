# LedgerLoom

**LedgerLoom** is a small, MIT-licensed Python project that teaches accounting
concepts (journal, ledger, debits/credits, trial balance, financial statements)
using *modern* developer mental models (event logs, databases, OOP).

It also includes a tiny library + CLI you can run locally to generate:

- a demo journal (`ledger.jsonl`)
- a trial balance
- an income statement
- a balance sheet

## Quick start

```bash
python -m venv .venv
source .venv/Scripts/activate
pip install -r requirements.txt
pip install -r requirements-dev.txt
pip install -e .

make lint
pytest -q
make ll-ch01
make docs
```

Then open the built docs:

```bash
ledgerloom-docs
```

## License

MIT (see LICENSE).
