# Spec: Subagent Override Diagnostics

## Domain: subagent-dispatch

### MODIFIED Requirements

#### Requirement: Task interface and validation

The `task` call MUST treat `provider`, `model`, and `reasoningEffort` as optional literal overrides. The caller MUST omit an override field to use lower-precedence configuration. For each string call-level `provider` and `model` value, validation MUST trim surrounding whitespace before the empty and reserved-value checks. It MUST reject a value that is empty after trimming. It MUST reject the values `default`, `inherit`, and `auto` after case-insensitive normalization. It MUST preserve all internal content in other values. A rejected value MUST prevent all child startup. A rejected placeholder MUST explain that omission selects inherited configuration.

##### Scenario: Reserved override placeholders

- GIVEN a task call passes `default`, `inherit`, or `auto` as `provider` or `model`
- AND the value can contain surrounding whitespace and mixed-case letters
- WHEN request validation runs for each field and value combination
- THEN no child starts
- AND content identifies the affected field as a literal override
- AND content tells the caller to omit that field to use the configured value

##### Scenario: Exact literal override

- GIVEN a task call passes `provider: " openai "` and `model: " vendor/model name "`
- WHEN request validation runs
- THEN `openai` and `vendor/model name` reach child configuration
- AND validation changes no content except the surrounding whitespace

##### Scenario: Whitespace-only override

- GIVEN a task call passes only whitespace as `provider` or `model`
- WHEN request validation runs for each field
- THEN no child starts
- AND content states that the affected field must be a non-empty string

#### Requirement: Provider, model, and reasoning-effort overrides

The task schema and always-visible prompt guidance MUST identify `provider`, `model`, and `reasoningEffort` as optional literal overrides. They MUST tell callers to omit these fields during normal calls and for inheritance. They MUST state that placeholder values do not select defaults. Provider guidance MUST require an exact configured provider name. Model guidance MUST require an exact model ID supported by the selected provider. Reasoning guidance MUST list the supported thinking levels.

##### Scenario: Schema describes literal values

- GIVEN the task tool is registered
- WHEN a caller reads the three override parameter descriptions
- THEN each description identifies its field as optional and literal
- AND each description tells the caller to omit its field for inheritance
- AND provider guidance refers to an exact name from `tau providers`
- AND model guidance refers to an exact model ID supported by the selected provider
- AND reasoning guidance lists `off`, `minimal`, `low`, `medium`, `high`, and `xhigh`
- AND all three descriptions state that placeholder values do not select defaults

##### Scenario: Prompt describes omission and exact values

- GIVEN the task tool is registered
- WHEN a caller reads its always-visible prompt guidance
- THEN the guidance identifies all three fields as optional literal overrides
- AND it tells the caller to omit all three fields from normal calls and for inheritance
- AND it forbids `default`, `inherit`, and `auto` placeholders
- AND it states that placeholders do not select defaults
- AND it requires an exact configured provider name or an exact supported model ID when an override is requested
- AND it lists `off`, `minimal`, `low`, `medium`, `high`, and `xhigh` as the supported thinking levels

#### Requirement: Tau JSON collection

When a Tau child exits with a nonzero code and no existing error message, the runner MUST create an error message that contains the exit code. Cleaning MUST remove ECMA-48 CSI sequences that contain `ESC [`, zero or more parameter bytes from `0` through `?`, zero or more intermediate bytes from space through `/`, and one final byte from `@` through `~`. It MUST change no other code points. Truncation MUST occur after cleaning and count Unicode code points. If cleaned stderr contains 2,000 or fewer code points, the error message MUST contain all cleaned stderr. If cleaned stderr contains more than 2,000 code points, the error message MUST contain exactly its final 2,000 code points as the excerpt. The complete unmodified stderr MUST remain in structured child details. If the child already has an error message, the runner MUST preserve it unchanged and retain complete stderr in structured details.

If the runner creates the error and the excerpt contains `Unknown provider:` case-insensitively, the error message MUST tell the caller to omit provider, model, and reasoning overrides to use configured values. It MUST also tell the caller to use an exact provider name from `tau providers` for an override. If the runner creates the error and the excerpt contains `Model is not configured for provider` case-insensitively, the error message MUST tell the caller to omit the model for inheritance or use an exact model ID supported by the provider. Recovery instructions MUST NOT depend on diagnostic text outside the excerpt.

##### Scenario: Nonzero exit exposes stderr

