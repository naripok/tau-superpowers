# Spec: Subagent usage aggregation in the sidebar

## Domain: Subagent Dispatch

### ADDED Requirements

#### Requirement: Session-scoped subagent usage aggregation
The extension SHALL accumulate each child result's reported token usage and cost into session-scoped totals across task calls. Live partial results SHALL update an in-flight snapshot of the current call's children that replaces the call's previous snapshot; each call's final result SHALL be folded into the committed totals exactly once. The displayed totals at any moment SHALL equal the committed totals plus the latest in-flight snapshot. Children whose results report no token usage or cost SHALL contribute nothing, including the run count. The accumulation SHALL reset to zero when the active session rebinds to a new, resumed, or branched session. The aggregation SHALL NOT alter task result content, details, or per-child usage reporting.

##### Scenario: No double counting across live updates
- GIVEN a running call emits multiple live updates whose per-child usage accumulates over the child's messages
- WHEN the call commits its final result
- THEN each child's final usage is included exactly once in the committed totals

##### Scenario: Sequential calls accumulate
- GIVEN two calls complete successfully in the same session
- WHEN the totals are read
- THEN they equal the sum of both calls' child usage and cost

##### Scenario: Zero-usage children
- GIVEN a child never started or reported no token usage or cost
- WHEN the totals are read
- THEN it contributes no tokens, cost, or run count

##### Scenario: Partial usage after timeout
- GIVEN a timed-out child retains partial messages with usage
- WHEN its call commits
- THEN its partial usage is included in the totals

##### Scenario: Session rebind resets
- GIVEN the active session rebinds to a new, resumed, or branched session
- WHEN the totals are read
- THEN they are zero

#### Requirement: Sidebar subagent usage section
In a frontend that shows a sidebar summary, the extension SHALL display the current totals (committed plus in-flight) in a `subagents` section positioned immediately below the `usage` section. The section SHALL be omitted when no child has reported token usage or cost. The section SHALL present accumulated input, output, and cost using the same token and cost formatting as the `usage` section, and SHALL show a cost value only when at least one child reported a non-zero cost. Whenever the sidebar summary is rebuilt, the section SHALL reflect the latest committed or in-flight totals.

##### Scenario: Rebuild shows the section
- GIVEN a task call with child usage completed
- WHEN the sidebar summary is rebuilt
- THEN a `subagents` section appears directly below the `usage` section
- AND it shows the accumulated token and cost totals

##### Scenario: Empty totals hide the section
- GIVEN no child has reported token usage or cost
- WHEN the sidebar summary is rebuilt
- THEN no `subagents` section appears

##### Scenario: Cost omitted when unreported
- GIVEN children reported token usage but no cost
- WHEN the `subagents` section renders
- THEN token totals remain visible and no cost value appears

#### Requirement: Unavailable sidebar display degrades safely
The display of the `subagents` section SHALL fail safe: when the running frontend shows no sidebar or lacks the sidebar-summary integration point the display relies on, the extension SHALL skip the display without raising, and the task tool, its results, and the usage aggregation SHALL remain fully functional.

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

### No Behavioral Changes

Task result content, details, per-child usage fields, and the tool's portable rendering are unchanged.
