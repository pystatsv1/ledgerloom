from __future__ import annotations

# Keep `python -m ledgerloom` working while making the console script
# point at the product CLI (see ledgerloom.cli).
from ledgerloom.cli import main, open_docs_cli  # noqa: F401


if __name__ == "__main__":
    raise SystemExit(main())
