from __future__ import annotations

import ast
import json
from pathlib import Path

from ledgerloom.artifacts import MANIFEST_SCHEMA_V1, RUN_META_SCHEMA_V1


TRUST_FILENAMES = {"manifest.json", "run_meta.json"}


def _is_trust_path_expr(expr: ast.AST, trust_vars: set[str]) -> bool:
    # Direct string literal.
    if isinstance(expr, ast.Constant) and isinstance(expr.value, str):
        return expr.value in TRUST_FILENAMES

    # Name that we previously tracked.
    if isinstance(expr, ast.Name):
        return expr.id in trust_vars

    # outdir / "manifest.json"
    if isinstance(expr, ast.BinOp) and isinstance(expr.op, ast.Div):
        right = expr.right
        if isinstance(right, ast.Constant) and isinstance(right.value, str):
            return right.value in TRUST_FILENAMES

    # Path("manifest.json")
    if isinstance(expr, ast.Call) and isinstance(expr.func, ast.Name) and expr.func.id == "Path":
        if expr.args and isinstance(expr.args[0], ast.Constant) and isinstance(expr.args[0].value, str):
            return expr.args[0].value in TRUST_FILENAMES

    return False


def _call_name(call: ast.Call) -> str | None:
    if isinstance(call.func, ast.Name):
        return call.func.id
    if isinstance(call.func, ast.Attribute):
        return call.func.attr
    return None


def _is_write_mode(call: ast.Call) -> bool:
    # built-in open(path, mode=...)
    mode = None
    if len(call.args) >= 2 and isinstance(call.args[1], ast.Constant) and isinstance(call.args[1].value, str):
        mode = call.args[1].value
    for kw in call.keywords:
        if kw.arg == "mode" and isinstance(kw.value, ast.Constant) and isinstance(kw.value.value, str):
            mode = kw.value.value
    if mode is None:
        return False
    return "w" in mode or "a" in mode or "+" in mode


def _writes_trust_file(call: ast.Call, trust_vars: set[str]) -> bool:
    name = _call_name(call)

    # Direct deterministic writers should *not* be called from chapters;
    # they should go through emit_trust_artifacts.
    if name in {"write_manifest", "write_run_meta"}:
        return True

    # write_json(path, ...) / write_text(path, ...) / write_bytes(path, ...)
    if name in {"write_json", "write_text", "write_bytes"}:
        if call.args and _is_trust_path_expr(call.args[0], trust_vars):
            return True
        for kw in call.keywords:
            if kw.arg in {"path", "p"} and _is_trust_path_expr(kw.value, trust_vars):
                return True

    # open(path, "w") and Path.open("w")
    if name == "open":
        # built-in open(...)
        if isinstance(call.func, ast.Name):
            if call.args and _is_trust_path_expr(call.args[0], trust_vars) and _is_write_mode(call):
                return True
        # Path(...).open(...)
        if isinstance(call.func, ast.Attribute):
            if _is_trust_path_expr(call.func.value, trust_vars) and _is_write_mode(call):
                return True

    # Path(...).write_text(...) / write_bytes(...)
    if name in {"write_text", "write_bytes"} and isinstance(call.func, ast.Attribute):
        if _is_trust_path_expr(call.func.value, trust_vars):
            return True

    return False


def test_chapters_do_not_write_trust_files_directly() -> None:
    """Audit: chapters must use the pipeline entrypoint, not bespoke writers."""

    chapters_dir = Path("src/ledgerloom/chapters")
    chapter_files = sorted(p for p in chapters_dir.glob("ch*.py") if p.name != "__init__.py")
    assert chapter_files, "No chapter files found"

    offenders: list[str] = []
    missing_entrypoint: list[str] = []

    for p in chapter_files:
        tree = ast.parse(p.read_text(encoding="utf-8"))
        trust_vars: set[str] = set()

        # Track simple assignments like: manifest_path = outdir / "manifest.json"
        for node in ast.walk(tree):
            if isinstance(node, ast.Assign):
                if len(node.targets) == 1 and isinstance(node.targets[0], ast.Name):
                    if _is_trust_path_expr(node.value, set()):
                        trust_vars.add(node.targets[0].id)
            if isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name) and node.value is not None:
                if _is_trust_path_expr(node.value, set()):
                    trust_vars.add(node.target.id)

        has_entrypoint = False
        for node in ast.walk(tree):
            if isinstance(node, ast.Call):
                n = _call_name(node)
                if n == "emit_trust_artifacts":
                    has_entrypoint = True
                if _writes_trust_file(node, trust_vars):
                    offenders.append(f"{p.as_posix()}: direct trust write via {n}")

        if not has_entrypoint:
            missing_entrypoint.append(p.as_posix())

    assert not missing_entrypoint, "Missing emit_trust_artifacts in: " + ", ".join(missing_entrypoint)
    assert not offenders, "Found chapters writing trust files directly:\n" + "\n".join(offenders)


def test_golden_trust_files_have_schema_ids() -> None:
    """Audit: goldens for trust artifacts must carry explicit schema IDs."""

    golden_root = Path("tests/golden")
    assert golden_root.exists()

    for manifest_path in golden_root.glob("**/manifest.json"):
        obj = json.loads(manifest_path.read_text(encoding="utf-8"))
        assert obj.get("schema") == MANIFEST_SCHEMA_V1, f"{manifest_path} missing/invalid schema"

    for run_meta_path in golden_root.glob("**/run_meta.json"):
        obj = json.loads(run_meta_path.read_text(encoding="utf-8"))
        assert obj.get("schema") == RUN_META_SCHEMA_V1, f"{run_meta_path} missing/invalid schema"
