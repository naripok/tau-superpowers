#!/usr/bin/env bash
# Install Tau Superpowers into ~/.tau as real directory copies, or check
# the installed copies against their source with --check.
#
# The managed entries are every directory under <repo>/skills/ that contains
# SKILL.md plus <repo>/extensions/superpowers-subagent. Each destination at
# $HOME/.tau/<entry> is replaced with a copy of its source under delete
# propagation, entries the source no longer provides are removed, and a
# stamp at $HOME/.tau/.tau-superpowers-install records the source and the
# installed entries. A symlinked ~/.tau/skills or ~/.tau/extensions base
# directory stops the install before any change. --check compares the
# installed content against the source tree recorded in the stamp and
# changes nothing.
#
# Usage: install.sh [--check]
#
# Exit status: 0 on success or a matching --check, 1 on a preflight, copy,
# or check failure, 2 on a usage error. Errors go to stderr.
set -euo pipefail

: "${HOME:?HOME must be set to install Tau Superpowers}"

repo_root=
stamp_path="$HOME/.tau/.tau-superpowers-install"
mode=install
entries=()
stamp_entries=()
classes=()
conflicts=()
destination_class=
check_source=
sha=none
dirty=none

# The excludes keep development paths out of the installed copies, and
# delete propagation removes a destination path matching one when the
# source lacks it, so a taken-over directory converges to the produced
# tree exactly.
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
  printf 'Usage: install.sh [--check]\n' >&2
  exit 2
}

die() {
  printf 'Error: %s\n' "$1" >&2
  exit 1
}

