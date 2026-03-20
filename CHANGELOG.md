# Changelog

All notable changes to x-migrate are documented here.
Format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).
Versioning follows [Semantic Versioning](https://semver.org/).

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
