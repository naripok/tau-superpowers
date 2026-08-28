# Subagent Cost Estimation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use subagent-driven-development (recommended) or executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Price each subagent message from Tau's provider catalog and show the estimated cost in the sidebar `subagents` section and the rendered usage lines.

**Architecture:** The extension estimates cost per accepted child assistant message at JSONL collection time, where per-request token counts are exact. A guarded seam module wraps Tau's own response estimator. Reported cost and estimates stay separate in the child usage model; the tracker totals combine them for display, and the sidebar plus the rendered usage lines show the combined amount with an estimate mark.

**Tech Stack:** Python 3.14, pytest, pytest-asyncio, ruff, mypy strict. The extension runs inside Tau and imports `tau_agent` and `tau_coding`.

**Standards:** Apply the shared code standards in every task: DRY, minimal implementation (YAGNI), low cyclomatic complexity, type safety, no unnecessary abstractions or fallbacks, no hacks or workarounds, informative docstrings, documentation of current state only, writing-developer-facing-text prose.

**Feature spec:** `docs/design/2026-08-27-subagent-cost-estimation-spec.md` (the behavioral contract)

---

## Commands

Run every command from the extension directory in the worktree. The virtualenv lives in the main checkout because worktrees do not copy it. `PYTHONPATH` exposes the Tau install for tests and mypy.

```bash
cd /workspace/.worktrees/subagent-cost-estimation/extensions/superpowers-subagent
PY=/workspace/extensions/superpowers-subagent/.venv/bin/python
export PYTHONPATH=/opt/tau/lib/python3.14/site-packages
$PY -m pytest -q                            # full suite; baseline is 212 passed
$PY -m pytest tests/test_costing.py -q      # one file
$PY -m ruff check .                         # lint; baseline is clean
$PY -m mypy                                 # strict, files=superpowers_subagent; baseline is clean
```

`tests/conftest.py` loads the package as `superpowers_subagent`, so tests import `from superpowers_subagent...` directly.

### Test fixture facts

- `AssistantMessage` and `Usage` come from `tau_agent.messages`. Construct directly: `AssistantMessage(provider="prov-a", model="model-a", usage=Usage(input=100, output=10, cache_read=5, cache_write=3, cache_write_1h=1234))`. Every field has a default.
- For `_process_json_line` tests, build raw lines as `json.dumps({"type": "message_end", "message": {...}}).encode("utf-8")`. The message dict uses camelCase aliases: `"cacheRead"`, `"cacheWrite"`, `"cacheWrite1H"` (capital `H`), `"totalTokens"`, and `"cost": {"input": ..., "output": ..., "cacheRead": ..., "cacheWrite": ..., "total": ...}`. The wire model forbids unknown keys, so a misspelled alias drops the message as malformed.
- `ChildResult(agent=..., agent_source="bundled", task="work", cwd="/tmp")` needs only those four arguments; the rest defaults.
- `tests/test_usage.py` has a `_child(...)` fixture builder that the tracker tests extend. `tests/test_sidebar.py` has its own `_child(...)` builder without cost provenance; Task 5 extends it too.
- `tests/test_sidebar.py` builds sidebar content through the injection seam and extracts section text with a `_section_body(content, title)` helper.
- The provider catalog in this Tau build prices 14 `anthropic` models; `claude-fable-5` has rates `input 10.0, output 50.0, cacheRead 1.0, cacheWrite 12.5, cacheWrite1h 20.0` per million tokens. Tiered pricing exists only on `MiniMax-M3` (`minimax`, `minimax-cn`): threshold 512000, input `0.3` below and at the threshold, `0.6` above it.

---

### Task 1: Guarded estimator seam

**Files:**
- Create: `superpowers_subagent/costing.py` — prices one assistant message through Tau's estimator, guarded.
- Test: `tests/test_costing.py`

**Spec requirement:** ADDED "Catalog-based subagent cost estimation" — scenarios `Priced message`, `One-hour cache-write pricing split`, `Estimator unavailable`.

**Interface:**
- `estimated_message_cost(message: AssistantMessage) -> float | None` — returns the catalog estimate in USD for one accepted child assistant message. It imports `tau_coding.session_usage.estimated_request_cost` lazily inside the call and forwards `provider=message.provider`, `model=message.model`, `fresh=message.usage.input`, `cached=message.usage.cache_read`, `cache_write=message.usage.cache_write`, `cache_write_1h=message.usage.cache_write_1h or 0`, `output=message.usage.output`. It returns the estimator's return value. It returns `None` when the import fails, when the estimator raises, or when the estimator returns `None`. It never raises.

