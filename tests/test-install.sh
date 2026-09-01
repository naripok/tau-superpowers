#!/usr/bin/env bash
set -euo pipefail

# Proves the installer: copy semantics with excludes, symlink migration,
# copy take-over that also removes excluded paths left in a destination,
# collision preflight, all-or-nothing aborts, the install stamp including
# a git repository with no commits, idempotent re-install, a missing rsync
# dependency, a partway copy failure, deletion propagation for dropped
# entries and dropped source files, repository-link cleanup, stamp entry
# lines that stay inside ~/.tau, and the --check staleness mode. The suite
# also runs
# tests/check-references.sh in full-scan mode and fails when it exits
# nonzero. Every test runs the installer against a sandboxed HOME (mktemp)
# and, for the fixture scenarios, against a minimal source fixture in the
# same temporary tree.

repo_root=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd -P)
installer="$repo_root/install.sh"
restart_line='Restart Tau, or run /reload for skill changes in an active session.'
temporary_dir=$(mktemp -d)
trap 'rm -rf "$temporary_dir"' EXIT

fail() {
  printf 'FAIL: %s\n' "$*" >&2
  exit 1
}

# The install excludes, restated here as the test's independent definition
# of the contract. The comparison helper and the excluded-path probe use it.
install_excludes=(
  --exclude=.git
  --exclude=.venv
  --exclude=__pycache__
  --exclude=.mypy_cache
  --exclude=.pytest_cache
  --exclude=.ruff_cache
  --exclude=.worktrees
)

# run_installer HOME LOG SOURCE_ROOT ARGS... — run the installer for HOME,
# capturing stdout to LOG and stderr to LOG.err; set install_status
install_status=0
run_installer() {
  local home=$1 log=$2 source_root=$3
  shift 3
  install_status=0
  HOME="$home" "$source_root/install.sh" "$@" >"$log" 2>"$log.err" ||
    install_status=$?
}

# assert_install_succeeded LOG — the last installer run exited 0
assert_install_succeeded() {
  local log=$1
  ((install_status == 0)) || {
    cat "$log.err" >&2
    fail "installer exited $install_status"
  }
}

# assert_install_failed LOG [STATUS] — the last installer run exited with
# STATUS, 1 by default
assert_install_failed() {
  local log=$1 expected=${2:-1}
  ((install_status == expected)) ||
    fail "installer exited $install_status, expected $expected (see $log.err)"
}

# assert_real_directory PATH — the path is a directory and not a symlink
assert_real_directory() {
  [[ -d $1 && ! -L $1 ]] || fail "$1 is not a real directory"
}

# assert_absent PATH — the path neither exists nor dangles as a symlink
assert_absent() {
  [[ ! -e $1 && ! -L $1 ]] || fail "$1 exists but must not exist"
}

# assert_symlink_to PATH TARGET — the path is a symlink with TARGET as its
# raw link target
assert_symlink_to() {
  [[ -L $1 ]] || fail "$1 is not a symbolic link"
  [[ $(readlink -- "$1") == "$2" ]] ||
    fail "$1 does not point to $2"
}

# assert_matches_source SOURCE DEST — content matches under the install
# excludes with delete propagation of excluded names; an empty dry-run
# itemize means identical
assert_matches_source() {
  local source=$1 dest=$2 changes
  if ! changes=$(rsync -a -n -i --delete --delete-excluded "${install_excludes[@]}" \
    "$source/" "$dest" 2>&1); then
    fail "content comparison failed for $dest:
$changes"
  fi
  [[ -z $changes ]] || fail "$dest does not match $source:
$changes"
}

# assert_no_excluded_paths ROOT — no excluded development path anywhere
# below ROOT
assert_no_excluded_paths() {
  local found
  found=$(find "$1" \( -name .git -o -name .venv -o -name __pycache__ \
    -o -name .mypy_cache -o -name .pytest_cache -o -name .ruff_cache \
    -o -name .worktrees \) -print -quit)
  [[ -z $found ]] || fail "excluded development path present below $1: $found"
}

# assert_output_line LOG KIND ENTRY — LOG contains exactly the line
# '<KIND>: <ENTRY>'
assert_output_line() {
  grep -Fqx "$2: $3" "$1" ||
    fail "$1 does not contain the line '$2: $3'"
}

# assert_no_entry_lines LOG — no Installed or Updated line appears
assert_no_entry_lines() {
  if grep -Eq '^(Installed|Updated):' "$1"; then
    fail "$1 reports installed or updated entries"
  fi
}

# stamp_field STAMP KEY — print every 'KEY: value' value, one per line
stamp_field() {
  local stamp=$1 key=$2
  sed -n "s/^$key: //p" "$stamp"
}

# assert_stamp_entries STAMP EXPECTED — the entry lines equal EXPECTED, one
# entry per line, sorted lexically
assert_stamp_entries() {
  local stamp=$1 expected=$2 actual
  actual=$(stamp_field "$stamp" entry)
  [[ $actual == "$expected" ]] || fail "stamp entry list mismatch; expected:
$expected
got:
$actual"
}

# assert_stamp_time VALUE — parses as ISO-8601 UTC and is near the test run
assert_stamp_time() {
  local value=$1 epoch now
  [[ $value =~ ^[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}Z$ ]] ||
    fail "stamp time is not ISO-8601 UTC: $value"
  if ! epoch=$(date -u -d "$value" +%s); then
    fail "stamp time does not parse: $value"
  fi
  now=$(date -u +%s)
  ((now - epoch >= 0 && now - epoch < 600)) ||
    fail "stamp time is not near the test run: $value"
}

