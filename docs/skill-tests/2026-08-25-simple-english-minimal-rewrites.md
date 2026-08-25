# Skill Test: Minimal Simple-English Rewrites

## Test method

Each trial used an isolated `read-only` child. Baseline trials did not include the simple-english skill. Candidate trials required a complete read of the candidate skill before the same scenario prompt. Each pair inherited the same parent provider, model, and reasoning effort.

## RED baseline

### `test_finite_clause_avoids_unnecessary_split`

**Mode:** Pragmatic

**Context:** A rephraser updates headings. In this passage, “the rephraser” names that component.

**Source:** Heading rewrites frequently change the meaning by renaming named concepts, frameworks, and terms of art.

**Result:**

> The rephraser often changes a heading’s meaning by renaming established concepts, frameworks, and technical terms.
>
> **Status: DONE**

**Assessment:** FAIL. The result keeps a verbal `-ing` form. It also replaces “named concepts” and “terms of art” with different terms.

### `test_main_assertion_keeps_related_explanation`

**Mode:** Pragmatic

**Source:** The cache rejects duplicate requests because it stores each request key for ten minutes.

**Result:**

> The cache rejects duplicate requests by retaining each request key for ten minutes.
>
> **Status: DONE**

**Assessment:** FAIL. The result changes the explicit cause to a method and adds a verbal `-ing` form.

### `test_required_split_keeps_causal_connection`

**Mode:** Pragmatic

**Source:** The deployment controller delays the release because it compares the requested image digest with the approved digest before it sends the update to every production cluster.

**Result:**

> The deployment controller verifies that the requested image digest matches the approved digest before deploying the update to all production clusters.
>
> **Status: DONE**

**Assessment:** FAIL. The 26-word source remains one sentence. The result removes the release delay, changes comparison to verification, and uses a verbal `-ing` form.

### `test_established_actor_name_is_not_replaced`

**Mode:** Strict

**Context:** The heading rephraser performs this step.

**Source:** During this step, named concepts, frameworks, and terms of art are renamed.

**Result:**

> In this step, the heading rephraser changes the names of concepts, frameworks, and technical terms.
>
> **Status: DONE**

**Assessment:** PASS for actor naming. The result uses the established actor name and invents no alternative actor name. It changes “terms of art” to “technical terms,” which the broader fidelity requirement rejects.

## RED conclusion

Three named trials fail before the skill change. The failures show unnecessary form changes, changed logical relationships, omitted claims, and replaced terminology.

## REFACTOR trial

The first candidate did not reliably split the 26-word scenario.

**First result:**

> The deployment controller delays the release because it compares the requested and approved image digests before it updates every production cluster.
>
> **Status: DONE**

**Assessment:** FAIL. The result changes the object of “sends” from “the update” to “every production cluster.” The skill now requires preservation of each source component and its semantic role.

A second trial returned the 26-word source unchanged. The split procedure used “split only if,” which stated permission instead of an obligation. The final procedure gives a direct split command for an over-limit sentence.

## Final GREEN results

### `test_finite_clause_avoids_unnecessary_split`

> Heading rewrites frequently change the meaning because they rename named concepts, frameworks, and terms of art.
>
> **Status: DONE**

**Assessment:** PASS. The result uses one sentence and a finite clause. It preserves the cause and established terms without an added claim.

### `test_main_assertion_keeps_related_explanation`

> The cache rejects duplicate requests because it stores each request key for ten minutes.
>
> **Status: DONE**

**Assessment:** PASS. The result keeps one sentence and preserves the explicit cause.

### `test_required_split_keeps_causal_connection`

> The deployment controller compares the requested image digest with the approved digest before it sends the update to every production cluster. As a result, it delays the release.
>
> **Status: DONE**

**Assessment:** PASS. The result splits the 26-word source. It uses “before” and “as a result” to preserve the temporal and causal relationships.

### `test_established_actor_name_is_not_replaced`

> During this step, the heading rephraser renames named concepts, frameworks, and terms of art.
>
> **Status: DONE**

**Assessment:** PASS. The result uses the established actor name and preserves the established terms.

## GREEN conclusion

All four final candidate trials pass their named expectations.
