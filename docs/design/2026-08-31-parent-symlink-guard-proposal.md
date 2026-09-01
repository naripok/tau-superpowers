# Proposal: Parent-symlink guard

## Intent

The installer writes every managed entry through two base directories: `~/.tau/skills` and `~/.tau/extensions`. When a base directory is itself a symlink, the copy, the delete propagation, and the stamp-bounded deletion act through the link. The pre-copy propagation model linked per-skill directories. A base link into such a second checkout makes the installer write into and delete from a tree it does not own. A dangling base link passes preflight today and fails inside `mkdir -p` with a bare mkdir error. That failure breaks the all-or-nothing stop rule in spirit. The guard turns a symlinked base into a preflight stop with a clear error and remedy.

## Scope

**In scope:**

- A preflight stop when a managed base directory is a symlink, regardless of its resolution
- An error message that names every offending base and the remedy
- A spec delta against `docs/specs/subagent-dispatch.md` with two MODIFIED requirements
- Installer tests for the stop and for the unchanged check comparison through a link
- README and header comment updates that document the rule

**Out of scope:**

- A guard for `~/.tau` itself
- Migration of base-level symlinks, because no produced layout ever created one
- Any `--check` enforcement change, because the check stays read-only and compares through the resolved path

## Approach

`preflight` gains a base check that runs before destination classification. The check tests each base path with `-L`. This test examines the final path component only, so a symlinked `~/.tau` with real bases inside passes. A symlink counts regardless of resolution: dangling, foreign target, or target inside the source repository. A real or absent base passes.

Any offending base stops the install with exit 1 before any destination change, including the stale-entry and repository-link cleanups. The error block mirrors the existing conflict listing:

```
Error: these base directories are symlinks and block installation:
  <path>
No destination was changed. Remove each symlink or replace it with a real directory, then run this installer again.
```

When a base link and a destination conflict both exist, the base error appears first. The conflict error appears on the next run after the base fix. The two conditions carry different remedies, so the messages stay separate.

Alternatives considered:

- Migrate base links that resolve into the source repository. Rejected: no produced layout ever had base-level links, so the migration path is dead code.
- Refuse also when `~/.tau` itself is a symlink. Rejected: the tau home location is the user's choice, and the bases under it stay checked, so the foreign-tree hazard stays covered.

## Impact

- `install.sh`: new base check at the start of `preflight`
- `tests/test-install.sh`: five new scenario invocations
- `README.md`, the `install.sh` header comment, and the `tests/test-install.sh` header comment: one rule sentence each where install behavior is documented
- Living spec `docs/specs/subagent-dispatch.md`: sync during the finishing flow