# assert_final_lines LOG STAMP_REGEX — the last two output lines are the
# stamp summary matching STAMP_REGEX and the restart reminder
assert_final_lines() {
  local log=$1 stamp_regex=$2 second_last last
  second_last=$(tail -n 2 "$log" | head -n 1)
  last=$(tail -n 1 "$log")
  [[ $second_last =~ $stamp_regex ]] ||
    fail "unexpected stamp line: $second_last"
  [[ $last == "$restart_line" ]] || fail "unexpected final line: $last"
}

# hash_tree ROOT — a digest over every file path and its content
hash_tree() {
  find "$1" -type f -print0 | LC_ALL=C sort -z |
    xargs -0 -r md5sum | md5sum
}

# make_fixture ROOT — create a minimal source tree: two skills and the
# extension with tests/ and pyproject.toml, plus a copy of the installer
make_fixture() {
  local root=$1
  mkdir -p "$root/skills/alpha" "$root/skills/beta" \
    "$root/extensions/superpowers-subagent/tests"
  printf '# Alpha\n' >"$root/skills/alpha/SKILL.md"
  printf 'alpha data\n' >"$root/skills/alpha/data.md"
  printf '# Beta\n' >"$root/skills/beta/SKILL.md"
  printf 'beta data\n' >"$root/skills/beta/data.md"
  printf 'def entry():\n    pass\n' \
    >"$root/extensions/superpowers-subagent/extension.py"
  printf '[project]\nname = "fixture"\n' \
    >"$root/extensions/superpowers-subagent/pyproject.toml"
  printf 'def test_entry():\n    pass\n' \
    >"$root/extensions/superpowers-subagent/tests/test_entry.py"
  cp "$installer" "$root/install.sh"
}

# make_git_fixture ROOT — make_fixture plus one committed tree
make_git_fixture() {
  local root=$1
  make_fixture "$root"
  git -C "$root" -c init.defaultBranch=main init -q
  git -C "$root" add -A
  git -C "$root" -c user.email=install-test@example.com \
    -c user.name='Install Test' commit -q -m 'fixture'
}

# add_excluded_paths ROOT — put development paths into the fixture source so
# the install excludes have something to skip
add_excluded_paths() {
  local root=$1
  mkdir -p "$root/skills/alpha/.git" "$root/skills/alpha/.venv" \
    "$root/skills/alpha/__pycache__" \
    "$root/extensions/superpowers-subagent/.pytest_cache"
  printf 'gitdir\n' >"$root/skills/alpha/.git/HEAD"
  printf 'v\n' >"$root/skills/alpha/.venv/marker"
  printf 'c\n' >"$root/skills/alpha/__pycache__/x.pyc"
  printf 'p\n' >"$root/extensions/superpowers-subagent/.pytest_cache/marker"
}

# fixture_entries — the managed entry list of the standard fixture, sorted
# lexically
fixture_entries() {
  printf 'extensions/superpowers-subagent\nskills/alpha\nskills/beta\n'
}

# The suite runs the same scan the pre-commit hook runs. Runs first so the
# scan verdict is reported even when an installer test fails.
test_reference_scan_runs() {
  if ! "$repo_root/tests/check-references.sh"; then
    fail "check-references.sh found checkout-only references"
  fi
}

# Scenario "Copy install": the worktree installs every skill and the
# extension as real directories whose content matches under the excludes,
# the stamp records the source and the full entry list, and the output ends
# with the stamp summary and the restart reminder.
test_fresh_install_from_worktree() {
  local home="$temporary_dir/home-fresh" log="$temporary_dir/fresh.log"
  local stamp="$home/.tau/.tau-superpowers-install"
  local expected_entries skill_dir skill_name sha
  mkdir -p "$home/.tau/skills/unrelated"
  printf 'keep\n' >"$home/.tau/skills/unrelated/marker"
  run_installer "$home" "$log" "$repo_root"
  assert_install_succeeded "$log"
  for skill_dir in "$repo_root"/skills/*; do
    [[ -f "$skill_dir/SKILL.md" ]] || continue
    skill_name=${skill_dir##*/}
    assert_real_directory "$home/.tau/skills/$skill_name"
    assert_matches_source "$skill_dir" "$home/.tau/skills/$skill_name"
    assert_output_line "$log" Installed "skills/$skill_name"
  done
  expected_entries=$(LC_ALL=C sort <<<"$(
    for skill_dir in "$repo_root"/skills/*; do
      [[ -f "$skill_dir/SKILL.md" ]] || continue
      printf 'skills/%s\n' "${skill_dir##*/}"
    done
    printf 'extensions/superpowers-subagent\n'
  )")
  assert_real_directory "$home/.tau/extensions/superpowers-subagent"
  assert_matches_source "$repo_root/extensions/superpowers-subagent" \
    "$home/.tau/extensions/superpowers-subagent"
  assert_output_line "$log" Installed "extensions/superpowers-subagent"
  assert_no_excluded_paths "$home/.tau"
  [[ -f "$home/.tau/extensions/superpowers-subagent/tests/conftest.py" ]] ||
    fail "the extension copy lost its tests directory"
  [[ -f "$home/.tau/extensions/superpowers-subagent/pyproject.toml" ]] ||
    fail "the extension copy lost pyproject.toml"
  [[ -f "$home/.tau/skills/unrelated/marker" ]] ||
    fail "a foreign destination was removed"
  sha=$(git -C "$repo_root" rev-parse HEAD)
  [[ $(stamp_field "$stamp" source) == "$repo_root" ]] ||
    fail "the stamp does not record the source repository"
  [[ $(stamp_field "$stamp" sha) == "$sha" ]] ||
    fail "the stamp does not record the source commit"
  [[ $(stamp_field "$stamp" dirty) =~ ^(yes|no)$ ]] ||
    fail "the stamp dirty marker is missing"
  assert_stamp_time "$(stamp_field "$stamp" time)"
  assert_stamp_entries "$stamp" "$expected_entries"
  assert_final_lines "$log" \
    "^Stamp: ${stamp//./\\.} \\(sha [0-9a-f]{7}, (dirty|clean)\\)$"
}

