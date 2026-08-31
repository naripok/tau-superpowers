# Homogeneous rsync install Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use subagent-driven-development (recommended) or executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the link-based installer with a copy-based installer for skills and the extension, with migration, deletion propagation, a stamp file, and a `--check` staleness mode, plus a pre-commit reference scan that keeps installed resources self-contained.

**Architecture:** `install.sh` becomes a single-shot rsync installer: it preflights every destination, installs each managed entry with `rsync -a --delete` and a fixed exclude set, and records the managed entries in a stamp file. `--check` compares installed content against the stamp-recorded source. A standalone scan script backs a pre-commit hook and the installer test suite; it detects references that resolve only inside the source checkout. The old link semantics disappear; existing symlinks and the hand-copied extension directory migrate automatically.

**Tech Stack:** Bash 4+, rsync, git. No new runtime dependencies beyond rsync.

**Standards:** Apply the shared code standards in every task: DRY, minimal implementation (YAGNI), low cyclomatic complexity, type safety, no unnecessary abstractions or fallbacks, no hacks or workarounds, informative docstrings, documentation of current state only, writing-developer-facing-text prose.

**Feature spec:** `docs/design/2026-08-31-homogeneous-rsync-install-spec.md` (the behavioral contract)

---

## Commands

Run all verification from the worktree root. Bash 4+ and rsync must be on PATH.

```bash
bash tests/test-install.sh      # installer behavior suite (Tasks 2 and 3 extend it)
bash tests/test-references.sh   # reference scan suite (Task 1)
bash tests/check-references.sh  # scan the shipped tree; exit 0 expected after Task 1
```

There is no lint or type-check infrastructure for the bash scripts. The scan script doubles as the style-free static check for the self-containment property. Each task's `Check` lists its exact commands.

`rsync` availability: the test suite requires it; install it with the system package manager when absent.

---

### Task 1: Reference scan, pre-commit hook, and self-containment repair

**Files:**
- Create: `tests/check-references.sh` — the shared reference scanner (single implementation used by the hook and the test suite)
- Create: `.githooks/pre-commit` — thin wrapper that runs the scanner in staged mode
- Create: `tests/test-references.sh` — scan behavior suite, fixture-driven plus one shipped-tree case
- Modify: `skills/receiving-code-review/SKILL.md` — delete the dead `docs/FLOW_DESCRIPTION.md` pointer sentence
- Modify: `README.md` — add a short contributor-hooks subsection that contains the enablement command `git config core.hooksPath .githooks`

**Spec requirement:** ADDED requirement "Installed self-containment" (all seven scenarios).

**Interface:**

- `tests/check-references.sh [--staged] [ROOT]` — scan for checkout-only references.
  - No arguments: scan the repository that contains the script; worktree content.
  - `--staged`: scan the staged (index) content of git-managed `.md` files under `skills/` and `extensions/superpowers-subagent/`; file contents come from the index (`git show :<path>`); path existence checks use the worktree; resolves the repository from the current working directory (`git rev-parse --show-toplevel`), and combining `--staged` with `[ROOT]` is a usage error (exit 2).
  - `[ROOT]`: positional override for the tree to scan in worktree mode (fixture mode; ROOT must contain `skills/` and `extensions/superpowers-subagent/`; rejected with exit 2 when `--staged` is set).
  - Exit 0 when no checkout-only reference is found. Exit 1 when at least one is found. Exit 2 on usage error.
  - Finding output, one line each: `<path relative to ROOT>: <reference text>`; additional context lines are allowed on stderr only.
- Scan set: all `.md` files, recursive, under `skills/` and `extensions/superpowers-subagent/`.
- Reference extraction: Markdown link targets `](TARGET)` that are not `http://`, `https://`, `mailto:`, or a pure `#fragment`; a trailing `#fragment` is stripped from a target before classification; backticked tokens that contain `/`.
- Classification, per reference, in order:
  - Workflow reference: text begins with `docs/design/`, `docs/specs/`, or `docs/plans/` — never flagged.
  - Directory target: the checkout-side resolution names an existing directory — never flagged.
  - Checkout-only: a regular file exists at the reference resolved against the referencing file's directory or against ROOT, and no file exists at that reference resolved against, in order: the referencing file's installed directory, the owning resource's installed directory, any sibling installed skill directory, or the installed tree root. The installed side is the layout this install produces, evaluated by mapping installed paths back to source paths: `~/.tau/skills/<name>/...` maps to `<ROOT>/skills/<name>/...`; `~/.tau/extensions/superpowers-subagent/...` maps to `<ROOT>/extensions/superpowers-subagent/...`; any other `~/.tau` path has no produced counterpart. The installed tree root is `~/.tau`. A source path that the install excludes (`\.git`, `\.venv`, `__pycache__`, `\.mypy_cache`, `\.pytest_cache`, `\.ruff_cache`, `\.worktrees`) has no produced counterpart and does not exist installed-side.
  - Nowhere-resolving: no file exists at either source-side basis — never flagged.
