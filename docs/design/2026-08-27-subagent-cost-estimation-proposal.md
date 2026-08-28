# Proposal: Catalog-based subagent cost estimation in the sidebar

## Intent

The `subagents` sidebar section shows run counts and token totals but no cost. Subagent results carry a provider-reported cost field, and the section shows that value when it is non-zero. Tau never fills this field itself, and no backend in this Tau build reports billing through it, so children always report zero cost. The parent's usage section shows an estimated cost, so the sidebar understates a session's spend by exactly the subagent share. This change prices subagent tokens with the same provider catalog Tau uses and shows the estimate next to the token totals. No Tau core changes.

## Scope

**In scope:**

- Per-message estimation of child usage cost from Tau's built-in provider catalog rates, computed at collection time from each assistant message's provider, model, and token breakdown.
- Per-message fallback to the provider-reported cost when the catalog has no entry for the child's provider and model.
- Accumulation of estimated cost into the session totals alongside reported cost, plus an unpriced-run count for runs whose cost cannot be determined.
- An additive child-result usage field carrying the estimated cost; every existing usage field stays unchanged.
- Sidebar `subagents` section display of the combined cost, with the usage section's estimate marker and an incompleteness marker.
- Rendered per-child usage lines and the `Total:` aggregate line showing the combined cost with the estimate mark.
- Guarded degradation: a missing estimator, missing rates, or a failure never blocks dispatch or aggregation.

**Out of scope:**

- Tau core changes (provider catalog, session stats, sidebar rendering, usage export).
- Rendering changes beyond the cost segment of the per-child usage lines and the `Total:` aggregate line.
- Changes to token totals, statuses, result content, or any existing usage field.
- Config toggles: estimation is always on when rates exist.
- The narrow-layout session summary and print mode; the sidebar display rules do not change there.

## Approach

Estimate at collection time, one call per accepted assistant message, where the per-request token counts are exact. Tau's cost tiers key on a single request's prompt tokens. Estimating from summed child totals distorts tier selection and loses the 1-hour cache-write split. The extension calls Tau's own response estimator, the same function the usage export dashboard uses, with each message's provider, model, fresh, cached, cache-written, and output tokens; the message's 1-hour cache-write count is passed through. That estimator prices from the built-in provider catalog. When the catalog has no entry for the message's provider and model, the runner falls back to that message's provider-reported cost when it is non-zero, matching the export dashboard's ordering. When neither source yields a cost, the message contributes tokens but no cost. The estimator import is guarded: if Tau moves or removes it, estimation is skipped and nothing else changes. This follows the repo's guarded-seam precedent.

Provenance stays split. Reported cost keeps the existing usage field; estimates accumulate into a new additive usage field. The tracker totals add the estimated share and count unpriced runs, where a run is unpriced when it reports usage but contributes no cost. The sidebar section shows the combined total. The estimate marker (`~`) appears when any estimated cost contributes, and a trailing `+` appears when at least one run is unpriced, so the figure cannot silently understate. With no determinable cost the section behaves as today and shows tokens only. Estimates are API-rate equivalents; the tilde matches the parent usage section, whose estimates carry the same meaning.

Rendered usage lines show cost too. Each per-child usage line shows that child's combined cost when it is above zero. The `Total:` aggregate line shows the sum across children. Both lines carry the `~` mark when estimated cost contributes, in their existing cost format. They carry no incompleteness mark: a line without cost already signals an unknown cost, and the sidebar carries the session-level mark. The tool row already re-renders after every accepted child message, so costs appear while children run, not only after they finish.

Alternatives considered and rejected:

- **Estimating from summed per-child totals in the tracker**: simpler, but cost tiers key on per-request prompt tokens; sums distort tier selection and lose the 1-hour cache-write split.
- **Reusing the parent session's pricing resolver** so custom provider rate configurations are priced: that resolver is a private session seam, and the built-in catalog is the same source the export dashboard uses; custom-rate providers degrade to the reported-cost fallback and the incompleteness marker.
- **Folding estimates into the existing reported-cost field with a flag**: loses the reported-versus-estimated split in details and changes per-child rendering semantics.
- **A Tau core change to price child sessions natively**: previously ruled out; the extension owns subagent aggregation.

## Impact

- `superpowers_subagent/models.py`: additive `estimated_cost` on the child usage model, serialized as `estimatedCost`; existing fields and the details schema version stay unchanged.
- `superpowers_subagent/runner.py`: per-message estimation with the reported-cost fallback at the existing usage accumulation point; the message's 1-hour cache-write count feeds the estimator; guarded estimator import.
- `superpowers_subagent/usage.py`: totals gain the estimated share and the unpriced-run count; the zero-usage gates include the new field.
- `superpowers_subagent/sidebar.py`: combined-cost display with the estimate and incompleteness markers.
- `superpowers_subagent/rendering.py`: the per-child usage line and the `Total:` aggregate line gain the combined cost with the estimate mark, read from the additive usage field.
- `docs/specs/subagent-dispatch.md`: living-spec sync after acceptance (added estimation requirement; modified aggregation and sidebar requirements). The sync SHALL treat the old `Cost omitted when unreported` sidebar scenario and the old `Aggregation leaves results unchanged` scenario as superseded by their renamed versions in the spec, SHALL take the corrected `Rebuild shows the section` scenario from the spec so the conditional cost display cannot overstate tokens-only calls, and SHALL align the retained `Zero-usage children` and `Empty totals hide the section` GIVENs with the modified determinable-cost gate.
- Tests: per-message estimation and fallback, per-request tier selection, the additive details field, totals accumulation with unpriced-run counting, the sidebar markers, the rendered usage-line cost with its mark, and degradation without the estimator.
