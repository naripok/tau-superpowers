# skill-catalog

## Purpose

This domain defines which skills the package ships, the metadata each skill carries, how skills route work, how the installer carries skills, and how the package documents its own catalog. The shipped markdown content is the observable behavior of the package.

Terms used by every requirement:

- **Skill**: one directory under `skills/` that contains a `SKILL.md` file.
- **Frontmatter**: the YAML block at the top of a `SKILL.md`, before the closing `---` delimiter. Relevant fields: `name`, `description`, `disable-model-invocation`.
- **Body**: the content of a `SKILL.md` below the frontmatter.
- **Model-invocable skill**: a skill whose frontmatter sets no `disable-model-invocation` field. Tau lists it in every skill index, including subagent prompts.
- **Chained skill**: a skill whose frontmatter sets `disable-model-invocation: true`. Tau keeps it out of every skill index. A workflow step that requires it loads it on demand: read its `SKILL.md` by sibling path, then follow it. It stays available through explicit `/skill:<name>` invocation.
- **Entrypoint skill**: one of the package's model-invocable skills. Entrypoint skills route work into the package.
- **Skill Map**: the table in the `using-superpowers` skill that lists every skill in the package with its tier and its "Load it when" condition.
- **Reachable**: a chained skill is reachable when at least one visible skill, dispatch template, or sibling skill references it so a workflow step can resolve it. A chained skill without a reachable reference is dead.
- **Installed tree**: the content the installer produces under `~/.tau/skills/<skill-name>` for every skill directory, plus the extension under `~/.tau/extensions/superpowers-subagent`.
- **Upstream**: the `taste-skill` collection at commit `e988add` of `naripok/taste-skill`, a mirror of `Leonxlnx/taste-skill`, licensed MIT.
- **Carried**: copied from upstream. A **verbatim** body is byte-identical to the upstream body below the frontmatter.

## Requirements

#### Requirement: Seven carried chained skills

The package SHALL ship seven new chained skills as seven new directories under `skills/`, one directory per skill and one `SKILL.md` per directory, with this mapping:

| Upstream directory | Upstream name | New directory and name |
| --- | --- | --- |
| `taste-skill` | `design-taste-frontend` | `designing-frontend-interfaces` |
| `gpt-tasteskill` | `gpt-taste` | `enforcing-strict-design-direction` |
| `redesign-skill` | `redesign-existing-projects` | `redesigning-existing-interfaces` |
| `soft-skill` | `high-end-visual-design` | `designing-premium-soft-interfaces` |
| `minimalist-skill` | `minimalist-ui` | `designing-minimalist-interfaces` |
| `brutalist-skill` | `industrial-brutalist-ui` | `designing-brutalist-interfaces` |
| `output-skill` | `full-output-enforcement` | `enforcing-complete-output` |

The body of each new `SKILL.md` SHALL be byte-identical to the body of the corresponding upstream `SKILL.md` at upstream commit `e988add`. The bodies SHALL NOT be rewritten to the writing-unambiguous-text standard; this verbatim carry is the operator-accepted exception to the package writing standard. The package SHALL carry no upstream artifact other than the seven `SKILL.md` files.

##### Scenario: Skill directory inventory

- GIVEN the repository after the change
- WHEN an auditor lists the directories under `skills/` that contain a `SKILL.md`
- THEN the list SHALL contain exactly 23 directories
- AND the list SHALL include the seven new names from the mapping table
- AND each of the seven new directories SHALL contain exactly one file, `SKILL.md`

##### Scenario: Verbatim body carry

- GIVEN the repository after the change and the upstream checkout at commit `e988add`
- WHEN an auditor compares, for each of the seven skills, the bytes of the new `SKILL.md` body with the bytes of the corresponding upstream `SKILL.md` body
- THEN every comparison SHALL show identical bytes

#### Requirement: Carried skill frontmatter

Each new `SKILL.md` SHALL carry frontmatter with exactly three fields: `name`, `description`, and `disable-model-invocation`. The `name` SHALL be identical to the skill's directory name. The `disable-model-invocation` field SHALL be `true`. The `description` SHALL be the exact pinned text for that skill in this table:

| Skill | Pinned description |
| --- | --- |
| `designing-frontend-interfaces` | `Use when building a landing page, portfolio, or other frontend interface from a brief, when a frontend design or redesign must not look templated, when inferring the right design direction for the work, when a real design system applies, or when a redesign needs an audit-first approach and a strict pre-flight check.` |
| `enforcing-strict-design-direction` | `Use when a frontend needs true randomization for layout variance, strict AIDA page structure, wide editorial typography that bans long line wraps, gapless bento grids, GSAP ScrollTrigger motion such as pinning, stacking, or scrubbing, inline micro-images, or massive section spacing.` |
| `redesigning-existing-interfaces` | `Use when upgrading an existing website or app to premium quality, when auditing a current design for generic AI patterns, or when applying high-end design standards to an existing project without breaking functionality, with any CSS framework or vanilla CSS.` |
| `designing-premium-soft-interfaces` | `Use when a website must feel expensive or high-end, when a design needs agency-level fonts, spacing, shadows, card structures, or animations, or when a design looks cheap or generic because of common default choices.` |
| `designing-minimalist-interfaces` | `Use when a design calls for clean editorial-style interfaces, a warm monochrome palette, typographic contrast, flat bento grids, or muted pastels, with no gradients and no heavy shadows.` |
| `designing-brutalist-interfaces` | `Use when a data-heavy dashboard, portfolio, or editorial site needs to feel like a declassified blueprint, with raw mechanical interfaces, Swiss typographic print fused with military terminal aesthetics, rigid grids, extreme type scale contrast, utilitarian color, or analog degradation effects.` |
| `enforcing-complete-output` | `Use when a task requires complete, exhaustive, unabridged output, when generated code would be truncated at a token limit, when placeholder patterns would stand in for real content, or when a token-limit split needs clean handling.` |

Each pinned description SHALL start with "Use when...", SHALL stay in third person, SHALL list triggers only, SHALL NOT summarize the workflow of the skill, and SHALL stay under 500 characters.

##### Scenario: Frontmatter audit

- GIVEN the seven new `SKILL.md` files after the change
- WHEN an auditor reads the frontmatter of each file
- THEN each file SHALL set `name` identical to its directory name, `description` identical to its pinned description in the table above, and `disable-model-invocation: true`
- AND no file SHALL set any other frontmatter field
- AND each description SHALL start with "Use when...", SHALL stay under 500 characters, and SHALL state triggering conditions only

#### Requirement: New skill naming convention

Each new skill name SHALL follow the package naming convention: lowercase letters and single hyphens, in verb-first gerund form. Each new name SHALL be unique in the package's flat skill namespace.

##### Scenario: Name audit

- GIVEN the seven new skill names after the change
- WHEN an auditor checks each name against the naming convention
- THEN every name SHALL use only lowercase letters and single hyphens
- AND every name SHALL start with a verb-first gerund (`designing`, `enforcing`, or `redesigning`)
- AND no name SHALL duplicate an existing or another new skill name

#### Requirement: Model-invocable set stays five skills

The change SHALL add no model-invocable skill. The change SHALL change no existing skill's frontmatter, including the frontmatter of `writing-actionable-text`. After the change, the model-invocable skills of the package SHALL be exactly the five entrypoint skills: `using-superpowers`, `systematic-debugging`, `writing-unambiguous-text`, `writing-skills`, and `writing-actionable-text`.

##### Scenario: Skill index contents

- GIVEN the package after the change, installed for a user
- WHEN a session starts and Tau builds the skill index
- THEN the index SHALL list exactly `using-superpowers`, `systematic-debugging`, `writing-unambiguous-text`, `writing-skills`, and `writing-actionable-text`
- AND the index SHALL list none of the seven new skill names

##### Scenario: Existing frontmatter unchanged

- GIVEN the change diff against the baseline
- WHEN an auditor compares the frontmatter of the 16 pre-existing skills with the baseline frontmatter
- THEN no frontmatter line SHALL differ

#### Requirement: Chained skills load on demand only

The seven new skills SHALL never be model-invocable. A new chained skill SHALL enter a session automatically only when a workflow step reads its `SKILL.md` by sibling path and follows it, or when a user invokes it explicitly with `/skill:<name>`; no skill index SHALL carry it, and no body content SHALL appear in the session prompt until one of these entry paths loads it. The carried bodies total approximately 137 KB; the largest body, `designing-frontend-interfaces`, is approximately 87 KB.

##### Scenario: On-demand load by sibling path

- GIVEN the package after the change, installed for a user
- WHEN a workflow step inside any installed skill reads `../designing-frontend-interfaces/SKILL.md` by sibling path
- THEN the file SHALL resolve and its content SHALL be the carried body

##### Scenario: No automatic load

- GIVEN a session that starts after installation and reads no new skill
- WHEN the session's skill index is built
- THEN the index SHALL contain none of the seven new names
- AND the session prompt SHALL contain none of the seven new names as skills
- AND the session prompt SHALL contain none of the carried body content

#### Requirement: Excluded upstream artifacts stay out

The package SHALL NOT ship the four image-dependent upstream skills `image-to-code-skill`, `imagegen-frontend-web`, `imagegen-frontend-mobile`, and `brandkit`; they require an image-generation tool this package does not have, and the future media-pipeline integration project owns their adaptation. The package SHALL NOT ship the upstream `stitch-skill` (`stitch-design-taste`); the operator excluded it by decision, so no Stitch-related skill ships and it receives no requirement. The package SHALL NOT ship `taste-skill-v1` or any non-skill upstream artifact: installers, assets, examples, research, plugin manifests, the changelog, the upstream README, `llms.txt`, and `stitch-skill/DESIGN.md`.

