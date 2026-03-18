# x-migrate CEO Plan Review
Generated: 2026-03-18 | Mode: SCOPE_EXPANSION | Approach: Proper CLI Tool

---

## Accepted Scope (v1)

1. **Proper CLI package** — `x-migrate extract / follow / report / setup` via typer
2. **Extract from X Following** — `--source following --account @handle` (not just lists)
3. **Rich TUI** — live progress bar, ETA, rate-limit status via `rich` library
4. **`--dry-run` mode** — preview who'd be followed, no browser needed
5. **PyPI packaging** — `pip install x-migrate`, pyproject.toml + entry point
6. **`~/.x-migrate.toml` config** — one-time setup, then just `x-migrate follow`

---

## Proposed Package Structure

```
x-migrate/
├── pyproject.toml              # pip install x-migrate → x-migrate CLI entry point
├── README.md
├── src/
│   └── x_migrate/
│       ├── __init__.py
│       ├── cli.py              # typer app: extract / follow / report / setup
│       ├── config.py           # ~/.x-migrate.toml load/save
│       ├── browser.py          # shared: launch_persistent_context()
│       ├── extract.py          # list + following extraction (GraphQL intercept)
│       ├── follow.py           # follow logic + human_delay + rate-limit detect
│       ├── progress.py         # unified {username: status} store
│       └── ui.py               # Rich TUI: progress bar, summary table
└── ~/.x-migrate/               # runtime data (NOT working dir)
    ├── config.toml
    ├── profile_source/         # Chrome persistent session (source account)
    ├── profile_dest/           # Chrome persistent session (dest account)
    └── progress/
        └── {job-id}.json       # per-migration progress store
```

---

## System Architecture

```
  CLI (cli.py)
    │
    ├── extract ──► browser.py ──► Chrome (source account)
    │                │                └── GraphQL intercept
    │                ▼                    ├── ListMembers endpoint
    │            extract.py               └── Following endpoint
    │                └──► progress/{job}.json (members list)
    │
    ├── follow  ──► browser.py ──► Chrome (dest account)
    │                │                └── DOM automation
    │                ▼                    ├── detect Follow button
    │            follow.py                ├── click + verify
    │                │                   └── rate-limit detect
    │                └──► progress/{job}.json (status per user)
    │
    ├── report  ──► browser.py ──► Chrome (dest account)
    │                └──► scrape Following list → compare vs members
    │
    └── setup   ──► config.py ──► ~/.x-migrate/config.toml
                    └── wizard: source URL/handle, dest handle, daily limit
```

## Data Flow — follow command

```
  members list ──► filter(not in FINAL_STATUSES) ──► follow_user()
       │                                                   │
     [nil?]                                         happy:  "followed"
     abort w/                                       nil:    page_unavailable
     clear msg                                      empty:  no_button → "unavailable"
                                                    error:  exception → "error"
                                                            │
                                                    progress.save(username, status)
                                                            │
                                                    rate_limited? → STOP session
```

---

## CLI Interface

```
x-migrate setup
    # Wizard: configure source, dest, daily_limit → ~/.x-migrate/config.toml

x-migrate extract --source list --url https://x.com/i/lists/...
x-migrate extract --source following --account @handle
    # Opens Chrome (source profile), scrolls, intercepts GraphQL, saves members

x-migrate follow [--limit 20] [--dry-run]
    # Opens Chrome (dest profile), follows members up to daily limit
    # --dry-run: prints plan, no browser, no follows

x-migrate report
    # Opens Chrome (dest profile), scrapes real following list, compares vs members
```

---

## Architecture Decisions

| Decision | Choice | Reason |
|---|---|---|
| CLI framework | typer | Auto --help, type hints, cleaner than argparse |
| Progress format | `{username: status}` dict | Single format, per-user history, resumable |
| Profile storage | `~/.x-migrate/` | Works from any directory, not tied to working dir |
| Job IDs | Hash of source URL/handle | Multiple migrations don't clobber each other |
| Browser launch | Shared `browser.py` | Eliminates 3× copy-pasted `launch_persistent_context()` |

---

## Error & Rescue Map

