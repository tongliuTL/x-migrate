# Changelog

All notable changes to x-migrate are documented here.
Format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).
Versioning follows [Semantic Versioning](https://semver.org/).

---

## [0.1.0] — 2026-03-18

### Added
- `x-migrate setup` — interactive wizard to create `~/.x-migrate/config.toml`
- `x-migrate extract` — intercepts X GraphQL responses to collect members from a list or following page
- `x-migrate follow` — follows extracted members from destination account with `--limit` and `--dry-run`
- `x-migrate list-add` — adds extracted members to a named X list
- `x-migrate report` — scrapes destination following and compares against extracted members
- Rich TUI: live progress bar, colored status output, summary table
- Unified progress store at `~/.x-migrate/progress/{job-id}.json`
- `active_job` tracking in config — `extract` sets it, other commands read it
- Human-like random delays and rate-limit detection/stop
- 24 tests covering all core logic (no browser required)
