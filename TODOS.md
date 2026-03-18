# TODOS

## P2 — Post-v1 / Before v2

### Adapter Protocol for Multi-Platform Support

**What:** Define `SourceAdapter` and `DestinationAdapter` Protocol classes in
`src/x_migrate/adapters.py` (or inline in `__init__.py`).

**Why:** The CEO plan scopes Bluesky/Mastodon adapters to v2. Without a protocol
interface in v1, adding a second adapter will require refactoring the existing
X-specific code rather than simply adding a new file.

**Pros:** Makes v2 adapter addition a new file, not a refactor. Zero runtime cost.
Documents the intended extensibility clearly.

**Cons:** Premature abstraction if Bluesky support is never built. Minor noise in
the codebase if only one implementation ever exists.

**Context:** Current architecture: `extract.py` and `follow.py` are X-specific.
The Protocol stubs would be ~10 lines total — `SourceAdapter.extract() -> list[Member]`
and `DestinationAdapter.apply(member) -> str`. The X adapter is the sole implementation.

**Depends on:** v1 shipping.

---

### Self-Healing GraphQL Schema Detection

**What:** On a 0-members result from `x-migrate extract`, print the most recent
intercepted response URLs to help identify if X renamed the endpoint.

**Why:** X has renamed GraphQL endpoints before. Today a URL change silently returns
0 members with no actionable diagnostic. The fix: track all intercepted URLs during
the session and show them when extraction returns 0.

**Pros:** Turns a "why did it break?" session into a 10-second diagnosis.

**Cons:** Must be careful not to log URLs that contain auth tokens. Requires filtering
before output/logging.

**Context:** Current behavior: `extract.py` prints `[ListMembers: +0 users, total: 0]`.
The fix adds a small URL log buffer in `extract.py` that's dumped on 0-members exit.
Companion: add a `--debug-responses` flag to `x-migrate extract` that writes all
intercepted URLs to `~/.x-migrate/debug-{datetime}.log`.

**Depends on:** v1 shipping.