- GIVEN a child writes an ANSI-colored diagnostic to stderr
- AND the child exits with a nonzero code without an existing error message
- WHEN the runner finalizes the child result
- THEN the error message contains the exit code and diagnostic text
- AND the error message contains no ECMA-48 CSI sequence
- AND structured details retain the original stderr

##### Scenario: Short and long stderr excerpts

- GIVEN one child writes `ESC [31m`, `error`, and `ESC [2J` to stderr, where each `ESC` is the escape code point
- AND another child writes `ESC [31m`, then `x`, then 2,000 `😀` code points, then `ESC [2J`
- AND each child exits with a nonzero code without an existing error message
- WHEN the runner finalizes each child result
- THEN the short stderr excerpt is `error`
- AND the long stderr excerpt is exactly 2,000 `😀` code points
- AND each child's structured details retain its complete original stderr

##### Scenario: Malformed CSI text is preserved

- GIVEN a child writes a trailing bare `ESC [` without a final byte
- AND the child exits with a nonzero code without an existing error message
- WHEN the runner finalizes the child result
- THEN the stderr excerpt retains the trailing bare `ESC [` unchanged

##### Scenario: Existing error message is preserved

- GIVEN a child already has the error message `provider request failed`
- AND the child writes `Unknown provider: default` to stderr and exits with a nonzero code
- WHEN the runner finalizes the child result
- THEN its error message remains `provider request failed`
- AND structured details retain the complete stderr

##### Scenario: Unknown provider recovery

- GIVEN Tau stderr contains `uNkNoWn PrOvIdEr: default`
- AND the child exits with a nonzero code without an existing error message
- WHEN the runner finalizes the child result
- THEN the error message tells the caller to omit provider, model, and reasoning overrides for inheritance
- AND it refers to exact provider names from `tau providers`

##### Scenario: Unknown model recovery

- GIVEN Tau stderr contains `mOdEl Is NoT cOnFiGuReD fOr PrOvIdEr openai: missing-model`
- AND the child exits with a nonzero code without an existing error message
- WHEN the runner finalizes the child result
- THEN the error message tells the caller to omit the model for inheritance
- AND it refers to an exact model ID supported by the provider

##### Scenario: Diagnostic outside the excerpt

- GIVEN cleaned Tau stderr contains `Unknown provider: default` followed by more than 2,000 code points
- AND the child exits with a nonzero code without an existing error message
- WHEN the runner finalizes the child result
- THEN the error message contains the bounded stderr excerpt
- AND it contains no unknown-provider recovery instruction

#### Requirement: Override user documentation

The user documentation MUST identify `provider`, `model`, and `reasoningEffort` as optional literal overrides. It MUST tell users to omit these fields for inheritance. It MUST state that `default`, `inherit`, and `auto` are invalid placeholders. It MUST direct users to `tau providers` for exact provider names and to the selected provider's supported model IDs for model overrides.

##### Scenario: README explains override selection

- GIVEN a user reads the task common options and provider-selection documentation
- WHEN the user decides whether to pass an override
- THEN the documentation identifies `provider`, `model`, and `reasoningEffort` as optional literal overrides
- AND it tells the user to omit each field for inheritance
- AND it distinguishes exact literal values from invalid placeholders
- AND it identifies where to find valid provider names and model IDs

#### Requirement: Content envelope and complete details

A failed child's model-visible content MUST include the actionable error message produced by the runner when no final assistant text is available. This content MUST let the controller identify a child startup configuration error and retry with corrected arguments. Structured details MUST continue to contain complete stderr independently from the bounded error excerpt.

##### Scenario: Single startup failure is recoverable

- GIVEN one child fails before it emits a valid assistant message
- AND the final 2,000 cleaned stderr code points identify an invalid provider or model
- WHEN the task result is returned
- THEN content includes the failed agent name
- AND content includes Tau's diagnostic
- AND content includes the matching recovery instruction
- AND structured details retain complete stderr

## Delivery Gates

- Focused automated tests MUST cover each modified scenario before implementation completion.
- The accepted feature-spec changes MUST be merged into `docs/specs/subagent-dispatch.md` before integration.
- A unified patch MUST be generated at `/workspace/tau-superpowers-subagent-override-diagnostics.patch` from base commit `37dbaa972c555236117def9314ab5c857c5d8bd4` through the completed branch.
- A clean checkout at that base commit MUST accept the patch with `git apply --check`.
