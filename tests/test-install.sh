#!/usr/bin/env bash
set -euo pipefail

repo_root=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd -P)
temporary_dir=$(mktemp -d)
trap 'rm -rf "$temporary_dir"' EXIT

fail() {
  printf 'FAIL: %s\n' "$*" >&2
  exit 1
}

assert_link() {
  local link_path=$1
  local expected_target=$2

  [[ -L "$link_path" ]] || fail "$link_path is not a symbolic link"
  [[ $(readlink -- "$link_path") == "$expected_target" ]] ||
    fail "$link_path does not point to $expected_target"
}

installed_home="$temporary_dir/installed-home"
mkdir -p "$installed_home/.agents/skills" "$temporary_dir/unrelated-skill"
ln -s "$temporary_dir/unrelated-skill" "$installed_home/.agents/skills/unrelated"

HOME="$installed_home" "$repo_root/install.sh" >"$temporary_dir/first-install.log"

skill_count=0
for skill_dir in "$repo_root"/skills/*; do
  [[ -f "$skill_dir/SKILL.md" ]] || continue
  skill_name=${skill_dir##*/}
  assert_link "$installed_home/.agents/skills/$skill_name" "$skill_dir"
  ((skill_count += 1))
done
[[ $skill_count -gt 0 ]] || fail "no source skills found"
assert_link \
  "$installed_home/.tau/extensions/superpowers-subagent" \
  "$repo_root/extensions/superpowers-subagent"
assert_link "$installed_home/.agents/skills/unrelated" "$temporary_dir/unrelated-skill"

HOME="$installed_home" "$repo_root/install.sh" >"$temporary_dir/second-install.log"

conflicting_home="$temporary_dir/conflicting-home"
mkdir -p "$conflicting_home/.agents/skills/brainstorming"
printf 'keep me\n' >"$conflicting_home/.agents/skills/brainstorming/marker"

if HOME="$conflicting_home" "$repo_root/install.sh" \
  >"$temporary_dir/conflict.log" 2>&1; then
  fail "installer accepted a conflicting destination"
fi
[[ -f "$conflicting_home/.agents/skills/brainstorming/marker" ]] ||
  fail "installer replaced a conflicting destination"
[[ ! -e "$conflicting_home/.agents/skills/using-superpowers" ]] ||
  fail "installer made partial skill links before reporting a conflict"
[[ ! -e "$conflicting_home/.tau/extensions/superpowers-subagent" ]] ||
  fail "installer made the extension link before reporting a conflict"

grep -q "already exist" "$temporary_dir/conflict.log" ||
  fail "installer did not explain the conflict"

printf 'Installer tests passed (%d skills).\n' "$skill_count"