- `.githooks/pre-commit` — exec `tests/check-references.sh --staged` from the repository top level and propagate its exit code. The wrapper resolves the scanner relative to its own location.

**Behavior:**

- The scanner is the only implementation of the classification rules. The hook and the test suite both call it; no logic duplication.
- The hook runs on staged content only; a working-tree correction without restaging does not unblock a bad staged reference.
- The repair deletes exactly this sentence from `skills/receiving-code-review/SKILL.md`: `For dispatch conventions, read `docs/FLOW_DESCRIPTION.md`.` The preceding sentence about absent verification commands stays unchanged. After the repair, the shipped tree contains no checkout-only reference.

**Tests must prove:**

- Shipped tree passes: `tests/check-references.sh` exits 0 on the repository (scenario "Shipped resources carry no checkout-only references")
- Checkout-only detection: a fixture skill referencing a `docs/FLOW_DESCRIPTION.md` file that exists in the fixture checkout exits 1 and prints `path: reference` (scenario "Commit with a checkout-only reference fails", scan side)
- Cross-skill carried reference passes: `../<other-skill>/ref.md` with the target present (scenario "Sibling skill reference resolves")
- File-level installed basis passes: a reference from a skill subdirectory to a file in the skill root, written as `../guide.md` (scenario "Carried references resolve")
- Tree-root basis passes: a skill referencing `extensions/superpowers-subagent/pyproject.toml`
- Extension resource-dir basis passes: an extension Markdown file referencing `pyproject.toml` (scenario "Extension file reference resolves")
- Workflow prefixes are never flagged, including an existing `docs/specs/<file>.md` file target (scenario "Workflow artifact paths are not carried resources")
- Directory targets are never flagged
- Nowhere-resolving references are never flagged (scenario "Nowhere-resolving reference does not fail the scan")
- Staged mode: stage a bad reference, correct the working-tree copy without restaging, then `--staged` fails on the staged content and the full worktree scan passes (proves staged-content scanning)
- Hook wrapper: run `.githooks/pre-commit` inside a fixture repository with a staged bad reference → nonzero exit; with a clean staged tree → exit 0
- Anchored targets classify by their path component: `../b/ref.md#section` behaves exactly like `../b/ref.md`
- Non-reference noise is ignored: `http(s)://` links, `#fragment` targets, and backticked tokens without `/`

**Check:** `bash tests/test-references.sh && bash tests/check-references.sh` — expected: both exit 0

- [ ] Write the failing tests for the behaviors above. Run them and check that each fails for the expected reason
- [ ] Implement the scanner, the hook wrapper, and the repair
- [ ] Run verification (both suites)
- [ ] Commit: `git add tests/check-references.sh .githooks/pre-commit tests/test-references.sh skills/receiving-code-review/SKILL.md README.md && git commit -m "feat: reference scan with pre-commit hook and self-containment repair"`

---

### Task 2: Installer core — copy install, migration, take-over, collision preflight, stamp

**Files:**
- Modify: `install.sh` — rewrite from link semantics to copy semantics with stamp; single-shot install mode only in this task (`--check` arrives in Task 3; passing it exits 2 with usage)
- Modify: `tests/test-install.sh` — rewrite the assertions from links to copies; add migration, take-over, collision, stamp, and rsync-missing cases; the suite runs `tests/check-references.sh` in full-scan mode and fails when it exits nonzero; keep the sandboxed-HOME pattern (`mktemp` home, `HOME=... install.sh`), the `trap` cleanup, and the existing conflict-preservation assertions style

**Spec requirement:** MODIFIED requirement "Tau-discoverable installation" (scenarios: Copy install, Idempotent re-install, Symlink migration, Copy take-over, User installation collision, Missing rsync dependency) and ADDED requirement "Install stamp" (all three scenarios).

**Interface:**

