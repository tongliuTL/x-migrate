# x-migrate

Migrate X (Twitter) lists and follows between accounts.

**Note:** This is a personal tool for migrating X (Twitter) accounts. It helps you extract members from an X list or following list and then follow or add those members to a list on your destination account.

## Requirements

- Python 3.11+
- Google Chrome installed

## Installation

```bash
git clone https://github.com/tongliuTL/x-migrate
cd x-migrate
python3 -m venv venv
source venv/bin/activate
pip install -e .
playwright install chromium
```

## Quick Start

### 1. Run setup wizard (first time only)

```bash
x-migrate setup
```

This creates `~/.x-migrate/config.toml` with your source and destination Chrome profile paths and daily follow limit.

### 2. Extract members from an X list

```bash
x-migrate extract --source list --url "https://x.com/i/lists/YOUR_LIST_ID/members"
```

Or extract from someone's following list:

```bash
x-migrate extract --source following --account "@handle"
```

### 3. Follow those members from your destination account

Follow up to 20 members (default):

```bash
x-migrate follow
```

Increase the limit:

```bash
x-migrate follow --limit 50
```

Preview who would be followed without launching the browser:

```bash
x-migrate follow --dry-run
```

### 4. Add to a list instead of following

```bash
x-migrate list-add --list-name "My List Name"
```

### 5. Check progress

```bash
x-migrate report
```

Shows your following/members counts and migration progress.

## Rate Limits

X typically allows ~400 follows per day. The script detects rate limiting and stops automatically. Re-run the next day — your progress is saved in `~/.x-migrate/progress/`.

## Configuration

Configuration is stored in `~/.x-migrate/config.toml`:

```toml
source_profile = "/path/to/source/profile"
dest_profile = "/path/to/dest/profile"
daily_limit = 20
active_job = "list_name_or_url"
```

## Data Storage

All data is stored in `~/.x-migrate/`:

- `config.toml` — settings (profiles, daily limit)
- `profile_source/` — Chrome profile for source account (contains login session)
- `profile_dest/` — Chrome profile for destination account
- `progress/` — per-job progress files (JSON format, automatically managed)

## Development

Install with dev dependencies:

```bash
pip install -e ".[dev]"
```

Run tests:

```bash
pytest
```

## Commands

- `x-migrate setup` — Create or update configuration
- `x-migrate extract` — Extract members from a list or following list
- `x-migrate follow` — Follow extracted members on destination account
- `x-migrate list-add` — Add extracted members to a list
- `x-migrate report` — Show progress and statistics
