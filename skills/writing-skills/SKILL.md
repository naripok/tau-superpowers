---
name: writing-skills
description: Use when creating or editing skills, or checking that skills work before deployment
---

# Writing Skills

## What a Skill Is

A skill is a reference guide for a proven technique, pattern, or tool. It is written as a procedure: what to do, when to do it, and how to do it. Skills state rules and steps. They do not argue for them, justify them, or persuade.

**Skills are:** reusable techniques, patterns, tools, reference guides.

**Skills are NOT:** narratives about how you solved a problem once.

## Skill Discovery

Tau discovers skills from these directories in increasing precedence:

1. `~/.tau/skills/`
2. `~/.agents/skills/`
3. `<cwd>/.tau/skills/`
4. `<cwd>/.agents/skills/`

Each skill is a directory containing `SKILL.md`. A higher-precedence skill with the same name overrides a lower-precedence one. Tau initially injects only each skill's name, description, and path into the system prompt. When the description matches its task, the agent reads the full `SKILL.md`. If you change a skill in an active TUI, run `/reload`. Users invoke a skill explicitly with `/skill:<name> [request]`.

## When to Create a Skill

**Create when:**
- The technique was not intuitively obvious
- You will reference it again across projects
- The pattern applies broadly (not project-specific)

**Do not create for:**
- One-off solutions
- Standard practices documented elsewhere
- Project-specific conventions (put those in AGENTS.md)
- Mechanically enforceable constraints (automate with regex/validation instead)

## Skill Types

- **Technique** — concrete method with steps (condition-based-waiting, root-cause-tracing)
- **Pattern** — way of thinking about problems
- **Reference** — API docs, syntax guides, tool documentation

## Directory Structure

```
<skills-dir>/
  skill-name/
    SKILL.md              # Main reference (required)
    supporting-file.*     # Only for heavy reference or reusable tools
```

Keep the directory name and frontmatter `name` identical. All skills share one flat namespace.

**Separate files for:** heavy reference (100+ lines), reusable tools/scripts/templates.

**Keep inline:** principles, procedures, code patterns (< 50 lines), everything else.

## SKILL.md Structure