**Behavior:**
- A message whose provider and model exist in the built-in catalog gets a positive float.
- A message on an unknown provider or model gets `None`, because the estimator returns `None` for missing catalog entries.
- A missing or broken Tau seam degrades to `None`; the caller decides what that means.
- The one-hour cache-write count reaches the estimator as its own argument, not folded into `cache_write`.

**Tests must prove:**
- `test_passthrough_returns_estimator_value_and_forwards_message_values` — a monkeypatched `tau_coding.session_usage.estimated_request_cost` recorder returning `0.5` yields `0.5`, and the recorder received the message's provider, model, and all five token values with `cache_write_1h=1234`.
- `test_none_cache_write_1h_forwards_zero` — a message with `cache_write_1h=None` forwards `cache_write_1h=0`.
- `test_missing_seam_returns_none` — with `sys.modules["tau_coding.session_usage"]` set to `None`, the call returns `None`.
- `test_raising_seam_returns_none` — a recorder that raises yields `None`.
- `test_estimator_none_passes_through` — a recorder returning `None` yields `None`.
- `test_real_catalog_prices_a_costed_model` — the first `anthropic` model with cost metadata prices a small token message to a positive float, proving the real import path works.
- `test_real_catalog_prices_one_hour_cache_writes_at_their_rate` — read the rates of `claude-fable-5` from the catalog at test time. A message with `cache_write=1_000_000`, `cache_write_1h=500_000` prices at the 1-hour rate for half and the 5-minute rate for the rest; the same message with `cache_write_1h=None` prices everything at the 5-minute rate. Assert both amounts with `pytest.approx`, computed from the catalog rates in the test.
- `test_real_catalog_selects_tier_per_request_size` — the tiered models in this catalog are `MiniMax-M3` under the `minimax` provider (also `minimax-cn`), with a 512000-token threshold and input rates rising from the lower to the higher tier above it. Read the model's `cost_tiers` from the catalog at test time. A message sized at the tier threshold prices at the lower-tier input rate; one token more prices at the higher-tier rate. Compute both expectations from the catalog's own tier data.

**Check:** `$PY -m pytest tests/test_costing.py -q && $PY -m ruff check . && $PY -m mypy` — expected: all pass

- [ ] Write the failing tests for the behaviors above. Run them and check that each fails for the expected reason
- [ ] Implement the interface and behavior
- [ ] Run verification (tests, lint, type check)
- [ ] Commit: `git add superpowers_subagent/costing.py tests/test_costing.py && git commit -m "feat: add guarded catalog estimator seam"`

---

### Task 2: Estimated cost on the child usage model

**Files:**
- Modify: `superpowers_subagent/models.py` — `UsageStats` gains the estimate accumulator and its serialization.
- Create: `tests/test_models.py`

**Spec requirement:** ADDED "Catalog-based subagent cost estimation" — scenario `Additive details field`.

**Interface:**
- `UsageStats.estimated_cost: float = 0.0` — the sum of catalog estimates over the child's accepted messages.
- `UsageStats.catalog_priced: bool = False` — `True` when at least one accepted message was priced from the catalog. This field is internal provenance and MUST NOT appear in `to_dict()`.
- `UsageStats.to_dict()` — before → after: the returned dict gains one key, `"estimatedCost": self.estimated_cost`, placed after `"cost"`. Every existing key and value stays identical. Task 4 consumes `catalog_priced`; details consumers never see it.

**Behavior:**
- A default `UsageStats` serializes `"estimatedCost": 0.0`.
- A child result's details carry the field through `ChildResult.to_dict()` because it embeds `usage.to_dict()`.
- The details schema version stays `2`; the field is additive.

**Tests must prove:**
- `test_usage_stats_to_dict_adds_estimated_cost` — a populated `UsageStats` serializes all seven existing keys with unchanged values plus `estimatedCost`.
- `test_usage_stats_catalog_priced_is_not_serialized` — `catalog_priced=True` does not appear in the dict.
- `test_default_usage_stats_serializes_zero_estimated_cost` — defaults serialize `estimatedCost: 0.0`.
- `test_child_result_to_dict_carries_estimated_cost` — a `ChildResult` details dict exposes `usage.estimatedCost`.

**Check:** `$PY -m pytest tests/test_models.py -q && $PY -m ruff check . && $PY -m mypy` — expected: all pass

- [ ] Write the failing tests for the behaviors above. Run them and check that each fails for the expected reason
- [ ] Implement the interface and behavior
- [ ] Run verification (tests, lint, type check)
- [ ] Commit: `git add superpowers_subagent/models.py tests/test_models.py && git commit -m "feat: add estimated cost and catalog pricing fields to child usage"`

