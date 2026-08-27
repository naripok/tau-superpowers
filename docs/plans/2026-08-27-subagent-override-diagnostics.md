# Subagent Override Diagnostics Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use subagent-driven-development (recommended) or executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make task override arguments unambiguous and return actionable Tau child startup failures.

**Architecture:** Validate known placeholder misuse at the task request boundary. Keep Tau responsible for real provider and model validation, then convert nonzero Tau exits into bounded diagnostics with targeted recovery text. Keep complete stderr in structured details while exposing only a cleaned excerpt in model-visible content.

**Tech Stack:** Python 3.14, Tau extension APIs, pytest, mypy, Ruff, Markdown.

**Standards:** Apply the shared code standards in every task: DRY, minimal implementation (YAGNI), low cyclomatic complexity, type safety, no unnecessary abstractions or fallbacks, no hacks or workarounds, informative docstrings, documentation of current state only, writing-developer-facing-text prose.

**Feature spec:** `docs/design/2026-08-27-subagent-override-diagnostics-spec.md` (the behavioral contract)

---

## Commands

Run setup, test, type, lint, and format commands from `extensions/superpowers-subagent`. Run Git commands from the repository root, or use `git -C ../..` from that extension directory.

```bash
TAU_PYTHON=$(sed -n '1s/^#!//p' "$(command -v tau)")
TAU_SITE_PACKAGES=$(
  "$TAU_PYTHON" -c 'import sysconfig; print(sysconfig.get_paths()["purelib"])'
)
uv sync --all-groups --locked
PYTHONPATH="$TAU_SITE_PACKAGES" uv run pytest <test-path> -v
PYTHONPATH="$TAU_SITE_PACKAGES" uv run pytest
PYTHONPATH="$TAU_SITE_PACKAGES" uv run mypy
uv run ruff check .
uv run ruff format --check .
```

### Task 1: Literal Override Contract and Validation

**Files:**
- Modify: `extensions/superpowers-subagent/superpowers_subagent/extension.py` — clarify the task schema and always-visible override guidance.
- Modify: `extensions/superpowers-subagent/superpowers_subagent/dispatch.py` — normalize literal overrides and reject reserved placeholders.
- Modify: `extensions/superpowers-subagent/tests/test_extension.py` — prove the schema and prompt contract.
- Modify: `extensions/superpowers-subagent/tests/test_dispatch.py` — prove normalization, placeholder rejection, and child prevention.
- Modify: `README.md` — document omission, literal values, and provider and model discovery.

**Spec requirement:** Modified “Task interface and validation,” “Provider, model, and reasoning-effort overrides,” and “Override user documentation.”

**Interface:**
- `_RESERVED_OVERRIDE_PLACEHOLDERS: frozenset[str]` — contain `default`, `inherit`, and `auto` in normalized form.
- `_optional_literal_override(arguments: Mapping[str, JSONValue], key: str) -> str | None` — return `None` when absent; use existing string validation; trim surrounding whitespace; reject an empty normalized value; reject a reserved value case-insensitively with a field-specific inheritance instruction; preserve internal content in accepted values.
- `_TASK_PARAMETERS` descriptions — identify all three override fields as optional literals; define omission as inheritance; define exact provider, model, and reasoning values; state that placeholders do not select defaults.
- `AgentTool.prompt_guidelines` — tell controllers to omit all three fields during normal calls; forbid placeholder values; require exact override values when requested.

**Behavior:**
- Every accepted provider and model call override reaches resolution without surrounding whitespace.
- Internal whitespace and slash-containing model IDs remain unchanged.
- Every provider/model combination with `default`, `inherit`, or `auto`, regardless of case or surrounding whitespace, returns a normal validation result before any child starts.
- Existing non-string validation remains unchanged.
- User documentation gives the same omission and literal-value rules as the tool prompt.

