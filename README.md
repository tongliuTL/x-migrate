# x-migrate

[![PyPI version](https://img.shields.io/pypi/v/x-migrate)](https://pypi.org/project/x-migrate/)
[![CI](https://github.com/tongliuTL/x-migrate/actions/workflows/ci.yml/badge.svg)](https://github.com/tongliuTL/x-migrate/actions/workflows/ci.yml)
[![Python 3.11+](https://img.shields.io/badge/python-3.11%2B-blue)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

Migrate X (Twitter) lists and follows between accounts.

Extract members from any X list or following page, then follow them or add them to a list on your destination account — with automatic rate-limit recovery, progress tracking, and a Rich TUI.

## Requirements

- Python 3.11+
- Google Chrome installed

## Installation

```bash
pip install x-migrate
playwright install chromium
```

<details>
<summary>Install from source</summary>

```bash
git clone https://github.com/tongliuTL/x-migrate
cd x-migrate
pip install -e .
playwright install chromium
```
</details>

## Quick Start

> **Tip:** All commands support the short alias `xm` — use it instead of `x-migrate` to save typing.

### 1. Run setup wizard (first time only)

```bash
xm setup
```

Creates `~/.x-migrate/config.toml` with your source and destination Chrome profile paths and daily follow limit.

### 2. Extract members from an X list

```bash
xm extract --source list --url "https://x.com/i/lists/YOUR_LIST_ID"
```

> The `/members` suffix is added automatically if omitted.

Or extract from someone's following list:

```bash
xm extract --source following --account "@handle"
```

### 3. Follow those members from your destination account

```bash
# Follow up to 20 members (default) with an interactive login prompt:
xm follow

# Increase the daily cap:
xm follow --limit 50

# Unattended mode — skips login prompts (requires a saved browser session):
xm follow --auto

# Auto-resume after a rate-limit hit, fully unattended:
xm follow --auto --backoff 2h

# Walk away and let it finish overnight:
xm follow --auto --limit 400 --backoff 3h

# Preview who would be followed without opening a browser:
xm follow --dry-run
```

### 4. Add to a list instead of following

```bash
xm list-add --list-name "My List Name"
```

### 5. Check progress

```bash
xm report
```

Shows migration progress from local data (no browser needed). To cross-check against your live following list:

```bash
xm report --verify
```

## Rate Limits

X typically allows ~400 follows per day. x-migrate detects rate limiting automatically and can either stop (default) or sleep and retry:

| Behaviour | Command |
|-----------|---------|
| Stop on rate limit, re-run manually next day | `xm follow` |
| Stop on rate limit, skip login prompt on re-run | `xm follow --auto` |
| Auto-retry after 2 hours, fully unattended | `xm follow --auto --backoff 2h` |

Accepted backoff formats: `2h`, `90m`, `3600s`. Progress is saved after every follow — it is always safe to Ctrl-C mid-run.

The `--limit` cap is the total for the entire invocation, across all retry sessions.

## Configuration

`~/.x-migrate/config.toml`:

```toml
source_profile = "/path/to/source/profile"
dest_profile   = "/path/to/dest/profile"
daily_limit    = 20       # default for --limit when not specified
active_job     = "a1b2c3d4e5f6"   # auto-set by xm extract
```

## Data Storage

All data is stored under `~/.x-migrate/`:

| Path | Contents |
|------|----------|
| `config.toml` | Settings — profiles, daily limit, active job |
| `profile_source/` | Chrome profile for source account (saved login session) |
| `profile_dest/` | Chrome profile for destination account |
| `progress/` | Per-job JSON files tracking follow status per user |

## Commands

| Command | Description |
|---------|-------------|
| `xm setup` | Create or update `~/.x-migrate/config.toml` |
| `xm extract` | Extract members from a list or following page |
| `xm follow` | Follow extracted members on destination account |
| `xm list-add` | Add extracted members to a named list |
| `xm report` | Show local progress; `--verify` cross-checks live data |

All commands also work as `x-migrate <command>`.

### `xm follow` options

| Flag | Default | Description |
|------|---------|-------------|
| `--limit N` | `daily_limit` from config | Maximum follows for this invocation |
| `--auto` | off | Skip login prompts (uses saved browser session) |
| `--backoff DURATION` | `0` (disabled) | Sleep duration after a rate limit before retrying |
| `--dry-run` | off | Print the follow plan without opening a browser |

## Development

```bash
git clone https://github.com/tongliuTL/x-migrate
cd x-migrate
pip install -e ".[dev]"
pytest
```

See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines on submitting changes.

## Releasing a new version

1. Update `version` in `pyproject.toml`
2. Add a `## [X.Y.Z] — YYYY-MM-DD` section to `CHANGELOG.md`
3. Commit and tag:
   ```bash
   git commit -m "chore: bump version and changelog (vX.Y.Z)"
   git tag vX.Y.Z
   git push && git push --tags
   ```
4. GitHub Actions runs tests, builds the wheel, publishes a GitHub Release, and pushes to PyPI automatically.

Pre-releases (e.g. `v0.2.0-beta.1`) are automatically marked as pre-release on GitHub.

## Contributing

Bug reports, feature requests, and pull requests are welcome — see [CONTRIBUTING.md](CONTRIBUTING.md).

## License

[MIT](LICENSE)
