---
status: ACTIVE
generated-by: /plan-eng-review
date: 2026-03-18
---

# x-migrate Implementation Plan

Decisions locked in by the eng review. Start here before touching code.

---

## Package Structure

```
x-migrate/
├── pyproject.toml
├── README.md
├── src/
│   └── x_migrate/
│       ├── __init__.py
│       ├── cli.py          # typer app: extract / follow / list-add / report / setup
│       ├── config.py       # ~/.x-migrate/config.toml load/save
│       ├── browser.py      # launch_context(profile_path) -> BrowserContext  ← bare context
│       ├── extract.py      # list + following extraction (GraphQL intercept)
│       ├── follow.py       # follow logic + human_delay + rate-limit detect
│       ├── list_add.py     # add-to-list logic (from populate_list.py)
│       ├── progress.py     # unified {username: status} store
│       └── ui.py           # Rich TUI: progress bar, summary table
└── tests/
    ├── conftest.py
    ├── test_extract.py
    ├── test_follow.py
    ├── test_progress.py
    └── fixtures/
        ├── list_members_response.json
        └── following_response.json
```

Runtime data (NOT working dir):
```
~/.x-migrate/
  config.toml
  profile_source/
  profile_dest/
  progress/
    {sha256[:12]-of-source}.json   # {username: {status, name, id}}
```

---

## CLI Interface

```
x-migrate setup
    # Wizard → ~/.x-migrate/config.toml

x-migrate extract --source list --url https://x.com/i/lists/...
x-migrate extract --source following --account @handle
    # Opens Chrome (source profile), intercepts GraphQL, saves progress/{job-id}.json

x-migrate follow [--limit 20] [--dry-run]
    # Opens Chrome (dest profile), follows members
    # --dry-run: print plan, no browser launched

x-migrate list-add --list-name NAME
    # Opens Chrome (dest profile), adds members to a named list

x-migrate report
    # Opens Chrome (dest profile), scrapes following list, compares vs members
```

---

## Architecture Decisions

| Decision | Choice | Reason |
|---|---|---|
| `browser.py` API | Returns bare `BrowserContext` | Each command attaches its own `page.on('response', handler)`. Explicit > clever. |
| `list-add` command | Included in v1 | `add_to_list()` already works in populate_list.py — low lift, completes accepted scope |
| Job IDs | `sha256(source_arg.encode()).hexdigest()[:12]` | Stable, short, no collisions at personal use scale |
| Active job tracking | `extract` writes `active_job = "<job-id>"` to config.toml after save | `follow`/`list-add`/`report` read this to find the current progress file — no `--job-id` flag needed |
| Progress format | `{username: {status: str, name: str, id: str}}` | Richer than plain `{username: status}` — preserves display name + Twitter ID for TUI and future use |
| Interceptor state | Closure inside each command's `run_*()` fn | No module-level globals; `captured = {}` defined locally, handler closes over it |
| `human_delay()` guard | `max(3.0, human_delay())` must be preserved | `random.gauss(9, 2.5)` can theoretically return < 0 |
| Tests | Built in same PR, not deferred | 15 min with CC+gstack; silently-failing parsers are the highest-risk components |

---

## Critical Gaps to Resolve (were flagged in review)

### 1. Config missing on first run
Any command that needs config (`follow`, `extract`, `list-add`, `report`) must check at startup:
```python
if not config_path.exists():
    print("No config found. Run 'x-migrate setup' first.")
    raise SystemExit(1)
```

### 2. Chrome not installed
Catch `playwright._impl._errors.Error` at `launch_persistent_context`:
```python
except Exception as e:
    if "chrome" in str(e).lower() or "executable" in str(e).lower():
        print("Chrome not found. Install it: brew install --cask google-chrome")
        raise SystemExit(1)
    raise
```

### 3. Dest account confirmation before first follow
After launching Chrome and navigating to x.com/home, auto-detect `@handle` from the profile tab link and prompt:
```
Confirm: following as @handle? [y/N]
```
Abort with clear message if user says no.

### 4. Intercept handler must wrap full body in try/except
Playwright silently swallows exceptions thrown inside `page.on("response", handler)` coroutines.
Every `intercept_*` handler must wrap its entire body:
```python
async def intercept_members(response):
    try:
        ...
    except Exception as e:
        print(f"  [intercept error: {e}]")
```

### 5. Config TOML parse error
`config.load()` must catch `tomllib.TOMLDecodeError`:
```python
except tomllib.TOMLDecodeError:
    print("Config file is corrupted. Run 'x-migrate setup' to recreate it.")
    raise SystemExit(1)
```

