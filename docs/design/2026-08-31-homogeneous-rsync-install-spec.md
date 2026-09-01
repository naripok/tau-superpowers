# Spec: Homogeneous rsync install

## Domain: subagent-dispatch

### MODIFIED Requirements

#### Requirement: Tau-discoverable installation

The package SHALL keep one canonical top-level `skills/` tree. The installer SHALL install individual skills under `~/.tau/skills` and the extension under `~/.tau/extensions/superpowers-subagent` as real directory copies under delete propagation with the install excludes. The install excludes are `.git`, `.venv`, `__pycache__`, `.mypy_cache`, `.pytest_cache`, `.ruff_cache`, and `.worktrees`. The installer SHALL preflight every destination and the rsync dependency before it changes any destination. The installer SHALL stop without changing any destination when a destination conflicts or when rsync is unavailable. When a copy fails partway, the installer SHALL report the failure and exit nonzero, and a later run SHALL make the affected entry match its source. A checkout SHALL support explicit extension loading with `tau -e extensions/superpowers-subagent` and SHALL NOT expose executable code through project `.tau/extensions` by default.

##### Scenario: Checkout discovery

- GIVEN Tau runs in an approved repository checkout
- WHEN the extension is explicitly loaded with `tau -e extensions/superpowers-subagent`
- THEN Tau registers one tool named `task`
- AND Tau discovers no project skills from this checkout

##### Scenario: Prompt threshold

- GIVEN the task tool is registered
- WHEN its always-visible prompt surface (description, snippet, and guidelines) is read
- THEN it states that subagents exist for substantive multi-step work that benefits from an isolated context window or for long-running work that must not block the parent session
- AND it forbids dispatching simple reads, searches, commands, and small edits the parent can perform itself
- AND it forbids dispatching work the parent is about to perform itself, because a subagent replaces the parent's tool calls for its task

##### Scenario: Copy install

- GIVEN no destination exists for a skill the source provides or for the extension
- WHEN the installer runs
- THEN each destination exists as a real directory whose content matches its source under the install excludes
- AND each copy contains none of the excluded development paths: `.git`, `.venv`, `__pycache__`, `.mypy_cache`, `.pytest_cache`, `.ruff_cache`, `.worktrees`
- AND the extension copy keeps its `tests` directory and `pyproject.toml`

##### Scenario: Idempotent re-install

- GIVEN a completed install whose source matches the installed content under the install excludes
- WHEN the installer runs again
- THEN the managed destinations keep their content
- AND the output reports the entries as unchanged

##### Scenario: Symlink migration

- GIVEN a destination name that the source provides
- AND that destination is a symlink that resolves into the source repository
- WHEN the installer runs
- THEN the installer removes the symlink and installs a real directory copy
- AND the source repository content is unchanged

##### Scenario: Copy take-over

- GIVEN a destination name that the source provides
- AND that destination is a real directory that no stamp records
- WHEN the installer runs
- THEN the installer replaces the content with the source copy under delete propagation
- AND the output lists every removed and updated path

##### Scenario: User installation collision

- GIVEN a destination name that the source provides
- AND that destination is a symlink that does not resolve into the source repository, or is a file that is neither a directory nor a symlink
- WHEN the installer preflights the destinations
- THEN installation stops before changing any destination
- AND that destination is not replaced
- AND a recorded stamp does not exempt that destination from this stop

##### Scenario: Missing rsync dependency

- GIVEN rsync is not available on PATH
- WHEN the installer runs
- THEN it exits nonzero before changing any destination
- AND every destination keeps its pre-install state

##### Scenario: Partway failure repair

- GIVEN a previous run reported a partway copy failure for an entry
- WHEN the installer runs again
- THEN the affected entry matches its source under the install excludes

##### Scenario: Clone without extension approval

- GIVEN a user only clones the repository
- WHEN Tau starts without a user installation or explicit extension path
- THEN no executable project extension is discovered from this checkout

### ADDED Requirements

#### Requirement: Managed-entry deletion

The installer SHALL remove an installed entry that a recorded stamp lists as managed when the source no longer provides that entry. The installer SHALL also remove a symlink destination that resolves into the source repository when the source provides no entry under its name. Within a managed entry, the installer SHALL delete destination paths that the source does not provide. The installer SHALL NOT remove a destination that no stamp records and whose name matches no source entry, except a symlink that resolves into the source repository.

##### Scenario: Removed entry

- GIVEN a stamp records an installed entry whose source no longer exists
- WHEN the installer runs
- THEN the installer removes that destination
- AND the output reports the removal

##### Scenario: Source file deletion propagates

- GIVEN a stamp records a managed entry
- AND the source of that entry no longer contains a file that the destination contains
- WHEN the installer runs
- THEN the destination no longer contains that file

##### Scenario: Repository link without source entry removed

- GIVEN a symlink destination resolves into the source repository
- AND the source provides no entry under its name
- WHEN the installer runs
- THEN the installer removes that symlink

##### Scenario: Foreign destination untouched

- GIVEN `~/.tau/skills` contains a directory that no stamp records and whose name matches no source entry
- WHEN the installer runs
- THEN that destination keeps its content

#### Requirement: Install stamp

The installer SHALL write a stamp file at `~/.tau/.tau-superpowers-install` after each successful install. The stamp SHALL record the source repository path, the source git SHA with a dirty marker when the source tree has uncommitted changes or a none marker when the source tree has no git metadata, the install time in UTC, and the managed destination list. The stamp SHALL decide which installed entries the installer removes.

