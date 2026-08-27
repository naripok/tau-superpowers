# Proposal: Subagent Override Diagnostics

## Intent

The `task` tool accepts optional provider, model, and reasoning overrides. The current prompt does not clearly state that callers must omit these fields to inherit configured values. A caller can pass placeholder values such as `default` or `inherit`, which Tau treats as literal provider or model names.

The child runner captures Tau stderr, but its model-visible failure message reports only the exit code. The controller cannot identify the invalid argument from that message and can repeat the same mistake.

## Scope

**In scope:**

- Define call-level provider, model, and reasoning fields as optional literal overrides.
- Tell callers to omit these fields for inheritance.
- Reserve `default`, `inherit`, and `auto` as invalid provider and model placeholders.
- Reject reserved placeholders before child startup.
- Include a bounded, ECMA-48-CSI-free stderr excerpt in a failed child's error message.
- Add targeted recovery instructions for unknown provider and model errors.
- Preserve complete stderr in structured result details.
- Update user documentation with the override omission and literal-value rules.
- Deliver a unified patch that applies to repository commit `37dbaa972c555236117def9314ab5c857c5d8bd4`.

**Out of scope:**

- Dynamic provider or model discovery before child startup.
- Automatic replacement of invalid overrides with inherited values.
- Changes to provider, model, or reasoning precedence.
- Changes to successful child output.

## Approach

Use validation and diagnostics at separate boundaries.

Existing validation rejects non-string and empty common fields. The new validation trims surrounding whitespace from every string call-level provider and model value. It rejects empty normalized values and the case-insensitive placeholders `default`, `inherit`, and `auto`. The validation result tells the caller to omit the field for inheritance. Other provider and model content remains opaque.

The child runner converts nonzero process exits without an existing error message into an actionable error. It removes ECMA-48 CSI sequences from stderr. It changes no other code points and includes at most the final 2,000 cleaned code points. The final portion usually contains the CLI error. Unknown-provider and unknown-model diagnostics add a focused recovery instruction. The complete stderr remains in structured details.

The task schema and always-visible prompt guidelines use the same terms. The README documents the omission rule and literal override values.

A documentation-only approach cannot prevent child startup with known placeholders. Dynamic preflight requires a new Tau API dependency or another subprocess. The proposed validation uses the existing request boundary and leaves Tau responsible for validating real provider and model names.

## Impact

The change affects task schema text, request validation, child process failure messages, user documentation, the subagent-dispatch living spec, focused tests, and a unified patch deliverable. Calls that use the reserved placeholders will receive an immediate validation result instead of starting a child. Other invalid provider and model values will produce a child failure that includes Tau's diagnostic and recovery instructions.
