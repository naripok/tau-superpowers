# Context: Subagent cost in the sidebar

This document explains the current system and the planned change. It is background for the proposal and the spec in this folder. Read it before the other two documents.

## What you have today

### The sidebar

The Tau TUI sidebar shows a `usage` section. It lists the current session's token counts and one cost line. The cost line carries a `~` mark, for example `~$3.10`. The `~` means the number is an estimate, not a bill.

Our addon adds a `subagents` section directly below the `usage` section. Today it shows a run count and token counts, for example `2 runs · 45k in, 12k out`. It shows no cost.

### How subagents run

The `task` tool starts each subagent as a separate Tau process. Each subagent writes its own session file. Tau builds the sidebar numbers from the current session only. It does not read the subagent session files. So the `usage` section's cost covers the parent conversation alone. Subagent spend is invisible in Tau's own numbers.

### Where cost numbers come from

A model response carries three kinds of cost data.

- Token counts: prompt tokens, output tokens, cache reads, and cache writes. Providers always report these.
- A provider-reported cost: a billed dollar amount on the response. Tau never fills this field, and nothing in this Tau build reads a cost from provider responses. The field is always zero.
- An estimate: Tau prices each response itself. It uses its built-in price list, called the provider catalog, and the response's token counts. The sidebar's `~` line and the HTML export dashboard show this estimate.

### Why the subagents section shows no cost

The addon collects each subagent's token counts from its message stream. It also collects the provider-reported cost field. The section shows cost only when the cost total is above zero. Because that field is always zero, the cost never appears. The addon does not estimate cost today.

## What the design changes

### The addon will estimate cost itself

The addon will price each subagent response with the same provider catalog that Tau uses. It will call Tau's own estimator function, the same one the export dashboard uses. The import is guarded. If Tau moves or removes that function, the addon skips estimation and everything else keeps working.

Estimation happens per response, not per child total. Cost tiers depend on one request's prompt size, so per-response pricing is exact. One-hour cache writes get their own price when the catalog has one.

### Two cost totals stay separate

The provider-reported cost keeps its current field. The estimate goes into a new field named `estimatedCost` in the task details. No existing field changes. The addon combines the two totals only for display.

### The sidebar line will show cost

The section will show the combined cost next to the token counts. The examples below show the three shapes.

```text
2 runs · 45k in, 12k out · ~$1.23
3 runs · 60k in, 15k out · ~$1.23+
2 runs · 30k in, 8k out
```

- The `~` mark means the number is an estimate, matching the `usage` section's mark.
- The trailing `+` means the cost of at least one run is unknown, so the real total is higher.
- No cost appears when no run's cost can be determined. The section then behaves as today.

### The per-child usage lines will show cost too

Each child has a card in the transcript, inside the tool result row. The last line of that card is the usage line. Today it shows turns, token counts, and the model name. It never shows cost, because its cost source is the always-zero reported field. After the change, it shows the child's combined cost with the `~` mark, for example:

```text
3 turns ↑45k ↓12k R30k W1k ~$0.4231 claude-sonnet-4-5
```

The line does not use the `+` mark. A usage line without cost already signals an unknown cost for that child. The `+` mark stays on the sidebar's session total.

With several children, the tool result shows one more line named `Total:` below the cards. It sums the children's usage and gains the cost the same way.

The tool row re-renders after every message a child accepts. The usage line appears with the child's first answer and updates while the child runs. It does not wait for the child to finish. It stays visible after the child finishes, in the collapsed and the expanded view.

### Today and after the change

| Item | Today | After the change |
| --- | --- | --- |
| `usage` section cost | Estimate, parent session only | Unchanged |
| Subagent tokens in the sidebar | Shown | Unchanged |
| Subagent cost in the sidebar | Never shown | `~` estimate from the catalog |
| Per-child usage line | Token counts only | Token counts plus `~` estimated cost |
| Task details | A `cost` field, always zero | The `cost` field plus a new `estimatedCost` field |
| Tau core | No subagent cost support | No change |

### What stays the same

Token totals, statuses, result text, and every existing usage field stay unchanged. The narrow-layout summary and print mode stay unchanged. Tau core stays unchanged. The addon owns all the new code.

## Known limits

- Estimates are API-rate equivalents. With an OAuth subscription, the real charge does not follow per-token API billing. The `usage` section has the same limit, and the `~` mark applies to both.
- The estimate uses Tau's built-in catalog. A provider configured with custom rates is not priced. Its runs show as unknown cost through the `+` mark.
- A subagent on a model that is missing from the catalog also shows as unknown cost.

## Where the work stands

- The proposal and the spec are on the branch `subagent-cost-estimation`, in the worktree `.worktrees/subagent-cost-estimation/`.
- A reviewer agent approved the spec after six review rounds.
- The next steps are your approval, a commit of the two artifacts, and an implementation plan.
