# Taste Design Skills Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Execute this plan task-by-task with the skill the workflow depth selects: executing-plans for Bounded, subagent-driven-development for Standard or High-risk. The controller marks every checkbox of a task `[x]` in the plan file when the task completes its gate, and records each flip in one tracking commit named `docs(plan): mark <plan-file-stem> Task N complete`.

**Goal:** Ship the seven carried taste design skills as routed chained skills and sync the package documents to a five-entrypoint, 23-skill catalog.

**Architecture:** Markdown-only carry from the upstream clone at `/tmp/taste-skill` (commit `e988add`): each new skill is one directory with one `SKILL.md`; the frontmatter is adapted (new name, pinned "Use when..." description, `disable-model-invocation: true`) and the body below the frontmatter is byte-identical to upstream. `using-superpowers` routes the new skills through 8 new Skill Map rows and 1 Skill Priority line, and its entrypoint wording names five entrypoint skills. The README gains 8 Included Skills rows, the corrected count 23, matching entrypoint wording, and a trailing MIT attribution note. The installer and the test scripts change nothing.

**Tech Stack:** Markdown, Bash (existing test scripts), Git.

**Standards:** Apply the shared code standards in every task: DRY, minimal implementation (YAGNI), low cyclomatic complexity, type safety, no unnecessary abstractions or fallbacks, no hacks or workarounds, informative docstrings, documentation of current state only, writing-unambiguous-text prose.

**Feature spec:** `docs/design/2026-09-22-taste-design-skills-spec.md` (the behavioral contract)

**Approved proposal:** `docs/design/2026-09-22-taste-design-skills-proposal.md` (intent, scope, binding architecture, constraints, non-goals, acceptance, and risk treatment; the exact operator-approved version, content digest `bd8a38954ca3b0c9a94ed2a2b56bf787e444dc28`)

**Execution route:** Standard depth. The controller executes this plan with subagent-driven-development (`../subagent-driven-development/SKILL.md`), one task per implementation dispatch, one final whole-change review.

**Testing depth (operator waiver):** the carried bodies get no per-skill behavioral testing. Testing covers routing and reachability only: the existing suite in `tests/` plus the named check commands in each task. The plan creates no new test files (proposal Out of scope: test-infrastructure changes beyond what the outcomes require).

**Rollback (proposal risk treatment):** revert the change commit. No migration, no recovery procedure.

---

## Commands

Run every command from the worktree root. The upstream clone must exist at `/tmp/taste-skill` and `git -C /tmp/taste-skill rev-parse --short HEAD` must print `e988add`.

```bash
# Reference scan over the worktree content of skills/ and the extension.
# Exit 0 = no checkout-only reference.
bash tests/check-references.sh

# Reference-scan behavior regression.
bash tests/test-references.sh

# Full installer regression: copy semantics, the install stamp, --check,
# plus check-references.sh in full-scan mode and the three guidance suites.
bash tests/test-install.sh

# Guidance suites (also run inside test-install.sh).
bash tests/test-proposal-baseline-guidance.sh
bash tests/test-plan-execution-guidance.sh
bash tests/test-finishing-workflow-guidance.sh
```

No environment setup beyond the repository itself. The test scripts run the installer against a sandboxed temporary HOME and need `git`, `bash`, and `rsync`.

Body and frontmatter extraction used by the task checks: the body of a `SKILL.md` is the raw content below the closing frontmatter delimiter, printed by `tail -n +5 <upstream-file>` for an upstream file (frontmatter is exactly opening `---`, `name`, `description`, closing `---` on line 4) and by `tail -n +6 <new-file>` for a new skill file (pinned 5-line frontmatter, closing `---` on line 5). The tail keeps every body byte, including `---` horizontal-rule lines. Never use an awk rule that skips every `^---$` line: it deletes body horizontal rules and hides body mutations.

---

### Task 1: Carry the seven upstream skills

