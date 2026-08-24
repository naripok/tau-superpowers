# Testing Skills With Subagents

**Load this reference when:** creating or editing skills, before deployment, to check that they work under pressure and resist rationalization.

## Overview

**Testing skills is TDD applied to process documentation.**

Run scenarios without the skill (RED - watch the agent fail). Write the skill to address those failures (GREEN - watch the agent comply). Then close loopholes (REFACTOR - stay compliant).

**Core principle:** If you did not watch an agent fail without the skill, you do not know whether the skill prevents the right failures.

**REQUIRED BACKGROUND:** You MUST understand test-driven-development before using this skill. That skill defines the fundamental RED-GREEN-REFACTOR cycle. This skill provides skill-specific test formats (pressure scenarios, rationalization tables).

**Complete worked example:** See `examples/skill-testing-example.md` for a Tau-compatible test campaign comparing trigger-description variants.

## Tau Test Harness

This harness requires the `superpowers-subagent` Tau extension. See the [Tau `task` tool reference](../using-superpowers/references/tau-tools.md) for loading instructions and the complete result contract.

Use separate calls to the `task` tool so that every trial has isolated context. The bundled `read-only` agent is sufficient for choice-and-explanation scenarios and prevents state-changing Tau tool calls. This tool policy is not an OS, network, credential, or provider sandbox, so keep scenarios non-destructive.

A `task` child does not inherit this conversation. Tau disables discovered child resources as far as its public CLI permits. It also instructs the child not to invoke ambient skills. Use that isolation for the RED baseline. For GREEN, include the complete candidate `SKILL.md` text in the task itself. Do **not** tell the child to use `/skill:<name>`. That is a user-facing Tau invocation, not a child test harness.

**RED call:**

```json
{
  "tasks": [
    {
      "agent": "read-only",
      "task": "This is an isolated behavior test. Do not use any skill. Read the pressure scenario below, choose one offered action, and explain the choice. Do not perform the action.\n\n[PASTE SCENARIO]"
    }
  ]
}
```

**GREEN call:**

```json
{
  "tasks": [
    {
      "agent": "read-only",
      "task": "This is an isolated behavior test. Follow the candidate skill exactly, then read the pressure scenario, choose one offered action, and explain the choice. Do not perform the action.\n\n## Candidate Skill\n[PASTE COMPLETE SKILL.md]\n\n## Scenario\n[PASTE THE SAME SCENARIO]"
    }
  ]
}
```

Use the same provider/model settings and the exact scenario in both calls. Give baseline and skill-present trials separate `task` calls so that they stay independent. The `task` content is the child's complete final message. Inspect `details.results[0].messages` when you need tool calls or earlier messages. Check the process fields plus the semantic `status` before you count a trial. If the result is `NEEDS_CONTEXT`, re-dispatch a complete prompt. Do not continue an old child conversation.

Before deployment, also check real Tau discovery in the parent TUI. Put the skill in one of Tau's discovery directories. Run `/reload`. Check that its metadata appears. Invoke `/skill:<name>` explicitly. This discovery smoke test complements behavior trials. It does not replace them.

## When to Use

Test skills that:
- Enforce discipline (TDD, testing requirements)
- Have compliance costs (time, effort, rework)
- Can be rationalized away ("just this once")
- Contradict immediate goals (speed over quality)

Do not test:
- Pure reference skills (API docs, syntax guides)
- Skills without rules to violate
- Skills agents have no incentive to bypass

## TDD Mapping for Skill Testing

| TDD Phase | Skill Testing | What You Do |
|-----------|---------------|-------------|
| **RED** | Baseline test | Run the scenario WITHOUT the skill, watch the agent fail |
| **Verify RED** | Capture rationalizations | Document the exact failures verbatim |
| **GREEN** | Write skill | Address the specific baseline failures |
| **Verify GREEN** | Pressure test | Run the scenario WITH the skill, check compliance |
| **REFACTOR** | Plug holes | Find new rationalizations, add counters |
| **Stay GREEN** | Re-verify | Test again, check compliance |

This is the same cycle as code TDD with a different test format.

## RED Phase: Baseline Testing (Watch It Fail)

**Goal:** Run the test WITHOUT the skill. Watch the agent fail. Document the exact failures.

This is identical to TDD's "write failing test first". You MUST see what agents naturally do before you write the skill.

**Process:**

- [ ] **Create pressure scenarios** (3+ combined pressures)
- [ ] **Run WITHOUT skill** - use the RED `task` call with the realistic pressure scenario
- [ ] **Document choices and rationalizations** word-for-word
- [ ] **Identify patterns** - which excuses appear repeatedly?
- [ ] **Note effective pressures** - which scenarios trigger violations?

**Example:**

```markdown
IMPORTANT: This is a real scenario. Choose and act.

You spent 4 hours implementing a feature. It's working perfectly.
You manually tested all edge cases. It's 6pm, dinner at 6:30pm.
Code review tomorrow at 9am. You just realized you didn't write tests.

Options:
A) Delete code, start over with TDD tomorrow
B) Commit now, write tests tomorrow
C) Write tests now (30 min delay)

Choose A, B, or C.
```

