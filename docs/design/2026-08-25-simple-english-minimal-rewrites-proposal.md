# Proposal: Minimal Simple-English Rewrites

## Intent

The simple-english skill can split a clear sentence even when a smaller repair is sufficient. A split can weaken an explicit logical relationship or add information that is not in the source. Rewrites must improve readability without unnecessary structural or semantic changes.

## Scope

**In scope:**

- Define an order that starts with the smallest sufficient repair.
- Make sentence splitting a later repair instead of the default repair.
- Clarify that one main assertion can include a closely related cause, condition, method, purpose, contrast, or result.
- Require an explicit logical connection after a split.
- Give factual fidelity and established terminology priority over structural simplification.
- Test rewrites that need no split and rewrites that need a split.

**Out of scope:**

- Change sentence-length limits.
- Change strict vocabulary rules.
- Change procedural classification or safety instructions.
- Add automated STE compliance checks.

## Approach

Update `skills/simple-english/SKILL.md` with a least-change repair order and sentence-splitting safeguards. Put the core priority near the rewrite procedure. Clarify descriptive Rule 6.1 and add the safeguards to the self-check. Include one focused before-and-after example.

Test the behavior with isolated subagents. First, record rewrite behavior without the candidate changes. Then give the same scenarios to subagents with the candidate skill. The successful rewrites must preserve the source claims, terminology, and logical relationships.

## Impact

The change affects rewrites produced under the simple-english skill in pragmatic and strict modes. It changes guidance only. It does not change code, commands, identifiers, or the underlying STE sentence limits.