**Files:**
- Create: `skills/designing-frontend-interfaces/SKILL.md` — anti-slop frontend design guidance (carried body)
- Create: `skills/enforcing-strict-design-direction/SKILL.md` — strict layout, typography, and GSAP motion enforcement (carried body)
- Create: `skills/redesigning-existing-interfaces/SKILL.md` — premium redesign of existing projects (carried body)
- Create: `skills/designing-premium-soft-interfaces/SKILL.md` — high-end agency design language (carried body)
- Create: `skills/designing-minimalist-interfaces/SKILL.md` — minimalist editorial UI direction (carried body)
- Create: `skills/designing-brutalist-interfaces/SKILL.md` — brutalist industrial UI direction (carried body)
- Create: `skills/enforcing-complete-output/SKILL.md` — complete-output enforcement, no truncation or placeholders (carried body)
- Test: none. The existing suite plus the named check commands prove the behavior; new test files are out of scope.

**Spec or proposal source:** spec requirements "Seven carried chained skills", "Carried skill frontmatter", and "New skill naming convention"; the frontmatter and on-demand clauses of "Chained skills load on demand only"; the carry-nothing-else clause of "Excluded upstream artifacts stay out".

**Proposal constraints:**
- Bodies stay verbatim: the body below the frontmatter is byte-identical to the upstream body. No body text is edited, reordered, or rewritten to the writing-unambiguous-text standard (operator-accepted exception).
- The frontmatter is the only adapted part. It holds exactly three fields: `name`, `description`, `disable-model-invocation`. No other field.
- `name` is identical to the directory name. Names use lowercase letters and single hyphens, in verb-first gerund form.
- Each description starts with "Use when...", stays in third person, lists triggers only, and stays under 500 characters. The exact description per skill is the pinned text below.
- Carry nothing from upstream except the seven `SKILL.md` files: no other file, no other upstream directory, no asset, script, example, or research file.
- Upstream source pin: commit `e988add` of `/tmp/taste-skill` (mirror of `Leonxlnx/taste-skill`, MIT).

**Interface:** each created file is a 5-line frontmatter block (pinned below) followed by the verbatim upstream body. The upstream body for a skill is the raw output of `tail -n +5 /tmp/taste-skill/skills/<upstream-dir>/SKILL.md` for its mapped upstream directory; build each file by writing the pinned 5-line block, then appending those raw upstream bytes unchanged (for example with `tail -n +5 <upstream-file> >> <new-file>`). Never pass the body through an extraction that skips `---` lines.

Upstream-to-new mapping:

| Upstream directory (body source) | New directory |
| --- | --- |
| `/tmp/taste-skill/skills/taste-skill` | `skills/designing-frontend-interfaces` |
| `/tmp/taste-skill/skills/gpt-tasteskill` | `skills/enforcing-strict-design-direction` |
| `/tmp/taste-skill/skills/redesign-skill` | `skills/redesigning-existing-interfaces` |
| `/tmp/taste-skill/skills/soft-skill` | `skills/designing-premium-soft-interfaces` |
| `/tmp/taste-skill/skills/minimalist-skill` | `skills/designing-minimalist-interfaces` |
| `/tmp/taste-skill/skills/brutalist-skill` | `skills/designing-brutalist-interfaces` |
| `/tmp/taste-skill/skills/output-skill` | `skills/enforcing-complete-output` |

Pinned frontmatter blocks, one per created file. The block is exactly 5 lines: the opening `---`, the three fields in this order, the closing `---`.

`skills/designing-frontend-interfaces/SKILL.md`:

```yaml
---
name: designing-frontend-interfaces
description: Use when building a landing page, portfolio, or other frontend interface from a brief, when a frontend design or redesign must not look templated, when inferring the right design direction for the work, when a real design system applies, or when a redesign needs an audit-first approach and a strict pre-flight check.
disable-model-invocation: true
---
```