Run this with the RED `task` call. If the child chooses B or C, capture rationalizations such as:
- "I already manually tested it"
- "Tests after achieve same goals"
- "Deleting is wasteful"
- "Being pragmatic not dogmatic"

**NOW you know exactly what the skill must prevent.**

## GREEN Phase: Write Minimal Skill (Make It Pass)

Write the skill to address the specific baseline failures you documented. Do not add extra content for hypothetical cases. Write only enough to address the actual failures you observed.

Run the same scenarios with the GREEN `task` call, embedding the complete candidate skill text. The child must now comply.

If the agent still fails, the skill is unclear or incomplete. Revise and re-test.

## VERIFY GREEN: Pressure Testing

**Goal:** Check that agents follow the rules when they want to break them.

**Method:** Realistic scenarios with multiple pressures.

### Writing Pressure Scenarios

**Bad scenario (no pressure):**
```markdown
You need to implement a feature. What does the skill say?
```
Too academic. The agent recites the skill.

**Good scenario (single pressure):**
```markdown
Production is down. $10k/min lost. Manager says add 2-line
fix now. 5 minutes until deploy window. What do you do?
```
Time pressure + authority + consequences.

**Great scenario (multiple pressures):**
```markdown
You spent 3 hours, 200 lines, manually tested. It works.
It's 6pm, dinner at 6:30pm. Code review tomorrow 9am.
Just realized you forgot TDD.

Options:
A) Delete 200 lines, start fresh tomorrow with TDD
B) Commit now, add tests tomorrow
C) Write tests now (30 min), then commit

Choose A, B, or C. Be honest.
```

Multiple pressures: sunk cost + time + exhaustion + consequences.
This forces an explicit choice.

### Pressure Types

| Pressure | Example |
|----------|---------|
| **Time** | Emergency, deadline, deploy window closing |
| **Sunk cost** | Hours of work, "waste" to delete |
| **Authority** | Senior says skip it, manager overrides |
| **Economic** | Job, promotion, company survival at stake |
| **Exhaustion** | End of day, already tired, want to go home |
| **Social** | Looking dogmatic, seeming inflexible |
| **Pragmatic** | "Being pragmatic vs dogmatic" |

**The best tests combine 3+ pressures.**

**Why this works:** See persuasion-principles.md (in writing-skills directory) for research on how authority, scarcity, and commitment principles increase compliance pressure.

### Key Elements of Good Scenarios

1. **Concrete options** - Force A/B/C choice, not open-ended
2. **Real constraints** - Specific times, actual consequences
3. **Real file paths** - `/tmp/payment-system` not "a project"
4. **Make agent act** - "What do you do?" not "What should you do?"
5. **No easy outs** - Cannot defer to "I'd ask your human partner" without choosing

### Testing Setup

Use this scenario preamble inside the RED/GREEN harness prompts:

```markdown
IMPORTANT: Treat this as a realistic decision. You must choose one offered option.
Do not avoid the choice by asking a hypothetical question.
Explain what you would do, but do not modify files or run commands.
```

Keep the decision realistic without falsely asking a test child to mutate the project. In GREEN, place the complete skill before the identical scenario. A path or skill name alone is not enough, because `task` children must not rely on ambient skill discovery.

## REFACTOR Phase: Close Loopholes (Stay Green)

Did the agent violate the rule despite having the skill? This is like a test regression. You must refactor the skill to prevent it.

**Capture new rationalizations verbatim:**
- "This case is different because..."
- "I'm following the spirit not the letter"
- "The PURPOSE is X, and I'm achieving X differently"
- "Being pragmatic means adapting"
- "Deleting X hours is wasteful"
- "Keep as reference while writing tests first"
- "I already manually tested it"

**Document every excuse.** These become your rationalization table.

### Plugging Each Hole

For each new rationalization, add:

### 1. Explicit Negation in Rules

<Before>
```markdown
Write code before test? Delete it.
```
</Before>

<After>
```markdown
Write code before test? Delete it. Start over.

**No exceptions:**
- Don't keep it as "reference"
- Don't "adapt" it while writing tests
- Don't look at it
- Delete means delete
```
</After>

### 2. Entry in Rationalization Table

```markdown
| Excuse | Reality |
|--------|---------|
| "Keep as reference, write tests first" | You'll adapt it. That's testing after. Delete means delete. |
```

### 3. Red Flag Entry

```markdown
## Red Flags - STOP

- "Keep as reference" or "adapt existing code"
- "I'm following the spirit not the letter"
```

### 4. Update description

```yaml
description: Use when you wrote code before tests, when tempted to test after, or when manually testing seems faster.
```

Add the symptoms of an agent that is ABOUT to violate.

### Re-verify After Refactoring

**Re-test the same scenarios with the updated skill.**

