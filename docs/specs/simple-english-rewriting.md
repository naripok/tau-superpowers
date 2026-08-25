# simple-english-rewriting

## Purpose

The simple-english skill rewrites developer-facing text into a practical standard for unambiguous, easy-to-read technical prose. The standard is inspired by ASD-STE100 (Simplified Technical English) but adheres to no dictionary. It classifies each passage as procedural or descriptive, applies 20/25-word sentence limits, and requires the smallest sufficient repair that preserves the source facts.

## Requirements

### Requirement: Practical standard identity

The skill SHALL describe itself as a practical standard for unambiguous, easy-to-read technical prose. The skill SHALL name ASD-STE100 (Simplified Technical English) as its inspiration in exactly one line, and that line SHALL point to ASD-STE100 as the source of further guidance. The skill MUST NOT claim ASD-STE100 compliance, MUST NOT present the ASD dictionary as authoritative, and MUST NOT use "STE", "Simplified Technical English", or "ASD-STE100" as activation terms. The body SHALL NOT use standalone "STE" outside that attribution line.

#### Scenario: No compliance claim

- GIVEN a user asks for text that complies with ASD-STE100 or with the ASD dictionary
- WHEN the agent applies the skill
- THEN the agent SHALL apply the practical rules to the text
- AND the agent SHALL NOT present the result as ASD-STE100 compliance
- AND the agent SHALL direct the user to the attribution line for official guidance

#### Scenario: Document audit

- GIVEN the completed SKILL.md
- WHEN an auditor searches for "ASD-STE100" and "Simplified Technical English"
- THEN each search SHALL find exactly one match
- AND the match SHALL be in the line that names ASD-STE100 (Simplified Technical English) as the inspiration
- AND a search for "ASD dictionary" SHALL find no matches
- AND a search for standalone "STE" (word boundary) SHALL find no match outside that line
- AND a search for "complian" SHALL find no matches

#### Scenario: No activation term

- GIVEN the completed skill document
- WHEN an auditor reads the activation triggers
- THEN none of "STE", "Simplified Technical English", or "ASD-STE100" SHALL appear as a trigger

### Requirement: Lean rule catalog

The rule catalog SHALL contain 12 to 22 rules numbered in one unbroken sequence with no gaps. Every rule citation in the document, including the self-check and the prose, SHALL resolve to an existing rule.

#### Scenario: Numbering audit

- GIVEN the completed skill document
- WHEN an auditor reads every rule and every citation
- THEN every citation SHALL match an existing rule number
- AND the rule numbers SHALL form one unbroken sequence with no gaps
- AND the rule count SHALL be between 12 and 22

### Requirement: Self-contained document

The skill SHALL be fully usable from SKILL.md alone. The document SHALL contain the checklist guidance and the use-case adaptations that a reader needs for error messages, runbooks, incident reports, commits, release notes, agent prompts, support updates, and UI copy. The skill directory SHALL contain no `references/` directory and no files other than `SKILL.md` and `LICENSE`.

#### Scenario: Reference removal

- GIVEN a reader who has only SKILL.md
- WHEN the reader follows the writing, checking, and use-case guidance
- THEN the reader SHALL need no other file

#### Scenario: Directory audit

- GIVEN the completed skill directory
- WHEN an auditor lists its files
- THEN the directory SHALL contain no `references/` directory and no files other than `SKILL.md` and `LICENSE`

### Requirement: Bounded document size

The skill document SHALL contain fewer than 14,000 characters.

#### Scenario: Size gate

- GIVEN the completed skill
- WHEN the agent measures the document length
- THEN the length SHALL be below 14,000 characters

### Requirement: Repair procedure in the rules

The procedure's intent lives in the rule catalog and in the self-check: apply the smallest repair that satisfies the rules; split a sentence only when an applicable limit or rule requires it; after a split, state each original logical relationship explicitly.

#### Scenario: Procedure intent preserved

- GIVEN a rewrite task that needs a repair
- WHEN the agent applies the skill
- THEN the agent SHALL make the smallest change that satisfies the applicable rules
- AND the agent SHALL split a sentence only when an applicable limit or rule requires it

### Requirement: Terminology consistency without dictionary authority

The pick-one-and-keep-it rule survives without any dictionary justification. The skill SHALL tell the agent to pick one term and keep it for check/verify/confirm/ensure, for config/settings, and for run/execute.

#### Scenario: Pick without dictionary

- GIVEN source text that uses "verify" here and "check" there
- WHEN the agent rewrites the text
- THEN the rewrite SHALL use the same chosen term for the same concept

### Requirement: Use the smallest sufficient repair

The rewriter SHALL use the smallest change that makes source text compliant and clear.

#### Scenario: A finite clause removes a prohibited form

- GIVEN a descriptive sentence within the word limit
- AND the sentence contains a prohibited `-ing` verb form
- AND a finite-clause rewrite retains the source subjects, objects, modifiers, and logical relationships
- WHEN the rewriter applies the structural rules
- THEN the rewrite SHALL contain one sentence
- AND the rewrite SHALL contain no prohibited `-ing` verb form
- AND the rewrite SHALL preserve the source claims and terminology

### Requirement: Split only when necessary

The rewriter SHALL split a sentence only when a smaller repair cannot satisfy an applicable structural rule or preserve clarity.

#### Scenario: The original sentence is already short and clear

- GIVEN a descriptive sentence within the word limit
- AND the sentence has one main assertion with a closely related explanation
- AND a one-sentence rewrite satisfies all applicable rules
- WHEN the rewriter applies the structural rules
- THEN the rewrite SHALL contain the same number of sentences as the source

#### Scenario: A sentence exceeds its word limit

- GIVEN a sentence that exceeds its applicable word limit
- WHEN the rewriter cannot shorten it without a semantic change
- THEN the rewriter SHALL split the sentence

### Requirement: Preserve logical relationships

The rewriter MUST preserve each causal, conditional, temporal, contrastive, purposive, method, and result relationship from the source.

#### Scenario: A rewrite keeps related clauses together

- GIVEN a source sentence with an explicit logical relationship
- AND the rewrite does not split the sentence
- WHEN the rewriter changes the clause structure
- THEN the rewrite MUST state the same logical relationship explicitly

#### Scenario: A necessary split separates related clauses

- GIVEN a source sentence with an explicit logical relationship
- AND an applicable rule requires a sentence split
- WHEN the rewriter splits the sentence
- THEN the rewrite MUST state the same logical relationship explicitly
- AND sentence adjacency alone MUST NOT represent that relationship

### Requirement: Preserve claims and terminology

The rewriter MUST NOT add a cause, intention, judgment, mechanism, degree of certainty, or other claim. It MUST NOT replace established terms only to simplify sentence structure.

#### Scenario: A structural rewrite is more specific than the source

- GIVEN source text that states a general action
- WHEN a possible rewrite adds a cause, intention, judgment, mechanism, or degree of certainty
- THEN the rewriter MUST reject that rewrite
- AND the final rewrite MUST contain only claims supported by the source and established context

#### Scenario: The context establishes an actor name

- GIVEN the source context establishes a name for an actor
- WHEN the rewriter makes that actor explicit
- THEN the rewriter SHALL use the established name
- AND the rewriter MUST NOT invent a different name
