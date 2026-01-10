# Release checklist (LedgerLoom)

This checklist is designed for a small, low-drama release.

## 1) Pre-flight

- [ ] `git switch main && git pull origin main`
- [ ] Working tree clean: `git status`
- [ ] Version bumped in `pyproject.toml`
- [ ] `CHANGELOG.md` updated (and docs `docs/source/changelog.rst` updated)

## 2) Local verification

Run the full “green bar” locally:

```bash
make lint
pytest -q
make docs-strict
```

(Optional but recommended) Verify the runnable example:

```bash
ledgerloom check --project examples/real_world_scenario
ledgerloom build --project examples/real_world_scenario --run-id sanity
```

## 3) Build distributions

```bash
python -m pip install --upgrade build twine
python -m build
twine check dist/*
```

Confirm the sdist contains the example folder:

```bash
tar -tf dist/*.tar.gz | grep -E '^examples/real_world_scenario/'
```

## 4) Tag + push

```bash
git tag -a v0.2.0 -m "v0.2.0"
git push origin v0.2.0
```

## 5) Publish

- [ ] Create a GitHub Release from the tag, and paste highlights from `CHANGELOG.md`.
- [ ] Publish to PyPI (via your preferred workflow).
- [ ] Verify `pip install ledgerloom` installs cleanly and `ledgerloom --help` works.
- [ ] Verify docs build on ReadTheDocs.

## 6) Post-release

- [ ] Bump version to next development number (e.g., `0.2.1-dev` or similar).
- [ ] Open a milestone for the next set of PRs.
