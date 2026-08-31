# Proposal: Homogeneous rsync install

## Intent

The installer currently links skills and the extension into `~/.tau`. The deployed extension at `~/.tau/extensions/superpowers-subagent` is a hand-made copy from before the installer existed. Nothing refreshes that copy. A sandbox incident showed the cost: skill changes reached every sandbox through dereferenced symlinks, while the extension code stayed frozen in every project. The installer as written cannot run today: its conflict check aborts on the hand-copied extension destination.

This change gives both resource kinds one propagation model: repository, then `./install.sh`, then `~/.tau`, then the sandbox snapshot. Installed state becomes explicit and checkable. `install.sh --check` detects staleness. The audit for this change also found a self-containment defect: the `receiving-code-review` skill directs the agent to `docs/FLOW_DESCRIPTION.md`, which the install does not carry. In any sandbox outside a checkout of this repository, that reference is dead. Enforcement of self-containment belongs at commit time, where the fix is cheapest, so a pre-commit hook rejects such references and the test suite runs the same scan as a backstop.

## Scope

**In scope:**

- `install.sh`: rsync-based copy install for skills and the extension, single-shot
- Migration from the two current states: symlinked skills and the hand-copied extension directory
- Deletion propagation inside managed entries and across stamp-recorded entries
- An install stamp that records the source, git state, install time, and managed entries
- `install.sh --check` for staleness detection
- An installed self-containment invariant: a pre-commit hook rejects commits whose installed resources carry a path reference that resolves only inside the source checkout, and the installer test suite runs the same scan
- Repair of the checkout-only reference in the `receiving-code-review` skill, so that the shipped repository passes the self-containment scan
- A rewrite of `tests/test-install.sh`, updates to `README.md` and `docs/FLOW_DESCRIPTION.md`, and a living-spec delta for `docs/specs/subagent-dispatch.md`

**Out of scope:**

- tau-sandbox changes. The snapshot already copies real directories with `cp -aL`.
- `catalog.toml` and `providers.json`. Dotfiles-managed symlinks stay untouched.
- Version pinning, wheels, PyPI publishing, and `tau install` migration.
- Per-project installs and worktree source overrides.

## Approach

`install.sh` stays a single-shot bash script and gains an `rsync` dependency. It preflights every destination and the rsync dependency before it changes anything. When a copy fails partway, it reports the failure and exits nonzero, and a later run makes the affected entry match its source. It installs each managed entry with `rsync -a --delete` and a fixed exclude set: `.git`, `.venv`, `__pycache__`, `.mypy_cache`, `.pytest_cache`, `.ruff_cache`, `.worktrees`. It removes a repository-pointing symlink before any write, so the repository is never written through a link. It takes over a real directory at a managed name with itemized output. It aborts on any other conflicting destination with no partial changes. A stamp at `~/.tau/.tau-superpowers-install` records the managed entries. Entries that the stamp records but the source no longer provides get removed. `--check` reruns the same comparison dry, prints differing paths, and changes nothing.

Alternatives considered:

- Uniform symlinks: no machinery, but keeps hidden live state on the host and cannot express installed semantics.
- `tau install`: tau-native for the extension, but it has no skills story, no update command yet, and the monorepo layout does not fit the `git:` form.
- uv-packaged distribution: tau discovers extensions and skills by filesystem path only, and the sandbox syncs `~/.tau` exclusively. A wheel still needs a custom placement step. Revisit this when version pinning or multi-machine distribution is needed.

## Impact

- `install.sh` is rewritten. `tests/test-install.sh` is rewritten and runs the reference scan. A pre-commit hook is added; the README documents enabling it with `git config core.hooksPath`. The README install section and `docs/FLOW_DESCRIPTION.md` are updated. `skills/receiving-code-review/SKILL.md` is repaired. `docs/specs/subagent-dispatch.md` gets one modified requirement and four added requirements.
- User workflow: run `./install.sh` after every skills or extensions change. Run `/reload` in active host sessions. Sandboxes pick up installed state at their next launch.
- No changes to tau, the sandbox, or the extension runtime.