- `install.sh` — install mode. Exit 0 on success. Exit 1 on preflight failure with zero destination changes. Exit 2 on usage error. Errors go to stderr.
- Managed source set: every directory under `<repo>/skills/` containing `SKILL.md`, plus `<repo>/extensions/superpowers-subagent`. Destinations: `$HOME/.tau/skills/<name>` and `$HOME/.tau/extensions/superpowers-subagent`.
- Preflight, all destinations before any change:
  - `rsync` absent from PATH: one stderr line, exit 1, no changes
  - destination absent: installable
  - destination is a symlink that resolves into the running installer's repository root: migratable — the resolver tolerates missing targets, so dangling repository links classify here; the stamp-recorded source root does not participate in this classification, so a symlink into a different checkout is a conflict
  - destination is a real directory not recorded in an existing stamp: take over
  - destination is a real directory recorded in an existing stamp: managed
  - destination is a symlink that does not resolve into the repository, or any other file type: conflict
  - any conflict: list every conflicting destination on stderr with the existing "already exist" wording, exit 1, zero changes
- Install per entry: `rsync -a --delete --itemize-changes` plus exactly these excludes: `.git`, `.venv`, `__pycache__`, `.mypy_cache`, `.pytest_cache`, `.ruff_cache`, `.worktrees`; capture the itemize output.
- Per-entry output line: `Installed: <entry>` when the destination was absent or a symlink; `Updated: <entry>` when a real directory changed (take-over and managed updates also print their itemize lines); `Unchanged: <entry>` when a real directory produced an empty itemize. `<entry>` is the destination path relative to `~/.tau` (`skills/<name>`, `extensions/superpowers-subagent`).
- Install order: entries install in lexical `<entry>` order. This order governs which entries count as later when a copy fails partway.
- Cross-entry removal and `--check` are Task 3; this task writes the stamp that Task 3 consumes.
- Partway copy failure: when rsync exits nonzero for an entry, the installer prints an error naming the failing entry, installs no further entries, writes no stamp, and exits 1. Earlier entries are already installed when the failure happens. A later run makes the affected entry match its source.
- Stamp file: `$HOME/.tau/.tau-superpowers-install`, written after every successful install, exact format:

```text
source: <absolute repository root>
sha: <40-hex commit id | none>
dirty: <yes | no | none>
time: <UTC ISO-8601, for example 2026-08-31T12:34:56Z>
entry: <managed entry relative to ~/.tau>      (one line per entry, sorted lexically)
```

  `sha: none` with `dirty: none` when the source has no git metadata. A git repository with no commits records `sha: none` and keeps the normal `dirty:` rule. `dirty: yes` when `git status --porcelain` output is non-empty, `dirty: no` when empty.
- Final output lines after the per-entry lines: `Stamp: $HOME/.tau/.tau-superpowers-install (sha <first 7 hex | none>, dirty | clean | none)` and `Restart Tau, or run /reload for skill changes in an active session.`

**Behavior:**

- Migration removes the symlink before any write, so the repository is never written through a link. A marker file created through an old-style link stays in the source and appears in the fresh copy.
- Take over of a real directory replaces content under delete propagation and prints the removed and updated paths.
- The destination state decision table is exhaustive for source-provided names: absent, repository-resolving symlink, unrecorded real directory, recorded real directory, everything else stops.
- All-or-nothing: a conflict or a missing rsync aborts before the first destination changes.

**Tests must prove:**