# Scenario "Copy install" with a source that contains the excluded
# development paths: the install skips them and keeps tests/ and
# pyproject.toml.
test_fresh_install_from_fixture() {
  local root="$temporary_dir/fixture-fresh" home="$temporary_dir/home-fresh-fixture"
  local log="$temporary_dir/fresh-fixture.log"
  make_fixture "$root"
  add_excluded_paths "$root"
  run_installer "$home" "$log" "$root"
  assert_install_succeeded "$log"
  assert_real_directory "$home/.tau/skills/alpha"
  assert_real_directory "$home/.tau/extensions/superpowers-subagent"
  assert_matches_source "$root/skills/alpha" "$home/.tau/skills/alpha"
  assert_matches_source "$root/extensions/superpowers-subagent" \
    "$home/.tau/extensions/superpowers-subagent"
  assert_no_excluded_paths "$home/.tau"
  [[ -f "$home/.tau/extensions/superpowers-subagent/tests/test_entry.py" ]] ||
    fail "the extension copy lost its tests directory"
  [[ -f "$home/.tau/extensions/superpowers-subagent/pyproject.toml" ]] ||
    fail "the extension copy lost pyproject.toml"
  assert_output_line "$log" Installed "skills/alpha"
  assert_output_line "$log" Installed "skills/beta"
  assert_output_line "$log" Installed "extensions/superpowers-subagent"
}

# Scenario "Foreign destination untouched": an unmanaged directory under
# ~/.tau/skills survives an install.
test_foreign_destination_untouched() {
  local root="$temporary_dir/fixture-foreign" home="$temporary_dir/home-foreign"
  local log="$temporary_dir/foreign.log"
  make_fixture "$root"
  mkdir -p "$home/.tau/skills/unrelated"
  printf 'keep\n' >"$home/.tau/skills/unrelated/marker"
  run_installer "$home" "$log" "$root"
  assert_install_succeeded "$log"
  [[ -f "$home/.tau/skills/unrelated/marker" ]] ||
    fail "the foreign destination was removed"
  assert_real_directory "$home/.tau/skills/alpha"
  assert_matches_source "$root/skills/alpha" "$home/.tau/skills/alpha"
}

# Scenario "Foreign destination untouched with a stamp": the second install
# run is the one that reads the stamp and runs the stale-entry and
# repository-link removal. An unmanaged directory under ~/.tau/skills
# survives it. The scenario builds its own fresh fixture and home. It is
# not a rerun of the scenario above against mutated state.
test_foreign_destination_untouched_with_stamp() {
  local root="$temporary_dir/fixture-foreign-stamp" home="$temporary_dir/home-foreign-stamp"
  local first_log="$temporary_dir/foreign-stamp-first.log" second_log="$temporary_dir/foreign-stamp-second.log"
  make_fixture "$root"
  mkdir -p "$home/.tau/skills/unrelated"
  printf 'keep\n' >"$home/.tau/skills/unrelated/marker"
  run_installer "$home" "$first_log" "$root"
  assert_install_succeeded "$first_log"
  run_installer "$home" "$second_log" "$root"
  assert_install_succeeded "$second_log"
  [[ -f "$home/.tau/skills/unrelated/marker" ]] ||
    fail "the foreign destination was removed on the second run"
  assert_real_directory "$home/.tau/skills/alpha"
  assert_matches_source "$root/skills/alpha" "$home/.tau/skills/alpha"
}

# Scenario "User installation collision": a foreign symlink and a foreign
# regular file at managed names stop the install with no changes anywhere.
test_collision_aborts() {
  local root="$temporary_dir/fixture-collision" home="$temporary_dir/home-collision"
  local log="$temporary_dir/collision.log"
  local foreign="$temporary_dir/foreign-skill"
  local stamp="$home/.tau/.tau-superpowers-install"
  make_fixture "$root"
  mkdir -p "$home/.tau/skills" "$foreign"
  printf 'user content\n' >"$foreign/marker"
  ln -s "$foreign" "$home/.tau/skills/alpha"
  printf 'user file\n' >"$home/.tau/skills/beta"
  run_installer "$home" "$log" "$root"
  assert_install_failed "$log"
  grep -q "already exist" "$log.err" ||
    fail "the installer did not explain the conflict"
  assert_symlink_to "$home/.tau/skills/alpha" "$foreign"
  [[ -f "$foreign/marker" ]] || fail "the foreign symlink target was modified"
  [[ $(cat "$home/.tau/skills/beta") == 'user file' ]] ||
    fail "the foreign regular file was replaced"
  assert_absent "$home/.tau/extensions/superpowers-subagent"
  assert_absent "$stamp"
}