---

### Task 3: Per-message estimation during collection

**Files:**
- Modify: `superpowers_subagent/runner.py` — `_process_json_line` prices each accepted assistant message.
- Test: `tests/test_runner.py`

**Spec requirement:** ADDED "Catalog-based subagent cost estimation" — scenarios `Priced message`, `Per-request tier selection`, `One-hour cache-write pricing split`, `Priced message ignores reported cost`, `Unpriced provider with reported cost`, `Unpriced provider without reported cost`, `Estimator unavailable`, `Partial usage keeps estimates`.

**Interface:**
- `_process_json_line(raw_line: bytes, result: ChildResult, on_message: ChildUpdate | None) -> None` — behavior change inside the `isinstance(message, AssistantMessage)` branch: after the existing `result.usage.cost += message.usage.cost.total` line, call `estimated_message_cost(message)`. When it returns a float, add it to `result.usage.estimated_cost` and set `result.usage.catalog_priced = True`. When it returns `None`, change nothing.
- Module import: `from .costing import estimated_message_cost` alongside the existing relative imports.
- Existing behavior: reported-cost accumulation stays unconditional for every accepted assistant message. Token accumulation, turn counting, provider/model capture, and the `on_message` callback stay unchanged.

**Behavior:**
- Each message is priced by its own call with its own token breakdown, so two messages accumulate independently. This is what keeps cost-tier selection exact.
- Tests stub the estimator by patching `estimated_message_cost` on the runner module with `monkeypatch.setattr`, because the runner calls its own imported binding of that name.
- A priced message with a non-zero provider-reported cost accumulates both: the estimate into `estimated_cost`, the report into `cost`.
- An unpriced message keeps the reported-cost path exactly as today.
- A raising estimator changes nothing except that no estimate is recorded.
- The fake-tau children in existing tests use providers that are absent from the catalog, so their results gain `estimatedCost: 0.0` and nothing else.

**Tests must prove:**
- `test_priced_message_accumulates_estimated_cost` — a stubbed `estimated_message_cost` returning `0.25` gives `usage.estimated_cost == 0.25`, `usage.catalog_priced is True`, and unchanged token fields.
- `test_each_message_is_priced_with_its_own_usage` — two messages priced `0.25` then `0.5` accumulate to `0.75`, and the second stub call received the second message's own input count. This proves per-message pricing, which is what the tier-selection and one-hour-split scenarios need.
- `test_unpriced_message_with_reported_cost_accumulates_reported_only` — stub returns `None`, message reports `cost.total = 0.3`: `usage.cost == 0.3`, `estimated_cost == 0.0`, `catalog_priced is False`.
- `test_unpriced_message_without_reported_cost_adds_no_cost` — stub returns `None`, no reported cost: both cost fields stay `0.0` while tokens accumulate.
- `test_priced_message_also_accumulates_reported_cost` — stub returns `0.25` and the message reports `cost.total = 0.3`: both fields accumulate.
- The spec scenario `Estimator unavailable` needs no runner-level raising test: Task 1 proves the seam returns `None` when the import fails or the estimator raises, and the `None` tests above prove the collection path keeps tokens and reported cost. A runner-level raising stub simulates a state the seam cannot produce, because the seam never raises.
- `test_timed_out_child_keeps_estimated_cost` — following the fake-child pattern of `test_runner_times_out_and_terminates_child`, a child that emits one assistant message and then exceeds its timeout finalizes with `usage.estimated_cost == 0.5` from a `0.5` stub.
- Update the existing exact-dict assertion in `test_runner_collects_jsonl_usage_stderr_updates_and_cleans_temp_files`: the expected usage dict gains `"estimatedCost": 0.0`. This is the only existing assertion the feature changes.

**Check:** `$PY -m pytest tests/test_runner.py -q && $PY -m ruff check . && $PY -m mypy` — expected: all pass

- [ ] Write the failing tests for the behaviors above. Run them and check that each fails for the expected reason
- [ ] Implement the interface and behavior
- [ ] Run verification (tests, lint, type check)
- [ ] Commit: `git add superpowers_subagent/runner.py tests/test_runner.py && git commit -m "feat: estimate child message cost during jsonl collection"`

---

### Task 4: Session totals for estimated cost and unpriced runs

**Files:**
- Modify: `superpowers_subagent/usage.py` — `SubagentUsageTotals` and `_add_child` carry the estimate share and provenance.
- Test: `tests/test_usage.py`

