# Spec: Subagent Cost Estimation

## Domain: subagent-dispatch

Unchanged scenarios of a modified requirement are retained from the living spec. The proposal names superseded scenarios.

### ADDED Requirements

#### Requirement: Catalog-based subagent cost estimation

The extension SHALL estimate a USD cost for each accepted child assistant message from Tau's built-in provider catalog rates, using that message's provider, model, and token usage. Prompt tokens SHALL include fresh, cached, and cache-written tokens, and the message's own request size SHALL select the catalog cost tier. One-hour cache-write tokens SHALL be priced at the catalog's one-hour cache-write rate when the catalog distinguishes one-hour writes. A message is priced from the catalog when the estimator applies catalog rates to it. When the catalog has no entry for the message's provider and model, the extension SHALL use that message's provider-reported cost when it is non-zero. When neither source applies, the message SHALL contribute tokens but no cost. When both sources apply to one message, the child's two cost fields each SHALL accumulate their own contribution. Each child result SHALL carry its accumulated estimated cost as an additive usage field serialized as `estimatedCost`. No existing usage field, token total, status, or result content SHALL change because of estimation. The tool's rendered per-child usage line and `Total:` aggregate line SHALL show the combined reported and estimated cost of the child or of all children when it is above zero. The rendered cost SHALL keep the line's existing cost format and SHALL carry the `~` estimate mark before the amount when any estimated cost contributes to it. These lines SHALL NOT carry the incompleteness mark. When the estimator is unavailable or fails for a message, the extension SHALL skip estimation for that message and continue with reported-cost and token accounting unchanged.

The estimator is imported through a guarded seam. Estimates are API-rate equivalents of the catalog rates, matching the meaning of the parent usage section's estimate marker.

##### Scenario: Priced message

- GIVEN a child assistant message whose provider and model exist in the built-in catalog with rates
- WHEN the runner collects the message
- THEN the child's estimated-cost usage field increases by the catalog price of that message's token breakdown

##### Scenario: Per-request tier selection

- GIVEN a catalog model prices prompt tokens above a size threshold at a different rate
- WHEN a child emits two messages whose prompt sizes fall on opposite sides of the threshold
- THEN each message is priced at its own request's tier

##### Scenario: One-hour cache-write pricing split

- GIVEN a catalog that prices one-hour cache writes above other cache writes
- WHEN the runner collects two messages with equal prompt totals but different one-hour and shorter-write splits
- THEN each message is priced at its own split

##### Scenario: Priced message ignores reported cost

- GIVEN a catalog-priced message that also carries a non-zero provider-reported cost
- WHEN the runner collects the message
- THEN the child's estimated-cost usage field increases by the catalog price of that message's token breakdown
- AND the child's reported-cost usage field increases by the reported amount

##### Scenario: Unpriced provider with reported cost

- GIVEN a message whose provider and model are absent from the catalog
- AND the message carries a non-zero provider-reported cost
- WHEN the runner collects the message
- THEN the child's estimated-cost usage field does not change
- AND the child's reported-cost usage field increases by the reported amount

##### Scenario: Unpriced provider without reported cost

- GIVEN a message whose provider and model are absent from the catalog
- AND the message carries no provider-reported cost
- WHEN the runner collects the message
- THEN the message contributes its tokens to the child's usage
- AND neither cost field changes

##### Scenario: Additive details field

- GIVEN a completed child with estimated cost
- WHEN the task details are inspected
- THEN the child's usage contains the `estimatedCost` field
- AND every previously existing usage field equals the same call without estimation

##### Scenario: Rendered usage line shows estimated cost

- GIVEN two completed children with non-zero token usage whose messages were priced from the catalog
- WHEN the tool result renders
- THEN each per-child usage line shows that child's combined cost with the `~` prefix
- AND the `Total:` aggregate line shows the children's combined cost with the `~` prefix

##### Scenario: Rendered usage line reported-only cost

- GIVEN two completed children whose only cost contribution is provider-reported
- WHEN the tool result renders
- THEN each per-child usage line shows the cost without the `~` prefix
- AND the `Total:` aggregate line shows the cost without the `~` prefix

##### Scenario: Estimator unavailable

- GIVEN the estimator seam is missing or raises for a message
- WHEN the runner collects the message
- THEN the child still reports its token totals and any reported cost
- AND no error propagates to the task result

##### Scenario: Partial usage keeps estimates

- GIVEN a child times out or is cancelled after emitting priced messages
- WHEN its result finalizes
- THEN the accumulated estimated cost for those messages remains on the child result

### MODIFIED Requirements

#### Requirement: Session-scoped subagent usage aggregation