# Scenario "Symlink migration": old-style links into the repository become
# real directories, a dangling repository link migrates too, and the source
# repository content is unchanged. A marker written through an old-style
# link stays in the source and appears in the fresh copy.
test_symlink_migration() {
  local root="$temporary_dir/fixture-migrate" home="$temporary_dir/home-migrate"
  local log="$temporary_dir/migrate.log"
  local before after
  make_fixture "$root"
  mkdir -p "$home/.tau/skills" "$home/.tau/extensions"
  ln -s "$root/skills/alpha" "$home/.tau/skills/alpha"
  ln -s "$root/skills/renamed-away" "$home/.tau/skills/beta"
  ln -s "$root/extensions/superpowers-subagent" \
    "$home/.tau/extensions/superpowers-subagent"
  [[ ! -e "$root/skills/renamed-away" ]] ||
    fail "the dangling link target unexpectedly exists"
  printf 'marker\n' >"$home/.tau/skills/alpha/marker-through-link"
  [[ -f "$root/skills/alpha/marker-through-link" ]] ||
    fail "the marker was not written through the link into the source"
  before=$(hash_tree "$root")
  run_installer "$home" "$log" "$root"
  assert_install_succeeded "$log"
  after=$(hash_tree "$root")
  [[ $before == "$after" ]] || fail "the installer modified the source repository"
  assert_real_directory "$home/.tau/skills/alpha"
  assert_real_directory "$home/.tau/skills/beta"
  assert_real_directory "$home/.tau/extensions/superpowers-subagent"
  assert_matches_source "$root/skills/alpha" "$home/.tau/skills/alpha"
  assert_matches_source "$root/skills/beta" "$home/.tau/skills/beta"
  assert_matches_source "$root/extensions/superpowers-subagent" \
    "$home/.tau/extensions/superpowers-subagent"
  [[ -f "$root/skills/alpha/marker-through-link" ]] ||
    fail "the marker left the source"
  [[ -f "$home/.tau/skills/alpha/marker-through-link" ]] ||
    fail "the marker is missing from the fresh copy"
  assert_output_line "$log" Installed "skills/alpha"
  assert_output_line "$log" Installed "skills/beta"
  assert_output_line "$log" Installed "extensions/superpowers-subagent"
}

# Scenario "Copy take-over": a real directory at a managed name converges to
# the source under delete propagation, the delete reaches excluded paths
# planted in the destination, and the output lists the removed and updated
# paths.
test_copy_take_over() {
  local root="$temporary_dir/fixture-takeover" home="$temporary_dir/home-takeover"
  local log="$temporary_dir/takeover.log" dest
  dest="$home/.tau/extensions/superpowers-subagent"
  make_fixture "$root"
  mkdir -p "$dest" "$dest/.venv" "$dest/__pycache__"
  printf 'stale\n' >"$dest/extension.py"
  printf 'junk\n' >"$dest/junk.txt"
  printf 'v\n' >"$dest/.venv/marker"
  printf 'c\n' >"$dest/__pycache__/x.pyc"
  run_installer "$home" "$log" "$root"
  assert_install_succeeded "$log"
  assert_real_directory "$dest"
  assert_matches_source "$root/extensions/superpowers-subagent" "$dest"
  assert_absent "$dest/junk.txt"
  assert_absent "$dest/.venv"
  assert_absent "$dest/__pycache__"
  assert_output_line "$log" Updated "extensions/superpowers-subagent"
  grep -q 'junk.txt' "$log" ||
    fail "the output does not list the removed path"
  grep -q 'extension.py' "$log" ||
    fail "the output does not list the updated path"
  assert_output_line "$log" Installed "skills/alpha"
}

# Scenario "Stamp records a clean tree" and "Stamp records git state": a
# clean commit records the SHA and no dirty marker; an uncommitted change
# flips the marker on the next install.
test_stamp_git_state() {
  local root="$temporary_dir/fixture-git" home="$temporary_dir/home-git"
  local first_log="$temporary_dir/git-first.log" second_log="$temporary_dir/git-second.log"
  local stamp="$home/.tau/.tau-superpowers-install" sha
  make_git_fixture "$root"
  run_installer "$home" "$first_log" "$root"
  assert_install_succeeded "$first_log"
  sha=$(git -C "$root" rev-parse HEAD)
  [[ $sha =~ ^[0-9a-f]{40}$ ]] || fail "the fixture has no 40-hex commit"
  [[ $(stamp_field "$stamp" source) == "$root" ]] ||
    fail "the stamp does not record the fixture source"
  [[ $(stamp_field "$stamp" sha) == "$sha" ]] ||
    fail "the stamp does not record the fixture commit"
  [[ $(stamp_field "$stamp" dirty) == no ]] ||
    fail "a clean tree is recorded as dirty"
  assert_stamp_time "$(stamp_field "$stamp" time)"
  assert_stamp_entries "$stamp" "$(fixture_entries)"
  assert_final_lines "$first_log" \
    "^Stamp: ${stamp//./\\.} \\(sha ${sha:0:7}, clean\\)$"
  printf 'uncommitted\n' >"$root/uncommitted.txt"
  run_installer "$home" "$second_log" "$root"
  assert_install_succeeded "$second_log"
  [[ $(stamp_field "$stamp" sha) == "$sha" ]] ||
    fail "the stamp lost the commit id"
  [[ $(stamp_field "$stamp" dirty) == yes ]] ||
    fail "uncommitted changes are not recorded as dirty"
  assert_final_lines "$second_log" \
    "^Stamp: ${stamp//./\\.} \\(sha ${sha:0:7}, dirty\\)$"
}