**Spec requirement:** MODIFIED "Session-scoped subagent usage aggregation" — scenarios `Estimated cost accumulates across calls`, `Unpriced runs are counted`, `Aggregation leaves existing fields unchanged`, plus every retained aggregation scenario.

**Interface:**
- `SubagentUsageTotals` gains four fields after `cost`:
  - `estimated_cost: float = 0.0` — the sum of catalog estimates over contributing runs.
  - `has_determinable_cost: bool = False` — `True` when at least one contributing run is priced from the catalog or carries a non-zero reported cost.
  - `has_catalog_estimate: bool = False` — `True` when at least one contributing run is estimated from catalog rates, regardless of the amount.
  - `unpriced_runs: int = 0` — the count of runs that report non-zero token usage and have no determinable cost.
- The `has_usage` docstring changes from "reported token usage or cost" to "token usage or a determinable cost", because a run can now come from catalog pricing alone.
- New property `SubagentUsageTotals.total_cost -> float` — returns `cost + estimated_cost`.
- `_add_child` behavior: a run is a child with non-zero token usage, a non-zero reported cost, or `catalog_priced` set. A run is determinable when `catalog_priced` is set or `cost > 0`. An unpriced run reports non-zero token usage and is not determinable. The zero-contribution gate extends to `consumed <= 0 and usage.cost <= 0 and not usage.catalog_priced`. Unpriced runs contribute their tokens but no cost. Snapshot, commit, discard, and reset semantics stay unchanged; the new fields fold exactly once per commit like the existing ones.

**Behavior:**
- Reported `cost` keeps its meaning and its existing assertions.
- A run priced from the catalog with a `0.0` estimate is determinable and not unpriced; this is the free-model case the spec pins with "regardless of the estimated amount".
- A run with a non-zero reported cost and no catalog pricing is determinable but not estimated, so it never produces the estimate mark.

**Tests must prove:** extend the `_child` fixture with `estimated_cost: float = 0.0` and `catalog_priced: bool = False` parameters.
- `test_estimated_cost_accumulates_across_calls` — two sequential calls with priced children fold to the summed estimate.
- `test_unpriced_runs_are_counted` — a priced child plus a token-bearing child with no pricing gives `unpriced_runs == 1` and `total_cost` equal to the priced child's cost.
- `test_zero_estimate_priced_child_is_determinable` — `catalog_priced=True, estimated_cost=0.0` counts as a run, sets `has_determinable_cost`, never counts as unpriced, and leaves `has_catalog_estimate` `True`.
- `test_reported_only_child_is_determinable_but_not_estimated` — tokens plus reported cost, no catalog pricing: `has_determinable_cost` `True`, `has_catalog_estimate` `False`, `unpriced_runs == 0`.
- `test_in_flight_snapshot_carries_estimated_cost` — a live update shows the snapshot's estimate before commit.
- `test_reset_clears_estimated_totals` — after `reset()`, all four new fields return to their defaults.
- All existing tracker tests pass unchanged.

**Check:** `$PY -m pytest tests/test_usage.py -q && $PY -m ruff check . && $PY -m mypy` — expected: all pass

- [ ] Write the failing tests for the behaviors above. Run them and check that each fails for the expected reason
- [ ] Implement the interface and behavior
- [ ] Run verification (tests, lint, type check)
- [ ] Commit: `git add superpowers_subagent/usage.py tests/test_usage.py && git commit -m "feat: accumulate estimated cost and unpriced runs in session totals"`

---

### Task 5: Sidebar combined cost with marks

**Files:**
- Modify: `superpowers_subagent/sidebar.py` — `_section_body` renders the combined cost with the estimate and incompleteness marks.
- Test: `tests/test_sidebar.py`

**Spec requirement:** MODIFIED "Sidebar subagent usage section" — scenarios `Rebuild shows the section`, `Estimated cost shown`, `Incomplete cost marked`, `Reported cost with unpriced run`, `Reported-only cost unmarked`, `Cost omitted when undeterminable`.

**Interface:**
- `_section_body(totals, theme, widgets)` — behavior change in the cost segment only. The run label and token counts stay unchanged. The segment rule replaces the current `if totals.cost > 0` gate:
  - When `totals.has_determinable_cost` is `True`, append the separator and the amount `widgets._format_cost(totals.total_cost)`.
  - Prefix `~` when `totals.has_catalog_estimate` is `True`.
  - Suffix `+` when `totals.unpriced_runs > 0`.
  - When `totals.has_determinable_cost` is `False`, append nothing; the line ends after the token counts, as today.