`skills/enforcing-strict-design-direction/SKILL.md`:

```yaml
---
name: enforcing-strict-design-direction
description: Use when a frontend needs true randomization for layout variance, strict AIDA page structure, wide editorial typography that bans long line wraps, gapless bento grids, GSAP ScrollTrigger motion such as pinning, stacking, or scrubbing, inline micro-images, or massive section spacing.
disable-model-invocation: true
---
```

`skills/redesigning-existing-interfaces/SKILL.md`:

```yaml
---
name: redesigning-existing-interfaces
description: Use when upgrading an existing website or app to premium quality, when auditing a current design for generic AI patterns, or when applying high-end design standards to an existing project without breaking functionality, with any CSS framework or vanilla CSS.
disable-model-invocation: true
---
```

`skills/designing-premium-soft-interfaces/SKILL.md`:

```yaml
---
name: designing-premium-soft-interfaces
description: Use when a website must feel expensive or high-end, when a design needs agency-level fonts, spacing, shadows, card structures, or animations, or when a design looks cheap or generic because of common default choices.
disable-model-invocation: true
---
```

`skills/designing-minimalist-interfaces/SKILL.md`:

```yaml
---
name: designing-minimalist-interfaces
description: Use when a design calls for clean editorial-style interfaces, a warm monochrome palette, typographic contrast, flat bento grids, or muted pastels, with no gradients and no heavy shadows.
disable-model-invocation: true
---
```

`skills/designing-brutalist-interfaces/SKILL.md`:

```yaml
---
name: designing-brutalist-interfaces
description: Use when a data-heavy dashboard, portfolio, or editorial site needs to feel like a declassified blueprint, with raw mechanical interfaces, Swiss typographic print fused with military terminal aesthetics, rigid grids, extreme type scale contrast, utilitarian color, or analog degradation effects.
disable-model-invocation: true
---
```

`skills/enforcing-complete-output/SKILL.md`:

```yaml
---
name: enforcing-complete-output
description: Use when a task requires complete, exhaustive, unabridged output, when generated code would be truncated at a token limit, when placeholder patterns would stand in for real content, or when a token-limit split needs clean handling.
disable-model-invocation: true
---
```

**Behavior:** after this task, `skills/` contains the seven new directories, each holding exactly one file, `SKILL.md`. Each frontmatter matches its pinned block. Each body is byte-identical to the mapped upstream body. Every reference inside the new bodies resolves inside the installed tree. The installer, unchanged, carries each new directory on the next install.

**Tests must prove:**
- Upstream pin: the clone sits at upstream commit `e988add`.
- Directory inventory: each new directory contains exactly one file, `SKILL.md`.
- Verbatim body carry: each new body is byte-identical to its upstream body; 7 `cmp` compares of the raw tails, all silent.
- Frontmatter exactness: each file starts with its pinned 5-line block; 7 diffs, all with empty output.
- Self-contained references: `bash tests/check-references.sh` exits 0, and the pre-commit hook (staged scan) passes on the commit.

**Check:**

```bash
git -C /tmp/taste-skill rev-parse --short HEAD
# expected output: e988add

for pair in \
  "taste-skill designing-frontend-interfaces" \
  "gpt-tasteskill enforcing-strict-design-direction" \
  "redesign-skill redesigning-existing-interfaces" \
  "soft-skill designing-premium-soft-interfaces" \
  "minimalist-skill designing-minimalist-interfaces" \
  "brutalist-skill designing-brutalist-interfaces" \
  "output-skill enforcing-complete-output"
do
  set -- $pair
  cmp <(tail -n +5 "/tmp/taste-skill/skills/$1/SKILL.md") \
      <(tail -n +6 "skills/$2/SKILL.md") \
    && echo "BODY OK: $2"
  test "$(ls "skills/$2")" = "SKILL.md" && echo "INVENTORY OK: $2"
done
# expected: BODY OK and INVENTORY OK for all 7 names, no diff output
```

