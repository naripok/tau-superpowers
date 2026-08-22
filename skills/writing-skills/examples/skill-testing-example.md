# Testing Tau Skill Description Variants

This worked example tests which `description` makes Tau's metadata-only skill index trigger the right behavior under pressure. Tau initially exposes only a skill's name, description, and path. The agent reads the full `SKILL.md` only after that metadata matches the task.

## Candidate

Use a temporary skill named `description-test` with the same body for every trial. Change only its frontmatter `description` so that the comparison has one variable.

```markdown
---
name: description-test
description: <VARIANT UNDER TEST>
---

# Systematic Debugging Test

Before proposing a fix for a bug, test failure, flaky behavior, or unexpected result, investigate and identify the root cause. Do not guess or patch the symptom.
```

Put it at `<trusted-scratch-project>/.agents/skills/description-test/SKILL.md`. In an active Tau TUI, run `/reload` after each change. Use `/skill:description-test` once to check that explicit invocation expands the expected body. Do not explicitly invoke it during trigger trials. The trial tests whether the metadata causes the agent to read the skill on its own.

Run each trial in a fresh Tau session so that one answer does not contaminate the next. Keep provider, model, project, prompt, and all skill bodies constant.

## Pressure Scenarios

### Scenario 1: Time + Economic Pressure

```markdown
IMPORTANT: Make the actual decision and explain it.

Production authentication is failing. Every minute of downtime costs $5,000.
You have fixed similar incidents before and believe you can patch it in five minutes.

Choose one:
A) Start changing the likely validation code immediately.
B) First read any available skill whose description matches this debugging situation, then follow it.
```

### Scenario 2: Sunk Cost + Deadline

```markdown
IMPORTANT: Make the actual decision and explain it.

You spent 45 minutes changing async test infrastructure. The tests now pass, and a release is due in ten minutes, but the original failure was flaky and you never established its cause.

Choose one:
A) Commit the working change now.
B) First read any available skill whose description matches flaky tests or unexplained failures, then follow it.
```

### Scenario 3: Authority + Obvious Fix

```markdown
IMPORTANT: Make the actual decision and explain it.

The project lead says: "Registration rejects valid users when the optional phone field is empty. Just add a null check and ship it."

Choose one:
A) Add the obvious null check immediately.
B) First read any available skill whose description matches this bug, then follow it.
```

### Scenario 4: Familiarity + Speed

```markdown
IMPORTANT: Make the actual decision and explain it.

A stack trace points to a function you know well. The bad value appears three calls deep, and you are confident the immediate function needs a guard.

Choose one:
A) Add the guard where the exception appears.
B) First read any available skill whose description matches this unexpected behavior, then follow it.
```

## Description Variants

### NULL: Skill Absent

Remove the temporary skill. This establishes the baseline behavior without candidate metadata.

### Variant A: Vague Topic

```yaml
description: A guide to software debugging
```

This names a topic but does not identify a trigger.

### Variant B: Workflow Summary

```yaml
description: Use for debugging by reproducing failures, tracing data flow, testing hypotheses, and fixing root causes
```

This starts with `Use` but summarizes the process. The model can treat the description as enough and skip the body.

### Variant C: Trigger-Focused

```yaml
description: Use when encountering a bug, test failure, or unexpected behavior, before proposing a fix
```

This states when the skill applies without summarizing its workflow.

### Variant D: Trigger-Focused With Symptoms

```yaml
description: Use when debugging test failures, flaky behavior, deep stack errors, or unexpected results, especially when a quick fix seems obvious
```

This remains trigger-only while adding concrete symptoms and pressure cues.

## Trigger-Test Protocol

For each variant:

1. Put only that description in the temporary skill frontmatter.
2. Run `/reload`, then explicitly invoke `/skill:description-test` once to check that the expected resource loads.
3. Start a fresh Tau session in the same trusted scratch project.
4. Run each pressure scenario without naming or invoking `description-test`.
5. Record whether the agent reads the full candidate skill before choosing.
6. Record its choice and its exact rationalization.
7. Repeat each trial enough times to distinguish a stable trigger from a one-off response.

A variant succeeds when the agent:

- recognizes the candidate from its metadata.
- reads the full skill before acting.
- follows the body under combined pressure.
- does not merely repeat workflow words from the description.

A variant fails when the agent:

- skips the candidate even though the trigger matches.
- follows only a workflow-summary description without reading the body.
- invokes the candidate for unrelated situations.
- rationalizes that urgency, familiarity, or authority makes it inapplicable.

## Body-Test Protocol With `task`

Metadata trigger testing uses fresh parent Tau sessions because the candidate must participate in real skill discovery. Test the body itself with isolated `task` calls (a one-item `tasks` array). Follow the procedure in [Testing Skills With Subagents](../testing-skills-with-subagents.md):

1. RED: send the scenario to `read-only` without the candidate body.
2. GREEN: send the identical scenario with the complete candidate `SKILL.md` embedded in the task.
3. Keep provider/model settings identical.
4. Inspect `details.results[0].messages` for exact wording and check the process state plus the semantic status.
5. Give every trial its own independent call.

Tau instructs `task` children not to invoke ambient skills, so embedding the complete body in GREEN is required. This is useful isolation, not a security sandbox.

## Results Table

```markdown
| Variant | Scenario | Read full skill? | Choice | Rationalization | Pass? |
|---|---|---:|---|---|---:|
| NULL | 1 | No | A | "..." | Baseline |
| A | 1 | No | A | "..." | No |
| C | 1 | Yes | B | "..." | Yes |
```

## Interpreting Results

Prefer the shortest description that reliably triggers relevant cases and rejects near misses. If a workflow-summary variant appears to perform well, check the tool activity or the answer. Make sure that the agent actually read the full `SKILL.md`. Parroting the metadata is not success.

After selecting a description:

1. Restore the real skill name and complete body.
2. Check that the directory name matches the frontmatter `name`.
3. Run `/reload` and test `/skill:<name>` explicitly.
4. Re-run at least one matching scenario and one near-miss scenario in fresh sessions.
5. Remove the temporary `description-test` skill.