##### Scenario: Inventory of excluded names

- GIVEN the repository and the installed tree after the change
- WHEN an auditor searches both trees for the excluded upstream directory names and artifact names listed above
- THEN no search SHALL find a shipped skill, directory, or file carried from any excluded artifact

#### Requirement: Installer carries every skill directory

The installer SHALL manage every directory under `skills/` that contains a `SKILL.md`, copied into `~/.tau/skills/<skill-name>`, plus the extension copied into `~/.tau/extensions/superpowers-subagent`. The change SHALL alter no installer mechanism and no extension behavior. After the change, the installed tree SHALL include the seven new skill directories.

##### Scenario: Install carries the new skills

- GIVEN the repository after the change
- WHEN the installer runs and `tests/test-install.sh` runs
- THEN `tests/test-install.sh` SHALL pass
- AND the installed tree SHALL contain the seven new skill directories under `~/.tau/skills/`

#### Requirement: Self-contained references in new skills

Every reference in every new skill SHALL resolve inside the installed tree: a file in the skill's own directory, a sibling installed skill directory, or the installed extension directory. No new skill SHALL contain a checkout-only reference, which is a reference whose target exists in the checkout but has no counterpart in the produced install tree. The carried bodies reference no upstream-local script, asset, example, or research file. The shipped reference scanner does not flag references to files that exist nowhere; the self-contained-reference rule of the `writing-skills` skill governs that case.

##### Scenario: Staged reference scan

- GIVEN the new and edited files staged for commit
- WHEN `bash tests/check-references.sh` runs against the staged tree
- THEN it SHALL exit 0
- AND the pre-commit hook that runs the scan SHALL pass

##### Scenario: Sibling path resolves from any installed skill

- GIVEN the package after the change, installed for a user
- WHEN a workflow step reads `../designing-frontend-interfaces/SKILL.md` by sibling path from any installed skill
- THEN the file SHALL resolve

#### Requirement: Verification suite stays green

With the change applied, every test script under `tests/` SHALL pass, and the reference scan SHALL exit 0 both on the shipped tree and on the staged tree. The baseline at commit `b833ebd` passes the same suite: five test scripts pass and the reference scan is clean.

##### Scenario: Full suite run

- GIVEN the repository after the change
- WHEN an operator runs every test script under `tests/` and `bash tests/check-references.sh`
- THEN every test script SHALL pass
- AND the reference scan SHALL exit 0

#### Requirement: Two skill tiers

The package SHALL keep two tiers of skills. Entrypoint skills are model-invocable, and Tau lists them in every skill index, including subagent prompts. Chained skills set `disable-model-invocation: true`, and Tau keeps them out of every skill index; a workflow step that requires a chained skill loads it on demand by sibling path. After the change the package SHALL have 5 entrypoint skills and 18 chained skills, 23 skills total.

##### Scenario: Tier membership audit

- GIVEN the 23 skill directories after the change
- WHEN an auditor classifies each skill by its frontmatter
- THEN exactly 5 skills SHALL carry no `disable-model-invocation` field, and they SHALL be the five entrypoint skills
- AND the remaining 18 skills SHALL each set `disable-model-invocation: true`

#### Requirement: Skill Map lists every skill

The Skill Map in the `using-superpowers` skill SHALL carry exactly one row per skill in the package. After the change, the Skill Map SHALL have 23 rows: the 15 baseline rows unchanged, 7 new chained-skill rows (see Carried skill load conditions), and 1 new entrypoint row for `writing-actionable-text`. This resolves the baseline discrepancy in which the Skill Map listed 15 of the package's skills. The Skill Map SHALL remain the reachable reference that keeps every chained skill alive.

##### Scenario: Row inventory

- GIVEN the `using-superpowers` skill after the change
- WHEN an auditor counts the Skill Map rows and compares them with the skill directories under `skills/`
- THEN the Skill Map SHALL have one row per skill directory, 23 rows
- AND the Skill Map SHALL contain an entrypoint-tier row for `writing-actionable-text`

##### Scenario: Baseline rows unchanged

- GIVEN the Skill Map after the change and the 15-row baseline Skill Map
- WHEN an auditor compares the baseline rows with the post-change rows
- THEN every baseline row SHALL keep its skill name, tier, and "Load it when" condition

#### Requirement: Carried skill load conditions

Each of the 7 new chained-skill rows SHALL use the Skill Map columns, SHALL set the tier to `chained`, and SHALL state this "Load it when" condition:

| Skill | Load it when |
| --- | --- |
| `designing-frontend-interfaces` | frontend work: build or restyle |
| `enforcing-strict-design-direction` | strict motion and layout enforcement |
| `redesigning-existing-interfaces` | existing-project redesigns |
| `designing-premium-soft-interfaces` | a chosen soft-premium direction |
| `designing-minimalist-interfaces` | a chosen minimalist direction |
| `designing-brutalist-interfaces` | a chosen brutalist direction |
| `enforcing-complete-output` | truncation or placeholder shortcuts |

##### Scenario: Condition routes to the right skill

- GIVEN the Skill Map after the change
- WHEN a workflow step meets one of the conditions above and loads the chained skill for that step
- THEN the step SHALL load the skill named in that condition's row
- AND each of the seven skills SHALL be reachable through its Skill Map row

#### Requirement: Skill Priority routes frontend work

The Skill Priority section of the `using-superpowers` skill SHALL add one line that routes frontend work to `designing-frontend-interfaces` first, and then to the preset skill for the chosen direction: `designing-premium-soft-interfaces`, `designing-minimalist-interfaces`, or `designing-brutalist-interfaces`. The existing priority rules SHALL stay unchanged: process skills (`brainstorming`, `systematic-debugging`) come first, and implementation skills come second.

##### Scenario: Frontend work routes through the priority line

- GIVEN the Skill Priority section after the change
- WHEN a task builds or restyles a frontend and the operator chose a direction
- THEN the routing SHALL name `designing-frontend-interfaces` first
- AND the routing SHALL then name the preset skill for the chosen direction: `designing-premium-soft-interfaces`, `designing-minimalist-interfaces`, or `designing-brutalist-interfaces`

##### Scenario: Non-frontend priority unchanged

- GIVEN the Skill Priority section after the change
- WHEN a task is "Fix this bug"
- THEN the routing SHALL send the task to `systematic-debugging` first, then to domain-specific skills

#### Requirement: Entrypoint wording names five skills

The entrypoint wording in the `using-superpowers` skill SHALL name the five entrypoint skills: this skill, `systematic-debugging`, `writing-unambiguous-text`, `writing-skills`, and `writing-actionable-text`. The wording SHALL NOT describe a four-entrypoint package. This resolves the stale baseline prose that named four entrypoint skills.

##### Scenario: Entrypoint wording audit

- GIVEN the `using-superpowers` skill after the change
- WHEN an auditor reads the entrypoint wording and compares it with the skills that carry no `disable-model-invocation` frontmatter in the tree
- THEN the wording SHALL name exactly the same five skills
- AND no other name SHALL appear in that wording as an entrypoint

#### Requirement: README states the correct skill catalog

The README SHALL state a skill count of 23, and that number SHALL equal the number of skill directories the package ships. The Included Skills table SHALL list every shipped skill: the 15 baseline rows, 7 new rows for the carried skills, and 1 new row for `writing-actionable-text`, which the baseline table omitted. Each new row SHALL name the skill and state a one-line purpose for it. This resolves the baseline discrepancy in which the README stated 15 skills.

##### Scenario: Count audit

- GIVEN the README after the change and the skill directories under `skills/`
- WHEN an auditor compares the stated skill count with the directory count
- THEN the README SHALL state 23 Tau-discoverable Agent Skills
- AND that number SHALL equal the number of skill directories

##### Scenario: Table completeness

- GIVEN the Included Skills table after the change
- WHEN an auditor compares the table rows with the skill directories
- THEN the table SHALL have one row per shipped skill, 23 rows
- AND the table SHALL contain the rows for the seven carried skills and for `writing-actionable-text`
- AND each new row SHALL state a one-line purpose

#### Requirement: README entrypoint wording matches the tree

The two-tier paragraph in the README SHALL name the same five skills that carry no `disable-model-invocation` frontmatter in the tree. This resolves the stale baseline wording that named four entrypoint skills.

##### Scenario: README wording audit

- GIVEN the README after the change
- WHEN an auditor reads the entrypoint wording and compares it with the model-invocable skills in the tree
- THEN the wording SHALL name exactly `using-superpowers`, `systematic-debugging`, `writing-unambiguous-text`, `writing-skills`, and `writing-actionable-text`

#### Requirement: README attribution note

The README SHALL end with a short attribution note as its last section. The note SHALL name the upstream repository `naripok/taste-skill`, a mirror of `Leonxlnx/taste-skill`, and its MIT license. The note SHALL state the adaptation: the skills ship under new names with adapted frontmatter and verbatim upstream bodies.

##### Scenario: Attribution note audit

- GIVEN the README after the change
- WHEN an auditor reads the last section of the README
- THEN the last section SHALL be the attribution note
- AND the note SHALL name the upstream repository and its MIT license
- AND the note SHALL state the adaptation of the carried skills