##### Scenario: Stamp records git state

- GIVEN the source tree has git metadata
- WHEN the installer completes and the stamp is read
- THEN the stamp records a git SHA
- AND the stamp records a dirty marker when the source tree has uncommitted changes
- AND the stamp records the install time in UTC

##### Scenario: Stamp records no git metadata

- GIVEN the source tree has no git metadata
- WHEN the installer completes and the stamp is read
- THEN the stamp records the none marker

##### Scenario: Stamp records a clean tree

- GIVEN the source tree has git metadata with no uncommitted changes
- WHEN the installer completes and the stamp is read
- THEN the stamp records a git SHA
- AND the stamp records no dirty marker

#### Requirement: Staleness check

The installer SHALL support `install.sh --check`. The check SHALL compare installed content against the source tree at the source path recorded in the stamp, with the same rules and excludes as installation. A managed destination that does not exist is a difference. A stamp-recorded entry whose source no longer exists is a difference. The check performs the content comparison only and performs no destination preflights and no reference scan. The check SHALL change nothing and SHALL exit 0 on a match. The check SHALL exit 1 and print every differing path when content differs. The check SHALL exit 1 when the stamp is missing. The check SHALL exit 1 and report the recorded source path when no source tree exists at that path.

##### Scenario: Fresh check passes

- GIVEN installed content matches the source under the install excludes
- WHEN `install.sh --check` runs
- THEN it exits 0 and changes nothing

##### Scenario: Stale content fails

- GIVEN an installed file differs from its source file
- WHEN `install.sh --check` runs
- THEN it exits 1 and prints the differing path
- AND it changes nothing

##### Scenario: Missing stamp fails

- GIVEN no stamp file exists
- WHEN `install.sh --check` runs
- THEN it exits 1 and reports the missing stamp

##### Scenario: Unavailable source fails

- GIVEN the source tree is not available at the recorded source path
- WHEN `install.sh --check` runs
- THEN it exits 1 and reports the recorded source path

##### Scenario: Comparison uses the recorded source

- GIVEN installed content matches the source tree at the recorded source path
- AND the running checkout is a different checkout
- WHEN `install.sh --check` runs
- THEN it exits 0

#### Requirement: Installed self-containment

The installed resources SHALL be self-contained. A skill SHALL carry every non-workflow file that the agent must read while using the skill inside its own skill directory, a sibling installed skill directory, or elsewhere inside the installed tree. The workflow artifact paths `docs/design/`, `docs/specs/`, and `docs/plans/` of the project under work are not carried resources. A reference whose text begins with one of those three paths is a workflow reference. A workflow reference is not checkout-only.

The repository SHALL provide a pre-commit hook that scans the Markdown files of every skill and the extension for path references written as backticked paths or Markdown link targets. The scan checks file targets only. A path that names a directory is never checkout-only. A reference is checkout-only when a file exists at its path inside the source checkout, resolved against the referencing file's directory or against the source root, and no file exists at that path resolved against the referencing file's installed directory, the referencing resource's installed directory, any sibling installed skill directory, or the installed tree root. The referencing resource is the skill or the extension that owns the referencing file. The installed side is evaluated against the tree that this install produces. The evaluation does not use the current state of `~/.tau`. The installed tree root is `~/.tau`. A reference whose target exists nowhere is not checkout-only. The hook SHALL reject the commit when the scan finds a checkout-only reference, and its output SHALL name the offending file and reference. The hook SHALL scan the staged content of the commit. The installer test suite SHALL run the same scan and SHALL fail when the scan finds a checkout-only reference.

##### Scenario: Carried references resolve

- GIVEN the installed configuration without the source checkout
- WHEN every non-workflow file-target reference whose target exists inside the source checkout is resolved against the referencing file's installed directory, the referencing resource's installed directory, sibling installed skill directories, and the installed tree root
- THEN each target exists inside the installed configuration tree

##### Scenario: Sibling skill reference resolves

- GIVEN an installed skill references a file in a sibling installed skill directory
- WHEN that reference is resolved from the installed location
- THEN the target exists inside the installed configuration tree

##### Scenario: Extension file reference resolves

- GIVEN a Markdown file inside the installed extension references a file that the install places in the extension's installed directory
- WHEN that reference is resolved from the extension's installed directory
- THEN the target exists inside the installed configuration tree

##### Scenario: Workflow artifact paths are not carried resources

- GIVEN a skill directs the agent to `docs/design/`, `docs/specs/`, or `docs/plans/` of the project under work
- WHEN the scan runs on that skill
- THEN the scan does not flag those references

##### Scenario: Commit with a checkout-only reference fails

- GIVEN a staged skill file contains a relative path reference whose target exists only inside the source checkout
- WHEN the pre-commit hook runs
- THEN the hook rejects the commit
- AND the output names the offending file and reference

##### Scenario: Nowhere-resolving reference does not fail the scan

- GIVEN a skill file contains a path reference whose target exists neither inside the source checkout nor inside the installed configuration tree
- WHEN the scan runs on that skill
- THEN the scan does not report that reference

##### Scenario: Shipped resources carry no checkout-only references

- GIVEN the repository as shipped
- WHEN the scan runs on the skills and the extension
- THEN no checkout-only reference is found
