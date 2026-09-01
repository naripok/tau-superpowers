#!/usr/bin/env bash
# Scan the skill and extension Markdown for checkout-only references.
#
# A checkout-only reference names a file that exists inside this source tree
# but has no counterpart in the tree this install produces under ~/.tau, so
# an agent working from the installed resource cannot resolve it. This
# scanner is the single implementation of the classification rules: the
# pre-commit hook (.githooks/pre-commit) runs it in staged mode and
# tests/test-references.sh proves its behavior.
#
# Usage: tests/check-references.sh [--staged] [ROOT]
#
# Without --staged the scanner reads the worktree content of every .md file
# under skills/ and extensions/superpowers-subagent/ of the repository that
# contains the script, or of ROOT when given. With --staged it reads the
# index content of the git-managed .md files in those trees of the current
# repository; path existence checks always use the worktree.
#
# Exit status: 0 when no checkout-only reference is found, 1 when at least
# one is found, 2 on a usage error. Each finding prints to stdout as
# '<path relative to ROOT>: <reference>'.
set -euo pipefail

scanner_name=tests/check-references.sh
root=
staged=0
findings=0
produced_path=

die_usage() {
  printf 'Error: %s\n' "$1" >&2
  printf 'Usage: %s [--staged] [ROOT]\n' "$scanner_name" >&2
  exit 2
}

# parse_arguments ARGS... — set $staged and $root from the command line;
# worktree mode resolves ROOT from the argument or from this script's
# repository, and --staged resolves the repository from the current directory
parse_arguments() {
  local root_arg=""
  while (($# > 0)); do
    case $1 in
      --staged) staged=1 ;;
      -*) die_usage "unknown option: $1" ;;
      *)
        [[ -z $root_arg ]] || die_usage "expected at most one ROOT argument"
        root_arg=$1
        ;;
    esac
    shift
  done
  if (( staged )); then
    [[ -z $root_arg ]] || die_usage "--staged takes no ROOT argument"
    root=$(git rev-parse --show-toplevel 2>/dev/null) ||
      die_usage "--staged needs a working directory inside a git repository"
  else
    if [[ -n $root_arg ]]; then
      root=$root_arg
    else
      root=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd -P)
    fi
    root=$(cd -- "$root" && pwd -P) || die_usage "ROOT is not a directory: $root_arg"
    [[ -d $root/skills && -d $root/extensions/superpowers-subagent ]] ||
      die_usage "the tree at $root must contain skills/ and extensions/superpowers-subagent/"
  fi
}

# scan_worktree — scan every .md file under the two resource roots of $root
scan_worktree() {
  local rel content
  while IFS= read -r -d '' rel; do
    content=$(cat -- "$root/$rel")
    scan_file "$rel" "$content"
  done < <(
    cd -- "$root" &&
      find skills extensions/superpowers-subagent -type f -name '*.md' -print0 | sort -z
  )
}

# scan_staged — scan the index content of the git-managed .md files under the
# two resource roots of $root
scan_staged() {
  local rel content
  while IFS= read -r -d '' rel; do
    case $rel in
      *.md) ;;
      *) continue ;;
    esac
    content=$(git -C "$root" show ":$rel")
    scan_file "$rel" "$content"
  done < <(git -C "$root" ls-files -z -- skills extensions/superpowers-subagent | sort -z)
}

# scan_file REL CONTENT — classify every reference in one file's content
scan_file() {
  local rel=$1 content=$2 ref
  while IFS= read -r ref; do
    [[ -n $ref ]] || continue
    classify "$rel" "$ref"
  done < <(extract_refs "$content")
}

# extract_refs CONTENT — print the references to classify, one per line and
# deduplicated: Markdown link targets that are not http(s), mailto:, or a
# pure '#fragment', plus backticked tokens containing '/'; a trailing
# '#fragment' is stripped before classification
extract_refs() {
  local content=$1
  {
    grep -oE '\]\([^)]*\)' <<<"$content" | sed -e 's/^](//' -e 's/)$//' |
      grep -vE '^(https?://|mailto:|#)' || true
    grep -oE '`[^`]*`' <<<"$content" | sed -e 's/^`//' -e 's/`$//' | grep '/' || true
  } | sed -e 's/#[^#/]*$//' | sort -u
}

