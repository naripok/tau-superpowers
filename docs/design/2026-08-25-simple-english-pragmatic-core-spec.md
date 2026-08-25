# Spec: Pragmatic Core for the simple-english Skill

## Domain: simple-english-rewriting

Baseline: the implemented skill rules — procedural/descriptive classification, 20/25-word limits, one instruction per sentence, the `-ing` restriction, active voice, the smallest-sufficient-repair procedure, the self-check. Requirements from the minimal-rewrites spec that this document does not mention (preserve claims and terminology; preserve logical relationships; use the smallest sufficient repair) remain in force.

### ADDED Requirements

#### Requirement: Practical standard identity

The skill SHALL describe itself as a practical standard for unambiguous, easy-to-read technical prose. The skill SHALL name ASD-STE100 (Simplified Technical English) as its inspiration in exactly one line, and that line SHALL point to ASD-STE100 as the source of further guidance. The skill MUST NOT claim ASD-STE100 compliance, MUST NOT present the ASD dictionary as authoritative, and MUST NOT use "STE", "Simplified Technical English", or "ASD-STE100" as activation terms. The body SHALL NOT use standalone "STE" outside that attribution line.

##### Scenario: No compliance claim

- GIVEN a user asks for text that complies with ASD-STE100 or with the ASD dictionary
- WHEN the agent applies the skill
- THEN the agent SHALL apply the practical rules to the text
- AND the agent SHALL NOT present the result as ASD-STE100 compliance
- AND the agent SHALL direct the user to the attribution line for official guidance

##### Scenario: Document audit

- GIVEN the completed SKILL.md
- WHEN an auditor searches for "ASD-STE100" and "Simplified Technical English"
- THEN each search SHALL find exactly one match
- AND the match SHALL be in the line that names ASD-STE100 (Simplified Technical English) as the inspiration
- AND a search for "ASD dictionary" SHALL find no matches
- AND a search for standalone "STE" (word boundary) SHALL find no match outside that line
- AND a search for "complian" SHALL find no matches

##### Scenario: No activation term

- GIVEN the completed skill document
- WHEN an auditor reads the activation triggers
- THEN none of "STE", "Simplified Technical English", or "ASD-STE100" SHALL appear as a trigger

#### Requirement: Lean rule catalog

The rule catalog SHALL contain 12 to 22 rules numbered in one unbroken sequence with no gaps. Every rule citation in the document, including the self-check and the prose, SHALL resolve to an existing rule.

##### Scenario: Numbering audit

- GIVEN the completed skill document
- WHEN an auditor reads every rule and every citation
- THEN every citation SHALL match an existing rule number
- AND the rule numbers SHALL form one unbroken sequence with no gaps
- AND the rule count SHALL be between 12 and 22

#### Requirement: Self-contained document

The skill SHALL be fully usable from SKILL.md alone. The document SHALL contain the checklist guidance and the use-case adaptations that a reader needs for error messages, runbooks, incident reports, commits, release notes, agent prompts, support updates, and UI copy. The skill directory SHALL contain no `references/` directory and no files other than `SKILL.md` and `LICENSE`.

##### Scenario: Reference removal

- GIVEN a reader who has only SKILL.md
- WHEN the reader follows the writing, checking, and use-case guidance
- THEN the reader SHALL need no other file

##### Scenario: Directory audit

- GIVEN the completed skill directory
- WHEN an auditor lists its files
- THEN the directory SHALL contain no `references/` directory and no files other than `SKILL.md` and `LICENSE`

#### Requirement: Bounded document size

The skill document SHALL contain fewer than 14,000 characters.

##### Scenario: Size gate

- GIVEN the completed skill
- WHEN the agent measures the document length
- THEN the length SHALL be below 14,000 characters

### MODIFIED Requirements

#### Requirement: Repair procedure in the rules

The standalone least-change procedure section is removed. The procedure's intent SHALL live in the rule catalog and in the self-check: apply the smallest repair that satisfies the rules; split a sentence only when an applicable limit or rule requires it; after a split, state each original logical relationship explicitly.

##### Scenario: Procedure intent preserved

- GIVEN a rewrite task that needs a repair
- WHEN the agent applies the skill
- THEN the agent SHALL make the smallest change that satisfies the applicable rules
- AND the agent SHALL split a sentence only when an applicable limit or rule requires it

#### Requirement: Terminology consistency without dictionary authority

The pick-one-and-keep-it rule SHALL survive without any dictionary justification. The skill SHALL tell the agent to pick one term and keep it for check/verify/confirm/ensure, for config/settings, and for run/execute.

##### Scenario: Pick without dictionary

- GIVEN source text that uses "verify" here and "check" there
- WHEN the agent rewrites the text
- THEN the rewrite SHALL use the same chosen term for the same concept

### REMOVED Requirements

#### Requirement: Approved-word compliance

The dictionary-based restriction that legal words are only dictionary-approved words, technical nouns, and approved verb forms is removed. The skill MUST NOT reject a word because a dictionary lacks it.

##### Scenario: Domain word stays

- GIVEN source text that uses a domain word absent from any dictionary
- WHEN the agent rewrites the text
- THEN the agent SHALL keep the domain word

#### Requirement: Dictionary rulings content

The part-of-speech rulings table, the recurring-errors table, and the dictionary-rulings table are removed. Plain substitutes that need no dictionary (no contractions, no semicolons, no e.g./i.e./etc., no filler words, `however` → `but`) SHALL remain in the catalog.

##### Scenario: No dictionary citations

- GIVEN the completed skill document
- WHEN an auditor searches the document for dictionary rulings
- THEN the document SHALL contain no approved-word lists, part-of-speech rulings, or dictionary-rulings tables