```bash
diff <(printf -- '---\nname: designing-frontend-interfaces\ndescription: Use when building a landing page, portfolio, or other frontend interface from a brief, when a frontend design or redesign must not look templated, when inferring the right design direction for the work, when a real design system applies, or when a redesign needs an audit-first approach and a strict pre-flight check.\ndisable-model-invocation: true\n---\n') <(head -n 5 skills/designing-frontend-interfaces/SKILL.md) && echo "FRONTMATTER OK: designing-frontend-interfaces"
diff <(printf -- '---\nname: enforcing-strict-design-direction\ndescription: Use when a frontend needs true randomization for layout variance, strict AIDA page structure, wide editorial typography that bans long line wraps, gapless bento grids, GSAP ScrollTrigger motion such as pinning, stacking, or scrubbing, inline micro-images, or massive section spacing.\ndisable-model-invocation: true\n---\n') <(head -n 5 skills/enforcing-strict-design-direction/SKILL.md) && echo "FRONTMATTER OK: enforcing-strict-design-direction"
diff <(printf -- '---\nname: redesigning-existing-interfaces\ndescription: Use when upgrading an existing website or app to premium quality, when auditing a current design for generic AI patterns, or when applying high-end design standards to an existing project without breaking functionality, with any CSS framework or vanilla CSS.\ndisable-model-invocation: true\n---\n') <(head -n 5 skills/redesigning-existing-interfaces/SKILL.md) && echo "FRONTMATTER OK: redesigning-existing-interfaces"
diff <(printf -- '---\nname: designing-premium-soft-interfaces\ndescription: Use when a website must feel expensive or high-end, when a design needs agency-level fonts, spacing, shadows, card structures, or animations, or when a design looks cheap or generic because of common default choices.\ndisable-model-invocation: true\n---\n') <(head -n 5 skills/designing-premium-soft-interfaces/SKILL.md) && echo "FRONTMATTER OK: designing-premium-soft-interfaces"
diff <(printf -- '---\nname: designing-minimalist-interfaces\ndescription: Use when a design calls for clean editorial-style interfaces, a warm monochrome palette, typographic contrast, flat bento grids, or muted pastels, with no gradients and no heavy shadows.\ndisable-model-invocation: true\n---\n') <(head -n 5 skills/designing-minimalist-interfaces/SKILL.md) && echo "FRONTMATTER OK: designing-minimalist-interfaces"
diff <(printf -- '---\nname: designing-brutalist-interfaces\ndescription: Use when a data-heavy dashboard, portfolio, or editorial site needs to feel like a declassified blueprint, with raw mechanical interfaces, Swiss typographic print fused with military terminal aesthetics, rigid grids, extreme type scale contrast, utilitarian color, or analog degradation effects.\ndisable-model-invocation: true\n---\n') <(head -n 5 skills/designing-brutalist-interfaces/SKILL.md) && echo "FRONTMATTER OK: designing-brutalist-interfaces"
diff <(printf -- '---\nname: enforcing-complete-output\ndescription: Use when a task requires complete, exhaustive, unabridged output, when generated code would be truncated at a token limit, when placeholder patterns would stand in for real content, or when a token-limit split needs clean handling.\ndisable-model-invocation: true\n---\n') <(head -n 5 skills/enforcing-complete-output/SKILL.md) && echo "FRONTMATTER OK: enforcing-complete-output"

bash tests/check-references.sh
# expected: exit 0, no findings
```

- [x] Create the seven `SKILL.md` files: the pinned frontmatter block, then the verbatim upstream body
- [x] Run the check commands; every check passes
- [x] Commit: `git add skills/designing-frontend-interfaces skills/enforcing-strict-design-direction skills/redesigning-existing-interfaces skills/designing-premium-soft-interfaces skills/designing-minimalist-interfaces skills/designing-brutalist-interfaces skills/enforcing-complete-output && git commit -m "skills: carry 7 taste design skills from upstream"` (the pre-commit hook runs the staged reference scan)