# classify REL REF — report REF as a checkout-only reference when a regular
# file exists for it in the source checkout, resolved against the referencing
# file's directory or against $root, and none exists in the produced tree
classify() {
  local rel=$1 ref=$2 file_dir
  case $ref in
    # Workflow artifact paths are not carried resources.
    docs/design/* | docs/specs/* | docs/plans/*) return ;;
  esac
  file_dir=$(dirname -- "$rel")
  local in_file_dir="$root/$file_dir/$ref" in_root="$root/$ref"
  # A target whose checkout-side resolution names an existing directory is
  # never checkout-only.
  if [[ -d $in_file_dir || -d $in_root ]]; then return; fi
  # A target that exists nowhere is not checkout-only.
  if [[ ! -f $in_file_dir && ! -f $in_root ]]; then return; fi
  if installed_side_resolves "$rel" "$ref"; then return; fi
  printf '%s: %s\n' "$rel" "$ref"
  findings=$((findings + 1))
}

# map_produced_path CANDIDATE — set produced_path to the source-relative path
# the install produces for CANDIDATE, or return 1 when CANDIDATE escapes the
# tree, runs through an excluded directory, or does not land inside skills/
# or extensions/superpowers-subagent/, the only trees the install produces
map_produced_path() {
  local parts=() part result=""
  IFS=/ read -r -a parts <<<"$1"
  for part in "${parts[@]}"; do
    case $part in
      '' | .) ;;
      # Keep in sync with exclude_args in install.sh; a new exclude there needs the same entry here.
      .git | .venv | __pycache__ | .mypy_cache | .pytest_cache | .ruff_cache | .worktrees)
        return 1
        ;;
      ..)
        if [[ $result == */* ]]; then
          result=${result%/*}
        elif [[ -n $result ]]; then
          result=""
        else
          return 1
        fi
        ;;
      *) result+="${result:+/}$part" ;;
    esac
  done
  case $result in
    skills/* | extensions/superpowers-subagent/*) ;;
    *) return 1 ;;
  esac
  produced_path=$result
}

# probe_install CANDIDATE — return 0 when the install produces a regular file
# at the source-relative CANDIDATE
probe_install() {
  map_produced_path "$1" && [[ -f $root/$produced_path ]]
}

# installed_side_resolves REL REF — return 0 when the tree this install
# produces contains a file for REF. The produced tree is evaluated by mapping
# installed locations back to source paths: ~/.tau/skills/<name>/... maps to
# <root>/skills/<name>/..., ~/.tau/extensions/superpowers-subagent/... maps
# to <root>/extensions/superpowers-subagent/..., and no other ~/.tau path is
# produced. The bases are, in order, the referencing file's installed
# directory, the owning resource's installed directory, any sibling installed
# skill directory, and the installed tree root ~/.tau.
installed_side_resolves() {
  local rel=$1 ref=$2 owning="" file_sub=""
  case $rel in
    skills/*)
      local rest=${rel#skills/}
      case $rest in
        */*) owning=skills/${rest%%/*} file_sub=${rest#*/} ;;
      esac
      ;;
    extensions/superpowers-subagent/*)
      owning=extensions/superpowers-subagent
      file_sub=${rel#extensions/superpowers-subagent/}
      ;;
  esac
  if [[ -n $owning ]]; then
    local sub_dir
    sub_dir=$(dirname -- "$file_sub")
    probe_install "$owning/$sub_dir/$ref" && return 0
    probe_install "$owning/$ref" && return 0
  fi
  local skill_dir name
  for skill_dir in "$root"/skills/*/SKILL.md; do
    [[ -f $skill_dir ]] || continue
    name=${skill_dir%/*}
    probe_install "skills/${name##*/}/$ref" && return 0
  done
  probe_install "$ref"
}

parse_arguments "$@"
if (( staged )); then
  scan_staged
else
  scan_worktree
fi
if (( findings > 0 )); then
  exit 1
fi
