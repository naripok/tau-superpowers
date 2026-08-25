# Spec: Minimal Simple-English Rewrites

## Domain: simple-english-rewriting

### ADDED Requirements

#### Requirement: Use the smallest sufficient repair

The rewriter SHALL use the smallest change that makes source text compliant and clear.

##### Scenario: A finite clause removes a prohibited form

- GIVEN a descriptive sentence within the word limit
- AND the sentence contains a prohibited `-ing` verb form
- AND a finite-clause rewrite retains the source subjects, objects, modifiers, and logical relationships
- WHEN the rewriter applies the structural rules
- THEN the rewrite SHALL contain one sentence
- AND the rewrite SHALL contain no prohibited `-ing` verb form
- AND the rewrite SHALL preserve the source claims and terminology

#### Requirement: Split only when necessary

The rewriter SHALL split a sentence only when a smaller repair cannot satisfy an applicable structural rule or preserve clarity.

##### Scenario: The original sentence is already short and clear

- GIVEN a descriptive sentence within the word limit
- AND the sentence has one main assertion with a closely related explanation
- AND a one-sentence rewrite satisfies all applicable rules
- WHEN the rewriter applies the structural rules
- THEN the rewrite SHALL contain the same number of sentences as the source

##### Scenario: A sentence exceeds its word limit

- GIVEN a sentence that exceeds its applicable word limit
- WHEN the rewriter cannot shorten it without a semantic change
- THEN the rewriter SHALL split the sentence

#### Requirement: Preserve logical relationships

The rewriter MUST preserve each causal, conditional, temporal, contrastive, purposive, method, and result relationship from the source.

##### Scenario: A rewrite keeps related clauses together

- GIVEN a source sentence with an explicit logical relationship
- AND the rewrite does not split the sentence
- WHEN the rewriter changes the clause structure
- THEN the rewrite MUST state the same logical relationship explicitly

##### Scenario: A necessary split separates related clauses

- GIVEN a source sentence with an explicit logical relationship
- AND an applicable rule requires a sentence split
- WHEN the rewriter splits the sentence
- THEN the rewrite MUST state the same logical relationship explicitly
- AND sentence adjacency alone MUST NOT represent that relationship

#### Requirement: Preserve claims and terminology

The rewriter MUST NOT add a cause, intention, judgment, mechanism, degree of certainty, or other claim. It MUST NOT replace established terms only to simplify sentence structure.

##### Scenario: A structural rewrite is more specific than the source

- GIVEN source text that states a general action
- WHEN a possible rewrite adds a cause, intention, judgment, mechanism, or degree of certainty
- THEN the rewriter MUST reject that rewrite
- AND the final rewrite MUST contain only claims supported by the source and established context

##### Scenario: The context establishes an actor name

- GIVEN the source context establishes a name for an actor
- WHEN the rewriter makes that actor explicit
- THEN the rewriter SHALL use the established name
- AND the rewriter MUST NOT invent a different name
