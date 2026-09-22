# Proposal: Taste Design Skills

## Intent

Carry the community `taste-skill` frontend design skills into this package as chained skills. The package currently ships no frontend-design guidance: an agent that builds or restyles a UI has no skill to load. The taste-skill collection (upstream: `naripok/taste-skill`, a mirror of `Leonxlnx/taste-skill`, MIT) supplies that guidance as battle-tested Agent Skills, plus one output-discipline skill that targets truncation and placeholder shortcuts in generated work. This change carries 7 of its 13 skills, gates them under `using-superpowers` as chained skills, and keeps every other upstream artifact out of the repository.

**Selected depth: Standard.** The baseline has a material source discrepancy (see Baseline Evidence): the package's own documents disagree with the tree about which skills the package ships and which skills are model-invocable. The Bounded condition "the baseline has no material source discrepancy" fails, so this change classifies as Standard. The change resolves the discrepancy in scope.

## Baseline Evidence

**Baseline branch: undocumented existing domain.** No living spec covers the skill-catalog domain (which skills the package ships, the two-tier system, the Skill Map, reachability, and installer carry rules). Current behavior is reconstructed from these sources:

- The tree: `skills/` holds 16 skill directories, each with one `SKILL.md`. Five skills are model-invocable (no `disable-model-invocation` frontmatter): `using-superpowers`, `systematic-debugging`, `writing-unambiguous-text`, `writing-skills`, `writing-actionable-text`. The other 11 set `disable-model-invocation: true` and stay out of every skill index.
- `skills/using-superpowers/SKILL.md`: defines the two tiers, the Skill Map table (15 rows), and the reachability rule: a chained skill without a reachable reference from a visible skill, a dispatch template, or a sibling skill is dead. Its prose names four entrypoint skills and states that every other skill sets `disable-model-invocation: true`. Both statements are stale against the tree: `writing-actionable-text` is model-invocable and absent from the Skill Map.
- `skills/writing-skills/SKILL.md`: Tau discovers skills as directories that contain `SKILL.md`. The directory name and the frontmatter `name` MUST be identical. The description starts with "Use when...", stays in third person, lists triggers only, and never summarizes the workflow. Naming uses verb-first gerunds. Every reference in a skill resolves inside the installed tree (own directory, sibling skill directory, or the extension directory).
- `install.sh`: carries every directory under `skills/` that contains a `SKILL.md` into `~/.tau/skills/`, plus the extension. Nothing else ships.
- `README.md`: states "15 Tau-discoverable Agent Skills", lists 15 table rows, and omits `writing-actionable-text` from the Included Skills table.
- `tests/check-references.sh` (runs staged in the pre-commit hook): scans all skill and extension markdown for references that resolve in the checkout but not in the produced install tree, and exits non-zero on a finding. It does not flag references to files that exist nowhere; the self-contained-reference check in `writing-skills` covers that case.

Test baseline at commit `b833ebd`: all 5 test scripts in `tests/` pass, and the reference scan is clean.

**Material discrepancy.** The documents and the tree disagree about shipped behavior: `skills/using-superpowers/SKILL.md` and `README.md` describe a four-entrypoint, 15-skill package, while the tree ships 16 skills with 5 model-invocable. The discrepancy is material because its resolutions demand different edits: documenting `writing-actionable-text` as the fifth entrypoint keeps its frontmatter unchanged, while demoting it to a chained skill rewrites an existing skill's frontmatter. Resolution recorded in this proposal: `writing-actionable-text` stays model-invocable, and the documents sync to a five-entrypoint, 16-skill baseline. This matches current behavior and the intent of the commits that added the skill. This change edits those documents anyway, so the sync rides in scope.

**Upstream state.** The local clone at `/tmp/taste-skill` pins upstream commit `e988add`. The upstream `skills/` directory holds 13 skill directories plus one file. `taste-skill` carries version 2 (experimental) per the upstream `CHANGELOG.md`; `taste-skill-v1` preserves version 1 for backward compatibility. No upstream `SKILL.md` references an upstream-local script, asset, example, or research file (checked by pattern scan), so a markdown-only carry is self-contained. Four upstream skills (`image-to-code-skill`, `imagegen-frontend-web`, `imagegen-frontend-mobile`, `brandkit`) require an image-generation tool; this package has none.

