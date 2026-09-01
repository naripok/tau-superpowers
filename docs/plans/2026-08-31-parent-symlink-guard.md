# Parent-Symlink Guard Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use subagent-driven-development (recommended) or executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** The installer stops before any change when `~/.tau/skills` or `~/.tau/extensions` is a symlink, while `--check` stays read-only and compares through a linked base.

**Architecture:** One read-only check joins the existing preflight phase of `install.sh`, before destination classification and before every mutation. The check tests each base path with `-L`, which examines the final path component only. The stop mirrors the existing destination-conflict stop: exit 1, stderr, one error block naming every offending base.

**Tech Stack:** Bash (4.4 floor), rsync, the existing Bash test harness in `tests/test-install.sh`.

**Standards:** Apply the shared code standards in every task: DRY, minimal implementation (YAGNI), low cyclomatic complexity, type safety, no unnecessary abstractions or fallbacks, no hacks or workarounds, informative docstrings, documentation of current state only, writing-developer-facing-text prose.

**Feature spec:** `docs/design/2026-08-31-parent-symlink-guard-spec.md` (the behavioral contract)

**Living spec:** `docs/specs/subagent-dispatch.md` (the delta target for the finishing-flow sync, not modified by these tasks)

---

## Commands

All commands run from the worktree root.

```bash
bash tests/test-install.sh          # expected: prints "Installer tests passed.", exit 0
bash tests/test-references.sh       # expected: prints "Reference scan tests passed.", exit 0
bash tests/check-references.sh      # expected: silent, exit 0
```

Run all three after every task. There is no separate shell lint or format tool for this repository. The suites run against a sandboxed `HOME` (mktemp), so tests never touch the real `~/.tau`.

## Current state the implementer needs

- `install.sh` structure: `parse_arguments` → `check_dependencies` → `run_check` (check mode) or `run_install` (install mode). `run_install` order: `resolve_repo_root`, `check_sources`, `parse_entries`, `preflight`, `read_stamp_entries`, `remove_stale_stamp_entries`, `remove_stale_repo_links`, `install_entries`, `write_stamp`, `print_stamp_line`.
- `preflight()` classifies each destination with `classify_destination` and stops on conflicts. It performs no base-directory check today.
- `install_entries()` runs `mkdir -p -- "$HOME/.tau/skills" "$HOME/.tau/extensions"` and copies each entry. A symlinked base makes `mkdir -p` a no-op and rsync writes and deletes through the link. A dangling base link fails inside `mkdir -p` with a bare mkdir error.
- `run_check()` performs no destination preflight and no mutation. It stays unchanged by this plan.
- The stamp lives at `$HOME/.tau/.tau-superpowers-install`.
- Test harness helpers in `tests/test-install.sh`: `run_installer HOME LOG SOURCE_ROOT ARGS...` (sets `install_status`), `assert_install_succeeded`, `assert_install_failed [STATUS]`, `assert_absent`, `assert_symlink_to PATH TARGET`, `assert_real_directory`, `assert_matches_source`, `assert_output_line`, `hash_tree ROOT` (digest over paths and content), `make_fixture ROOT` (source fixture with skills `alpha` and `beta` plus the extension, and a copy of the installer), runner list of test invocations at the bottom of the file. Each test builds its own fixture root and home under `$temporary_dir` and greps `$log` (stdout) or `$log.err` (stderr).

## Task 1: Base-symlink preflight stop with tests

**Files:**

- Modify: `install.sh` — new base check inside `preflight`; no other function changes
- Modify: `tests/test-install.sh` — eight new test functions, runner list entries, and one header-comment coverage sentence

**Spec requirement:** MODIFIED "Tau-discoverable installation" (all three scenarios) and MODIFIED "Staleness check" (scenario "Check compares through a symlinked base") in `docs/design/2026-08-31-parent-symlink-guard-spec.md`.

**Interface:**

- `check_bases()` — no arguments, no stdout, no state change on success. Tests the final path component of `$HOME/.tau/skills` and `$HOME/.tau/extensions` with the `-L` test. A real or absent base passes. A symlink counts regardless of resolution: dangling, foreign target, or target inside the source repository. With no offending base, the function returns and `preflight` continues with destination classification. With one or more offending bases, it prints to stderr exactly this block, one `  <path>` line per offending base in lexical order (`extensions` before `skills`), and exits 1:

  ```
  Error: these base directories are symlinks and block installation:
    <path>
  No destination was changed. Remove each symlink or replace it with a real directory, then run this installer again.
  ```

- `preflight()` — behavior change: its first action calls `check_bases`. Destination classification, the conflict stop, stale-entry removal, repository-link cleanup, directory creation, and every copy run only after the base check passes. Nothing else in `preflight` changes.
- `run_check()` — unchanged. It performs no base check and compares through a linked base.

**Behavior:**

- The stop precedes every mutation: no destination classification effect, no `mkdir`, no `rsync`, no stale-entry removal, no repository-link cleanup, no stamp write. stdout carries no entry lines and no stamp line.
- A dangling base link stops the install like any other base link.
- A base link into the source repository stops the install. The source repository content stays unchanged. No migration runs at base level.
- With a base link and a destination conflict both present, the base error appears and no conflict message appears. The base check runs before destination classification, so the conflict error appears only on a later run after the base fix.
- A symlinked `~/.tau` itself does not stop the install: the `-L` test examines the final path component of each base only. The install succeeds when a base under a symlinked `~/.tau` is a real directory or absent.
- An install into real or absent bases behaves exactly as before.
- The check mode (`run_check`) performs no base check. With a linked base, it compares content through the resolved path and exits 0 on a match and 1 on a difference.

**Tests must prove:**

