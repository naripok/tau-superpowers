#!/usr/bin/env bash
set -euo pipefail

: "${HOME:?HOME must be set to install Tau Superpowers}"

repo_root=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)
skills_source="$repo_root/skills"
extension_source="$repo_root/extensions/superpowers-subagent"
skills_destination="$HOME/.tau/skills"
extensions_destination="$HOME/.tau/extensions"

if [[ ! -d "$skills_source" ]]; then
  printf 'Error: skills directory not found: %s\n' "$skills_source" >&2
  exit 1
fi
if [[ ! -f "$extension_source/extension.py" ]]; then
  printf 'Error: Tau extension entry point not found: %s\n' "$extension_source/extension.py" >&2
  exit 1
fi

sources=()
destinations=()
for skill_dir in "$skills_source"/*; do
  [[ -f "$skill_dir/SKILL.md" ]] || continue
  sources+=("$skill_dir")
  destinations+=("$skills_destination/${skill_dir##*/}")
done

if ((${#sources[@]} == 0)); then
  printf 'Error: no Agent Skills found under %s\n' "$skills_source" >&2
  exit 1
fi

sources+=("$extension_source")
destinations+=("$extensions_destination/superpowers-subagent")

conflicts=()
for index in "${!sources[@]}"; do
  source_path=${sources[$index]}
  destination_path=${destinations[$index]}
  if [[ -L "$destination_path" && "$destination_path" -ef "$source_path" ]]; then
    continue
  fi
  if [[ -e "$destination_path" || -L "$destination_path" ]]; then
    conflicts+=("$destination_path")
  fi
done

if ((${#conflicts[@]} > 0)); then
  printf 'Error: these destinations already exist and point elsewhere:\n' >&2
  printf '  %s\n' "${conflicts[@]}" >&2
  printf 'No links were changed. Remove or relocate the conflicts, then run this installer again.\n' >&2
  exit 1
fi

mkdir -p -- "$skills_destination" "$extensions_destination"

created=0
unchanged=0
for index in "${!sources[@]}"; do
  source_path=${sources[$index]}
  destination_path=${destinations[$index]}
  if [[ -L "$destination_path" && "$destination_path" -ef "$source_path" ]]; then
    printf 'Already linked: %s\n' "$destination_path"
    ((unchanged += 1))
    continue
  fi
  ln -s -- "$source_path" "$destination_path"
  printf 'Linked: %s -> %s\n' "$destination_path" "$source_path"
  ((created += 1))
done

printf '\nTau Superpowers installed: %d link(s) created, %d unchanged.\n' "$created" "$unchanged"
printf 'Keep this checkout at: %s\n' "$repo_root"
printf 'Restart Tau, or run /reload for skill changes in an active session.\n'