# Scenario "Stamp records no git metadata": a source without git records the
# none markers.
test_stamp_without_git() {
  local root="$temporary_dir/fixture-nogit" home="$temporary_dir/home-nogit"
  local log="$temporary_dir/nogit.log"
  local stamp="$home/.tau/.tau-superpowers-install"
  make_fixture "$root"
  run_installer "$home" "$log" "$root"
  assert_install_succeeded "$log"
  [[ $(stamp_field "$stamp" source) == "$root" ]] ||
    fail "the stamp does not record the fixture source"
  [[ $(stamp_field "$stamp" sha) == none ]] ||
    fail "a non-git source records a sha"
  [[ $(stamp_field "$stamp" dirty) == none ]] ||
    fail "a non-git source records a dirty marker"
  assert_stamp_time "$(stamp_field "$stamp" time)"
  assert_final_lines "$log" \
    "^Stamp: ${stamp//./\\.} \\(sha none, none\\)$"
}

# Scenario "Stamp records a repository with no commits": git init without a
# commit records sha none and keeps the normal dirty rule, so the untracked
# layout files record dirty yes.
test_stamp_no_commits() {
  local root="$temporary_dir/fixture-nocommits" home="$temporary_dir/home-nocommits"
  local log="$temporary_dir/nocommits.log"
  local stamp="$home/.tau/.tau-superpowers-install"
  make_fixture "$root"
  git -C "$root" -c init.defaultBranch=main init -q
  run_installer "$home" "$log" "$root"
  assert_install_succeeded "$log"
  [[ $(stamp_field "$stamp" source) == "$root" ]] ||
    fail "the stamp does not record the fixture source"
  [[ $(stamp_field "$stamp" sha) == none ]] ||
    fail "a repository without commits records a sha"
  [[ $(stamp_field "$stamp" dirty) == yes ]] ||
    fail "untracked layout files are not recorded as dirty"
  assert_stamp_time "$(stamp_field "$stamp" time)"
  assert_final_lines "$log" \
    "^Stamp: ${stamp//./\\.} \\(sha none, dirty\\)$"
}

# Scenario "Idempotent re-install": a second run reports every entry as
# unchanged and changes no content.
test_idempotent_reinstall() {
  local root="$temporary_dir/fixture-idempotent" home="$temporary_dir/home-idempotent"
  local first_log="$temporary_dir/idempotent-first.log" second_log="$temporary_dir/idempotent-second.log"
  local before after
  make_fixture "$root"
  run_installer "$home" "$first_log" "$root"
  assert_install_succeeded "$first_log"
  before=$(hash_tree "$home/.tau/skills")$(hash_tree "$home/.tau/extensions")
  run_installer "$home" "$second_log" "$root"
  assert_install_succeeded "$second_log"
  after=$(hash_tree "$home/.tau/skills")$(hash_tree "$home/.tau/extensions")
  [[ $before == "$after" ]] || fail "the second run changed content"
  assert_output_line "$second_log" Unchanged "skills/alpha"
  assert_output_line "$second_log" Unchanged "skills/beta"
  assert_output_line "$second_log" Unchanged "extensions/superpowers-subagent"
  assert_no_entry_lines "$second_log"
}

# Scenario "Missing rsync dependency": without rsync on PATH the installer
# exits 1 before changing any destination.
test_missing_rsync() {
  local root="$temporary_dir/fixture-norsync" home="$temporary_dir/home-norsync"
  local log="$temporary_dir/norsync.log" empty_bin="$temporary_dir/empty-bin"
  local stamp="$home/.tau/.tau-superpowers-install" bash_bin
  make_fixture "$root"
  mkdir -p "$home/.tau/skills/keep" "$empty_bin"
  printf 'keep\n' >"$home/.tau/skills/keep/marker"
  bash_bin=$(command -v bash)
  install_status=0
  HOME="$home" PATH="$empty_bin" "$bash_bin" "$root/install.sh" \
    >"$log" 2>"$log.err" || install_status=$?
  assert_install_failed "$log"
  [[ $(wc -l <"$log.err") -eq 1 ]] ||
    fail "the missing-rsync error is not one stderr line"
  grep -q rsync "$log.err" ||
    fail "the missing-rsync error does not name rsync"
  [[ -f "$home/.tau/skills/keep/marker" ]] ||
    fail "the pre-existing destination was modified"
  assert_absent "$home/.tau/skills/alpha"
  assert_absent "$home/.tau/extensions/superpowers-subagent"
  assert_absent "$stamp"
}

