# Spec: Parent-symlink guard

Delta against the living spec `docs/specs/subagent-dispatch.md`, domain `subagent-dispatch`. The MODIFIED entries restate only the changed sentences and their scenarios. The finishing-flow sync merges them into the living spec and preserves every unmentioned sentence and scenario.

## Domain: subagent-dispatch

### MODIFIED Requirements

#### Requirement: Tau-discoverable installation

The installer SHALL stop without changing any destination when the `~/.tau/skills` or `~/.tau/extensions` base directory is a symlink, dangling or resolving anywhere. A real or absent base directory passes this check. A base directory under a symlinked `~/.tau` passes this check when the base itself is a real directory or absent.

##### Scenario: Symlinked base directory stops the install

- GIVEN the `~/.tau/skills` or `~/.tau/extensions` base directory is a symlink, dangling or resolving anywhere
- WHEN the installer runs
- THEN the installer exits nonzero before changing any destination
- AND the error names each symlinked base directory
- AND the error states the remedy: remove the symlink or replace it with a real directory, then run the installer again

##### Scenario: Base error precedes a destination conflict

- GIVEN the `~/.tau/skills` base directory is a symlink
- AND the extension destination is a regular file
- WHEN the installer runs
- THEN the error names the symlinked base directory
- AND the error names no destination conflict
- AND the installer exits nonzero before changing any destination

##### Scenario: No migration for a repository base link

- GIVEN the `~/.tau/skills` base directory is a symlink into the source repository
- WHEN the installer runs
- THEN installation stops before changing any destination
- AND the source repository content is unchanged

#### Requirement: Staleness check

The check performs the content comparison only and performs no destination preflights, no base-directory preflights, and no reference scan.

##### Scenario: Check compares through a symlinked base

- GIVEN a completed install
- AND the `~/.tau/skills` base directory is a symlink to a real directory that holds the installed skills content
- WHEN `install.sh --check` runs
- THEN the check compares the installed content through the resolved path
- AND the check exits 0 when the content matches the source
- AND the check exits 1 when the content under the link target differs from the source
