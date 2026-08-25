---
name: simple-english
description: |
  Use when writing or rewriting developer-facing text — documentation,
  READMEs, runbooks, procedures, error messages, release notes, incident
  reports, commit messages, agent prompts, UI copy — to make it clear,
  short, and unambiguous. Also when the user says "make this readable"
  or "simplify this text", or asks for text that translates well.
---

# Simple English: A Practical Standard for Clear Technical Prose

Write technical text so that a tired reader who is not a native English speaker cannot misread it. One meaning per word, short sentences, complete grammar. Each sentence must survive one read.

These rules are a practical core inspired by ASD-STE100 (Simplified Technical English), the controlled language of aerospace maintenance documentation. For the official standard and further guidance, see asd-ste100.org.

## Your Task

When asked to write or rewrite technical text:

1. **Classify each passage** as procedural or descriptive. Every other rule depends on this.
2. **Protect the source before drafting.** Record each subject, action, object, modifier, relationship, actor, and technical name (Rule 19).
3. **Pick your vocabulary before drafting.** Pick one term per concept and keep it for the whole document (Rule 13).
4. **Use the smallest sufficient repair** (Rule 17). Split a sentence only when a limit or rule requires it.
5. **Apply the rules** from the catalog that follows.
6. **Do the self-check** before you deliver. This step is not optional.
7. **Never touch code**, identifiers, commands, or quoted errors (Rule 20).

When asked to CHECK text instead of writing it, report each violation as: rule number, the offending text, a corrected rewrite. Cite only rule numbers that exist in this file. Do not cite rule numbers from memory.

## Classify the Text

| | Procedural (instructions) | Descriptive (explanations) |
|---|---|---|
| Purpose | Tell the reader what to do | Explain what a thing is or does |
| Verb form | Imperative: "Install the pump." | Simple present, past, or future |
| Sentence limit | 20 words (Rule 1) | 25 words (Rule 1) |
| Unit rule | One instruction per sentence (Rule 2) | One topic per paragraph, at most six sentences (Rule 2) |

Do not mix the two in one passage. A note inside a procedure is descriptive: 25-word limit, no imperative.

## The Rules

1. **Sentence limits.** Procedural sentence: maximum 20 words. Descriptive sentence: maximum 25 words. Warnings and cautions count as procedural. Count words with the mechanics of Rule 16.

2. **One instruction per sentence**, unless two actions happen at the same time. A step can have a second sentence for an immediate result or limit. Descriptive text: one main assertion per sentence, one topic per paragraph, at most six sentences per paragraph.

3. **Imperative, condition first.** Write instructions in the imperative. Put a required condition before the command, divided by a comma: "If the build fails, read the log." In an instruction, every "if" and "when" stands at the start of its sentence, before the command.

4. **Warnings: command first, risk second.** Start with a clear command or condition, then give the risk. Use "CAUTION" for damage and "WARNING" for injury. "CAUTION: Do not use the `--force` flag against production. The flag deletes rows that do not match the source."

5. **Active voice.** In descriptive text, the passive is legal only when the agent is unknown. To repair an agentless passive, make "you" (the reader) or "we" (your company) the subject.

6. **Simple tenses.** Use simple present, simple past, simple future. No perfect forms ("has been"), no progressive forms ("is being rebuilt"). Use an "-ing" form only as a noun or inside one ("logging", "the mounting bracket"), never as a verb.

7. **Modals: can, will, must.** Banned: should, would, may, might, could, shall. "Should" as a requirement becomes "must". "Should" as a recommendation is deleted or stated as a fact. "May", "might", and "could" become "can". "Would" becomes "can" or is restructured. Never use "should" in agent instructions: models read it as optional.

8. **Complete grammar.** No contractions. Do not omit words to shorten sentences: keep the articles, keep "that". Wrong: "Ensure file exists before running." Right: "Make sure that the file exists before you run the command."

9. **No semicolons.** Write two sentences instead.

10. **Plain substitutes.** "However" becomes "but". "Therefore" becomes "as a result". "e.g." becomes "for example", "i.e." becomes "that is", and "etc." is deleted: name the items or write "and more". Delete filler words: "simply", "easily", "seamlessly", "robust".

