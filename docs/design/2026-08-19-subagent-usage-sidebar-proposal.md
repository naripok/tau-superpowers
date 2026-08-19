# Proposal: Subagent usage aggregation in the sidebar

## Intent

The sidebar's usage section reflects only the parent session's own token spend. Subagents run as separate Tau processes, so their token usage and cost are invisible in the sidebar and must be tracked across the two display surfaces. This change makes the extension aggregate subagent usage and cost itself and display the running totals in the sidebar directly below the session usage stats. No Tau core changes.

## Scope

**In scope:**

- Session-scoped accumulation of child token usage and cost across task calls: live snapshots during a call plus exactly-once per-call commits into committed totals, with no double counting.
- A `subagents` sidebar section positioned immediately below the `usage` section, shown only when subagent runs consumed tokens or reported cost, formatted in the usage section's style.
- Graceful degradation of the display when the sidebar integration point is unavailable (no TUI, or a Tau version without the internal builder seam): aggregation and dispatch continue unaffected.
- Reset of the accumulation when the active session rebinds (new, resumed, or branched session).

**Out of scope:**

- Tau core changes (`SessionStats`, session usage accounting, sidebar rendering).
- Live mid-run sidebar refresh: the section updates whenever the sidebar summary is rebuilt, and the final totals are visible once the task's tool result lands.
- `CompactSessionInfo` (narrow-layout) and print-mode display.
- Changes to the task tool's per-child usage line (it already shows each child's cost), result content, or details.
- Config toggles: the aggregation is always on.

## Approach

The extension keeps a `SubagentUsageTracker`, fed through a new optional observer hook on the dispatcher. Every live `Task` update carries each child's cumulative usage, so the observer replaces an in-flight snapshot of the current call's children; the call's final result is committed once into the session totals (committed + snapshot = displayed totals at any moment). Children with no reported usage or cost contribute nothing, including the run count. Timed-out, cancelled, and protocol-failed children keep their partial usage because it was really consumed. Totals reset when the session rebinds.

For display, Tau 0.3 exposes no public sidebar content extension point. The extension installs a guarded wrapper around the TUI's internal sidebar content builder — the single choke point through which the sidebar widget builds its sections (the host does not capture it by `from-import`, so a module-attribute wrap is effective). The wrapper calls the original builder and, when totals exist, splices a `subagents` section directly after the section titled `usage` (matched by header text, so a future core reordering degrades to no injection rather than a misplaced one). It reuses the builder's own compact-token and cost formatters so the line matches the sibling usage section. Every seam step is guarded: any failure disables only the display. This follows the repo's existing precedent for documented guarded seams (the `tau._runtime` thinking-level seam).

Alternatives considered and rejected:

- **Prompt-adjacent slot widget** (public `set_slot_widget` API): works everywhere but is not in the sidebar.
- **Fusing totals into `session.session_stats`**: requires Tau core changes, ruled out by the user.
- **Monkeypatching `SessionSidebar.update_from_session`**: wrong insertion point (append-only) compared with the content-builder wrap.

## Impact

- `superpowers_subagent/dispatch.py`: optional usage observer on `TaskDispatcher`, invoked on every live update (snapshot) and once per call (commit); no existing constructor or behavior changes.
- New `superpowers_subagent/usage.py`: totals model and session-scoped tracker with reset.
- New `superpowers_subagent/sidebar.py`: guarded installation of the sidebar section.
- `superpowers_subagent/extension.py`: tracker lifecycle, dispatcher wiring, rebind reset via the `session_start` event, sidebar installation.
- `docs/specs/subagent-dispatch.md`: living-spec sync after acceptance (new requirement: subagent usage aggregation and sidebar display).
- Tests: tracker semantics (snapshot/commit/reset/zero-usage), dispatcher observer wiring for all modes, sidebar section placement, hiding, and degradation.
