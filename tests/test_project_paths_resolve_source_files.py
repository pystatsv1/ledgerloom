from __future__ import annotations

from pathlib import Path

from ledgerloom.project.paths import resolve_source_files


def test_resolve_source_files_supports_inputs_relative_and_project_relative_patterns(tmp_path: Path) -> None:
    project_root = tmp_path / "proj"
    inputs_dir = project_root / "inputs" / "2026-01"
    inputs_dir.mkdir(parents=True)

    f = inputs_dir / "bank_01.csv"
    f.write_text("Date,Description,Amount\n", encoding="utf-8", newline="\n")

    # v1-ish pattern: inputs-dir-relative
    files1 = resolve_source_files(
        project_root=project_root,
        inputs_dir=inputs_dir,
        file_pattern="bank_*.csv",
        period="2026-01",
    )
    assert files1 == [f]

    # v2-ish pattern: project-root-relative with {period}
    files2 = resolve_source_files(
        project_root=project_root,
        inputs_dir=inputs_dir,
        file_pattern="inputs/{period}/bank_*.csv",
        period="2026-01",
    )
    assert files2 == [f]