# Scenario "User installation collision" with a stamp present: a recorded
# stamp does not exempt a destination from the collision stop, and a failed
# run leaves the stamp untouched.
test_collision_with_stamp() {
  local root="$temporary_dir/fixture-stamp-collision" home="$temporary_dir/home-stamp-collision"
  local log="$temporary_dir/stamp-collision.log"
  local foreign="$temporary_dir/foreign-takeover"
  local stamp="$home/.tau/.tau-superpowers-install" before
  make_fixture "$root"
  mkdir -p "$foreign"
  printf 'user content\n' >"$foreign/marker"
  run_installer "$home" "$log" "$root"
  assert_install_succeeded "$log"
  before=$(cat "$stamp")
  rm -rf "$home/.tau/skills/alpha"
  ln -s "$foreign" "$home/.tau/skills/alpha"
  run_installer "$home" "$log" "$root"
  assert_install_failed "$log"
  grep -q "already exist" "$log.err" ||
    fail "the installer did not explain the conflict"
  assert_symlink_to "$home/.tau/skills/alpha" "$foreign"
  [[ $(cat "$stamp") == "$before" ]] || fail "the stamp was rewritten"
  assert_matches_source "$root/skills/beta" "$home/.tau/skills/beta"
  assert_matches_source "$root/extensions/superpowers-subagent" \
    "$home/.tau/extensions/superpowers-subagent"
}

# Scenario "Partway failure repair" (failure half): an unreadable source
# file in the lexically first skill fails that entry's copy; later entries
# are not installed, no stamp is written, and the error names the entry.
test_partway_copy_failure() {
  local root="$temporary_dir/fixture-partway" home="$temporary_dir/home-partway"
  local log="$temporary_dir/partway.log"
  local stamp="$home/.tau/.tau-superpowers-install"
  make_fixture "$root"
  printf 'secret\n' >"$root/skills/alpha/secret.md"
  chmod 000 "$root/skills/alpha/secret.md"
  run_installer "$home" "$log" "$root"
  chmod 644 "$root/skills/alpha/secret.md"
  assert_install_failed "$log"
  grep -q "skills/alpha" "$log.err" ||
    fail "the error does not name the failing entry"
  assert_real_directory "$home/.tau/extensions/superpowers-subagent"
  assert_output_line "$log" Installed "extensions/superpowers-subagent"
  assert_absent "$home/.tau/skills/beta"
  assert_absent "$stamp"
}

# The repository-resolving rule: a symlink into a different checkout is a
# conflict for an install from this checkout, and the same link migrates
# when the install runs from the checkout it points into.
test_repository_resolving_rule() {
  local root_a="$temporary_dir/fixture-a" root_b="$temporary_dir/fixture-b"
  local home="$temporary_dir/home-repo-rule"
  local log="$temporary_dir/repo-rule.log"
  local stamp="$home/.tau/.tau-superpowers-install"
  make_fixture "$root_a"
  make_fixture "$root_b"
  mkdir -p "$home/.tau/skills"
  ln -s "$root_a/skills/alpha" "$home/.tau/skills/alpha"
  run_installer "$home" "$log" "$root_b"
  assert_install_failed "$log"
  grep -q "already exist" "$log.err" ||
    fail "the installer did not explain the conflict"
  assert_symlink_to "$home/.tau/skills/alpha" "$root_a/skills/alpha"
  assert_absent "$home/.tau/skills/beta"
  assert_absent "$home/.tau/extensions/superpowers-subagent"
  assert_absent "$stamp"
  run_installer "$home" "$log" "$root_a"
  assert_install_succeeded "$log"
  assert_real_directory "$home/.tau/skills/alpha"
  assert_matches_source "$root_a/skills/alpha" "$home/.tau/skills/alpha"
  assert_output_line "$log" Installed "skills/alpha"
}

# Scenario "Removed entry": an entry the previous stamp records and the
# source no longer provides is removed from the destination and reported.
test_removed_entry() {
  local root="$temporary_dir/fixture-removed" home="$temporary_dir/home-removed"
  local log="$temporary_dir/removed.log" stamp="$home/.tau/.tau-superpowers-install"
  make_fixture "$root"
  run_installer "$home" "$log" "$root"
  assert_install_succeeded "$log"
  rm -rf "$root/skills/beta"
  run_installer "$home" "$log" "$root"
  assert_install_succeeded "$log"
  assert_absent "$home/.tau/skills/beta"
  assert_output_line "$log" Removed "skills/beta"
  assert_matches_source "$root/skills/alpha" "$home/.tau/skills/alpha"
  assert_stamp_entries "$stamp" "$(printf 'extensions/superpowers-subagent\nskills/alpha\n')"
}

# Scenario "Invalid stamp entries are skipped": a stamp entry line that does
# not name a destination inside ~/.tau is invalid. The removal logic and
# --check ignore invalid lines, so a corrupted stamp cannot point a removal
# outside the managed tree. The next install rewrites the stamp with valid
# entries only.
test_invalid_stamp_entries_skipped() {
  local root="$temporary_dir/fixture-bound" home="$temporary_dir/home-bound"
  local check_log="$temporary_dir/bound-check.log" log="$temporary_dir/bound.log"
  local stamp="$home/.tau/.tau-superpowers-install"
  make_fixture "$root"
  run_installer "$home" "$log" "$root"
  assert_install_succeeded "$log"
  mkdir -p "$home/victim" "$temporary_dir/outside"
  printf 'keep\n' >"$home/victim/keep"
  printf 'keep\n' >"$temporary_dir/outside/keep"
  printf 'entry: ../victim\nentry: skills/..\nentry: skills/../../outside\nentry: \n' >>"$stamp"
  run_installer "$home" "$check_log" "$root" --check
  assert_install_succeeded "$check_log"
  [[ ! -s $check_log ]] || fail "the check reported stale entries for a valid tree"
  run_installer "$home" "$log" "$root"
  assert_install_succeeded "$log"
  [[ -f "$home/victim/keep" ]] ||
    fail "a stamp entry escaped ~/.tau and named a removal outside it"
  [[ -f "$temporary_dir/outside/keep" ]] ||
    fail "a stamp entry escaped ~/.tau and named a removal outside it"
  if grep -q '^Removed:' "$log"; then
    fail "the install removed an entry the source provides"
  fi
  assert_output_line "$log" Unchanged "skills/alpha"
  assert_output_line "$log" Unchanged "skills/beta"
  assert_output_line "$log" Unchanged "extensions/superpowers-subagent"
  assert_stamp_entries "$stamp" "$(fixture_entries)"
}