1. `test_symlinked_skills_base_stops_install` — skills base is a symlink to a foreign directory holding one marker file: exit 1, stderr names `$home/.tau/skills`, stderr contains `No destination was changed.` and `Remove each symlink or replace it with a real directory`, stdout has no `Installed:` or `Updated:` line and no `Stamp:` line, the foreign target keeps its marker and gains no entries, no stamp file exists, and `$home/.tau/extensions` was not created
2. `test_symlinked_extensions_base_stops_install` — extensions base is a symlink to a foreign directory holding one marker file: exit 1, stderr names `$home/.tau/extensions`, the foreign target keeps its marker, and `$home/.tau/skills` was not created (the stop is global, not per entry)
3. `test_dangling_base_symlink_stops_install` — skills base is a dangling symlink (target does not exist): exit 1, stderr names the base with the same message, and nothing was created under `$home/.tau`
4. `test_repository_base_link_not_migrated` — skills base is a symlink to the fixture's own `$root/skills`: exit 1 and `hash_tree "$root/skills"` is identical before and after the run
5. `test_base_error_precedes_destination_conflict` — skills base is a symlink to a foreign directory and `$home/.tau/extensions/superpowers-subagent` is a regular file: exit 1, stderr names `$home/.tau/skills`, stderr does not contain `already exist`, and the file is unchanged
6. `test_both_bases_linked_lists_both` — both bases are symlinks: exit 1, one message names both paths, with the `extensions` line before the `skills` line, and the message contains `Remove each symlink or replace it with a real directory`
7. `test_tau_home_symlink_installs` — `$home/.tau` is a symlink to an external real directory: two consecutive installs succeed. The first run proves the absent-base half of the final-component rule. The second run proves the real-base half. The stamp exists at `$home/.tau/.tau-superpowers-install`, the installed entries are real directories, and content matches the source
8. `test_check_compares_through_symlinked_base` — after a successful install, rename `$home/.tau/skills` to `$home/.tau/skills-dir` and link `$home/.tau/skills` to the relative name `skills-dir`: `--check` exits 0; after appending a line to `$home/.tau/skills/alpha/data.md`, `--check` exits 1 and prints `skills/alpha/data.md`; the link still points to `skills-dir` afterwards

**Check:** `bash tests/test-install.sh && bash tests/test-references.sh && bash tests/check-references.sh` — expected: `Installer tests passed.` and `Reference scan tests passed.`, exit 0

- [ ] Write the eight tests. Tests 1 through 6 fail before the fix, each for the expected reason: tests 1, 2, and 6 exit 0 and write through the base link; test 3 fails inside `mkdir -p` with the bare mkdir error; test 4 exits 0 before the fix because the entries reached through the base link classify as directories and rsync onto the identical fixture source changes nothing, so its exit-status assertion fails while its hash comparison passes; test 5 prints the conflict block and carries no base error. Tests 7 and 8 are characterization tests that pass before and after the fix. Run the suite and check that each failure matches this list
- [ ] Implement `check_bases` and its call at the start of `preflight`
- [ ] Run verification (all three suites)
- [ ] Commit: `git add install.sh tests/test-install.sh && git commit -m "feat: refuse a symlinked base directory in the installer preflight"`

Also in this task: extend the `tests/test-install.sh` header comment (the paragraph starting "Proves the installer:") with the new coverage: a symlinked base directory stops the install, and the check mode compares through a linked base. Comment prose follows writing-developer-facing-text.

## Task 2: Documentation alignment

**Files:**

- Modify: `README.md` — the "Install for Your User" section, the paragraph that begins `A symlink that points outside the checkout, or any other file type at a managed name, stops the install without changes.`
- Modify: `install.sh` — the header comment block (the comment above `set -euo pipefail`), no executable line changes
- Modify: `docs/design/2026-08-31-parent-symlink-guard-proposal.md` — the Impact bullet that counts the new test invocations

**Spec requirement:** documentation of current behavior only; the spec scenarios proved in Task 1. This task carries no behavioral change and no new test.

**Interface:** none (documentation only).

**Behavior:**

- README "Install for Your User", first stop-behavior paragraph: after the sentence about managed-name symlinks, add two sentences: `A symlinked ~/.tau/skills or ~/.tau/extensions base directory also stops the install, dangling or not. Remove each symlink or replace it with a real directory, then run the installer again.` (Paths in backticks.)
- `install.sh` header comment: add one sentence to the behavior description: `A symlinked ~/.tau/skills or ~/.tau/extensions base directory stops the install before any change.`
- Proposal Impact: replace the `tests/test-install.sh: five new scenario invocations` count with eight, and reword the documentation bullet to state the per-file additions: the rule in each header comment, and the rule plus its remedy in the README.

**Tests must prove:** nothing new; run the full verification to prove no regression.

**Check:** `bash tests/test-install.sh && bash tests/test-references.sh && bash tests/check-references.sh` — expected: all pass

- [ ] Apply the README and header-comment changes
- [ ] Run verification (all three suites)
- [ ] Commit: `git add README.md install.sh docs/design/2026-08-31-parent-symlink-guard-proposal.md && git commit -m "docs: document the base-symlink install stop"`

## Self-Review Record

- Spec coverage: each of the four delta scenarios maps to named tests (1, 2, 4, 5, 6, 8); the requirement sentence about a base under a symlinked `~/.tau` maps to test 7; the dangling clause maps to test 3
- Reverse coverage: Task 1 implements both MODIFIED requirements; Task 2 implements the proposal Impact documentation items only
- Placeholder scan: no TBD, no TODO, no unspecified behavior
- Signature consistency: `check_bases` named identically in both tasks that reference it
- Standards: no new abstraction beyond one function; no fallbacks; error text matches the proposal exactly
