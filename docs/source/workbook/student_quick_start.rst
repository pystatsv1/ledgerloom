Student Quick Start (Linux, Windows, macOS)
===========================================

This guide helps you run the LedgerLoom **Workbook** workflow as a student:

1) install LedgerLoom from **PyPI**
2) create a workbook project with ``ledgerloom init --profile workbook``
3) run ``check`` then ``build``
4) open the generated CSV artifacts

What you’ll build
-----------------

LedgerLoom reads CSV inputs from a project folder and generates accounting-cycle artifacts.

After a successful build, you should see these files:

- ``entries.csv``
- ``trial_balance_unadjusted.csv``
- ``trial_balance_adjusted.csv``
- ``closing_entries.csv``
- ``trial_balance_post_close.csv``

These files appear under:

- ``outputs/<run_id>/artifacts/``

.. note::
   LedgerLoom runs best inside a **virtual environment** (venv). This keeps your class setup clean and repeatable.

Linux (Ubuntu/Debian)
---------------------

1) Install Python tools
^^^^^^^^^^^^^^^^^^^^^^^

.. code-block:: bash

   sudo apt update
   sudo apt install -y python3 python3-venv python3-pip

2) Create a workspace + virtual environment
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. code-block:: bash

   mkdir -p ~/ledgerloom_student
   cd ~/ledgerloom_student

   python3 -m venv .venv
   source .venv/bin/activate
   pip install -U pip

3) Install LedgerLoom from PyPI
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. code-block:: bash

   pip install -U ledgerloom
   ledgerloom --help

4) Create a workbook project
^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. code-block:: bash

   ledgerloom init --profile workbook my_books
   cd my_books

5) Run the workflow (check → build)
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. code-block:: bash

   ledgerloom check --project . --run-id run1
   ledgerloom build --project . --run-id run1

6) View your outputs
^^^^^^^^^^^^^^^^^^^^

.. code-block:: bash

   ls -1 outputs/run1/artifacts

Common gotchas (Linux)
^^^^^^^^^^^^^^^^^^^^^^

- If ``ledgerloom`` is “not found”, you likely forgot: ``source .venv/bin/activate``.
- ``ledgerloom init`` requires a folder name at the end (example: ``my_books``).

Windows 11 (PowerShell)
-----------------------

1) Install Python
^^^^^^^^^^^^^^^^^

Install **Python 3.10+** from python.org and make sure you check:

- **Add Python to PATH**

Verify in PowerShell:

.. code-block:: powershell

   python --version
   pip --version

2) Create a workspace + virtual environment
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. code-block:: powershell

   mkdir $HOME\ledgerloom_student
   cd $HOME\ledgerloom_student

   python -m venv .venv
   .\.venv\Scripts\Activate.ps1
   python -m pip install -U pip

If activation is blocked, run this once:

.. code-block:: powershell

   Set-ExecutionPolicy -Scope CurrentUser RemoteSigned

Then activate again:

.. code-block:: powershell

   .\.venv\Scripts\Activate.ps1

3) Install LedgerLoom from PyPI
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. code-block:: powershell

   pip install -U ledgerloom
   ledgerloom --help

4) Create a workbook project
^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. code-block:: powershell

   ledgerloom init --profile workbook my_books
   cd my_books

5) Run the workflow (check → build)
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. code-block:: powershell

   ledgerloom check --project . --run-id run1
   ledgerloom build --project . --run-id run1

6) View your outputs
^^^^^^^^^^^^^^^^^^^^

.. code-block:: powershell

   dir outputs\run1\artifacts

Common gotchas (Windows)
^^^^^^^^^^^^^^^^^^^^^^^^

- If ``ledgerloom`` is not recognized, your venv is not active. Run:
  ``.\.venv\Scripts\Activate.ps1``
- If you pasted a multi-line command and PowerShell says something like
  “command not found”, re-run it as **one line**.

macOS (Terminal)
----------------

1) Install Python (recommended: Homebrew)
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

If you don’t have Homebrew, install it from brew.sh.

Then:

.. code-block:: bash

   brew install python
   python3 --version

2) Create a workspace + virtual environment
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. code-block:: bash

   mkdir -p ~/ledgerloom_student
   cd ~/ledgerloom_student

   python3 -m venv .venv
   source .venv/bin/activate
   pip install -U pip

3) Install LedgerLoom from PyPI
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. code-block:: bash

   pip install -U ledgerloom
   ledgerloom --help

4) Create a workbook project
^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. code-block:: bash

   ledgerloom init --profile workbook my_books
   cd my_books

5) Run the workflow (check → build)
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. code-block:: bash

   ledgerloom check --project . --run-id run1
   ledgerloom build --project . --run-id run1

6) View your outputs
^^^^^^^^^^^^^^^^^^^^

.. code-block:: bash

   ls -1 outputs/run1/artifacts

Common gotchas (macOS)
^^^^^^^^^^^^^^^^^^^^^^

- Prefer ``python3`` (not ``python``) unless you know ``python`` points to Python 3.
- If ``ledgerloom`` is “not found”, you likely forgot: ``source .venv/bin/activate``.