# Scenario "Repository link without source entry removed": repository-
# resolving symlinks at names the source does not provide are removed with
# and without a stamp, and a foreign symlink at an unprovided name stays.
test_repo_link_without_entry_removed() {
  local root="$temporary_dir/fixture-repolink" home="$temporary_dir/home-repolink"
  local log="$temporary_dir/repolink.log"
  local foreign="$temporary_dir/foreign-link-target"
  make_fixture "$root"
  mkdir -p "$home/.tau/skills" "$foreign"
  printf 'foreign\n' >"$foreign/marker"
  ln -s "$root/skills/alpha" "$home/.tau/skills/renamed-away"
  ln -s "$root/skills/deleted-skill" "$home/.tau/skills/dangling"
  ln -s "$foreign" "$home/.tau/skills/unrelated"
  run_installer "$home" "$log" "$root"
  assert_install_succeeded "$log"
  assert_absent "$home/.tau/skills/renamed-away"
  assert_absent "$home/.tau/skills/dangling"
  assert_output_line "$log" Removed "skills/renamed-away"
  assert_output_line "$log" Removed "skills/dangling"
  assert_symlink_to "$home/.tau/skills/unrelated" "$foreign"
  [[ -f "$foreign/marker" ]] || fail "the foreign link target was modified"
  ln -s "$root/skills/alpha" "$home/.tau/skills/late-link"
  run_installer "$home" "$log" "$root"
  assert_install_succeeded "$log"
  assert_absent "$home/.tau/skills/late-link"
  assert_output_line "$log" Removed "skills/late-link"
  assert_symlink_to "$home/.tau/skills/unrelated" "$foreign"
}

# Scenario "Source file deletion propagates": a file the source dropped is
# gone from the destination after the next install.
test_source_file_deletion_propagates() {
  local root="$temporary_dir/fixture-filedel" home="$temporary_dir/home-filedel"
  local log="$temporary_dir/filedel.log"
  make_fixture "$root"
  run_installer "$home" "$log" "$root"
  assert_install_succeeded "$log"
  rm "$root/skills/alpha/data.md"
  run_installer "$home" "$log" "$root"
  assert_install_succeeded "$log"
  assert_absent "$home/.tau/skills/alpha/data.md"
  assert_matches_source "$root/skills/alpha" "$home/.tau/skills/alpha"
  assert_output_line "$log" Updated "skills/alpha"
}

# Scenario "Fresh check passes": --check exits 0 on matching content and
# changes nothing.
test_fresh_check_passes() {
  local root="$temporary_dir/fixture-check-fresh" home="$temporary_dir/home-check-fresh"
  local log="$temporary_dir/check-fresh.log" before after
  make_fixture "$root"
  run_installer "$home" "$log" "$root"
  assert_install_succeeded "$log"
  before=$(hash_tree "$home/.tau/skills")$(hash_tree "$home/.tau/extensions")
  run_installer "$home" "$log" "$root" --check
  assert_install_succeeded "$log"
  after=$(hash_tree "$home/.tau/skills")$(hash_tree "$home/.tau/extensions")
  [[ $before == "$after" ]] || fail "the check changed content"
}

# Scenario "Stale content fails": --check exits 1, prints every differing
# path qualified by its entry, and changes nothing.
test_stale_check_fails() {
  local root="$temporary_dir/fixture-check-stale" home="$temporary_dir/home-check-stale"
  local log="$temporary_dir/check-stale.log"
  make_fixture "$root"
  run_installer "$home" "$log" "$root"
  assert_install_succeeded "$log"
  printf 'edited\n' >"$home/.tau/skills/alpha/data.md"
  printf 'extra\n' >"$home/.tau/skills/alpha/extra.md"
  run_installer "$home" "$log" "$root" --check
  assert_install_failed "$log"
  grep -Fq 'skills/alpha/data.md' "$log" ||
    fail "the check does not print the edited path"
  grep -Fq 'skills/alpha/extra.md' "$log" ||
    fail "the check does not print the added path"
  grep -q '^edited$' "$home/.tau/skills/alpha/data.md" ||
    fail "the check modified the edited file"
  [[ -f "$home/.tau/skills/alpha/extra.md" ]] ||
    fail "the check removed the added file"
}

# Scenario "Missing destination fails the check": a managed destination that
# does not exist is a difference. --check exits 1 and prints the entry in
# the qualified itemize form, and it creates nothing.
test_check_missing_destination_fails() {
  local root="$temporary_dir/fixture-check-nodest" home="$temporary_dir/home-check-nodest"
  local log="$temporary_dir/check-nodest.log"
  make_fixture "$root"
  run_installer "$home" "$log" "$root"
  assert_install_succeeded "$log"
  rm -rf "$home/.tau/skills/alpha"
  run_installer "$home" "$log" "$root" --check
  assert_install_failed "$log"
  grep -Eq 'skills/alpha/$' "$log" ||
    fail "the check does not print the missing entry as a qualified directory line"
  grep -Fq 'skills/alpha/SKILL.md' "$log" ||
    fail "the check does not print the missing entry's files with the entry as prefix"
  assert_absent "$home/.tau/skills/alpha"
}