| Codepath | Failure | Status |
|---|---|---|
| `page.goto()` | Timeout, network error | ✅ caught → "error" |
| `response.json()` | Malformed JSON from X | ✅ caught silently in intercept |
| `page.inner_text()` | Element not found | ✅ wrapped in try/except |
| `page.evaluate()` JS | X changes DOM | ✅ returns False, caught |
| Follow button click | X silently rejects | ✅ state-check → "rate_limited" |
| `open("members.json")` | File not found | ✅ clear error message |
| `launch_persistent_context` | Chrome not installed | 🔴 CRITICAL GAP — crashes with cryptic Playwright error |
| ListMembers GraphQL URL | X renames endpoint | 🔴 CRITICAL GAP — 0 members, no actionable message |
| Config missing | First run before setup | 🔴 CRITICAL GAP — must redirect to `x-migrate setup` |

---

## Security Notes

| Threat | Status |
|---|---|
| Chrome profiles store session cookies (local only) | ✅ acceptable |
| `members.json` contains public usernames/IDs | ✅ acceptable |
| X detects automation, locks account | ⚠️ partially mitigated by human delays |
| User runs with wrong dest account | 🔴 GAP — confirm dest account before first follow |
| Hard-coded list URL | ✅ fixed — becomes CLI arg |

---

## Rate Limit — Honest Assessment

Rate limits on new accounts are **server-side trust scores**, not detection of script behavior.
Even a human manually clicking Follow hits the same ~15–20/day ceiling on a new account.

**What engineering can improve:**
- Better entropy in delays and scroll behavior before following
- Stop immediately on first rate_limited signal (don't retry)
- Daily limit enforced by the tool, not just by X

**What engineering cannot solve:**
- X's per-account follow quota for new accounts — only time fixes this
- X's ML-based bot detection at scale

This is a documented limitation, not a bug. Document it clearly in README.

---

## Existing Code to Reuse Verbatim

- `parse_members_from_response()` — GraphQL parser
- `classify_buttons()` + `get_button_texts()` — follow button detection
- `human_delay()` — weighted random delay distribution
- `page_signals_unavailable()` — suspension/deletion detection
- `FINAL_STATUSES` set + progress save/load pattern

## Bugs to Fix During Refactor

- `import math` in follow_members.py — unused, remove
- `consecutive_rate_limits = 0` assigned in follow branches but never read — dead code
- Two conflicting progress formats (`{done:[], failed:[]}` vs `{username: status}`) — unify to dict format
- `profile_source/` and `profile_dest/` in working dir — move to `~/.x-migrate/`

---

## Implementation Notes (Temporal Interrogation)

```
HOUR 1 (scaffolding):
  → Check if "x-migrate" is available on PyPI before committing to that name
  → Use typer (not click) — cleaner for this use case

HOUR 2-3 (extract + follow):
  → Following extraction: GraphQL endpoint is "Following" not "ListMembers"
    Verify exact URL pattern and response structure before coding
  → Job IDs: hash of source URL/handle → one progress file per migration

HOUR 4-5 (Rich TUI):
  → Rich Live display conflicts with input() — pause/stop Live before prompting
  → ETA = rolling average of follow times, not just total count

HOUR 6+ (packaging + publish):
  → PyPI publish needs account + API token — document in CONTRIBUTING
  → Start at version 0.1.0, don't promise semver stability yet
```

---

## TODOs

### P1 — Before PyPI publish
- **Smoke test suite (pytest):** test GraphQL parser, button classifier, progress store.
  These three components fail silently today and are most likely to break on X DOM changes.

### P3 — Future roadmap
- **Bluesky/Mastodon adapters:** Design the source/destination adapter interface in v1
  so adding Bluesky later doesn't require a rewrite. Architecture: source adapters ×
  destination adapters. X→X is adapter pair #1.

---

## NOT in scope (v1)
- Bluesky/Mastodon source or destination
- CSV export
- Scheduled/daemon mode (auto-run daily quota)
- Web UI / GUI
- Cross-platform migration (X following → Bluesky)

## Dream State Delta
After v1 ships: ~60% of 12-month ideal.
Missing: multi-platform adapters, self-healing GraphQL schema detection.
Present: clean CLI, PyPI-installable, both X source types, Rich TUI, dry-run, config file.
