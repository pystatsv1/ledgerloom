"""Refactor safety check: ensure Ch08.5/Ch09/Ch10 don't import from other chapters.

Run locally after tests pass:

    python scripts/check_no_cross_chapter_imports.py

This is intentionally tiny and dependency-free; it exists to prevent "chapter
spaghetti" as Chapter 10+ is implemented.
"""

from __future__ import annotations

from pathlib import Path


DEFAULT_TARGETS = [
    Path("src/ledgerloom/chapters/ch085_opening_next_period.py"),
    Path("src/ledgerloom/chapters/ch09_ar_lifecycle.py"),
    Path("src/ledgerloom/chapters/ch10_ap_lifecycle.py"),
    Path("src/ledgerloom/chapters/ch11_inventory_cogs.py"),
]


def _check_file(path: Path) -> list[str]:
    text = path.read_text(encoding="utf-8")
    problems: list[str] = []

    if "ledgerloom.chapters" in text:
        problems.append("contains 'ledgerloom.chapters' import reference")
    if "noqa: SLF001" in text or "# noqa: SLF001" in text:
        problems.append("contains 'noqa: SLF001' (private member access)")

    return problems


def main() -> int:
    repo_root = Path(__file__).resolve().parents[1]

    failures: list[str] = []
    for rel in DEFAULT_TARGETS:
        path = repo_root / rel
        if not path.exists():
            failures.append(f"missing expected file: {rel.as_posix()}")
            continue

        problems = _check_file(path)
        if problems:
            failures.append(f"{rel.as_posix()}: {', '.join(problems)}")

    if failures:
        msg = "\n".join(["Refactor safety check failed:", *failures])
        raise SystemExit(msg)

    print("Refactor safety check OK (no cross-chapter imports / no SLF001).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