**Frontmatter (YAML)** — two required fields (see [agentskills.io/specification](https://agentskills.io/specification) for all supported fields):

- `name`: 1-64 characters. Use only lowercase letters, numbers, and single hyphens. No leading or trailing hyphen. The name must match the parent directory.
- `description`: 1-1024 characters (keep under 500). Third person. Starts with "Use when...". Lists triggering conditions, symptoms, and contexts. **NEVER summarize the skill's process or workflow in the description**. An agent can follow the summary instead of reading the skill body

**Body:**

```markdown
# Skill Name

## Overview
What this is; the core rule in 1-2 sentences.

## When to Use
[Small pseudocode decision block only if the decision is non-obvious]
Symptoms and use cases. When NOT to use.

## The Procedure
Numbered steps or a pseudocode decision block. Decision rules for edge cases.

## Quick Reference
Table or bullets for scanning common operations.

## Common Mistakes
What goes wrong + the correct action.
```

## Description Rules

The description answers only one question: "Does this skill apply now?"

- Start with "Use when..." and list concrete triggers, symptoms, situations
- Describe the problem (race conditions, flaky tests), not language-specific symptoms. If the skill is technology-specific, say so explicitly.
- Third person
- Never summarize the process or workflow

```yaml
# BAD: workflow summary the agent can follow instead of reading the skill
description: Use when executing plans - dispatches subagent per task with review between tasks

# GOOD: triggering conditions only
description: Use when executing implementation plans with independent tasks in the current session
```

Use searchable keywords in the body: error messages, symptom words, synonyms, tool and file names.

## Naming

Use active voice and verb-first names. Gerunds work well for processes:

- `condition-based-waiting`, not `async-test-helpers`
- `writing-skills`, not `skill-creation`

## Token Efficiency

- Keep descriptions concise. Tau always indexes their metadata.
- Keep frequently-used skill bodies focused. Move heavy reference and tools to supporting files.
- Cross-reference other skills by name instead of repeating their content
- One excellent example beats several mediocre ones
- Do not explain what a command already makes obvious. Do not give multiple examples of the same pattern.

## Cross-Referencing Other Skills

Reference by skill name with an explicit requirement marker:

- GOOD: `**REQUIRED SUB-SKILL:** Use test-driven-development`
- GOOD: `**REQUIRED BACKGROUND:** You MUST understand systematic-debugging`
- BAD: `See skills/testing/test-driven-development` (assumes an installation layout)
- BAD: `Open @skills/testing/test-driven-development/SKILL.md` (repository paths are not skill invocation)

`/skill:<name>` is user-facing syntax. Prose inside a skill states dependencies by name.

## Decision Blocks

Write decisions as pseudocode IF/ELSE blocks. Keep one representation per procedure. Do not pair a decision block with a list or a graph that repeats the same procedure.

**Use a decision block ONLY for:**
- Non-obvious decision points
- Process loops where you can stop too early
- "When to use A vs B" decisions

**Never use one for:**
- Reference material (use tables or lists)
- Code examples (use markdown blocks)
- Linear instructions (use numbered lists)
- Labels without semantic meaning (step1, helper2)

## Code Examples

- One complete, runnable example in the most relevant language
- Comment WHY where non-obvious
- Drawn from a real scenario, ready to adapt
- No multi-language dilution, no fill-in-the-blank templates, no contrived examples

## Stating Rules

Write rules as unambiguous procedure:

- State the rule, its boundaries, and its exceptions explicitly
- Give decision rules for edge cases ("test passes immediately → you're testing existing behavior; fix the test"), not justifications
- For discipline-enforcing skills (TDD, verification): close known workarounds explicitly ("delete means delete: don't keep it as reference, don't adapt it"). State that violating the letter of the rule violates its spirit. Provide a red-flags list the agent can self-check against. For the tone and announcement mechanics of discipline skills, see `persuasion-principles.md`.
- Do not explain why a rule exists, what research supports it, or what goes wrong philosophically. The agent follows the skill instead of debating it.

## Testing Skills

The Iron Law (applies to new skills AND edits):

```
NO SKILL WITHOUT A FAILING TEST FIRST
```

If you wrote or edited a skill without testing, delete the change and start over.

**Test cycle** (methodology: `testing-skills-with-subagents.md`):

1. **RED** — Run a pressure scenario with an isolated subagent WITHOUT the skill text. Record the exact behavior and rationalizations verbatim.
2. **GREEN** — Write the minimal skill addressing those specific failures. Run the same scenarios WITH the skill text included in the dispatch. Check that the agent now complies.
3. **REFACTOR** — Plug each new loophole the agent finds. Re-check until bulletproof.

**Test approach by skill type:**

| Type | Test with | Success criterion |
|------|-----------|-------------------|
| Discipline-enforcing | Academic questions + pressure scenarios (time, sunk cost, exhaustion, combined) | Agent follows the rule under maximum pressure |
| Technique | Application and variation scenarios, missing-information probes | Agent applies the technique correctly to a new scenario |
| Pattern | Recognition and application scenarios, counter-examples | Agent identifies when and how the pattern applies |
| Reference | Retrieval and application scenarios | Agent finds and correctly applies the information |

## Deployment Checklist

Before moving to the next skill, complete this checklist for EACH skill. Deploying an untested skill is deploying untested code.

**RED:**
- [ ] Create pressure scenarios (3+ combined pressures for discipline skills)
- [ ] Run the scenarios without the skill. Document the baseline behavior verbatim.

**GREEN:**
- [ ] Check that `name` is valid and matches its directory. Check that the frontmatter has `name` and `description` (≤1024 chars).
- [ ] Check that the description starts with "Use when...", uses third person, lists triggers only, and has no workflow summary.
- [ ] Check that the body states procedure as rules and steps: no rationale, no persuasion, no narratives.
- [ ] Check that the text follows the simple-english skill (pragmatic mode). Run its self-check.
- [ ] Include one excellent example. Keep supporting files only for heavy reference or tools.
- [ ] Re-run the scenarios with the skill. Check that the agent complies.

**REFACTOR:**
- [ ] Close new loopholes. Add a red-flags list for discipline skills.
- [ ] Use a decision block only where a decision is non-obvious.
- [ ] Re-test until bulletproof.

**Deployment:**
- [ ] Commit to git

## Anti-Patterns

- **Narrative examples** ("In session 2025-10-03, we found...") — not reusable. State the rule instead.
- **Multi-language example files** — mediocre quality, maintenance burden. Use one excellent example.
- **Dot graphs and rendered diagrams** — use a pseudocode decision block instead. Keep one representation per procedure.
- **Generic labels** (helper1, step3) — labels carry semantic meaning
- **Rationale sections** ("Why this matters", "The psychology of...") — delete them. Procedure only.