### Task 2: Route the new skills in using-superpowers

**Files:**
- Modify: `skills/using-superpowers/SKILL.md` — 8 new Skill Map rows, 1 new Skill Priority line, entrypoint wording grows from four to five names
- Test: none. The existing suite plus the named check commands prove the behavior; new test files are out of scope.

**Spec or proposal source:** spec requirements "Skill Map lists every skill", "Carried skill load conditions", "Skill Priority routes frontend work", and "Entrypoint wording names five skills"; the frontmatter-unchanged clause of "Model-invocable set stays five skills"; the baseline-rows-unchanged scenario of "Skill Map lists every skill".

**Proposal constraints:**
- Exactly 8 new Skill Map rows (7 chained rows + 1 entrypoint row for `writing-actionable-text`) and 1 Skill Priority line. No other structural change.
- The file's own frontmatter stays unchanged (no existing skill's frontmatter changes).
- The pinned "Load it when" condition of each new chained row is the spec-pinned text; baseline rows keep their skill name, tier, and condition.
- The existing priority rules stay unchanged: process skills first, implementation skills second.

**Interface (before → after), three edits.** The file is `skills/using-superpowers/SKILL.md`.

Edit 1 — section "How Skills Work", the entrypoint bullet grows by one name:

Before:

```markdown
- **Entrypoint skills** are model-invocable. Tau lists them in every skill index, including subagent prompts. They route work into the package: this skill, systematic-debugging, writing-unambiguous-text, and writing-skills.
```

After:

```markdown
- **Entrypoint skills** are model-invocable. Tau lists them in every skill index, including subagent prompts. They route work into the package: this skill, systematic-debugging, writing-unambiguous-text, writing-skills, and writing-actionable-text.
```

Edit 2 — Skill Map table. Insert one entrypoint row directly after the `writing-skills` row:

```markdown
| writing-actionable-text | entrypoint | writing responses, instructions, docs, runbooks, or error messages |
```

Append 7 chained rows directly after the `finishing-a-development-branch` row (the last current row), in this order with exactly this text:

```markdown
| designing-frontend-interfaces | chained | frontend work: build or restyle |
| enforcing-strict-design-direction | chained | strict motion and layout enforcement |
| redesigning-existing-interfaces | chained | existing-project redesigns |
| designing-premium-soft-interfaces | chained | a chosen soft-premium direction |
| designing-minimalist-interfaces | chained | a chosen minimalist direction |
| designing-brutalist-interfaces | chained | a chosen brutalist direction |
| enforcing-complete-output | chained | truncation or placeholder shortcuts |
```

Edit 3 — section "Skill Priority". Insert one line directly after the `"Fix this bug" → systematic-debugging first, then domain-specific skills.` line:

```markdown
"Build or restyle a frontend" → designing-frontend-interfaces (`../designing-frontend-interfaces/SKILL.md`) first, then the direction skill for the chosen direction: designing-premium-soft-interfaces, designing-minimalist-interfaces, or designing-brutalist-interfaces.
```

**Behavior:** the Skill Map holds 23 rows, one per skill directory; every baseline row keeps its skill name, tier, and condition; the entrypoint prose names exactly the five model-invocable skills; the priority routing names `designing-frontend-interfaces` first, then the chosen direction skill; every chained skill stays reachable through its Skill Map row; the sibling reference `../designing-frontend-interfaces/SKILL.md` resolves in the checkout and in the installed tree.

**Tests must prove:**
- Skill Map data-row count is 23.
- Each of the 7 chained rows is present with the pinned tier and condition; the `writing-actionable-text` entrypoint row is present.
- The entrypoint bullet names the five skills.
- The Skill Priority section names `designing-frontend-interfaces` and the three direction skills.
- The diff against HEAD touches no frontmatter line and removes exactly one line: the old four-name entrypoint bullet.

