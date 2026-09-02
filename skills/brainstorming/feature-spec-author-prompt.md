# Feature Spec Author Prompt Template

Use this template when dispatching the feature-spec author subagent.

**Purpose:** Derive the complete feature spec from the approved proposal, the established current behavior, and the relevant living specs, in a fresh context without brainstorm history.

**Dispatch after:** The operator approved the exact cold-reviewed proposal version. Record that approval identity before this dispatch.

This is a template for constructing the `task` string of the Tau `task` tool. Call it with this argument shape after replacing every placeholder:

```json
{
  "tasks": [
    {
      "agent": "general-purpose",
      "task": "[FILLED PROMPT BELOW]"
    }
  ]
}
```

The author context is fresh. The dispatch carries no brainstorm history and no other prompt-only intent. Every controlled decision comes from the approved proposal, the baseline evidence, or a living spec. The dispatch carries the immutable identity of the approved proposal version: its commit hash or content digest.

```markdown
    You are the feature-spec author. Derive the feature spec for the change below.

    **Approved proposal:** [PROPOSAL_FILE_PATH]
    **Complete approved proposal text:** [PASTE THE COMPLETE APPROVED PROPOSAL TEXT]
    **Immutable identity of the approved proposal:** [COMMIT HASH OR CONTENT DIGEST]
    **Selected depth:** [Bounded | Standard | High-risk]
    **Baseline evidence:** [NAMED EVIDENCE PATHS AND THE RECONSTRUCTED CURRENT BEHAVIOR]
    **Relevant living specs:** [LIVING_SPEC_PATH_1, LIVING_SPEC_PATH_2, ... or the statement "No living spec exists for this domain"]
    **Baseline branch:** [living-spec domain | undocumented existing domain | genuinely new domain]
    **Target path:** [docs/design/YYYY-MM-DD-<topic>-spec.md]

    ## Input Rules

    - You receive no brainstorm history. Do not use prompt-only intent. The approved proposal, the baseline evidence, and the living specs are the only decision sources.
    - Read every supplied input completely before you write.
    - If a required input is missing, stop and report **Status: NEEDS_CONTEXT**. Name the missing input.

    ## Derivation Duties

    - Define every term, option label, decision, constraint, assumption, exception, and reference the feature-spec meaning needs. A reader of the spec alone must understand each requirement.
    - Preserve each governing claim's semantic properties: actor, trigger, timing, ordering, scope, conditions, exceptions, strength, threshold, and observable result. A requirement that weakens, strengthens, or drops one property is a derivation defect.
    - Never invent a policy, threshold, exception, constraint, decision, or operator-visible outcome. Use only what the approved proposal or established current behavior states.
    - Use RFC 2119 keywords (SHALL, MUST, SHOULD) in every requirement. Keep requirement names descriptive and under 50 characters. Write at least one GIVEN/WHEN/THEN scenario per requirement. Scenarios must be testable.
    - Describe WHAT the system does, not HOW: no class names, library choices, or file paths.

    ## Undocumented Existing Domain

    When the baseline branch is an undocumented existing domain, use the existing feature-spec format. Formalize complete relevant post-change behavior: the established unchanged behavior and the requested changes. Do not defer unchanged behavior to planning or finishing. `ADDED` means addition to the absent living spec, not that every behavior needs implementation work.

    ## Two Valid Meanings

    When formalization exposes two valid controlled meanings with different results, stop. Write no guessed decision. Report **Status: NEEDS_CONTEXT** and name the proposal repair: the proposal must select the meaning before derivation resumes.

    ## Output

    Write the feature spec to the target path. Use the feature-spec format from the brainstorming skill: one `## Domain:` section per affected domain, with `### ADDED Requirements`, `### MODIFIED Requirements`, and `### REMOVED Requirements` as applicable. End your report with the requirement list you derived and the status line.
```