11. **Vertical lists.** Use a vertical list for complex text. Put a colon at the end of the lead-in. Start each item with an uppercase letter. An item gets a period only if it is a full sentence, never a comma or a semicolon. The last item gets a period. Do not nest lists. Do not mix instructions and facts in one list.

12. **Articles.** Put an article ("the", "a", "an") or a demonstrative ("this", "these") before a noun where applicable. Exception: no article when an identifier follows the noun: "Restart pod web-7f9b2", not "Restart the pod web-7f9b2".

13. **One concept, one term.** Pick one term and keep it for the whole document. Pick one of check, verify, confirm, ensure, "make sure that". Pick one of config, configuration, settings. Pick one of run, execute. Do not write "config" here and "settings" there.

14. **Domain vocabulary and substitutes.** The technical nouns and verbs of your project are legal ("webhook", "deploy", "compile"). No word list can reject them. "Validate" works as a technical verb, or write "make sure that". "Delete" is a legal technical verb in computer contexts: avoid "drop" and "destroy".

15. **No phrasal verbs.** "Go down" becomes "decrease". "Set up" becomes "install" or "configure". "Find out" becomes "find".

16. **Word count.** Each of these counts as one word: a number, a number with a unit, an abbreviation, an alphanumeric identifier, quoted text, a title, a label, a proper noun. A hyphenated word counts as one word. Text inside parentheses counts as one word. In a vertical list, the lead-in colon ends a sentence for word count. Each item after it counts as a new sentence with its own budget. Backticked code is quoted text.

17. **Smallest sufficient repair.** Count each word before you repair a sentence. Do not estimate. Mark a procedural sentence with 21 or more words and a descriptive sentence with 26 or more. Never deliver a marked sentence unchanged. Use this order and stop after the first repair that gives a clear sentence within the rules: (1) replace only the breaking word or form, (2) convert a phrase to a finite clause in the same sentence, (3) reorder the clauses without changing their relationships. Split only when a limit or rule requires it: the sentence stays over its limit, it holds more than one instruction, or it is unclear. A cause, condition, method, purpose, contrast, or result is not a separate fact: keep it with its assertion while the sentence stays within its limit.

18. **After a split, state the relationships.** State each original logical relationship explicitly with a connector such as "because", "then", "as a result", or "but". Sentence adjacency does not state the relationship. Repeat the established name or use a clear pronoun across the new sentences. Do not create a shortened name.

19. **Preserve the source.** Keep the information and the semantic role of each subject, action, object, modifier, claim, logical relationship, actor, technical name, and degree of certainty. Keep established terminology. Add no cause, intention, judgment, mechanism, degree of certainty, or new term. If the source gives no number, cause, or exact term, keep the general statement. "Sends the update to each cluster" cannot become "updates each cluster": the first acts on the update, the second on each cluster.

20. **Untouchables.** Leave these exact, even when they break a rule: code blocks, inline code, identifiers, CLI commands, flags, file paths, quoted error messages and log lines, product names, API endpoint names, UI labels, config keys, numbers with units. Facts are untouchable too: rewrite the style, not the content.

## Self-Check Before You Deliver

This step is not optional. Run these eight checks on your draft:

1. **Preservation (Rule 19).** Compare the draft with the source. Each source component keeps its information and semantic role. Restore each component that the repair did not have to change.
2. **Splits (Rule 17, Rule 18).** Examine every split. If a finite clause or a reorder gives a clear sentence within the limits, remove the split. Each necessary split states every original logical relationship explicitly.
3. **Word count (Rule 1, Rule 16).** Count the words in your three longest sentences. A sentence over its limit must be split (Rule 17). Never deliver an over-limit sentence unchanged.
4. **Banned patterns (Rule 6, Rule 7, Rule 8, Rule 9, Rule 10).** Search the draft for `'ll`, `'re`, `'s`, `has been`, `have been`, `should`, `shall`, `however`, `therefore`, `e.g.`, `i.e.`, `etc.`, an `-ing` verb after a comma (`, making`), and `;`. Each hit outside code and quoted text is a violation.
5. **Condition placement (Rule 3).** Search for every `if` and `when`. In an instruction, each stands at the start of its sentence, before the command.
6. **Term consistency (Rule 13).** Search for the pick-family terms you did not choose: check, verify, confirm, ensure, "make sure that". Scan for config/settings and run/execute rotations. Replace each hit with your chosen term.
7. **Lists (Rule 11).** Check each vertical list: colon on the lead-in, uppercase first letter on each item, a period only on a full-sentence item, no nested lists, no instructions mixed with facts.
8. **Untouchables (Rule 20).** Make sure that code, identifiers, quoted errors, UI labels, and numbers with units are unchanged.

