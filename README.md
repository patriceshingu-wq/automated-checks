# automated-checks

A GitHub Actions continuous integration (CI) pipeline that rebuilds a fraud-detection model
from scratch on a clean machine every time code is pushed to `main` or a pull request targets
it. If the data generation or model training breaks, the run fails and GitHub shows a red X
before the change is merged.

This folder holds the workflow definition ([`ci.yml`](ci.yml)) and documents how it works,
how to run it, and where it falls short.

## Contents

- [What it does](#what-it-does)
- [How a run flows](#how-a-run-flows)
- [Project layout](#project-layout)
- [The workflow, block by block](#the-workflow-block-by-block)
- [What the pipeline checks, and what it does not](#what-the-pipeline-checks-and-what-it-does-not)
- [Setup](#setup)
- [Verify it works](#verify-it-works)
- [Reproduce the checks locally](#reproduce-the-checks-locally)
- [Design decisions](#design-decisions)
- [Limitations and next steps](#limitations-and-next-steps)
- [Troubleshooting](#troubleshooting)
- [Skills demonstrated](#skills-demonstrated)

---

## What it does

On every push to `main` and every pull request aimed at `main`, the pipeline:

1. Starts a fresh Ubuntu virtual machine.
2. Checks out the repository.
3. Installs Python 3.11.
4. Creates a virtual environment and installs `pandas` and `scikit-learn`.
5. Runs `generate_data.py` to build a synthetic transactions dataset.
6. Runs `train_model.py` to train a decision-tree classifier and print its metrics.

If any step exits with an error, the job stops and the run is marked failed.

## How a run flows

```text
git push / pull request to main
            |
            v
   GitHub Actions trigger
            |
            v
   fresh ubuntu-latest VM
            |
   checkout -> Python 3.11 -> venv + deps
            |
            v
   generate_data.py  ->  02-data/data/transactions.csv
            |
            v
   train_model.py    ->  accuracy / precision / recall printed in the log
            |
            v
   all steps exit 0  ?   green check
   any step fails    ?   red X, later steps skipped
```

## Project layout

```text
ai-ml-platform/
├── .github/
│   └── workflows/
│       └── ci.yml          # the live copy GitHub reads (repository root)
├── 02-data/
│   └── src/
│       ├── generate_data.py   # builds 5,000 synthetic transactions
│       └── train_model.py     # trains and scores the model
└── automated-checks/
    ├── ci.yml              # source copy of the workflow, documented here
    └── README.md
```

GitHub only runs workflows found at `.github/workflows/` in the repository root. The copy in
this folder is the documented source; it must be copied to that location to run
(see [Setup](#setup)).

## The workflow, block by block

### Trigger

```yaml
on:
  push:
    branches: [main]
  pull_request:
    branches: [main]
```

The pipeline runs when commits land on `main` and when a pull request is opened or updated
against `main`. Running on pull requests means a broken change is flagged before it is merged.

### Job and runner

```yaml
jobs:
  build-and-test:
    runs-on: ubuntu-latest
```

One job, `build-and-test`, runs on a GitHub-hosted Ubuntu virtual machine. The machine is
created new for each run and discarded afterward, so nothing left over from an earlier run
can make a check pass by accident. That is what makes the result reproducible.

### Steps

| # | Step | What it does |
|---|------|--------------|
| 1 | Checkout code | `actions/checkout@v4` copies the repository onto the runner. |
| 2 | Set up Python 3.11 | `actions/setup-python@v5` installs the interpreter version the project expects. |
| 3 | Create venv and install deps | Creates an isolated `venv` and runs `pip install pandas scikit-learn`. |
| 4 | Generate training data | `cd 02-data/src && python generate_data.py` writes `../data/transactions.csv`. |
| 5 | Train and validate model | `cd 02-data/src && python train_model.py` trains and prints metrics. |

Each `run:` step re-activates the virtual environment with `source venv/bin/activate`,
because every step starts in a new shell.

The scripts use relative paths such as `../data/transactions.csv`, so the steps change into
`02-data/src` before running them. Running them from another directory would fail to find the
data.

## What the pipeline checks, and what it does not

**It does check that:**

- the dependencies install on a clean machine, so the project is not relying on packages that
  only exist on one developer's laptop;
- `generate_data.py` runs without raising an error and produces the dataset;
- `train_model.py` can load that dataset, train, score and finish without raising an error.

**It does not check:**

- model quality. `train_model.py` prints accuracy, precision and recall but contains no
  assertions, so a model with poor metrics would still pass;
- code style or formatting (there is no linter);
- unit tests (the project has none yet);
- deployment. This is the "CI" half of CI/CD; nothing is released or shipped.

Being clear about this matters: a green check means "the pipeline ran end to end", not "the
model is good".

## Setup

Requirements: a GitHub account (free tier is enough) and this repository pushed to GitHub.

1. Create the workflow location in the repository root:

   ```bash
   mkdir -p .github/workflows
   cp automated-checks/ci.yml .github/workflows/ci.yml
   ```

2. Commit and push, staging the file by name:

   ```bash
   git add .github/workflows/ci.yml
   git commit -m "Add automated-checks CI workflow"
   git push
   ```

3. Open the repository on GitHub and click the **Actions** tab. The run appears within a few
   seconds. If Actions is disabled, enable it under **Settings → Actions**.

YAML is indentation-sensitive. Use two spaces per level and never tabs.

## Verify it works

1. **Green run.** Push a harmless change (for example, edit a comment in
   `02-data/src/generate_data.py`). Confirm a new run appears in the Actions tab and every step
   shows a green check.
2. **Red run.** On a throwaway branch, introduce a deliberate error, such as misspelling a
   column name in `train_model.py`. Open a pull request into `main`. Confirm the run fails at
   the **Train and validate model** step and that the log shows the traceback.
3. **Recovery.** Fix the error, push again, and confirm the run turns green.

Catching the deliberate failure in step 2 is the real proof that the pipeline does its job.

## Reproduce the checks locally

To debug a failing run without pushing, repeat the steps on your own machine from the
repository root (Git Bash on Windows, macOS or Linux):

```bash
python -m venv venv
source venv/bin/activate        # Windows Git Bash: source venv/Scripts/activate
pip install pandas scikit-learn

cd 02-data/src
python generate_data.py
python train_model.py
```

Do not commit the `venv` folder.

## Design decisions

- **Clean runner every time.** Slower than reusing a machine, but results do not depend on
  hidden state.
- **A virtual environment inside CI.** Mirrors local development and keeps the project's
  packages separate from the runner's system Python.
- **Pinned action versions (`@v4`, `@v5`).** Prevents an upstream change from silently
  altering the pipeline.
- **One job.** The project is small and its steps depend on each other (data before
  training), so splitting into several jobs would add overhead without benefit.
- **Triggers on `main` and pull requests only.** Avoids spending runner time on every
  experimental branch while still gating what reaches `main`.

## Limitations and next steps

Concrete improvements, roughly in order of value:

1. **Fail the build on bad model quality.** Add a check (an `assert` in the script or a
   separate step) that exits non-zero when recall or precision falls below a threshold.
2. **Add unit tests** with `pytest` for the data generation and training functions, and run
   them as a step.
3. **Add a linter** such as `ruff` to catch errors and style problems early.
4. **Cache pip downloads** with `actions/setup-python`'s `cache: pip` option to shorten runs.
5. **Pin dependency versions** in a `requirements.txt` so builds do not change when a new
   library version is released.
6. **Test against a Python version matrix** (for example 3.10, 3.11 and 3.12).
7. **Add a delivery stage** (the "CD" half) that builds a Docker image and pushes it to a
   registry only after the checks pass.
8. **Protect `main`** with a branch rule that requires this check to pass before merging.

## Troubleshooting

| Symptom | Likely cause and fix |
|---------|----------------------|
| No run appears in the Actions tab | The file is not at `.github/workflows/ci.yml` in the repository root, or the filename is misspelled. |
| `Invalid workflow file` | Almost always indentation. Use two spaces, no tabs. |
| `No such file or directory` on `generate_data.py` | The `cd` path in the workflow does not match the folder name. This repository uses `02-data/src`. |
| `FileNotFoundError: ../data/transactions.csv` | The training step ran without data, or from the wrong directory. Check that the generate step succeeded and that both steps `cd` into `02-data/src`. |
| `ModuleNotFoundError` | A dependency is missing from the `pip install` line. |
| `git push` rejected | Your local branch is behind GitHub. Run `git pull`, then push again. |
| A step shows a red X | The pipeline is working as designed. Open the step, read the error, fix the cause and push again. |

## Skills demonstrated

- Writing and debugging a GitHub Actions workflow in YAML
- Choosing triggers, runners and pinned action versions
- Reproducible environments with virtual environments and clean CI machines
- Separating data generation from training and running both automatically
- Reading CI logs to diagnose failures
- Being explicit about what automated checks do and do not guarantee