**Behavior:**
- The displayed amount is the sum of reported and estimated cost. Unpriced runs contribute tokens but no amount, so the `+` cannot understate.
- A priced run with a `0.0` estimate renders `~$0.00`.
- The existing comment about the missing estimation tilde is obsolete and goes away; the tilde now marks estimates, matching the `usage` section.

**Tests must prove:** extend the `_child` fixture in `tests/test_sidebar.py` with `estimated_cost: float = 0.0` and `catalog_priced: bool = False` parameters, then assert the exact rendered text of the `subagents` section through the existing content fixtures.
- `test_estimate_shows_tilde_without_plus` — one priced run renders `~` and no `+`.
- `test_estimate_with_unpriced_runs_shows_tilde_and_plus` — a priced run plus a token-bearing unpriced run renders `~$X+`.
- `test_reported_only_with_unpriced_runs_shows_plus_without_tilde`.
- `test_reported_only_without_unpriced_runs_shows_no_marks`.
- `test_undeterminable_cost_shows_no_cost_segment` — token-bearing runs with no pricing render the line without a cost segment.
- `test_zero_estimate_priced_run_shows_tilde_with_zero_amount` — renders `~$0.00`.
- Existing sidebar tests pass unchanged except where they pinned the old cost gate; `test_injection_omits_cost_when_unreported` keeps its name and outcome because unpriced children still render no cost.

**Check:** `$PY -m pytest tests/test_sidebar.py -q && $PY -m ruff check . && $PY -m mypy` — expected: all pass

- [ ] Write the failing tests for the behaviors above. Run them and check that each fails for the expected reason
- [ ] Implement the interface and behavior
- [ ] Run verification (tests, lint, type check)
- [ ] Commit: `git add superpowers_subagent/sidebar.py tests/test_sidebar.py && git commit -m "feat: show combined subagent cost with estimate marks in sidebar"`

---

### Task 6: Rendered usage lines show cost

**Files:**
- Modify: `superpowers_subagent/rendering.py` — `_usage_line` and `_aggregate_usage` render the combined cost with the estimate mark.
- Test: `tests/test_rendering.py`

**Spec requirement:** ADDED "Catalog-based subagent cost estimation" — scenarios `Rendered usage line shows estimated cost`, `Rendered usage line reported-only cost`.

**Interface:**
- `_usage_line(usage, model, reasoning_effort)` — the cost segment changes from `cost` alone to the combined amount: `reported = _positive_number(usage.get("cost"))`, `estimated = _positive_number(usage.get("estimatedCost"))`, total = reported + estimated. When the total is above zero, append the amount with the existing `$X.XXXX` format, prefixed with `~` when `estimated > 0`. When it is zero, append no cost segment. Segment position, token counters, and the model segment stay unchanged. These lines never carry `+`.
- `_aggregate_usage(children)` — the totals dict gains `"estimatedCost"`, summed across children with the same `_positive_number` guard as the other keys. `_usage_line` then renders the mark and the sum; no other change.

**Behavior:**
- Details from Task 2 and Task 3 carry `estimatedCost`, so live and final renders show costs while children run, without dispatcher changes.
- Old details without the key render exactly as today, because `_positive_number` treats a missing key as zero.

**Tests must prove:**
- `test_usage_line_shows_estimated_cost_with_tilde` — `estimatedCost` `0.4231` alone renders `~$0.4231`.
- `test_usage_line_shows_reported_cost_without_tilde` — `cost` `0.2` alone renders `$0.2000`.
- `test_usage_line_combines_reported_and_estimated_cost` — `cost` `0.2` plus `estimatedCost` `0.4231` renders `~$0.6231`.
- `test_usage_line_omits_zero_cost` — both zero or absent renders no cost segment.
- `test_total_line_sums_estimated_cost_with_tilde` — two children with `estimatedCost` `0.1` and `0.3231` produce a `Total:` line containing `~$0.4231`.
- `test_frame_child_sections_show_estimated_cost` — a rendered frame with two priced children shows `~$` in each child section and in the `Total:` line.
- Existing rendering tests pass unchanged: old fixtures without `estimatedCost` render the same strings.

**Check:** `$PY -m pytest tests/test_rendering.py -q && $PY -m pytest -q && $PY -m ruff check . && $PY -m mypy` — expected: all pass, full suite green

- [ ] Write the failing tests for the behaviors above. Run them and check that each fails for the expected reason
- [ ] Implement the interface and behavior
- [ ] Run verification (tests, lint, type check)
- [ ] Commit: `git add superpowers_subagent/rendering.py tests/test_rendering.py && git commit -m "feat: show estimated cost in rendered usage lines"`