**Check:**

```bash
sed -n '/^## Skill Map/,/^## Workflow Depth/p' skills/using-superpowers/SKILL.md \
  | awk '/^\| --- /{t=1; next} t && /^\|/{c++} END{print c+0}'
# expected output: 23

grep -F "| designing-frontend-interfaces | chained | frontend work: build or restyle |" skills/using-superpowers/SKILL.md && echo "ROW OK: designing-frontend-interfaces"
grep -F "| enforcing-strict-design-direction | chained | strict motion and layout enforcement |" skills/using-superpowers/SKILL.md && echo "ROW OK: enforcing-strict-design-direction"
grep -F "| redesigning-existing-interfaces | chained | existing-project redesigns |" skills/using-superpowers/SKILL.md && echo "ROW OK: redesigning-existing-interfaces"
grep -F "| designing-premium-soft-interfaces | chained | a chosen soft-premium direction |" skills/using-superpowers/SKILL.md && echo "ROW OK: designing-premium-soft-interfaces"
grep -F "| designing-minimalist-interfaces | chained | a chosen minimalist direction |" skills/using-superpowers/SKILL.md && echo "ROW OK: designing-minimalist-interfaces"
grep -F "| designing-brutalist-interfaces | chained | a chosen brutalist direction |" skills/using-superpowers/SKILL.md && echo "ROW OK: designing-brutalist-interfaces"
grep -F "| enforcing-complete-output | chained | truncation or placeholder shortcuts |" skills/using-superpowers/SKILL.md && echo "ROW OK: enforcing-complete-output"
# expected: ROW OK for all 7 names

grep -F "| writing-actionable-text | entrypoint | writing responses, instructions, docs, runbooks, or error messages |" skills/using-superpowers/SKILL.md && echo "ENTRYPOINT ROW OK"
grep -F "writing-unambiguous-text, writing-skills, and writing-actionable-text." skills/using-superpowers/SKILL.md && echo "ENTRYPOINT WORDING OK"
for n in designing-frontend-interfaces designing-premium-soft-interfaces designing-minimalist-interfaces designing-brutalist-interfaces; do
  awk '/^## Skill Priority/{f=1} f' skills/using-superpowers/SKILL.md | grep -F "$n" >/dev/null && echo "PRIORITY LINE OK: $n" || echo "PRIORITY MISSING: $n"
done
# expected: PRIORITY LINE OK for all 4 names

git diff HEAD -- skills/using-superpowers/SKILL.md | grep -E '^[-+](name|description):'
# expected: no output

git diff --numstat -- skills/using-superpowers/SKILL.md
# expected output: 10 and 1, TAB-separated (10 added lines: 8 Skill Map rows, 1 Skill Priority line, 1 rewritten entrypoint bullet; 1 deleted line: the old four-name entrypoint bullet)
```

- [x] Apply the three pinned edits to `skills/using-superpowers/SKILL.md`
- [x] Run the check commands; every check passes
- [x] Commit: `git add skills/using-superpowers/SKILL.md && git commit -m "skills: route taste design skills in the skill map and priority"`

### Task 3: Sync the README and pass the full suite

**Files:**
- Modify: `README.md` — skill count, 8 Included Skills rows, entrypoint wording, trailing attribution note
- Test: none. The existing suite plus the named check commands prove the behavior; new test files are out of scope.

**Spec or proposal source:** spec requirements "README states the correct skill catalog", "README entrypoint wording matches the tree", and "README attribution note".

**Proposal constraints:**
- 8 new table rows: 7 rows for the carried skills and 1 row for `writing-actionable-text`, which the baseline table omitted. Each new row states a one-line purpose.
- The stated skill count is 23 and equals the number of skill directories.
- The attribution note is the last section of the README. It names the upstream repository `naripok/taste-skill`, a mirror of `Leonxlnx/taste-skill`, and its MIT license. It states the adaptation: the skills ship under new names with adapted frontmatter and verbatim upstream bodies.
- No other README content changes.