Fix what you find, then deliver.

## Use Cases

The same rules apply wherever misreading has a cost. Each case names the passage type and the adaptation.

- **Error messages and CLI output** — procedural. An error message is a 2 a.m. instruction to a stressed reader. State what happened in the simple past, state the cause if known, then give the command or condition to fix it: "Connection to the database failed. The password for user `app` was not correct. Set `DB_PASSWORD` and connect again."
- **Runbooks** — procedural. One instruction per step, conditions first, warnings before the step (Rule 4). Enforce the 20-word limit hard: an operator under pager stress reads each sentence once.
- **Incident reports and postmortems** — descriptive. Simple past only: a timeline in the present perfect hides when things happened. State what is known and write "unknown" for the rest. "We have identified an issue that may have impacted some users" becomes "Between 14:02 and 14:31 UTC, 12% of requests failed."
- **Commit messages and PR descriptions** — imperative subject, descriptive body. Apply the substitutes (Rule 10) and the 25-word limit to the body. Delete "this PR aims to".
- **Release notes** — descriptive. One entry, one change, one sentence where possible. Breaking changes follow the warning pattern (Rule 4): command first, then the risk.
- **Agent prompts** — procedural. A prompt is a procedure for a reader that cannot ask questions. One instruction per sentence (Rule 2), one term per concept (Rule 13), conditions first (Rule 3), never "should" (Rule 7).
- **Support macros and status pages** — descriptive, 25-word limit. Skip the apology formula and state the facts: "The API was down for 18 minutes. Uploads made during this time were saved and will process today."
- **UI copy and empty states** — procedural, hard length limits. Buttons and labels are untouchable names (Rule 20). Body copy follows the rules: "No projects yet. Create a project to start."
- **Translation and localization prep** — any passage type. One meaning per word plus complete grammar (Rule 8, Rule 13) removes most translation ambiguity. Localized docs get fewer errors at a lower cost.

## Full Example

Before:

> **Connection timeouts.** If sqlpipe hangs or fails with `dial tcp: i/o timeout`, check that the host running sqlpipe can reach the Postgres port (usually 5432) — often a security group or firewall rule blocks it. If you're connecting to a managed database (RDS, Cloud SQL, etc.), confirm the instance allows connections from sqlpipe's IP. You can also try increasing `source.connect_timeout_seconds`, since a slow network can trip the default timeout.

After (classified procedural, verb pick "make sure that", conditions first, one instruction per sentence):

> **Connection timeouts.** sqlpipe stops with `dial tcp: i/o timeout` when it cannot connect to the Postgres port (5432 by default).
>
> 1. Make sure that the host that runs sqlpipe can connect to the Postgres port. A firewall or security group usually blocks it.
> 2. If the database is managed (RDS, Cloud SQL), make sure that the instance accepts connections from the IP of sqlpipe.
> 3. If the network is slow, increase `source.connect_timeout_seconds` in the configuration.

Self-check: source facts preserved (Rule 19), over-limit sentences split with explicit relationships (Rule 17, Rule 18), longest new sentence 18 words (Rule 1), no banned patterns, conditions first, one verb pick, code untouched (Rule 20).

## Limits

This standard is for technical facts and instructions. Do not apply it to marketing copy or brand writing: it deletes persuasion by design. Offer it for the docs instead.

No tool can guarantee conformance to the official standard. If a user asks for that, apply these rules and point to the attribution line for the official source.