**Tests must prove:**
- `test_task_override_schema_defines_optional_literal_values` — all schema descriptions contain the required omission and exact-value guidance, including all six reasoning levels.
- `test_task_tool_prompt_states_override_omission_and_literal_values` — prompt guidance forbids all reserved placeholders and defines valid override forms.
- `test_validation_rejects_every_reserved_provider_and_model_placeholder` — all six field/value combinations fail across case and whitespace variants.
- `test_validation_trims_literal_overrides_and_preserves_internal_content` — accepted values lose only surrounding whitespace.
- `test_validation_rejects_whitespace_only_literal_overrides` — provider and model whitespace-only values return field-specific errors and start no child.
- `test_validation_rejects_non_string_literal_overrides` — wrong-typed provider and model values return field-specific errors and start no child.
- Existing invalid-common-option tests still prove empty input rejection.
- Each rejection leaves the fake runner call list empty and returns the affected field plus omission guidance.
- `test_readme_documents_literal_override_selection` — README text covers all three optional literal fields, inheritance by omission, reserved placeholders, `tau providers`, and exact supported model IDs.

**Check:** `PYTHONPATH="$TAU_SITE_PACKAGES" uv run pytest tests/test_extension.py tests/test_dispatch.py -v && PYTHONPATH="$TAU_SITE_PACKAGES" uv run mypy && uv run ruff check . && uv run ruff format --check .` — expected: all pass.

- [ ] Write the failing tests for the behaviors above. Run them and check that each fails for the expected reason.
- [ ] Implement the interface and behavior.
- [ ] Update the README with the accepted behavior.
- [ ] Run verification.
- [ ] Commit from `extensions/superpowers-subagent`: `git -C ../.. add README.md extensions/superpowers-subagent/superpowers_subagent/extension.py extensions/superpowers-subagent/superpowers_subagent/dispatch.py extensions/superpowers-subagent/tests/test_extension.py extensions/superpowers-subagent/tests/test_dispatch.py && git -C ../.. commit -m "feat: validate literal subagent overrides"`

### Task 2: Recoverable Tau Child Exit Diagnostics

**Files:**
- Modify: `extensions/superpowers-subagent/superpowers_subagent/runner.py` — build bounded child exit errors from stderr.
- Modify: `extensions/superpowers-subagent/tests/test_runner.py` — prove cleaning, truncation, preservation, matching, and recovery behavior.
- Modify: `extensions/superpowers-subagent/tests/test_runtime_integration.py` — prove actionable errors reach model-visible task content while details retain stderr.
- Modify: `extensions/superpowers-subagent/tests/fixtures/fake_tau.py` — provide a deterministic unknown-provider child startup failure.

**Spec requirement:** Modified “Tau JSON collection” and “Content envelope and complete details.”

**Interface:**
- `_CSI_SEQUENCE: re.Pattern[str]` — match `ESC [`, zero or more parameter bytes in `0x30`–`0x3F`, zero or more intermediate bytes in `0x20`–`0x2F`, and one final byte in `0x40`–`0x7E`.
- `_MAX_STDERR_EXCERPT_CODEPOINTS: int` — equal 2,000.
- `_stderr_excerpt(stderr: str) -> str` — remove matched CSI sequences; preserve every other code point; return the complete cleaned string at or below the limit; return exactly the final 2,000 code points above the limit.
- `_child_exit_error(result: ChildResult) -> str` — report the nonzero exit code; append a nonempty stderr excerpt; add unknown-provider recovery for a case-insensitive `Unknown provider:` match in the excerpt; add unknown-model recovery for a case-insensitive `Model is not configured for provider` match in the excerpt; never inspect omitted stderr for recovery matching.
- `TauChildRunner.run(...)` finalization — call `_child_exit_error` only for a nonzero exit without an existing error message. Preserve existing error messages and complete `result.stderr`.

**Behavior:**
- Startup failures expose Tau's final bounded diagnostic to the controller.
- CSI SGR and non-SGR sequences disappear from the excerpt.
- Supplementary Unicode code points count as one code point each.
- Diagnostic text before the final 2,000 cleaned code points does not add recovery instructions.
- Existing child error messages remain unchanged even when stderr contains a recognized diagnostic.
- The single-child failure envelope includes the agent name, Tau diagnostic, and matching recovery instruction.

**Tests must prove:**
- `test_runner_nonzero_exit_includes_csi_free_stderr_excerpt` — SGR and erase-display CSI sequences are removed while other content remains.
- `test_runner_preserves_malformed_csi_text` — a trailing bare `ESC [` without a final byte remains unchanged.
- `test_runner_nonzero_exit_keeps_final_2000_unicode_codepoints` — a 2,001-code-point cleaned payload returns exactly the expected final 2,000 supplementary code points.
- `test_runner_adds_unknown_provider_recovery_from_excerpt` — mixed-case provider diagnostics produce omission and `tau providers` guidance.
- `test_runner_adds_unknown_model_recovery_from_excerpt` — mixed-case model diagnostics produce omission and exact-model guidance.
- `test_runner_ignores_diagnostic_outside_excerpt` — a recognized diagnostic before more than 2,000 later code points adds no recovery instruction.
- `test_runner_preserves_existing_error_and_complete_stderr` — an existing error remains unchanged and full stderr stays on the result.
- `test_runtime_returns_recoverable_child_startup_failure` — task content carries the actionable error while schema-v2 details contain unmodified stderr.

