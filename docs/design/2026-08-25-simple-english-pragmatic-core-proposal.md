# Proposal: Pragmatic Core for the simple-english Skill

## Intent

The simple-english skill still carries ASD-STE100 dictionary machinery — a 53-rule catalog and vocabulary-discipline tables (146 + 70 of 336 lines, 64% of the document) — even after strict mode was dropped. The skill was not reduced; only the word "strict" was removed.

The goal is a genuinely pragmatic writing standard: unambiguous, easy-to-read technical prose, with no dictionary adherence, no STE compliance claims, and a real reduction in size (the user's success criterion). The standalone least-change procedure section disappears; its intent lives in the rules instead.

## Scope

**In scope:**

- Rewrite `skills/simple-english/SKILL.md` around a lean clarity core.
- Keep: procedural/descriptive classification; 20/25-word limits; one instruction per sentence; imperative with conditions first; active voice; simple tenses; no `-ing` verb forms; no contractions; keep "that"; no semicolons; vertical-list mechanics; article placement; pick-one-and-keep-it terminology consistency; banned-modal guidance (`should` → `must`, `may/might/could` → `can`); plain substitutes that need no dictionary; identifier/quoted-text word-count mechanics; smallest-sufficient-repair rules; untouchables; the full example; a compressed self-check; exactly one line naming ASD-STE100 as the inspiration, so the lineage and a further-guidance pointer survive.
- Remove: compliance claims and dictionary authority (the ASD dictionary is not presented as authoritative); "STE", "Simplified Technical English", "ASD-STE100" as activation triggers; dictionary-derived content (approved-words rules 1.1–1.14, part-of-speech rulings, recurring-errors table, dictionary-rulings table, consistency-pass dictionary rows); the standalone `## Least-Change Rewrite Procedure` section; the `Limits` compliance disclaimer. The ASD-STE100 attribution appears only in that single kept line.
- Renumber the surviving rules into one lean catalog of 12–22 rules with no gaps; update every cross-reference (self-check citations, prose mentions, frontmatter).
- Fold the reusable content of `references/checklist.md` and `references/use-cases.md` into SKILL.md; delete both reference files. The skill becomes self-contained in one document.
- Keep the skill name `simple-english` and its directory; rewrite the frontmatter description to the practical standard.
- Size gate: SKILL.md under 14,000 characters (from ~23,100).

**Out of scope:**

- The 20/25 word limits and their supporting mechanics.
- Historical records: `docs/plans/2026-08-25-simple-english-minimal-rewrites.md`, `docs/skill-tests/2026-08-25-simple-english-minimal-rewrites.md`, `docs/design/2026-08-25-simple-english-minimal-rewrites-spec.md`.
- Renaming the skill file or touching extension/Tau wiring.
- Other skills in the repo.

## Approach

Selected: **Approach A — lean clarity core.** One self-contained document, roughly half the current size, no STE identity except a single "inspired by ASD-STE100" attribution line. Alternatives considered: B (surgical trim keeping the 53-rule numbering) — rejected: keeps the STE numbering smell and saves far less; C (rename the skill) — rejected by user, the name stays.

Implementation: a single subagent (provider `openai-codex`, model `gpt-5.6-sol`, reasoning effort `xhigh`) rewrites SKILL.md against the feature spec, working from the full current file. The parent verifies (installer test, size gate, rule-number audit, residual-STE-language search, diff review) and commits.

Verification gates: document-review subagent on the feature spec (this proposal cycle), then a code-review/document-review pass on the finished rewrite.

## Impact

- `skills/simple-english/SKILL.md` — rewritten, ~half size.
- `skills/simple-english/references/checklist.md`, `references/use-cases.md` — deleted after content is folded into SKILL.md.
- `tests/test-install.sh` — unaffected (links skill directories, requires only `SKILL.md` per skill; still 15 skills).
- Skill identity unchanged, so no other repo consumers are affected.
