# Simple-English Pragmatic Core Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use subagent-driven-development (recommended) or executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Rewrite the simple-english skill into a self-contained, pragmatic standard for unambiguous technical prose, roughly half its current size, with ASD-STE100 reduced to a single inspiration line.

**Architecture:** One self-contained SKILL.md written to a lean rule catalog (12–22 sequential rules) plus concise checklist and use-case sections, with both reference files deleted after their reusable content is folded in. The rewrite is performed by a single strong subagent (openai-codex / gpt-5.6-sol / xhigh) to maximize quality, then verified by the parent.

**Tech Stack:** Markdown agent skill, Bash installer test, `rg` audits.

**Standards:** Apply the shared code standards in every task: DRY, minimal implementation (YAGNI), low cyclomatic complexity, type safety, no unnecessary abstractions or fallbacks, no hacks or workarounds, informative docstrings, documentation of current state only, simple-english prose.

**Feature spec:** `docs/design/2026-08-25-simple-english-pragmatic-core-spec.md` (the behavioral contract)

---

## Commands

Run commands from the worktree root.

```bash
# Size gate (spec ADDED "Bounded document size", Scenario: Size gate)
test "$(wc -c < skills/simple-english/SKILL.md)" -lt 14000

# Installer regression test
bash tests/test-install.sh

# Residual STE language audit (spec ADDED "Practical standard identity", Scenario: Document audit)
rg -n 'ASD-STE100|Simplified Technical English' skills/simple-english/SKILL.md      # expect exactly 1 line total
rg -n 'ASD dictionary' skills/simple-english/SKILL.md                                 # expect no matches
rg -nw 'STE' skills/simple-english/SKILL.md                                           # expect no match outside the attribution line
rg -n 'complian' skills/simple-english/SKILL.md                                       # expect no matches

# Activation-trigger audit (spec ADDED "Practical standard identity", Scenario: No activation term)
rg -n 'STE|Simplified Technical English|ASD-STE100' skills/simple-english/SKILL.md
#   expect matches only in the single attribution line

# Rule-number audit (spec ADDED "Lean rule catalog", Scenario: Numbering audit)
rg -o 'Rule [0-9]+' skills/simple-english/SKILL.md | sort -t' ' -k2 -n -u
#   every cited number must resolve to a defined rule; the catalog must be one unbroken 1..N sequence, 12-22 totals

# Reference-file removal audit (spec ADDED "Self-contained document", Scenario: Directory audit)
ls skills/simple-english/ && test ! -d skills/simple-english/references

# Whitespace sanity
git diff --check
```

---

### Task 1: Rewrite the skill to the pragmatic core

**Files:**

- Rewrite: `skills/simple-english/SKILL.md` — one self-contained pragmatic technical-writing standard
- Delete: `skills/simple-english/references/checklist.md`, `skills/simple-english/references/use-cases.md` — content folded into SKILL.md first

**Spec requirement:** All ADDED requirements (practical standard identity, lean rule catalog, self-contained document, bounded document size); all MODIFIED requirements (repair procedure in the rules, terminology consistency without dictionary authority); all REMOVED requirements (approved-word compliance, dictionary rulings content).

**Interface (document contract):**

Frontmatter:
- `name: simple-english` (unchanged)
- `description` MUST NOT trigger on "STE", "Simplified Technical English", or "ASD-STE100", and MUST describe a practical standard for clear, unambiguous technical prose.

