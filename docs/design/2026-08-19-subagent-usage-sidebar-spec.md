# Spec: Subagent usage aggregation in the sidebar

## Domain: Subagent Dispatch

### ADDED Requirements

#### Requirement: Session-scoped subagent usage aggregation
The extension SHALL accumulate each child result's reported token usage and cost into session-scoped totals across task calls. Live partial results SHALL update an in-flight snapshot of the current call's children that replaces the call's previous snapshot. Committing a call's final result SHALL fold it into the committed totals exactly once and SHALL clear that call's in-flight snapshot. A call that ends without a final result being committed SHALL discard that call's in-flight snapshot. The displayed totals at any moment SHALL equal the committed totals plus the latest in-flight snapshot. A run SHALL be a child result that reports non-zero token usage or cost. Children whose results report no token usage or cost SHALL contribute nothing, including the run count. The accumulation SHALL reset to zero when the active session rebinds to a new, resumed, or branched session. The aggregation SHALL NOT alter task result content, details, per-child usage reporting, or the tool's portable rendering.

##### Scenario: No double counting across live updates
- GIVEN a running call emits multiple live updates whose per-child usage accumulates over the child's messages
- WHEN the call commits its final result
- THEN each child's final usage is included exactly once in the committed totals

##### Scenario: Snapshot cleared on commit
- GIVEN a call has committed and no later call has started
- WHEN the displayed totals are read
- THEN they equal the committed totals with no contribution from the committed call's snapshot

##### Scenario: Snapshot discarded without commit
- GIVEN a call is aborted before its final result is committed
- WHEN the displayed totals are read before any later call emits
- THEN they equal the committed totals alone

##### Scenario: Sequential calls accumulate
- GIVEN two calls complete successfully in the same session
- WHEN the totals are read
- THEN they equal the sum of both calls' child usage and cost

##### Scenario: Zero-usage children
- GIVEN a child never started or reported no token usage or cost
- WHEN the totals are read
- THEN it contributes no tokens, cost, or run count

##### Scenario: Partial usage on process failure
- GIVEN a child that timed out, was cancelled, or failed its protocol retains partial messages with usage
- WHEN its call commits
- THEN its partial usage is included in the totals

##### Scenario: Session rebind resets
- GIVEN the active session rebinds to a new, resumed, or branched session
- WHEN the totals are read
- THEN they are zero

##### Scenario: Aggregation leaves results unchanged
- GIVEN a task call completes while aggregation is active
- WHEN the task result, its details, and its per-child usage fields are inspected
- THEN they are identical to the same call without aggregation

#### Requirement: Sidebar subagent usage section
In a frontend that shows a sidebar summary, the extension SHALL display the current totals (committed plus in-flight) in a `subagents` section positioned immediately below the `usage` section. The section SHALL be omitted when no child has reported non-zero token usage or cost. When the summary contains no `usage` section, the `subagents` section SHALL NOT be injected. The section SHALL present the number of runs and the accumulated input, output, and cost using the same token and cost formatting as the `usage` section, and SHALL show a cost value only when at least one child reported a non-zero cost. The section SHALL NOT appear in the narrow-layout session summary. Whenever the sidebar summary is rebuilt, the section SHALL reflect the latest committed or in-flight totals.

##### Scenario: Rebuild shows the section
- GIVEN a task call with child usage completed
- WHEN the sidebar summary is rebuilt
- THEN a `subagents` section appears directly below the `usage` section
- AND it shows the run count and accumulated token and cost totals

##### Scenario: In-flight totals
- GIVEN a call is in progress and at least one child has emitted usage
- WHEN the sidebar summary is rebuilt
- THEN the section shows the committed totals plus that child's latest cumulative usage

##### Scenario: Empty totals hide the section
- GIVEN no child has reported token usage or cost
- WHEN the sidebar summary is rebuilt
- THEN no `subagents` section appears

##### Scenario: Cost omitted when unreported
- GIVEN children reported token usage but no cost
- WHEN the `subagents` section renders
- THEN the run count and token totals remain visible and no cost value appears

##### Scenario: Narrow layout omits the section
- GIVEN the frontend renders the narrow-layout session summary
- WHEN that summary is built
- THEN no `subagents` section appears

#### Requirement: Unavailable sidebar display degrades safely
The display of the `subagents` section SHALL fail safe: when the running frontend shows no sidebar, lacks the sidebar-summary integration point the display relies on, or the display path fails while a summary is being built, the extension SHALL skip or abandon the display without raising, and the task tool, its results, and the usage aggregation SHALL remain fully functional.

##### Scenario: Print mode
- GIVEN a session runs without a sidebar frontend
- WHEN a task call completes
- THEN the aggregation still records totals
- AND the display path raises no error

##### Scenario: Missing integration point
- GIVEN the sidebar-summary integration point is unavailable
- WHEN the extension loads
- THEN the display is skipped
- AND task dispatch and aggregation continue unaffected

##### Scenario: Display failure during rebuild
- GIVEN the display path fails while a sidebar summary is being built
- WHEN the summary build completes
- THEN the summary remains the normal sidebar summary
- AND no error propagates to the frontend or the task tool

### No Behavioral Changes

Task result content, details, per-child usage fields, and the tool's portable rendering SHALL NOT change as a result of this feature; the aggregation is additive and observational.