# parse_arguments ARGS... — no arguments installs, --check runs the
# staleness check, anything else is a usage error
parse_arguments() {
  if (($# == 0)); then
    return
  fi
  if (($# == 1)) && [[ $1 == --check ]]; then
    mode=check
    return
  fi
  die_usage "$1"
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
  # The extension entry is always present, so a count of one means zero skills
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

# check_bases — stop the install when a base directory is a symlink. The
# -L test examines the final path component only, so a base under a
# symlinked ~/.tau passes when the base itself is a real directory or
# absent. A link counts whatever it resolves to, including a dangling
# target or a target inside the source repository.
check_bases() {
  local base bases=()
  for base in "$HOME/.tau/extensions" "$HOME/.tau/skills"; do
    if [[ -L $base ]]; then
      bases+=("$base")
    fi
  done
  if ((${#bases[@]} > 0)); then
    {
      printf 'Error: these base directories are symlinks and block installation:\n'
      printf '  %s\n' "${bases[@]}"
      printf 'No destination was changed. Remove each symlink or replace it with a real directory, then run this installer again.\n'
    } >&2
    exit 1
  fi
}

# preflight — check the base directories, then classify every destination
# before changing any of them. A base symlink or a conflict stops the
# install with zero destination changes.
preflight() {
  check_bases
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

# entry_is_bounded ENTRY. Returns 0 when the entry names a destination
# inside ~/.tau. The stamp is written by this installer, so the check
# bounds a corrupted or edited stamp. A skill entry is skills/ plus a
# non-empty name with no slash and not the name '.' or '..'. The
# extension entry is exact.
entry_is_bounded() {
  local name
  [[ $1 == extensions/superpowers-subagent ]] && return 0
  [[ $1 == skills/* ]] || return 1
  name=${1#skills/}
  [[ -n $name && $name != . && $name != .. && $name != */* ]]
}

# read_stamp_entries STAMP. Fills stamp_entries[] with the stamp's
# recorded entries that pass entry_is_bounded. A missing stamp records
# nothing and an invalid entry line is skipped.
read_stamp_entries() {
  local line
  stamp_entries=()
  if [[ -f $1 ]]; then
    while IFS= read -r line; do
      if entry_is_bounded "$line"; then
        stamp_entries+=("$line")
      fi
    done < <(sed -n 's/^entry: //p' "$1")
  fi
}

# entry_is_managed ENTRY — the source provides this entry
entry_is_managed() {
  local candidate
  for candidate in "${entries[@]}"; do
    [[ $candidate == "$1" ]] && return 0
  done
  return 1
}

# remove_entry ENTRY — delete the destination of an entry the source no
# longer provides and report the removal
remove_entry() {
  rm -rf -- "$HOME/.tau/$1"
  printf 'Removed: %s\n' "$1"
}

# remove_stale_stamp_entries — remove destinations the previous stamp
# recorded but the source no longer provides
remove_stale_stamp_entries() {
  local entry dest
  for entry in "${stamp_entries[@]}"; do
    entry_is_managed "$entry" && continue
    dest="$HOME/.tau/$entry"
    if [[ -e $dest || -L $dest ]]; then
      remove_entry "$entry"
    fi
  done
}

# remove_stale_repo_links — remove repository-resolving symlinks at names
# the source does not provide, with or without a stamp
remove_stale_repo_links() {
  local path entry resolved
  for path in "$HOME/.tau/skills"/* "$HOME/.tau/extensions"/*; do
    [[ -L $path ]] || continue
    entry="${path#"$HOME/.tau/"}"
    entry_is_managed "$entry" && continue
    resolved=$(realpath -m -- "$path")
    if [[ $resolved == "$repo_root" || $resolved == "$repo_root"/* ]]; then
      remove_entry "$entry"
    fi
  done
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
  itemize=$(rsync -a --delete --delete-excluded --itemize-changes "${exclude_args[@]}" \
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

# run_check — compare the installed content against the source tree
# recorded in the stamp and exit 1 when anything differs. The check reads
# the stamp's source path, runs no destination preflight, and changes
# nothing.
run_check() {
  local entry entry_source itemize line status stale=0
  [[ -f $stamp_path ]] || die "no install stamp at $stamp_path"
  check_source=$(sed -n 's/^source: //p' "$stamp_path")
  read_stamp_entries "$stamp_path"
  [[ -d $check_source ]] || die "source tree not found: $check_source"
  for entry in "${stamp_entries[@]}"; do
    entry_source="$check_source/$entry"
    if [[ ! -d $entry_source ]]; then
      printf '%s\n' "$entry"
      stale=1
      continue
    fi
    status=0
    itemize=$(rsync -a --delete --delete-excluded --itemize-changes --dry-run \
      "${exclude_args[@]}" "$entry_source/" "$HOME/.tau/$entry" 2>&1) || status=$?
    if ((status != 0)); then
      printf 'Error: rsync failed for entry %s (exit %d)\n' "$entry" "$status" >&2
      exit 1
    fi
    if [[ -n $itemize ]]; then
      stale=1
      while IFS= read -r line; do
        # Itemize lines carry an 11-character change code or a *deleting
        # marker before the path; rsync notes without one name no differing
        # path and are skipped
        [[ ${line:11:1} == ' ' ]] || continue
        if [[ ${line:12} == ./ ]]; then
          printf '%s%s/\n' "${line:0:12}" "$entry"
        else
          printf '%s%s/%s\n' "${line:0:12}" "$entry" "${line:12}"
        fi
      done <<<"$itemize"
    fi
  done
  if ((stale != 0)); then
    exit 1
  fi
}

# run_install — preflight, remove stale entries, install every entry, and
# record the stamp
run_install() {
  resolve_repo_root
  check_sources
  parse_entries
  preflight
  read_stamp_entries "$stamp_path"
  remove_stale_stamp_entries
  remove_stale_repo_links
  install_entries
  write_stamp
  print_stamp_line
  printf '%s\n' 'Restart Tau, or run /reload for skill changes in an active session.'
}

main() {
  parse_arguments "$@"
  check_dependencies
  if [[ $mode == check ]]; then
    run_check
  else
    run_install
  fi
}

main "$@"