**Check:** `PYTHONPATH="$TAU_SITE_PACKAGES" uv run pytest tests/test_runner.py tests/test_runtime_integration.py -v && PYTHONPATH="$TAU_SITE_PACKAGES" uv run mypy && uv run ruff check . && uv run ruff format --check .` — expected: all pass.

- [ ] Write the failing tests for the behaviors above. Run them and check that each fails for the expected reason.
- [ ] Implement the interface and behavior.
- [ ] Run verification.
- [ ] Commit from `extensions/superpowers-subagent`: `git -C ../.. add extensions/superpowers-subagent/superpowers_subagent/runner.py extensions/superpowers-subagent/tests/test_runner.py extensions/superpowers-subagent/tests/test_runtime_integration.py extensions/superpowers-subagent/tests/fixtures/fake_tau.py && git -C ../.. commit -m "feat: expose recoverable subagent exit errors"`

### Task 3: Living Specification and Patch Verification

**Files:**
- Modify: `docs/specs/subagent-dispatch.md` — merge accepted override and child-error behavior into the canonical current contract.
- Add: `docs/plans/2026-08-27-subagent-override-diagnostics.md` — retain the reviewed implementation and verification contract.

**Spec requirement:** Delivery Gates and every modified requirement after Tasks 1 and 2 pass.

**Interface:**
- The living spec keeps its existing requirement organization.
- The task validation, override, JSON collection, and content-envelope requirements describe the accepted behavior as current state.
- The feature delta remains in `docs/design/2026-08-27-subagent-override-diagnostics-spec.md` for traceability.

**Behavior:**
- The living spec contains every accepted modified requirement and scenario without copying feature-delta headings.
- The full extension test, type, lint, format, and installer checks pass before patch generation.
- The generated patch applies cleanly to commit `37dbaa972c555236117def9314ab5c857c5d8bd4`.

**Tests must prove:**
- The full pytest suite covers every modified behavior from Tasks 1 and 2.
- The complete base-to-head diff reports no whitespace errors.
- A clean temporary checkout at the base commit accepts the generated patch with `git apply --check`.

**Check:** `PYTHONPATH="$TAU_SITE_PACKAGES" uv run pytest && PYTHONPATH="$TAU_SITE_PACKAGES" uv run mypy && uv run ruff check . && uv run ruff format --check . && cd ../.. && tests/test-install.sh` — expected: all pass. After the final documentation commit, run `git diff --check 37dbaa972c555236117def9314ab5c857c5d8bd4..HEAD` from the repository root.

- [ ] Merge the feature-spec delta into the living spec.
- [ ] Run complete verification.
- [ ] Commit from `extensions/superpowers-subagent`: `git -C ../.. add docs/specs/subagent-dispatch.md docs/design/2026-08-27-subagent-override-diagnostics-proposal.md docs/design/2026-08-27-subagent-override-diagnostics-spec.md docs/plans/2026-08-27-subagent-override-diagnostics.md && git -C ../.. commit -m "docs: sync subagent dispatch diagnostics"`.
- [ ] From the repository root, run `git diff --check 37dbaa972c555236117def9314ab5c857c5d8bd4..HEAD`.
- [ ] Generate the patch from the repository root: `git diff --binary 37dbaa972c555236117def9314ab5c857c5d8bd4..HEAD > /workspace/tau-superpowers-subagent-override-diagnostics.patch`.
- [ ] Create `/home/tau/tau-superpowers/.worktrees/patch-check` as a detached worktree at the base commit.
- [ ] Run `git -C /home/tau/tau-superpowers/.worktrees/patch-check apply --check /workspace/tau-superpowers-subagent-override-diagnostics.patch`.
- [ ] Remove the temporary worktree with `git -C /home/tau/tau-superpowers worktree remove /home/tau/tau-superpowers/.worktrees/patch-check`.