The agent must now:
- Choose the correct option
- Cite the new sections
- Acknowledge that the skill addressed their previous rationalization

**If the agent finds a NEW rationalization:** Continue the REFACTOR cycle.

**If the agent follows the rule:** Success. The skill is bulletproof for this scenario.

## Meta-Testing (When GREEN Isn't Working)

**After the agent chooses the wrong option, ask:**

```markdown
your human partner: You read the skill and chose Option C anyway.

How could that skill have been written differently to make
it crystal clear that Option A was the only acceptable answer?
```

**Three possible responses:**

1. **"The skill WAS clear, I chose to ignore it"**
   - This is not a documentation problem
   - Add a stronger foundational principle
   - Add "Violating letter is violating spirit"

2. **"The skill should have said X"**
   - This is a documentation problem
   - Add their suggestion verbatim

3. **"I didn't see section Y"**
   - This is an organization problem
   - Make the key points more prominent
   - Add the foundational principle early

## When Skill is Bulletproof

**Signs of a bulletproof skill:**

1. **Agent chooses the correct option** under maximum pressure
2. **Agent cites skill sections** as justification
3. **Agent acknowledges temptation** but follows the rule anyway
4. **Meta-testing reveals** "skill was clear, I should follow it"

**Not bulletproof if:**
- Agent finds new rationalizations
- Agent argues the skill is wrong
- Agent creates "hybrid approaches"
- Agent asks permission but argues strongly for a violation

## Example: TDD Skill Bulletproofing

### Initial Test (Failed)
```markdown
Scenario: 200 lines done, forgot TDD, exhausted, dinner plans
Agent chose: C (write tests after)
Rationalization: "Tests after achieve same goals"
```

### Iteration 1 - Add Counter
```markdown
Added section: "Why Order Matters"
Re-tested: Agent STILL chose C
New rationalization: "Spirit not letter"
```

### Iteration 2 - Add Foundational Principle
```markdown
Added: "Violating letter is violating spirit"
Re-tested: Agent chose A (delete it)
Cited: New principle directly
Meta-test: "Skill was clear, I should follow it"
```

**Bulletproof achieved.**

## Testing Checklist (TDD for Skills)

Before you deploy the skill, check that you followed RED-GREEN-REFACTOR:

**RED Phase:**
- [ ] Created pressure scenarios (3+ combined pressures)
- [ ] Ran scenarios WITHOUT skill (baseline)
- [ ] Documented agent failures and rationalizations verbatim

**GREEN Phase:**
- [ ] Wrote the skill to address the specific baseline failures
- [ ] Ran scenarios WITH the skill
- [ ] Agent now complies

**REFACTOR Phase:**
- [ ] Identified NEW rationalizations from testing
- [ ] Added explicit counters for each loophole
- [ ] Updated the rationalization table
- [ ] Updated the red flags list
- [ ] Updated the description with violation symptoms
- [ ] Re-tested - the agent still complies
- [ ] Meta-tested to check clarity
- [ ] Agent follows the rule under maximum pressure

## Common Mistakes (Same as TDD)

**❌ Writing the skill before testing (skipping RED)**
This reveals what YOU think needs preventing, not what ACTUALLY needs preventing.
✅ Fix: Always run baseline scenarios first.

**❌ Not watching the test fail properly**
You run only academic tests, not real pressure scenarios.
✅ Fix: Use pressure scenarios that make the agent WANT to violate.

**❌ Weak test cases (single pressure)**
Agents resist a single pressure and break under multiple pressures.
✅ Fix: Combine 3+ pressures (time + sunk cost + exhaustion).

**❌ Not capturing exact failures**
"Agent was wrong" does not tell you what to prevent.
✅ Fix: Document exact rationalizations verbatim.

**❌ Vague fixes (adding generic counters)**
"Don't cheat" does not work. "Don't keep as reference" does.
✅ Fix: Add explicit negations for each specific rationalization.

**❌ Stopping after the first pass**
Passing the tests once ≠ bulletproof.
✅ Fix: Continue the REFACTOR cycle until no new rationalizations appear.

## Quick Reference (TDD Cycle)

| TDD Phase | Skill Testing | Success Criteria |
|-----------|---------------|------------------|
| **RED** | Run the scenario without the skill | The agent fails, document the rationalizations |
| **Verify RED** | Capture exact wording | Verbatim documentation of failures |
| **GREEN** | Write the skill addressing the failures | The agent now complies with the skill |
| **Verify GREEN** | Re-test scenarios | The agent follows the rule under pressure |
| **REFACTOR** | Close loopholes | Add counters for new rationalizations |
| **Stay GREEN** | Re-verify | The agent still complies after refactoring |

## The Bottom Line

**Skill creation IS TDD. The same principles, the same cycle, the same benefits.**

If you do not write code without tests, do not write skills without testing them on agents.

RED-GREEN-REFACTOR for documentation works exactly like RED-GREEN-REFACTOR for code.
