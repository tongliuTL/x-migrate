# Changelog

All notable changes to x-migrate are documented here.
Format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).
Versioning follows [Semantic Versioning](https://semver.org/).

---

## [0.1.3] — 2026-03-25

### Changed
- Extracted `_build_user_record()` helper in `extract.py` — both `parse_members_from_response` and `parse_following_from_response` now share a single source of truth for user record construction.
- Removed dead `added_count`/`failed_count` counters in `list_add.py` — they were incremented but never read; `ui.print_summary` handles all reporting.
- Single-pass partition in `report_cmd.py` — `following`/`not_following` split now computes `u.lower()` once per username instead of twice.
- Added `.coverage` and `htmlcov/` to `.gitignore`.
- Removed self-evident comments throughout `extract.py`, `follow.py`, and `list_add.py`.

---

## [0.1.2] — 2026-03-21

### Fixed
- `xm extract` no longer silently drops a full page of results when a single malformed entry is encountered. Previously the try/except wrapped the entire entries loop, so one bad entry aborted all remaining users from that page. Each entry is now handled independently — a malformed entry is skipped, and the rest are still captured.

### Changed
- Removed a redundant session-limit counter in `xm follow` — the `pending[:limit]` slice already enforces the cap, so the secondary check could never trigger.
- Moved `Counter` import to module level in `ui.py` (was deferred inside a function body for no reason).
- Removed several narrating comments that described exactly what the adjacent code already made obvious.

### Test Coverage
- 53 tests, 59% overall coverage (unchanged — all existing tests continue to pass)

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