# Scenario "Deleted source entry fails the check": a stamp-recorded entry
# whose source directory is gone is a difference. --check exits 1 and
# prints the bare entry name without an itemize, and it removes nothing.
test_check_missing_source_entry_fails() {
  local root="$temporary_dir/fixture-check-goneentry" home="$temporary_dir/home-check-goneentry"
  local log="$temporary_dir/check-goneentry.log"
  make_fixture "$root"
  run_installer "$home" "$log" "$root"
  assert_install_succeeded "$log"
  rm -rf "$root/skills/beta"
  run_installer "$home" "$log" "$root" --check
  assert_install_failed "$log"
  grep -Fqx 'skills/beta' "$log" ||
    fail "the check does not print the bare entry name for the deleted source"
  [[ -f "$home/.tau/skills/beta/SKILL.md" ]] ||
    fail "the check removed the installed entry"
}

# Scenario "Missing stamp fails": --check without a stamp exits 1 with the
# exact error line and changes nothing.
test_missing_stamp_check_fails() {
  local root="$temporary_dir/fixture-check-nostamp" home="$temporary_dir/home-check-nostamp"
  local log="$temporary_dir/check-nostamp.log"
  local stamp="$home/.tau/.tau-superpowers-install"
  make_fixture "$root"
  run_installer "$home" "$log" "$root" --check
  assert_install_failed "$log"
  grep -Fqx "Error: no install stamp at $stamp" "$log.err" ||
    fail "the missing-stamp error line is missing"
  assert_absent "$home/.tau"
}

# Scenario "Unavailable source fails": --check when the recorded source
# tree is gone exits 1 and names the recorded source path.
test_unavailable_source_check_fails() {
  local root="$temporary_dir/fixture-check-gonesrc" home="$temporary_dir/home-check-gonesrc"
  local log="$temporary_dir/check-gonesrc.log"
  make_fixture "$root"
  run_installer "$home" "$log" "$root"
  assert_install_succeeded "$log"
  rm -rf "$root"
  run_installer "$home" "$log" "$repo_root" --check
  assert_install_failed "$log"
  grep -Fqx "Error: source tree not found: $root" "$log.err" ||
    fail "the unavailable-source error line is missing"
}

# Scenario "Comparison uses the recorded source": --check from a different
# checkout compares against the stamp's recorded source, so differing
# content in the running checkout does not matter.
test_check_uses_recorded_source() {
  local root_a="$temporary_dir/fixture-check-a" root_b="$temporary_dir/fixture-check-b"
  local home="$temporary_dir/home-check-source" log="$temporary_dir/check-source.log"
  make_fixture "$root_a"
  make_fixture "$root_b"
  printf 'different\n' >"$root_b/skills/alpha/data.md"
  run_installer "$home" "$log" "$root_a"
  assert_install_succeeded "$log"
  run_installer "$home" "$log" "$root_b" --check
  assert_install_succeeded "$log"
}

# Scenario "Partway failure repair": an install run restores a destination
# file that a previous run left missing.
test_partway_failure_repair() {
  local root="$temporary_dir/fixture-repair" home="$temporary_dir/home-repair"
  local log="$temporary_dir/repair.log"
  make_fixture "$root"
  run_installer "$home" "$log" "$root"
  assert_install_succeeded "$log"
  rm "$home/.tau/skills/alpha/data.md"
  run_installer "$home" "$log" "$root"
  assert_install_succeeded "$log"
  assert_matches_source "$root/skills/alpha" "$home/.tau/skills/alpha"
  assert_output_line "$log" Updated "skills/alpha"
}

# Unexpected arguments are usage errors; --check is the one valid mode
# argument. No destination is touched.
test_usage_error() {
  local root="$temporary_dir/fixture-usage" home="$temporary_dir/home-usage"
  local log="$temporary_dir/usage.log"
  make_fixture "$root"
  run_installer "$home" "$log" "$root" --bogus
  assert_install_failed "$log" 2
  grep -q '^Usage: install.sh \[--check\]$' "$log.err" ||
    fail "the usage error does not print the usage"
  assert_absent "$home/.tau"
}

test_reference_scan_runs
test_fresh_install_from_worktree
test_fresh_install_from_fixture
test_foreign_destination_untouched
test_collision_aborts
test_symlink_migration
test_copy_take_over
test_stamp_git_state
test_stamp_without_git
test_stamp_no_commits
test_idempotent_reinstall
test_missing_rsync
test_collision_with_stamp
test_partway_copy_failure
test_repository_resolving_rule
test_removed_entry
test_invalid_stamp_entries_skipped
test_repo_link_without_entry_removed
test_source_file_deletion_propagates
test_foreign_destination_untouched_with_stamp
test_fresh_check_passes
test_stale_check_fails
test_check_missing_destination_fails
test_check_missing_source_entry_fails
test_missing_stamp_check_fails
test_unavailable_source_check_fails
test_check_uses_recorded_source
test_partway_failure_repair
test_usage_error

printf 'Installer tests passed.\n'
