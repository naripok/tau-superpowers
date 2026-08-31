#!/usr/bin/env bash
# Install Tau Superpowers into ~/.tau as real directory copies.
#
# The managed entries are every directory under <repo>/skills/ that contains
# SKILL.md plus <repo>/extensions/superpowers-subagent. Each destination at
# $HOME/.tau/<entry> is replaced with a copy of its source under delete
# propagation, and a stamp at $HOME/.tau/.tau-superpowers-install records
# the source and the installed entries.
#
# Usage: install.sh
#
# Exit status: 0 on success, 1 on a preflight or copy failure, 2 on a usage
# error. Errors go to stderr.
set -euo pipefail

: "${HOME:?HOME must be set to install Tau Superpowers}"

repo_root=
stamp_path="$HOME/.tau/.tau-superpowers-install"
entries=()
classes=()
conflicts=()
destination_class=
sha=none
dirty=none
stamp_time=

# The excludes keep development paths out of the installed copies.
exclude_args=(
  --exclude=.git
  --exclude=.venv
  --exclude=__pycache__
  --exclude=.mypy_cache
  --exclude=.pytest_cache
  --exclude=.ruff_cache
  --exclude=.worktrees
)

die_usage() {
  printf 'Error: unexpected argument: %s\n' "$1" >&2
  printf 'Usage: install.sh\n' >&2
  exit 2
}

die() {
  printf 'Error: %s\n' "$1" >&2
  exit 1
}