### 6. Follow with 0 pending members
Before launching Chrome in `follow`/`list-add`, check remaining count:
```python
remaining = [u for u, d in progress.items() if d["status"] not in FINAL_STATUSES]
if not remaining:
    print("All members already processed! Nothing to do.")
    raise SystemExit(0)
```

### 7. Session-expired detection during extract scroll
After stall exit with 0 new members, check if the page URL has drifted to login:
```python
if not members and "/login" in page.url or "/i/flow" in page.url:
    print("Session expired — please log in again in the browser and re-run.")
```

### 8. Bugs to also fix in list_add.py
`populate_list.py` saves progress as a list (`json.dump(list(done), f)`). The refactored
`list_add.py` must use the unified `{username: {status, name, id}}` format instead.

---

## Code to Reuse Verbatim

| Function | Source file | Destination |
|---|---|---|
| `parse_members_from_response()` | extract_members.py:16 | extract.py |
| `intercept_following()` parser logic | report.py:16 | extract.py → `parse_following_from_response()` |
| `classify_buttons()` + `get_button_texts()` | follow_members.py:26,38 | follow.py |
| `human_delay()` | follow_members.py:143 | follow.py |
| `page_signals_unavailable()` | follow_members.py:46 | follow.py |
| `FINAL_STATUSES` + progress save/load | follow_members.py:184 | progress.py |
| `add_to_list()` | populate_list.py:24 | list_add.py |

---

## Bugs to Fix During Refactor

- `import math` in follow_members.py — unused
- `consecutive_rate_limits` variable — assigned but never read (dead code)
- Two conflicting progress formats (`{done:[], failed:[]}` vs `{username: status}`) — unify to dict
- `profile_source/` and `profile_dest/` in working dir — move to `~/.x-migrate/`

---

## Test Suite (build in same PR)

| # | Test | File |
|---|---|---|
| T1 | `parse_members_from_response()` with valid fixture | test_extract.py |
| T2 | `parse_members_from_response()` with malformed/empty JSON | test_extract.py |
| T3 | `parse_following_from_response()` with valid fixture | test_extract.py |
| T4 | `classify_buttons()` — all 5 states | test_follow.py |
| T5 | `progress.save()` / `load()` round-trip | test_progress.py |
| T6 | `progress.load()` on missing file → empty dict | test_progress.py |
| T7 | `config.load()` on missing file → clear error | test_config.py |
| T8 | `human_delay()` always returns > 0 | test_follow.py |
| T9 | Job ID: same source → same ID; different source → different ID | test_extract.py |
| T10 | `--dry-run`: no browser launched, expected usernames in output | test_follow.py |
| T11 | `follow_user()` rate_limited path: button stays "follow" after click | test_follow.py |

| T12 | `add_to_list()` already-in-list path: aria-checked=true → no click | test_list_add.py |
| T13 | `browser.py` Chrome-not-found: exception message contains "chrome" → SystemExit(1) | test_browser.py |
| T14 | `config.load()` on malformed TOML → SystemExit(1) with friendly message | test_config.py |
| T15 | `follow` with 0 pending members → exits before launching browser | test_follow.py |
| T16 | session-expired URL detection: `/login` in URL → prints session-expired message | test_extract.py |

Fixtures needed:
- `fixtures/list_members_response.json` — captured from a real ListMembers GraphQL response
- `fixtures/following_response.json` — captured from a real Following GraphQL response (see report.py `intercept_following` for the expected shape)

---

## NOT in Scope (v1)

- Bluesky/Mastodon adapters (see TODOS.md)
- CSV export
- Scheduled/daemon mode
- Web UI
- PyPI publish automation (manual for v1)

---

## Implementation Order

1. **Scaffold** — `pyproject.toml`, `src/x_migrate/__init__.py`, `cli.py` skeleton, `conftest.py`
2. **Config** — `config.py` + `x-migrate setup` wizard + `config.load()` guard
3. **Progress** — `progress.py` unified store + T5/T6 tests
4. **Browser** — `browser.py` bare context + Chrome error handling
5. **Extract** — `extract.py` list + following + T1/T2/T3/T9 tests
6. **Follow** — `follow.py` + `x-migrate follow --dry-run` + T4/T8/T10/T11 tests
7. **List-add** — `list_add.py` + `x-migrate list-add`
8. **Report** — `report.py` refactored as `x-migrate report`
9. **Rich TUI** — `ui.py` + wire into follow/list-add (stop Live before any `input()`)
10. **Packaging** — `pyproject.toml` entry point, README (include `playwright install chromium` step), test on clean venv