- Fresh install: every skill and the extension are real directories whose content matches the source under the excludes; no `.venv`, `__pycache__`, or other excluded path in any destination; the extension copy keeps `tests/` and `pyproject.toml` (scenario "Copy install")
- Foreign destination untouched: an unrelated directory under `$HOME/.tau/skills` survives (scenario "Foreign destination untouched")
- Collision aborts: a foreign symlink at a managed name and a foreign regular file at another managed name both stop the install; nothing anywhere changed; the message contains "already exist" (scenario "User installation collision")
- Migration: old-style symlinks become real directories; the repository content is unchanged after install; a dangling repository-pointing symlink at a provided name becomes a real directory (scenario "Symlink migration")
- Take over: a real directory at the extension destination with a junk file converges to the source, the junk file is gone, and the output lists the removed and updated paths (scenario "Copy take-over")
- Stamp: correct fields for a git source with uncommitted changes (`sha:` 40-hex, `dirty: yes`), a clean git fixture (`sha:` 40-hex, `dirty: no`), and a non-git source (`sha: none`, `dirty: none`); the entry list is sorted and complete; `time:` parses as ISO-8601 UTC (scenarios "Stamp records git state", "Stamp records no git metadata", "Stamp records a clean tree")
- Idempotent second run: every entry reports `Unchanged:` and no content changes (scenario "Idempotent re-install")
- Missing rsync: `PATH` without rsync exits 1 before any destination changes (scenario "Missing rsync dependency")
- Collision with a stamp present: install once, replace one managed destination with a foreign symlink, re-install → exit 1, nothing changes, message contains "already exist" (proves that a recorded stamp does not exempt a destination from the collision stop)
- Partway copy failure: make one source skill file unreadable with chmod 000, install → exit 1, an error names the entry, later entries are not installed, no stamp is written; restore the permissions (the recovery half is Task 3's convergence test)
- Repository-resolving rule: install from fixture A over old-style links, then install from fixture B over the same HOME → the A-pointing symlinks are conflicts (exit 1, no changes), and a re-install from fixture A migrates cleanly (pins that classification uses the running source root)
- Suite runs the scan: `tests/test-install.sh` invokes `tests/check-references.sh` with no arguments and fails the suite when it exits nonzero (spec clause: the installer test suite SHALL run the same scan)

**Check:** `bash tests/test-install.sh` — expected: all pass

- [ ] Write the failing tests for the behaviors above. Run them and check that each fails for the expected reason
- [ ] Implement the installer rewrite
- [ ] Run verification (full suite)
- [ ] Commit: `git add install.sh tests/test-install.sh && git commit -m "feat: copy-based installer with migration, take-over, and stamp"`

---

### Task 3: Deletion propagation and --check staleness mode

**Files:**
- Modify: `install.sh` — add cross-entry deletion to the install path; add the `--check` mode
- Modify: `tests/test-install.sh` — add deletion, convergence, and `--check` cases

**Spec requirement:** ADDED requirement "Managed-entry deletion" (all four scenarios) and ADDED requirement "Staleness check" (all five scenarios); the "Partway failure repair" scenario of the MODIFIED requirement.

**Interface:**

- `install.sh` gains, in the install path:
  - Cross-entry removal: entries recorded in a previous stamp that the source no longer provides are removed with `rm -rf` and reported as `Removed: <entry>`
  - Repository-link cleanup: a symlink under `$HOME/.tau/skills/` or `$HOME/.tau/extensions/` that resolves into the running installer's repository root (with or without a stamp present), at a name the source does not provide, is removed and reported as `Removed: <entry>` (scenario "Repository link without source entry removed")
  - Within-entry deletion already comes from `rsync --delete` (Task 2)
- `install.sh --check` — staleness mode. Never changes any destination, performs no destination preflights, and runs no reference scan. Exit 0 on a match. Exit 1 and print every differing path when content differs. Exit 1 when the stamp is missing, with the stderr line `Error: no install stamp at <path>`. Exit 1 when no source tree exists at the recorded source path, with the stderr line `Error: source tree not found: <path>`.
- Comparison rules, per stamp-recorded entry: `rsync -a --delete --itemize-changes --dry-run` with the Task 2 excludes, source `<recorded source root>/<entry source>` against destination `$HOME/.tau/<entry>`; a managed destination that does not exist is a difference; a stamp-recorded entry whose source no longer exists is a difference. Differences print their itemize lines. Each differing path prints qualified by its entry as `<entry>/<entry-relative path>`.

**Behavior:**

- `--check` reads the stamp's source path, so it compares against that checkout even when run from a different checkout (scenario "Comparison uses the recorded source").
- Deletion convergence: a destination missing a file that the source provides, or carrying a file the source dropped, matches the source after one install run (scenario "Partway failure repair", scenario "Source file deletion propagates").

**Tests must prove:**

- Removed entry: install from a fixture source copy, delete one skill directory from the fixture, re-install → destination removed, `Removed: skills/<name>` printed (scenario "Removed entry")
- Repository link without source entry removed: a repo-pointing symlink at an unprovided name under `$HOME/.tau/skills/` disappears on install (scenario "Repository link without source entry removed")
- Source file deletion propagates: delete a file inside a fixture source skill, re-install → the file is gone from the destination (scenario "Source file deletion propagates")
- Foreign destination stays untouched across runs (regression of Task 2 with a stamp present)
- Fresh check passes: exit 0, nothing changes (scenario "Fresh check passes")
- Stale check fails: edit one installed file → exit 1, the differing path prints in the qualified `<entry>/...` form, nothing changes (scenario "Stale content fails")
- Missing stamp fails: no stamp file → exit 1 with the exact error line (scenario "Missing stamp fails")
- Unavailable source fails: delete the recorded fixture source → exit 1 with the exact error line (scenario "Unavailable source fails")
- Comparison uses the recorded source: install from fixture A, run `install.sh --check` from a different checkout (fixture B containing this installer) → exit 0 (scenario "Comparison uses the recorded source")
- Partway failure repair: remove a file inside an installed entry, re-install → the entry matches its source (scenario "Partway failure repair")

**Check:** `bash tests/test-install.sh && bash tests/test-references.sh` — expected: all pass

- [ ] Write the failing tests for the behaviors above. Run them and check that each fails for the expected reason
- [ ] Implement deletion propagation and the `--check` mode
- [ ] Run verification (full suite)
- [ ] Commit: `git add install.sh tests/test-install.sh && git commit -m "feat: deletion propagation and --check staleness mode"`

---

### Task 4: Documentation alignment

**Files:**
- Modify: `README.md` — Requirements line and "Install for Your User" section
- Modify: `docs/FLOW_DESCRIPTION.md` — "Tau Activation" install wording

**Spec requirement:** MODIFIED requirement "Tau-discoverable installation" (documentation of current behavior) and the proposal's Impact statement.

**Interface:** no code interfaces. Content contracts:

- README Requirements: replace `Git and Bash for the symlink installer.` with `Git, Bash, and rsync for the installer.`
- README "Install for Your User": replace the link semantics with the current behavior: the installer copies skills and the extension under `~/.tau`; it preflights and stops on conflicts without partial changes; it takes over existing symlinks and copies from earlier installs; it records the stamp `~/.tau/.tau-superpowers-install`; run `./install.sh` after every skills or extensions change; `install.sh --check` exits 0 fresh and 1 stale, printing differing paths; `/reload` refreshes changed skills in an active host session; sandboxes pick up installed state at their next launch. Remove `Keep the checkout in place because the installation refers to it.` and the link diagram. Replace the Repository Layout comment `install.sh` # safe per-resource user linker with `install.sh` # per-resource installer (rsync copies). Replace the sentence `A user-installed link under `~/.tau/extensions`, as created by `install.sh`, is user code and is discovered by default.` so that it says a user-installed copy instead of a user-installed link. Reference the contributor-hooks subsection for `git config core.hooksPath .githooks`. Keep the installer-regression-test pointer and add `tests/test-references.sh` beside it.
- `docs/FLOW_DESCRIPTION.md` "Tau Activation": replace `A user installation links skills individually under \`~/.tau/skills\`.` with the copy-based wording for skills and the extension.

**Behavior:** documentation describes current behavior only; no old system states remain.

**Tests must prove:** documentation-only task; verification by search.

**Check:**

```bash
rg -n "symlink installer|creates individual links|Keep the checkout in place|links skills individually|user linker|user-installed link|creating links|-> <checkout>|adds a skill" README.md docs/FLOW_DESCRIPTION.md
rg -n "rsync|install.sh --check|core.hooksPath" README.md
```

Expected: first command exits 1 (no matches); second exits 0 with matches.

- [ ] Apply the content changes
- [ ] Run the verification searches
- [ ] Commit: `git add README.md docs/FLOW_DESCRIPTION.md && git commit -m "docs: install-based workflow for skills and extension"`

---

## Self-Review

- Spec coverage: MODIFIED "Tau-discoverable installation" → Tasks 2 and 3 (install semantics, stamp consumption, convergence) and Task 4 (docs); its carried scenarios "Checkout discovery", "Prompt threshold", and "Clone without extension approval" are unaffected by all tasks (no code or doc change touches tool registration, prompt surface, or project-extension discovery). ADDED "Managed-entry deletion" → Task 3. ADDED "Staleness check" → Task 3. ADDED "Installed self-containment" → Task 1.
- ADDED "Install stamp" → Task 2, checked further in Task 3. The "Installed self-containment" clause that the installer test suite runs the scan is covered by Task 2's suite rewrite, which invokes the Task 1 scanner and fails on its nonzero exit.
- Reverse coverage: every task maps to spec requirements; Task 4 maps to the proposal Impact statement and the MODIFIED requirement's documentation duty.
- Signatures: the scan script CLI in Task 1 is the only interface Task 1's tests and hook use; `--check` appears only from Task 3; the stamp format defined in Task 2 is the exact contract Task 3 consumes.
- No placeholders: every task lists named behaviors and exact commands.