# parse_arguments ARGS... — install mode is single-shot and takes no
# arguments; any argument is a usage error
parse_arguments() {
  (($# == 0)) || die_usage "$1"
}

# check_dependencies — rsync is the copy engine. Check it before anything
# that needs external tools, so a missing rsync exits before any work.
check_dependencies() {
  command -v rsync >/dev/null 2>&1 || die 'rsync is not available on PATH'
}

# resolve_repo_root — the repository that contains this installer; all
# managed sources live under it
resolve_repo_root() {
  repo_root=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)
}

# check_sources — both managed source roots must exist
check_sources() {
  [[ -d "$repo_root/skills" ]] ||
    die "skills directory not found: $repo_root/skills"
  [[ -d "$repo_root/extensions/superpowers-subagent" ]] ||
    die "extension source not found: $repo_root/extensions/superpowers-subagent"
}

# parse_entries — fill entries[] with every managed entry in lexical order.
# An entry names its source directory relative to the repository root and
# its destination directory relative to ~/.tau.
parse_entries() {
  local skill_dir
  mapfile -t entries < <(
    {
      for skill_dir in "$repo_root"/skills/*; do
        [[ -f "$skill_dir/SKILL.md" ]] || continue
        printf 'skills/%s\n' "${skill_dir##*/}"
      done
      printf 'extensions/superpowers-subagent\n'
    } | LC_ALL=C sort
  )
  ((${#entries[@]} > 1)) ||
    die "no Agent Skills found under $repo_root/skills"
}

# classify_destination DEST — set destination_class to absent, symlink,
# directory, or conflict. Symlink resolution tolerates missing targets, so
# a dangling link into the repository classifies as migratable.
classify_destination() {
  local dest=$1 resolved
  if [[ ! -e $dest && ! -L $dest ]]; then
    destination_class=absent
  elif [[ -L $dest ]]; then
    resolved=$(realpath -m -- "$dest")
    if [[ $resolved == "$repo_root" || $resolved == "$repo_root"/* ]]; then
      destination_class=symlink
    else
      destination_class=conflict
    fi
  elif [[ -d $dest ]]; then
    destination_class=directory
  else
    destination_class=conflict
  fi
}

# preflight — classify every destination before changing any of them; a
# conflict stops the install with zero destination changes
preflight() {
  local index
  for index in "${!entries[@]}"; do
    classify_destination "$HOME/.tau/${entries[$index]}"
    classes+=("$destination_class")
    if [[ $destination_class == conflict ]]; then
      conflicts+=("$HOME/.tau/${entries[$index]}")
    fi
  done
  if ((${#conflicts[@]} > 0)); then
    {
      printf 'Error: these destinations already exist and block installation:\n'
      printf '  %s\n' "${conflicts[@]}"
      printf 'No destination was changed. Remove or relocate the conflicts, then run this installer again.\n'
    } >&2
    exit 1
  fi
}

# install_entry INDEX — copy one source into its destination and print the
# per-entry result line. A symlink destination is removed before the copy so
# nothing is ever written through a link.
install_entry() {
  local index=$1
  local entry=${entries[$index]} dest="$HOME/.tau/${entries[$index]}"
  local itemize line status=0
  if [[ ${classes[$index]} == symlink ]]; then
    rm -- "$dest"
  fi
  itemize=$(rsync -a --delete --itemize-changes "${exclude_args[@]}" \
    "$repo_root/$entry/" "$dest" 2>&1) || status=$?
  if ((status != 0)); then
    printf 'Error: rsync failed for entry %s (exit %d)\n' "$entry" "$status" >&2
    if [[ -n $itemize ]]; then
      printf '%s\n' "$itemize" >&2
    fi
    exit 1
  fi
  case ${classes[$index]} in
    absent | symlink)
      printf 'Installed: %s\n' "$entry"
      ;;
    directory)
      if [[ -z $itemize ]]; then
        printf 'Unchanged: %s\n' "$entry"
      else
        printf 'Updated: %s\n' "$entry"
        while IFS= read -r line; do
          printf '  %s\n' "$line"
        done <<<"$itemize"
      fi
      ;;
  esac
}

# install_entries — copy every entry in lexical order; a failed copy stops
# the run before the next entry
install_entries() {
  local index
  mkdir -p -- "$HOME/.tau/skills" "$HOME/.tau/extensions"
  for index in "${!entries[@]}"; do
    install_entry "$index"
  done
}

# read_git_state — set sha and dirty from the source repository. A source
# without git metadata records none for both; a repository without commits
# records sha none and keeps the dirty rule.
read_git_state() {
  if git -C "$repo_root" rev-parse --is-inside-work-tree >/dev/null 2>&1; then
    sha=$(git -C "$repo_root" rev-parse HEAD 2>/dev/null) || sha=none
    [[ $sha =~ ^[0-9a-f]{40}$ ]] || sha=none
    if [[ -n $(git -C "$repo_root" status --porcelain) ]]; then
      dirty=yes
    else
      dirty=no
    fi
  else
    sha=none
    dirty=none
  fi
}

# write_stamp — record the source, its git state, the install time, and the
# managed entries after every successful install
write_stamp() {
  local entry
  stamp_time=$(date -u +%Y-%m-%dT%H:%M:%SZ)
  read_git_state
  {
    printf 'source: %s\n' "$repo_root"
    printf 'sha: %s\n' "$sha"
    printf 'dirty: %s\n' "$dirty"
    printf 'time: %s\n' "$stamp_time"
    for entry in "${entries[@]}"; do
      printf 'entry: %s\n' "$entry"
    done
  } >"$stamp_path"
}

# print_stamp_line — summarize the stamp for the user
print_stamp_line() {
  local sha_display=none dirty_display=none
  if [[ $sha != none ]]; then
    sha_display=${sha:0:7}
  fi
  case $dirty in
    yes) dirty_display=dirty ;;
    no) dirty_display=clean ;;
  esac
  printf 'Stamp: %s (sha %s, %s)\n' "$stamp_path" "$sha_display" "$dirty_display"
}

main() {
  parse_arguments "$@"
  check_dependencies
  resolve_repo_root
  check_sources
  parse_entries
  preflight
  install_entries
  write_stamp
  print_stamp_line
  printf '%s\n' 'Restart Tau, or run /reload for skill changes in an active session.'
}

main "$@"
