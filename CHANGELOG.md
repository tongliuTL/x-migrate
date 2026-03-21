# Changelog

All notable changes to x-migrate are documented here.
Format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).
Versioning follows [Semantic Versioning](https://semver.org/).

---

## [0.1.1] — 2026-03-21

### Fixed
- `xm extract --source list` now navigates to the `/members` tab instead of the list timeline (posts). URLs without `/members` suffix are auto-corrected.
- Extract scrolling: replaced `mouse.wheel` with JS-based scrolling targeting X's primary column container, fixing infinite-scroll loading for large lists.
- Extract response interception: switched from `page.on("response")` to route-based interception (`page.route`) to eliminate `Protocol error (Network.getResponseBody)` errors caused by Chromium discarding response bodies.

### Changed
- `xm report` now reads the local progress file by default (no browser needed). Use `xm report --verify` for the previous behavior of scraping the live following list.

### Test Coverage
- 53 tests (up from 50), 59% overall code coverage

| Module | Stmts | Cover |
|--------|-------|-------|
| config.py | 21 | 100% |
| ui.py | 21 | 100% |
| browser.py | 18 | 89% |
| progress.py | 50 | 86% |
| extract.py | 142 | 75% |
| cli.py | 46 | 52% |
| follow.py | 147 | 50% |
| report_cmd.py | 103 | 40% |
| list_add.py | 82 | 32% |
| **Total** | **630** | **59%** |

---

## [0.1.0] — 2026-03-18

### Added
- `xm` short alias — `xm` works everywhere `x-migrate` does (e.g. `xm follow`, `xm extract`)
- `xm setup` — interactive wizard to create `~/.x-migrate/config.toml`
- `xm extract` — intercepts X GraphQL responses to collect members from a list or following page
- `xm follow` — follows extracted members from destination account with `--limit` and `--dry-run`
- `xm list-add` — adds extracted members to a named X list
- `xm report` — scrapes destination following and compares against extracted members
- Rich TUI: live progress bar, colored status output, summary table
- Unified progress store at `~/.x-migrate/progress/{job-id}.json`
- `active_job` tracking in config — `extract` sets it, other commands read it
- Human-like random delays and rate-limit detection/stop
- 50 tests covering all core logic (no browser required)