## Required Outcomes

1. The package ships 7 new chained skills under `skills/<new-name>/SKILL.md`, one directory per skill, with the body content carried verbatim from upstream.
2. Each new skill's frontmatter declares the new name (identical to its directory), a description that starts with "Use when..." and lists triggers only, and `disable-model-invocation: true`.
3. The Skill Map in `skills/using-superpowers/SKILL.md` carries one row per new skill plus a Skill Priority entry that routes frontend work to `designing-frontend-interfaces`.
4. The README's Included Skills table lists the new skills, the skill count is correct, and the README ends with a short attribution note that names the upstream source and states the adaptation.
5. The baseline discrepancy is resolved: the Skill Map and the README list `writing-actionable-text` as the fifth entrypoint skill, the entrypoint wording in both files names five entrypoint skills, and no existing skill's frontmatter changes.
6. Every reference in every new skill resolves inside the installed tree. `tests/check-references.sh` exits 0, and all tests in `tests/` pass.
7. This change adds no model-invocable skill and changes no existing skill's frontmatter: the set of model-invocable skills after the change is exactly the five entrypoint skills the tree has today.

## Acceptance Examples

- A workflow step that reads `../designing-frontend-interfaces/SKILL.md` by sibling path from any installed skill resolves the file.
- The frontmatter of each new skill sets `disable-model-invocation: true`, so a skill index lists no new name.
- With the new files staged, `bash tests/check-references.sh` exits 0 and the pre-commit hook passes. The self-contained-reference check additionally passes: no new skill references a file outside the installed tree.
- `bash tests/test-install.sh` passes, and the installer carries the 7 new directories.
- The last section of `README.md` is the attribution note.
- The entrypoint wording in `skills/using-superpowers/SKILL.md` and `README.md` names the same five skills that carry no `disable-model-invocation` frontmatter in the tree.

## Scope

**In scope:**

- 7 new skill directories under `skills/`, each containing one `SKILL.md` with a verbatim upstream body and adapted frontmatter.
- Edits to `skills/using-superpowers/SKILL.md`: Skill Map rows, one Skill Priority line, and the entrypoint wording.
- Edits to `README.md`: Included Skills table rows, the skill count, the entrypoint wording, and the trailing attribution note.
- Sync of `writing-actionable-text` into the Skill Map and the README table as the fifth entrypoint skill (baseline discrepancy resolution).

**Out of scope:**

- The 4 image-dependent upstream skills (`image-to-code-skill`, `imagegen-frontend-web`, `imagegen-frontend-mobile`, `brandkit`). They wait for the future media-pipeline integration project, which owns their adaptation against the real pipeline interface.
- The upstream `stitch-skill` (`stitch-design-taste`): excluded by operator decision. No Stitch-related skill ships in this change.
- `taste-skill-v1` and every non-skill upstream artifact (installers, assets, examples, research, plugin manifests, changelog, README, `llms.txt`, `stitch-skill/DESIGN.md`).
- Any rewrite of skill bodies to the writing-unambiguous-text standard.
- Per-skill behavioral testing of skill bodies.
- Any change to an existing skill's frontmatter, including `writing-actionable-text`.
- Installer, extension, and test-infrastructure changes beyond what the outcomes require.

## Constraints

- Bodies stay verbatim: no edits to any upstream body content. The frontmatter is the only adapted part of each file.
- Directory name and frontmatter `name` are identical and follow the package naming convention (lowercase, single hyphens, verb-first gerunds).
- Each description stays under 500 characters.
- The attribution note names the upstream repository and its MIT license.
- No new entrypoint skill, and no change to any existing skill's frontmatter. The documented entrypoint set becomes the five skills that are model-invocable in the tree today.
- Every chained skill stays reachable through at least one Skill Map row.

## Approach

Carry the 7 skills under new names with this mapping:

| Upstream directory | Upstream name | New directory and name |
| --- | --- | --- |
| `taste-skill` | `design-taste-frontend` | `designing-frontend-interfaces` |
| `gpt-tasteskill` | `gpt-taste` | `enforcing-strict-design-direction` |
| `redesign-skill` | `redesign-existing-projects` | `redesigning-existing-interfaces` |
| `soft-skill` | `high-end-visual-design` | `designing-premium-soft-interfaces` |
| `minimalist-skill` | `minimalist-ui` | `designing-minimalist-interfaces` |
| `brutalist-skill` | `industrial-brutalist-ui` | `designing-brutalist-interfaces` |
| `output-skill` | `full-output-enforcement` | `enforcing-complete-output` |

Each carry step: copy the upstream `SKILL.md`, replace the frontmatter `name` with the new name, replace the description with a "Use when..." trigger description that preserves the upstream trigger content, and add `disable-model-invocation: true`. The body below the frontmatter stays byte-identical.

Skill Map integration: one row per skill in the chained tier with a "Load it when" condition (frontend work: build or restyle; strict motion and layout enforcement; existing-project redesigns; a chosen soft-premium, minimalist, or brutalist direction; truncation or placeholder shortcuts). One Skill Priority line routes frontend work to `designing-frontend-interfaces` first, then to the preset skill for the chosen direction.

README integration: 7 new rows in the Included Skills table, the missing `writing-actionable-text` row, a corrected skill count (23), corrected entrypoint wording, and the attribution note as the last section.

Alternatives considered and rejected:

- Keep upstream directory and frontmatter names: rejected; the operator selected the package naming convention.
- Rewrite bodies to the writing-unambiguous-text standard: rejected; the operator selected verbatim carry.
- Carry the image-dependent skills as dormant, unrouted files: rejected; an unrouted chained skill is dead weight, and their content is non-operational without an image-generation tool.
- Carry image-dependent skills now and adapt them to the future pipeline: rejected; their content assumes an image-generation interface that does not exist yet, so adaptation now designs against an imagined interface.
- Demote `writing-actionable-text` to a chained skill: rejected; demotion rewrites an existing skill's frontmatter and changes session behavior, which this change excludes, and the documented entrypoint set must name the tree's five model-invocable skills.

## Impact

- `skills/`: 7 new directories, each with one `SKILL.md`. No existing skill directory changes except `skills/using-superpowers/SKILL.md`.
- `skills/using-superpowers/SKILL.md`: 7 new Skill Map rows, 1 new entrypoint row for `writing-actionable-text`, 1 Skill Priority line, and entrypoint wording that names five entrypoint skills. The document's self-description grows by roughly 9 table rows and one sentence; its routing behavior for existing skills is unchanged.
- `README.md`: 8 new table rows, corrected count and entrypoint wording, attribution note.
- Installed tree at `~/.tau/skills/` after the next install: 7 new directories. The model-invocable skill index of a session is unchanged by this change.
- No extension change. No `task` tool change. No API or data change. No consumer outside this repository reads the new files.

## Risks

- Verbatim bodies violate the package writing standard in places (upstream voice, phrasing that does not follow the ASD-STE100 Simplified Technical English rules of writing-unambiguous-text). Treatment: operator-accepted exception, recorded in Constraints. A later pass can rewrite bodies if the operator requests it.
- Upstream `taste-skill` is version 2 (experimental) and upstream iterates it. Treatment: the attribution note records the source repository; a later change can re-sync a fixed upstream commit.
- Skill Map growth lengthens `using-superpowers`. Treatment: 8 rows and one priority line; the model-invocable index stays unchanged, so session cost does not grow.

Rollback: revert the change commit. No migration, no recovery procedure.

## Assumptions

- Upstream commit `e988add` of `naripok/taste-skill` is the carry source.
- The operator waives per-skill behavioral testing of the carried bodies this round; testing covers routing and reachability only.
- The future media-pipeline integration project owns the image-dependent skills and any new generation skills.

## Unresolved Decisions

None.