Body (recommended order — adopt the section ordering that reads best, but include each of these):
1. One attribution line naming ASD-STE100 (Simplified Technical English) as the inspiration and as the source of further official guidance. This is the ONLY place the STE terms appear; the rest of the document uses plain terms.
2. Classification: procedural vs descriptive (imperative vs present/past/future), with the 20-word / 25-word limits.
3. Your-Task steps: classify; protect the source; pick-one vocabulary; smallest-repair approach; apply the rules; self-check; untouchables.
4. A rule catalog of **12–22 rules numbered 1..N in one unbroken sequence**, with no gaps and no section sub-numbers (no "1.1"). It MUST encode:
   - sentence lengths (20 procedural / 25 descriptive)
   - one instruction per sentence
   - imperative + condition-first, if/when at the start
   - active voice preferred; passive only when the agent is unknown
   - simple tenses; no `-ing` forms as verbs (only as nouns)
   - no contractions, no omitted "that" (complete grammar)
   - no semicolons; two sentences instead
   - no e.g./i.e./etc.; no filler words (simply, easily, seamlessly, robust); `however` → `but`
   - vertical-list mechanics (colon lead-in, uppercase items, periods only on full sentences, no nested lists, no mixing instructions and facts)
   - article placement ("the", "a", "this" before nouns; exception: identifier follows a noun)
   - pick-one-and-keep-it for check/verify/confirm/ensure, config/settings, run/execute (no dictionary justification)
   - preferred substitutes: check/verify/confirm/ensure → pick one; `validate` → technical verb or `make sure that`; `delete` → legal technical verb in computer contexts (avoid `drop`/`destroy`)
   - no phrasal verbs ("go down" → "decrease", "set up" → "install"/"configure")
   - word-count mechanics (Rule 8.6/8.7 equivalents: numbers, numbers with units, abbreviations, alphanumeric identifiers, quoted text, titles, labels, proper nouns count as one word; hyphenated words count as one; parentheses content counts as one; colon lead-in ends a sentence for word count)
   - smallest sufficient repair; split only when a limit or rule requires it; after a split, state every original logical relationship explicitly (connectors like "because", "then", "as a result", "but"); no cause/condition/method/purpose/contrast/result is split from its assertion just because it is a related clause
   - preserve each source component and its semantic role; keep established terminology; no added cause, intention, judgment, mechanism, degree of certainty, or new term (this carries the spec's MODIFIED repair and the minimal-rewrites "preserve claims/terminology" requirements)
   - banned modals: `should` → `must` (requirement) or delete/state-as-fact (recommendation); `may/might/could` → `can`; `would` → `can`/restructure; never use `should` for agent instructions (models read it as optional)
   - untouchables: code, identifiers, commands, quoted errors, product/UI names, config keys, numbers with units — leave exact
5. A self-check of no more than 8 items, each citing a rule number, covering: source-component preservation; split-examination (remove unnecessary splits, verify explicit relationships); word-count of the three longest sentences (mandatory split over the limit); banned patterns (contractions, perfect tenses, `should`/`shall`, `however`/`therefore`, `-ing` verbs after a comma, semicolons); condition placement; pick-one verbs; list mechanics; untouchables.
6. A concise use-cases section with the adaptations folded in from `references/use-cases.md`: error messages; runbooks; incident reports; commits/PR descriptions; release notes; agent prompts; support macros/status pages; UI copy/empty states; translation/localization (with the "passage type: any" framing). Keep the short pattern per case, not a dictionary echo.
7. A compressed Full Example demonstrating classify + rules + self-check (short enough that it does not block the size gate).
8. NO sections for: two modes, dictionary-approved words, part-of-speech rulings, recurring errors, dictionary rulings, compliance claims, or an STE-specific "Where STE does not fit" (fold its one practical caution — STE is for technical facts, not marketing voice — into Limits-style prose without the term "STE" outside the attribution line, or drop it).

**Behavior:**

- The document reads as a single practical writing standard with no mention of modes or of the ASD dictionary anywhere.
- Every rule citation in prose, self-check, and tables resolves to a rule in the 1..N catalog; the numbers form one unbroken sequence; the total is between 12 and 22.
- The word "STE" appears only inside the attribution line (use `rg -nw 'STE'` to verify no standalone token elsewhere).
- The strings "ASD-STE100" and "Simplified Technical English" appear exactly once each, in the attribution line; "ASD dictionary" and "complian" appear nowhere.
- The frontmatter description contains none of the STE terms.
- The skill directory contains only `SKILL.md` and `LICENSE` after the references are deleted.
- The document is under 14,000 characters.
- The reusable checklist content (verification pass with searchable patterns) is folded into the self-check section, not lost.
- The reusable use-case content is folded into the use-cases section, not lost.

**Tests must prove:**

- `test_size_gate` — `wc -c < skills/simple-english/SKILL.md` is below 14,000
- `test_installer` — `bash tests/test-install.sh` passes (15 skills)
- `test_ste_terms_confined` — `rg -n 'ASD-STE100|Simplified Technical English'` shows exactly one line; `rg -nw 'STE'` shows no match outside the attribution line; `rg -n 'ASD dictionary'` and `rg -n 'complian'` show none
- `test_no_activation_terms` — the frontmatter `description` contains none of "STE", "Simplified Technical English", "ASD-STE100"
- `test_rule_catalog_audit` — every cited `Rule N` exists; the catalog is one unbroken 1..N sequence; the count is 12–22
- `test_references_removed` — `skills/simple-english/` contains no `references/` directory and no files other than `SKILL.md` and `LICENSE`
- `test_content_folded` — the checklist patterns ("has been", semicolon, "e.g.", quoted so the document does not violate its own rules) and use-case adaptations (runbook, incident report, commit message) appear in SKILL.md after the references are gone

**Check:** All commands in the Commands section; the seven `test_*` behaviors above; `git diff --check` clean.

- [ ] Preserve the current SKILL.md as the rewrite input (do not edit it before the rewrite; the subagent reads the full current file)
- [ ] With a single subagent (provider `openai-codex`, model `gpt-5.6-sol`, reasoning effort `xhigh`), rewrite SKILL.md per the feature spec into the pragmatic core, folding in the checklist/use-case content, then delete the two reference files
- [ ] Run all verification commands and the seven checks; fix any failure and re-run until all pass
- [ ] Review the final diff for coherence (no orphaned references, no lost content, prose reads as one standard)
- [ ] Commit: `git add skills/simple-english/ && git commit -m "docs: rewrite simple-english as a pragmatic core standard"`

---

## Self-review notes

- The plan's single task covers every ADDED/MODIFIED/REMOVED requirement: identity (attribution, audits), lean catalog (12–22, renumber), self-contained (fold + delete references), size gate, repair-in-the-rules, pick-one-without-dictionary, removal of approved-word/dictionary content.
- The plan has no implementation code; it specifies the document contract, section list, and rule coverage, leaving the exact prose to the implementer.
- No placeholders; every check has an exact command.
- The check commands are the exact commands from the Commands section (no invented ones).
- The rewrite is scoped to the simple-english skill; historical docs remain untouched.