The extension SHALL accumulate each child result's reported token usage, reported cost, and estimated cost into session-scoped totals across task calls. A run SHALL have a determinable cost when at least one of its accepted messages is priced from the catalog or carries a non-zero provider-reported cost. The totals SHALL count an unpriced run: a run that reports non-zero token usage and has no determinable cost. Live partial results SHALL update an in-flight snapshot of the current call's children that replaces the call's previous snapshot. Committing a call's final result SHALL fold it into the committed totals exactly once and SHALL clear that call's in-flight snapshot. A call that ends without a final result being committed SHALL discard that call's in-flight snapshot. The displayed totals at any moment SHALL equal the committed totals plus the latest in-flight snapshot of every active call; concurrent calls SHALL keep separate in-flight snapshots. A run SHALL be a child result that reports non-zero token usage or has a determinable cost. Children whose results report no token usage and have no determinable cost SHALL contribute nothing, including the run count. The accumulation SHALL reset to zero when the active session rebinds to a new, resumed, or branched session. The aggregation SHALL NOT alter task result content, details, statuses, token totals, or any per-child usage field other than the additive estimated-cost field introduced by the estimation requirement, and SHALL NOT alter the tool's portable rendering beyond the rendered cost segment the estimation requirement adds to the per-child usage lines and the `Total:` line.

The dispatcher feeds the tracker as an observer: every live `Task` update replaces the snapshot keyed to that call's tool call id, and each call's final result commits once, so snapshots never double-count even when concurrent task calls share one session.

##### Scenario: Aggregation leaves existing fields unchanged

- GIVEN a task call completes while aggregation and estimation are active
- WHEN the task result, its details, and its per-child usage fields are inspected
- THEN they equal the same call with aggregation and estimation disabled
- AND the additive `estimatedCost` field is the only new usage content

##### Scenario: Estimated cost accumulates across calls

- GIVEN two sequential calls complete with catalog-priced children in the same session
- WHEN the totals are read
- THEN the estimated-cost share equals the sum of both calls' child estimates

##### Scenario: Unpriced runs are counted

- GIVEN a catalog-priced child and a child with token usage but neither catalog rates nor reported cost
- WHEN the totals are read
- THEN the combined cost equals the priced child's cost
- AND the unpriced-run count is one

#### Requirement: Sidebar subagent usage section

In a frontend that shows a sidebar summary, the extension SHALL display the current totals (committed plus in-flight) in a `subagents` section positioned immediately below the `usage` section. The section SHALL be omitted when no child reports non-zero token usage and no child has a determinable cost. When the summary contains no `usage` section, the `subagents` section SHALL NOT be injected. The section SHALL present the number of runs and the accumulated input, output, and cost using the same token and cost formatting as the `usage` section, where input SHALL include cached and cache-written tokens as the `usage` section's input does. The section SHALL show a cost value only when at least one run has a determinable cost. The displayed cost SHALL be the sum of reported and estimated cost. A run is estimated from catalog rates when at least one of its accepted messages is priced from the catalog. The cost SHALL carry the estimate marker when at least one run with a determinable cost is estimated from catalog rates, regardless of the estimated amount, and it SHALL carry the incompleteness marker when at least one run is unpriced. The estimate marker SHALL be the `~` prefix, and the incompleteness marker SHALL be the trailing `+`. A run's tokens and run count SHALL be unaffected by its cost being undeterminable. The section SHALL NOT appear in the narrow-layout session summary. Whenever the sidebar summary is rebuilt, the section SHALL reflect the latest committed or in-flight totals.

Tau 0.3 exposes no public sidebar content extension point (the sidebar summary is built by core from session stats), so the display wraps `tau_coding.tui.widgets._build_sidebar_content`, the one function through which every sidebar summary is constructed, and splices the section below the usage section. The seam is version-guarded: when any expected part is missing or a build fails, the original summary is returned unchanged. Mid-run display updates on the sidebar's normal rebuild cadence; a live per-message refresh of subagent totals is intentionally not provided.

##### Scenario: Rebuild shows the section

- GIVEN a completed call whose children include one with a determinable cost
- WHEN the sidebar summary is rebuilt
- THEN a `subagents` section appears directly below the `usage` section
- AND it shows the run count and accumulated token and cost totals

##### Scenario: Estimated cost shown

- GIVEN at least one run's cost is estimated from catalog rates and no run is unpriced
- WHEN the `subagents` section renders
- THEN the cost appears with the `~` prefix and without the trailing `+`

##### Scenario: Incomplete cost marked

- GIVEN at least one run's cost is estimated from catalog rates and at least one run is unpriced
- WHEN the `subagents` section renders
- THEN the cost appears with the `~` prefix and the trailing `+`
- AND the displayed cost equals the sum of the reported and estimated cost of the runs with a determinable cost

##### Scenario: Reported cost with unpriced run

- GIVEN every determinable cost is provider-reported and at least one run is unpriced
- WHEN the `subagents` section renders
- THEN the cost appears with the trailing `+` and without the `~` prefix

##### Scenario: Reported-only cost unmarked

- GIVEN every determinable cost is provider-reported and no run is unpriced
- WHEN the `subagents` section renders
- THEN the cost appears without the `~` prefix and without the trailing `+`

##### Scenario: Cost omitted when undeterminable

- GIVEN children reported token usage but no run has a determinable cost
- WHEN the `subagents` section renders
- THEN the run count and token totals remain visible and no cost value appears
