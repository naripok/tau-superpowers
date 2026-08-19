---
name: writing-skills
description: Use when creating new skills, editing existing skills, or verifying skills work before deployment
---

# Writing Skills

## What a Skill Is

A skill is a reference guide for a proven technique, pattern, or tool, written as a procedure: what to do, when to do it, and how to do it. Skills state rules and steps; they do not argue for them, justify them, or persuade.

**Skills are:** reusable techniques, patterns, tools, reference guides.

**Skills are NOT:** narratives about how you solved a problem once.

## Skill Discovery

Tau discovers skills from these directories in increasing precedence:

1. `~/.tau/skills/`
2. `~/.agents/skills/`
3. `<cwd>/.tau/skills/`
4. `<cwd>/.agents/skills/`

Each skill is a directory containing `SKILL.md`. A higher-precedence skill with the same name overrides a lower-precedence one. Tau initially injects only each skill's name, description, and path into the system prompt; the agent reads the full `SKILL.md` when the description matches its task. In an active TUI, run `/reload` after changing a skill. Users invoke a skill explicitly with `/skill:<name> [request]`.

## When to Create a Skill

**Create when:**
- The technique wasn't intuitively obvious
- You'd reference it again across projects
- The pattern applies broadly (not project-specific)

**Don't create for:**
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

- `name`: 1-64 characters; lowercase letters, numbers, and single hyphens only; no leading or trailing hyphen; must match the parent directory
- `description`: 1-1024 characters (keep under 500); third person; starts with "Use when..."; lists triggering conditions, symptoms, and contexts. **NEVER summarize the skill's process or workflow in the description** — an agent may follow the summary instead of reading the skill body

**Body:**

```markdown
# Skill Name

## Overview
What this is; the core rule in 1-2 sentences.

## When to Use
[Small inline flowchart only if the decision is non-obvious]
Symptoms and use cases. When NOT to use.

## The Procedure
Numbered steps or a flowchart. Decision rules for edge cases.

## Quick Reference
Table or bullets for scanning common operations.

## Common Mistakes
What goes wrong + the correct action.
```

## Description Rules

The description answers only: "Should I read this skill right now?"

- Start with "Use when..." and list concrete triggers, symptoms, situations
- Describe the problem (race conditions, flaky tests), not language-specific symptoms, unless the skill is technology-specific — then say so explicitly
- Third person
- Never summarize the process or workflow

```yaml
# BAD: workflow summary the agent may follow instead of reading the skill
description: Use when executing plans - dispatches subagent per task with review between tasks

# GOOD: triggering conditions only
description: Use when executing implementation plans with independent tasks in the current session
```

Use searchable keywords in the body: error messages, symptom words, synonyms, tool and file names.

## Naming

Active voice, verb-first; gerunds work well for processes:

- `condition-based-waiting`, not `async-test-helpers`
- `writing-skills`, not `skill-creation`

## Token Efficiency

- Keep descriptions concise; their metadata is always indexed
- Keep frequently-used skill bodies focused; move heavy reference and tools to supporting files
- Cross-reference other skills by name instead of repeating their content
- One excellent example beats several mediocre ones
- Don't explain what a command already makes obvious; don't give multiple examples of the same pattern

## Cross-Referencing Other Skills

Reference by skill name with an explicit requirement marker:

- GOOD: `**REQUIRED SUB-SKILL:** Use test-driven-development`
- GOOD: `**REQUIRED BACKGROUND:** You MUST understand systematic-debugging`
- BAD: `See skills/testing/test-driven-development` (assumes an installation layout)
- BAD: `Open @skills/testing/test-driven-development/SKILL.md` (repository paths are not skill invocation)

`/skill:<name>` is user-facing syntax; prose inside a skill states dependencies by name.

## Flowcharts

**Use flowcharts ONLY for:**
- Non-obvious decision points
- Process loops where you might stop too early
- "When to use A vs B" decisions

**Never use flowcharts for:**
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
- For discipline-enforcing skills (TDD, verification): close known workarounds explicitly ("delete means delete: don't keep it as reference, don't adapt it"), state that violating the letter of the rule violates its spirit, and provide a red-flags list the agent can self-check against
- Do not explain why a rule exists, what research supports it, or what goes wrong philosophically — the skill is followed, not argued into

## Testing Skills

The Iron Law (applies to new skills AND edits):

```
NO SKILL WITHOUT A FAILING TEST FIRST
```

If you wrote or edited a skill without testing, delete the change and start over.

**Test cycle** (methodology: `testing-skills-with-subagents.md`):

1. **RED** — Run a pressure scenario with an isolated subagent WITHOUT the skill text. Record the exact behavior and rationalizations verbatim.
2. **GREEN** — Write the minimal skill addressing those specific failures. Run the same scenarios WITH the skill text included in the dispatch. Verify the agent now complies.
3. **REFACTOR** — Plug each new loophole the agent finds. Re-verify until bulletproof.

**Test approach by skill type:**

| Type | Test with | Success criterion |
|------|-----------|-------------------|
| Discipline-enforcing | Academic questions + pressure scenarios (time, sunk cost, exhaustion, combined) | Agent follows the rule under maximum pressure |
| Technique | Application and variation scenarios; missing-information probes | Agent applies the technique correctly to a new scenario |
| Pattern | Recognition and application scenarios; counter-examples | Agent identifies when and how the pattern applies |
| Reference | Retrieval and application scenarios | Agent finds and correctly applies the information |

## Deployment Checklist

Complete for EACH skill before moving to the next. Deploying an untested skill is deploying untested code.

**RED:**
- [ ] Pressure scenarios created (3+ combined pressures for discipline skills)
- [ ] Scenarios run without the skill; baseline behavior documented verbatim

**GREEN:**
- [ ] `name` valid and matches its directory; frontmatter has `name` and `description` (≤1024 chars)
- [ ] Description starts with "Use when...", third person, triggers only, no workflow summary
- [ ] Body states procedure as rules and steps — no rationale, no persuasion, no narratives
- [ ] One excellent example; supporting files only for heavy reference or tools
- [ ] Scenarios re-run with the skill; agent complies

**REFACTOR:**
- [ ] New loopholes closed; red-flags list present for discipline skills
- [ ] Flowchart only where a decision is non-obvious
- [ ] Re-tested until bulletproof

**Deployment:**
- [ ] Committed to git

## Anti-Patterns

- **Narrative examples** ("In session 2025-10-03, we found...") — not reusable; state the rule instead
- **Multi-language example files** — mediocre quality, maintenance burden; one excellent example
- **Code in flowchart labels** — not copy-pasteable
- **Generic labels** (helper1, step3) — labels carry semantic meaning
- **Rationale sections** ("Why this matters", "The psychology of...") — delete them; procedure only