**Interface (before → after), four edits.** The file is `README.md`.

Edit 1 — section "What You Get", the skill-count bullet:

Before:

```markdown
- 15 Tau-discoverable Agent Skills covering the full design-to-delivery workflow.
```

After:

```markdown
- 23 Tau-discoverable Agent Skills covering the full design-to-delivery workflow.
```

Edit 2 — Included Skills table. Insert the 7 carried-skill rows at their alphabetical positions, with exactly this text:

```markdown
| `designing-brutalist-interfaces` | Design raw mechanical brutalist interfaces with Swiss print, military terminal aesthetics, and rigid grids |
| `designing-frontend-interfaces` | Design frontend interfaces from a brief with an inferred direction and no templated look |
| `designing-minimalist-interfaces` | Design clean editorial minimalist interfaces with warm monochrome and flat bento grids |
| `designing-premium-soft-interfaces` | Design high-end premium interfaces with agency-level fonts, spacing, shadows, and motion |
| `enforcing-complete-output` | Enforce complete, unabridged output with no truncation and no placeholder patterns |
| `enforcing-strict-design-direction` | Enforce strict layout, typography, and GSAP motion direction for award-level frontend builds |
| `redesigning-existing-interfaces` | Redesign existing websites and apps to premium quality without breaking functionality |
```

Alphabetical positions: the four `designing-*` rows go directly after the `brainstorming` row; the two `enforcing-*` rows go directly after the `dispatching-parallel-agents` row; the `redesigning-existing-interfaces` row goes directly after the `receiving-code-review` row.

Insert the `writing-actionable-text` row directly before the `writing-plans` row:

```markdown
| `writing-actionable-text` | Write responses, instructions, docs, runbooks, and error messages that drive immediate action |
```

Edit 3 — the two-tier paragraph below the table:

Before:

```markdown
The package uses two tiers. Four entrypoint skills stay model-invocable and route work in: `using-superpowers` (workflow and depth gates), `systematic-debugging`, `writing-unambiguous-text`, and `writing-skills`. Every other skill sets `disable-model-invocation: true`, so no skill index carries it.
```

After:

```markdown
The package uses two tiers. Five entrypoint skills stay model-invocable and route work in: `using-superpowers` (workflow and depth gates), `systematic-debugging`, `writing-unambiguous-text`, `writing-skills`, and `writing-actionable-text`. Every other skill sets `disable-model-invocation: true`, so no skill index carries it.
```

Edit 4 — append the attribution note at the end of the file, so it is the last section:

```markdown

## Attribution

The frontend design and output-discipline skills derive from the [taste-skill](https://github.com/naripok/taste-skill) collection, a mirror of [Leonxlnx/taste-skill](https://github.com/Leonxlnx/taste-skill), licensed MIT. They ship in this package under new names with adapted frontmatter and verbatim upstream bodies.
```

**Behavior:** the README states 23 Tau-discoverable Agent Skills; the Included Skills table holds one row per shipped skill, 23 rows, including the 8 new rows; the two-tier paragraph names exactly the five model-invocable skills; the last section is the attribution note; the full test suite passes.

**Tests must prove:**
- The count bullet states 23, and the number equals the skill directory count.
- The Included Skills table holds 23 rows, including the 8 new rows.
- The two-tier paragraph names the five skills.
- The last section is `## Attribution`, and it names the upstream repository, the mirror, the MIT license, and the adaptation.
- All five test scripts in `tests/` pass, including the installer regression that proves the 7 new directories are carried.
- Whole-change path inventory: the diff from baseline commit `b833ebd` to HEAD touches exactly the planned paths and nothing else (no installer, extension, or test-infrastructure change; no excluded upstream artifact).

