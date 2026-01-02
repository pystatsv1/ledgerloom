# Contributing to PyStatsV1

**Don't just calculate your results — engineer them. We treat statistical analysis like production software.**

PyStatsV1 is an open-source organization applying modern software engineering standards to applied statistics.
Our mission is to help students, instructors, and researchers escape the Reproducibility Crisis by treating statistical analysis not as a scratchpad, but as a transparent, testable, and re-runnable system.

**PyStatsV1 = statistics + software engineering for transparent and reproducible research.**

**Welcome!** Thank you for helping us build a framework for rigorous, reproducible applied statistics.

Whether you are a veteran Python developer, a statistics student, or an instructor moving from R to Python, your contribution is valuable. We believe that **high-quality software engineering** can provide a strong foundation for **transparent and reproducible science**, and we are excited to have you join this mission.

---

## 🚦 Where to Start?

You do **not** need to be a “coder” to contribute. Here are some common ways to help.

### 1. I am a Student or Researcher (Non-Programmer)

You are our target audience! Your feedback is critical.

- **Fix typos and unclear text**  
  If a chapter explanation is confusing or has a typo, that is a bug. Please let us know.
- **Report “it didn’t work” moments**  
  If you followed a tutorial and got an error, please open an issue and paste:
  - the command you ran,
  - the full error message,
  - your OS and Python version (e.g. `python --version`).
- **Request a topic**  
  Need a specific analysis (e.g., *Two-way ANOVA* or *logistic regression*)? Open an issue labeled `feature request` and describe the use case.

### 2. I am an Instructor

- **Share a case study**  
  Have a great dataset or teaching example? We can help turn it into a PyStatsV1 “chapter” or lab.
- **Give course feedback**  
  Tell us how the scripts worked in your classroom: what flowed well, what students struggled with, and what you’d like to see next.

### 3. I am a Developer (Python / R)

- **Translate R to Python**  
  Many classic applied stats books are R-first. We are actively porting those examples into the PyStatsV1 structure.
- **Improve the “plumbing”**  
  Help us refine CI, Makefiles, type hints, and tests, or add new chapter helpers and simulators.

If you’re unsure where to start, look for issues labeled **`good first issue`** or **`help wanted`**.

---

## 🛠️ The Engineering-First Workflow

We treat statistical analysis like production software. That means:

- every chapter has scripts and tests,
- we use **CI** to catch bugs early,
- and contributors share a common workflow.

Don’t worry — the tooling is there to *help* you. You do not have to be an expert in any of it to contribute.

### 1. Fork and Clone

1. Fork the repository on GitHub to your own account.
2. Clone your fork:

   ```bash
   git clone https://github.com/YOUR_USERNAME/PyStatsV1.git
   cd PyStatsV1
   ```

3. Add the upstream remote (optional but recommended):

   ```bash
   git remote add upstream https://github.com/pystatsv1/PyStatsV1.git
   ```

### 2. Set Up Your Environment

We recommend using a virtual environment.

```bash
python -m venv .venv
# On macOS / Linux:
source .venv/bin/activate
# On Windows (PowerShell):
.venv\Scripts\Activate.ps1
```

Install dependencies:

```bash
pip install -r requirements.txt
pip install -r requirements-dev.txt
```

You should now be able to run:

```bash
pytest
make lint
```

without errors.

### 3. Create a Branch

Use a short, descriptive branch name:

```bash
# Examples:
git checkout -b fix/typo-ch09-ci-docs
git checkout -b feat/psych-ch10-independent-t
git checkout -b tests/psych-ch8-one-sample
```

We loosely follow a convention like:

- `docs/...` for documentation changes,
- `feat/...` for new functionality or scripts,
- `tests/...` for new or improved tests,
- `tooling/...` for Makefile / CI / tooling updates.

### 4. Make Your Changes

Some suggestions by contribution type:

- **Docs / textbook text**
  - Edit the relevant `.rst` files under `docs/source/`.
  - Keep explanations student-friendly and avoid unnecessary jargon.
- **Scripts**
  - Add or modify files under `scripts/...`.
  - Prefer small, pure functions that are easy to test.
  - Keep dependencies minimal and standard-library-first when possible.
- **Tests**
  - Put tests in `tests/` and follow the existing naming pattern  
    (e.g. `test_psych_ch8_one_sample_test.py`).
  - Use simple, deterministic examples with fixed random seeds when simulating.

Run the basic checks before committing:

```bash
pytest
make lint
```

If you are working on chapter-specific helpers, also run any relevant `make` target (e.g. `make psych-ch08`, `make psych-ch09`).

### 5. Commit Style

Use clear, focused commits. A few examples that match the existing history:

- `docs: clarify Chapter 8 p-value explanation`
- `feat: add Chapter 10 independent-samples simulator`
- `tests: add smoke tests for psych CLI`
- `tooling: add Make target for psych Chapter 9 lab`

Commit your work:

```bash
git add PATH/TO/FILES
git commit -m "docs: short, descriptive message"
```

### 6. Keep Your Branch Up to Date

If `main` has moved forward while you were working:

```bash
git fetch upstream
git checkout main
git pull upstream main
git checkout your-branch-name
git rebase main   # or merge, if you prefer
```

Resolve any conflicts, rerun tests, and push again.

### 7. Open a Pull Request

Push your branch to your fork:

```bash
git push -u origin your-branch-name
```

Then open a Pull Request (PR) on GitHub:

- Base repository: `pystatsv1/PyStatsV1`
- Base branch: `main`
- Compare: `your-branch-name`

In the PR description, please include:

- a short summary of what you changed,
- which chapter(s) or files are affected,
- how you tested it (`pytest`, `make lint`, specific `make` targets).

Maintainers will review your PR, possibly suggest changes, and then merge it once it’s ready.

---

## 💬 Questions, Ideas, and Support

If you’re not sure how to implement something — or you just want to float an idea — please:

- open an issue with the **question**, or  
- draft a PR and mark it as **Draft** to start a conversation.

We’re excited to collaborate with:

- students learning applied statistics,
- instructors building reproducible courses,
- and practitioners who care about transparent, defensible analyses.

Thank you again for contributing to **PyStatsV1** 💙
