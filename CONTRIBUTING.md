# Contributing to x-migrate

Thank you for your interest in contributing! This document explains how to get set up, what the conventions are, and how to submit a change.

## Prerequisites

- Python 3.11+
- Google Chrome (for integration-style testing against a real browser)
- Git

## Development setup

```bash
git clone https://github.com/tongliuTL/x-migrate
cd x-migrate
pip install -e ".[dev]"
playwright install chromium
```

## Running tests

```bash
pytest
```

All tests are headless (no browser window required). The test suite mocks Playwright entirely, so no X account or network access is needed.

To run a specific file or test:

```bash
pytest tests/test_follow.py -v
pytest tests/test_follow.py::test_backoff_sleeps_and_resumes_after_rate_limit -v
```

## Project layout

```
src/x_migrate/
  cli.py          # Typer entry-points; thin wrappers that call async runners
  follow.py       # Core follow loop — rate-limit detection, backoff, auto mode
  extract.py      # Playwright-based member extraction via XHR interception
  list_add.py     # Add members to a named X list
  report_cmd.py   # Local + live reporting
  progress.py     # Atomic JSON progress store (~/.x-migrate/progress/)
  browser.py      # Playwright context factory
  config.py       # TOML config read/write
  ui.py           # Rich TUI helpers

tests/            # One test file per source module; no browser required
```

## Code conventions

- **No speculative abstractions** — only add indirection when two concrete call-sites already exist.
- **No error handling for impossible cases** — trust framework and internal guarantees; only validate at system boundaries.
- **Comments only for non-obvious WHY** — well-named identifiers carry the what.
- **Typed signatures** — use Python type hints throughout.

## Commit messages

Follow the existing style — lowercase imperative, optionally prefixed with a type:

```
feat: add --auto flag to xm follow
fix: clamp backoff jitter to prevent zero-sleep retries
chore: bump version and changelog (v0.2.0)
```

## Submitting a pull request

1. Fork the repo and create a branch: `git checkout -b feat/my-feature`
2. Make your changes and add or update tests.
3. Verify everything passes: `pytest`
4. Push and open a PR against `main`.

The CI workflow runs `pytest` on every PR. A PR will not be merged unless CI is green.

## Reporting a bug

Open an issue using the [Bug report](.github/ISSUE_TEMPLATE/bug_report.md) template. Include your Python version, OS, and the full traceback.
