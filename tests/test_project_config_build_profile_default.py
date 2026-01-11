from __future__ import annotations

from pathlib import Path

from ledgerloom.project.config import ProjectConfig


def test_project_config_build_profile_defaults_to_practical(tmp_path: Path) -> None:
    cfg_yaml = """
schema_id: ledgerloom.project_config.v2
outputs:
  root: outputs
chart_of_accounts: config/chart_of_accounts.yaml
project:
  currency: USD
  name: Acme Corp
  period: 2026-01
""".lstrip()

    path = tmp_path / "ledgerloom.yaml"
    path.write_text(cfg_yaml, encoding="utf-8", newline="\n")

    cfg = ProjectConfig.load_yaml(path)

    assert cfg.build_profile == "practical"

    # Backward compatibility: default build_profile is omitted from normalized dict.
    out = cfg.to_dict()
    assert "build_profile" not in out


def test_project_config_build_profile_roundtrips_when_explicit(tmp_path: Path) -> None:
    cfg_yaml = """
schema_id: ledgerloom.project_config.v2
build_profile: workbook
outputs:
  root: outputs
chart_of_accounts: config/chart_of_accounts.yaml
project:
  currency: USD
  name: Acme Corp
  period: 2026-01
""".lstrip()

    path = tmp_path / "ledgerloom.yaml"
    path.write_text(cfg_yaml, encoding="utf-8", newline="\n")

    cfg = ProjectConfig.load_yaml(path)
    assert cfg.build_profile == "workbook"

    out = cfg.to_dict()
    assert out["build_profile"] == "workbook"

    dumped = tmp_path / "dumped.yaml"
    cfg.dump_yaml(dumped)
    cfg2 = ProjectConfig.load_yaml(dumped)
    assert cfg2.build_profile == "workbook"
    assert cfg2.to_dict()["build_profile"] == "workbook"