**Check:**

```bash
grep -F "23 Tau-discoverable Agent Skills" README.md && echo "COUNT OK"
test "$(ls -1 skills | wc -l)" = 23 && echo "DIRECTORY COUNT OK"

sed -n '/^## Included Skills/,/^## Requirements/p' README.md \
  | awk '/^\| --- /{t=1; next} t && /^\|/{c++} END{print c+0}'
# expected output: 23

grep -F '| `designing-brutalist-interfaces` | Design raw mechanical brutalist interfaces with Swiss print, military terminal aesthetics, and rigid grids |' README.md && echo "ROW OK: designing-brutalist-interfaces"
grep -F '| `designing-frontend-interfaces` | Design frontend interfaces from a brief with an inferred direction and no templated look |' README.md && echo "ROW OK: designing-frontend-interfaces"
grep -F '| `designing-minimalist-interfaces` | Design clean editorial minimalist interfaces with warm monochrome and flat bento grids |' README.md && echo "ROW OK: designing-minimalist-interfaces"
grep -F '| `designing-premium-soft-interfaces` | Design high-end premium interfaces with agency-level fonts, spacing, shadows, and motion |' README.md && echo "ROW OK: designing-premium-soft-interfaces"
grep -F '| `enforcing-complete-output` | Enforce complete, unabridged output with no truncation and no placeholder patterns |' README.md && echo "ROW OK: enforcing-complete-output"
grep -F '| `enforcing-strict-design-direction` | Enforce strict layout, typography, and GSAP motion direction for award-level frontend builds |' README.md && echo "ROW OK: enforcing-strict-design-direction"
grep -F '| `redesigning-existing-interfaces` | Redesign existing websites and apps to premium quality without breaking functionality |' README.md && echo "ROW OK: redesigning-existing-interfaces"
grep -F '| `writing-actionable-text` | Write responses, instructions, docs, runbooks, and error messages that drive immediate action |' README.md && echo "ROW OK: writing-actionable-text"
# expected: ROW OK for all 8 names

grep -F "Five entrypoint skills stay model-invocable" README.md && echo "WORDING OK"
test "$(awk '/^## /{s=$0} END{print s}' README.md)" = "## Attribution" && echo "ATTRIBUTION LAST OK"
for s in "naripok/taste-skill" "Leonxlnx/taste-skill" "MIT" "under new names with adapted frontmatter and verbatim upstream bodies"; do
  awk '/^## Attribution/{f=1} f' README.md | grep -F "$s" >/dev/null && echo "ATTRIBUTION OK: $s" || echo "ATTRIBUTION MISSING: $s"
done
# expected: ATTRIBUTION OK for all 4 strings

bash tests/test-install.sh
bash tests/test-references.sh
bash tests/test-proposal-baseline-guidance.sh
bash tests/test-plan-execution-guidance.sh
bash tests/test-finishing-workflow-guidance.sh
# expected: all five exit 0

git diff --name-only b833ebd..HEAD | sort
# expected output, exactly these 12 paths:
# README.md
# docs/design/2026-09-22-taste-design-skills-proposal.md
# docs/design/2026-09-22-taste-design-skills-spec.md
# docs/plans/2026-09-22-taste-design-skills.md
# skills/designing-brutalist-interfaces/SKILL.md
# skills/designing-frontend-interfaces/SKILL.md
# skills/designing-minimalist-interfaces/SKILL.md
# skills/designing-premium-soft-interfaces/SKILL.md
# skills/enforcing-complete-output/SKILL.md
# skills/enforcing-strict-design-direction/SKILL.md
# skills/redesigning-existing-interfaces/SKILL.md
# skills/using-superpowers/SKILL.md
```

- [x] Apply the four pinned edits to `README.md`
- [x] Run the check commands; every check passes
- [x] Commit: `git add README.md && git commit -m "docs: sync README to the 23-skill catalog with attribution"`
