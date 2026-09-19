# BLACK SWAN LABS

## Formal Claim Verification Engine

### Implementation Specification Sheet v1.0

**Status:** Implementation Specification
**Date:** September 18, 2026
**Primary use:** Independent, reproducible verification of mathematical claims
**Audience:** Mathematicians, formal-verification auditors, researchers, theorem authors, and verification engineers

---

# 1. SYSTEM PURPOSE

The Formal Claim Verification Engine (FCVE) converts a mathematical claim supplied in human-readable form into an auditable verification package.

The system must answer five different questions separately:

1. **What exactly does the source claim?**
2. **What mathematical statement does that claim mean?**
3. **Does Lean formally prove the normalized statement?**
4. **Does the formal statement faithfully represent the source statement?**
5. **What independent computational/adversarial evidence exists for or against the claim?**

The system MUST NOT collapse these questions into a single:

> VERIFIED = TRUE

status.

The core output is therefore an **evidence package**, not merely a Boolean.

---

# 2. CORE DESIGN PRINCIPLE

## The engine verifies both the theorem and the path by which the theorem was verified.

Canonical chain:

```text
SOURCE
  ↓
CLAIM EXTRACTION
  ↓
ASSUMPTION EXTRACTION
  ↓
SEMANTIC NORMALIZATION
  ↓
LEAN FORMALIZATION
  ↓
KERNEL VERIFICATION
  ↓
AXIOM AUDIT
  ↓
SEMANTIC RE-AUDIT
  ↓
INDEPENDENT CHECK
  ↓
COMPUTATIONAL / ADVERSARIAL TESTING
  ↓
EVIDENCE GRAPH
  ↓
HUMAN-READABLE REPORT
  ↓
GOVERNANCE DECISION
```

Every substantive transformation must be attributable to:

* an input,
* an action,
* a reason,
* an output,
* evidence,
* and a resulting state.

---

# 3. NON-GOALS

The MVP is NOT:

* an automated mathematician;
* a replacement for mathematical peer review;
* a proof-discovery system;
* a universal theorem prover;
* a guarantee that the original paper is mathematically correct;
* a claim that computational testing proves a theorem;
* a claim that Lean compilation alone establishes source fidelity;
* a claim that an independent checker is infallible;
* a mechanism for silently repairing a theorem.

If the system changes the meaning of a theorem, it must stop and report the change.

---

# 4. VERIFICATION LAYERS

The system shall maintain five distinct verification layers.

| Layer                            | Question                                              | Primary Evidence         |
| --------------------------------- | ----------------------------------------------------- | ------------------------- |
| L1 Source Integrity              | Did we preserve what was submitted?                   | SHA-256, byte comparison |
| L2 Source-Mathematical Integrity | Is the stated mathematics coherent?                   | semantic audit            |
| L3 Formal Integrity              | Does Lean prove the formal statement?                 | Lean kernel               |
| L4 Computational Integrity       | Does computation support or challenge the claim?      | symbolic/numeric tests    |
| L5 Reproducibility/Independence  | Can another environment/checker reproduce the result? | clean build/checker       |

No layer may inherit a PASS merely because another layer passed.

---

# 5. CLAIM TYPES

Every extracted claim receives one of three types.

### FORMAL

A mathematical proposition suitable for formal proof.

Example:

$$
\forall n \in \mathbb{N},\quad P(n).
$$

### EMPIRICAL

A claim requiring observation, measurement, experiment, or external data.

Example:

> The algorithm reduces runtime by 20%.

### MIXED

Contains both formal and empirical components.

Mixed claims MUST be decomposed.

Example:

> Theorem X proves that method A is optimal and experiments show A is faster in practice.

This becomes:

* FORMAL: Theorem X establishes the mathematical property.
* EMPIRICAL: Method A is faster under specified experimental conditions.

The MVP fully executes the FORMAL track.

---

# 6. INPUT CONTRACT

The engine must accept:

## Required

* source theorem/document;
* source location or identifier;
* theorem title/name if available;
* source format;
* intended mathematical domain if known.

## Optional

* existing Lean code;
* existing Lean project;
* existing MATLAB code;
* paper;
* supplementary proof;
* datasets;
* computational examples;
* external references;
* author's informal proof;
* known assumptions.

## Source preservation

The original input MUST be preserved byte-for-byte.

Required:

```text
source.original
source.sha256
source.format
source.timestamp
source.size
```

No normalization may overwrite the original.

---

# 7. THEOREM-PLAN-TEMPLATE

Before execution, the engine creates:

```text
THEOREM-PLAN.md
```

The plan must answer:

### Identity

* theorem ID;
* source;
* author;
* source location;
* theorem name;
* date;
* version.

### Mathematical classification

* algebra;
* number theory;
* combinatorics;
* analysis;
* topology;
* geometry;
* probability;
* logic;
* etc.

### Expected formalization difficulty

* elementary;
* moderate;
* heavy;
* unknown.

### Dependency risks

Check whether the theorem likely requires:

* real analysis;
* measure theory;
* topology;
* infinite structures;
* cardinal arithmetic;
* advanced algebra;
* quotient constructions;
* classical logic;
* choice;
* large Mathlib closures;
* external axioms;
* custom definitions.

### Verification scope

Explicitly define:

> What counts as DONE for this theorem?

---

# 8. GATE ARCHITECTURE

The engine has fourteen MVP gates.

---

## GATE 0 — SOURCE INTAKE

### Required

* source preserved;
* SHA-256 calculated;
* source readable;
* environment identified.

### PASS

Source is immutable and addressable.

### FAIL

STOP.

---

# 9. GATE 1 — CLAIM EXTRACTION

Extract:

* claim ID;
* theorem statement;
* source location;
* claim type;
* surrounding definitions;
* referenced lemmas;
* explicit conditions.

Every theorem receives a stable ID.

Example:

```text
CLAIM-001
CLAIM-002
LEMMA-001
LEMMA-002
```

---

# 10. GATE 2 — ASSUMPTION EXTRACTION

Extract:

### Explicit assumptions

Directly stated by the source.

### Implicit assumptions

Required for the mathematics to make sense.

### Formalization assumptions

Introduced by Lean representation.

### Computational assumptions

Introduced by MATLAB/numerical experiments.

The engine must distinguish:

```text
SOURCE_ASSUMPTION
FORMALIZATION_ASSUMPTION
COMPUTATIONAL_ASSUMPTION
```

An undisclosed assumption is a defect.

---

# 11. GATE 3 — SEMANTIC NORMALIZATION

Produce the mathematical statement in standard notation.

Example:

```text
SOURCE:

Card Ω = 301994a + 17087915b + 85137581c
```

becomes a fully typed statement defining:

* \(\Omega\);
* \(a,b,c\);
* domains;
* cardinality interpretation;
* equality interpretation;
* all constraints.

The normalized statement must be understandable without reading Lean.

### Required status

```text
MATCH
PARTIAL
MISMATCH
UNCLEAR
```

`MISMATCH` → STOP.

`UNCLEAR` → REPAIR.

---

# 12. GATE 4 — LEAN FORMALIZATION

Create a Lean representation of the normalized claim.

Required side-by-side comparison:

| Human mathematics | Lean                 |
| ------------------ | --------------------- |
| theorem statement  | theorem declaration   |
| domain              | Lean type              |
| assumptions         | hypotheses             |
| definitions         | definitions            |
| conclusion          | proposition            |

The engine must detect:

* stronger statement;
* weaker statement;
* altered domain;
* missing hypothesis;
* extra hypothesis;
* changed quantifier;
* changed equality;
* changed function;
* changed coercion;
* finite/infinite mismatch;
* exact/approximate mismatch.

Allowed semantic statuses:

```text
MATCH
STRONGER
WEAKER
DIFFERENT
FAILED
```

Only `MATCH` passes the formalization gate.

---

# 13. GATE 5 — LEAN BUILD

Use the project's actual Lean environment.

Required artifacts:

```text
lean-toolchain
lakefile.*
lake-manifest.json
Lean source
build log
Lean version
Mathlib version/commit
Git revision
```

The project's `lean-toolchain` must be respected. Lean documentation explicitly recommends a specific version in this file so developers use the same toolchain.

Required command:

```bash
lake build
```

The system records:

* command;
* exit code;
* stdout;
* stderr;
* duration;
* environment;
* Git state.

Lake tracks dependency/input hashes and build artifacts, making the build system itself useful for reproducibility evidence.

### Required conditions

* exit code = 0;
* no `sorry`;
* no `admit`;
* no unresolved declarations;
* no hidden local modifications.

---

# 14. GATE 6 — AXIOM AUDIT

Run:

```lean
#print axioms theoremName
```

Record every dependency.

Classify:

```text
KERNEL_STANDARD
MATHLIB_STANDARD
CLASSICAL
PROJECT_AXIOM
EXTERNAL
UNKNOWN
```

The report must state the actual axiom footprint.

Example:

```text
Axiom footprint:

propext
Classical.choice
Quot.sound
```

A proof that compiles is not automatically a proof that uses only the intended foundations.

### MVP rule

`PROJECT_AXIOM` → FAIL

`UNKNOWN` → FAIL

`CLASSICAL` → REPORT, not automatically fail.

The distinction matters because classical reasoning may be intentional while an undeclared project axiom may materially change the trust basis.

---

# 15. GATE 7 — SEMANTIC RE-AUDIT

After formalization, repeat the semantic comparison.

This is mandatory.

Reason:

> Formalization can introduce assumptions that were invisible during initial interpretation.

The system compares:

```text
SOURCE
   ↕
NORMALIZED CLAIM
   ↕
LEAN STATEMENT
```

The second audit must explicitly search for:

* added hypotheses;
* removed hypotheses;
* strengthened conclusions;
* weakened conclusions;
* changed domains;
* coercions;
* finite/infinite substitutions;
* extensionality assumptions;
* injectivity assumptions;
* decidability assumptions;
* classical assumptions.

Any undisclosed semantic change → REPAIR.

---

# 16. GATE 8 — ADVERSARIAL / COUNTEREXAMPLE SEARCH

Counterexample testing is NOT proof.

The system searches:

1. minimal cases;
2. boundary cases;
3. degenerate cases;
4. zero cases;
5. empty structures;
6. singleton structures;
7. equality cases;
8. maximal/minimal parameter cases;
9. domain-transition cases;
10. known pathological cases.

Possible results:

```text
COUNTEREXAMPLE_FOUND
NO_COUNTEREXAMPLE_FOUND_IN_TESTED_DOMAIN
NOT_APPLICABLE
```

The second result MUST NOT be represented as:

```text
PROVEN
```

or:

```text
SUPPORTED_AS_TRUE
```

A failed counterexample search is diagnostic evidence only.

---

# 17. GATE 9 — INDEPENDENT CHECK

Where technically supported, execute a second verification route.

Possible checkers:

* Lean kernel replay;
* `leanchecker`;
* nanoda;
* independent proof checker;
* clean-room rebuild;
* second formalization.

Lean itself includes `leanchecker`, which replays elaboration results from `.olean` files through the Lean kernel.

For high-assurance workflows, an external checker can provide an additional trust boundary.

However, the system must record the exact checker/version.

The Lean 4.32.2 security release explicitly notes that nanoda avoided the particular kernel bug fixed there, while also noting that nanoda itself had a separate bug that was fixed. Therefore the engine must never treat "uses nanoda" as synonymous with "independent verification completed."

Possible result:

```text
INDEPENDENTLY_CHECKED
CHECKER_UNAVAILABLE
CHECKER_INCOMPATIBLE
CHECKER_DISAGREEMENT
NOT_APPLICABLE
```

---

# 18. GATE 10 — COMPUTATIONAL CHECK

MATLAB is a computational verification backend.

It may perform:

* symbolic simplification;
* symbolic equality checks;
* assumption-aware reasoning;
* numerical evaluation;
* parameter sweeps;
* boundary tests;
* randomized tests;
* unit tests;
* sensitivity analysis;
* counterexample searches.

MATLAB Symbolic Math Toolbox supports symbolic expressions, simplification, solving, calculus, and exact symbolic computation.

MATLAB also supports explicit assumptions on variables and expressions, including integer, rational, real, and positive domains.

MATLAB's unit-testing framework supports script-, function-, and class-based tests, assertions, constraints, diagnostics, and parameterization.

### Critical rule

MATLAB evidence is classified as:

```text
COMPUTATIONAL_TEST
```

not:

```text
FORMAL_PROOF
```

unless a separately formalized proof establishes the corresponding result.

---

# 19. COMPUTATIONAL BACKEND ABSTRACTION

The engine should NOT hard-code MATLAB into its epistemic architecture.

Define:

```text
COMPUTATIONAL_BACKEND
```

with implementations such as:

```text
MATLAB
Python/SymPy
SageMath
Julia
Wolfram
custom numerical engine
```

The MVP may use MATLAB.

The architecture must remain backend-independent.

---

# 20. GATE 11 — EVIDENCE GRAPH

Every substantive event becomes a graph node.

### Node types

```text
SOURCE
CLAIM
ASSUMPTION
DEFINITION
SYMBOL
NORMALIZED_CLAIM
FORMAL_STATEMENT
FORMAL_PROOF
BUILD
AXIOM_AUDIT
COMPUTATIONAL_MODEL
COMPUTATIONAL_TEST
COUNTEREXAMPLE_SEARCH
ADVERSARIAL_TEST
INDEPENDENT_CHECK
SEMANTIC_AUDIT
RECEIPT
DECISION
FAILURE
REPAIR
COST
```

### Edge types

```text
DERIVED_FROM
TRANSFORMS
DEPENDS_ON
JUSTIFIES
TESTS
SUPPORTS
CONTRADICTS
INVALIDATES
REPAIRS
PRODUCES
RECHECKS
SUPERSEDES
```

---

# 21. EVIDENCE CLASS

Every evidence-producing node receives:

```text
EVIDENCE_CLASS
```

Allowed values:

```text
SOURCE_ASSERTION
HUMAN_REVIEW
FORMAL_PROOF
FORMAL_AXIOM_AUDIT
SEMANTIC_COMPARISON
COMPUTATIONAL_TEST
COUNTEREXAMPLE_ATTEMPT
INDEPENDENT_REPLICATION
REPRODUCIBILITY_CHECK
```

This prevents epistemic category errors.

For example:

```text
COMPUTATIONAL_TEST
```

cannot be silently promoted into:

```text
FORMAL_PROOF
```

---

# 22. REASON FIELD

Every substantive graph transition must include a machine-readable reason.

Example:

```json
{
  "event": "EVT-017",
  "action": "FORMALIZE",
  "reason": "Convert normalized claim into a kernel-checkable proposition",
  "input": "CLAIM-001",
  "output": "FORMAL-001",
  "method": "Lean 4",
  "result": "MATCH"
}
```

The system records **decision rationale**, not private model chain-of-thought.

It should not attempt to expose hidden internal reasoning.

---

# 23. TWO DIAGRAMS ONLY

The public mathematician-facing report contains exactly two diagrams.

## Diagram 1 — Proof Dependency Diagram

Shows:

```text
Definition
   ↓
Lemma 1
   ↓
Lemma 2
   ↓
Product Formula
   ↓
Sandwich Inequality
   ↓
Farey Bound
   ↓
Main Theorem
```

This diagram is theorem-specific.

It answers:

> What mathematical result depends on what?

---

## Diagram 2 — Trust / Verification Chain

Reusable diagram:

```text
SOURCE
  │
  ▼
NORMALIZED MATHEMATICS
  │
  ▼
LEAN FORMALIZATION
  │
  ▼
LEAN KERNEL
  │
  ├──────────────► AXIOM AUDIT
  │
  ▼
INDEPENDENT CHECKER
  │
  ▼
COMPUTATIONAL / ADVERSARIAL TESTS
  │
  ▼
EVIDENCE
  │
  ▼
VERDICT
```

This answers:

> Why should I trust the verification process?

No third process diagram should appear in the public mathematician-facing report.

---

# 24. GRAPH VIEWS

There is ONE underlying graph.

It has filtered views:

### Chronological View

What happened first, second, third?

### Evidence View

What evidence supports the claim?

### Dependency View

What depends on what?

### Reasoning View

Why was each substantive action taken?

### Failure View

Where did verification fail?

### Verification View

What checks actually passed?

These are views, not separate graphs.

---

# 25. GRAPH INTEGRITY

The graph must itself be auditable.

Every event receives:

```text
EVENT_ID
TIMESTAMP
INPUT_HASH
OUTPUT_HASH
ACTOR
ACTION
REASON
METHOD
RESULT
EVIDENCE
PARENT_EVENTS
```

The event ledger is hash chained.

Example:

```text
EVENT-001
   ↓ hash
EVENT-002
   ↓ hash
EVENT-003
   ↓ hash
...
```

The final graph receives:

```text
GRAPH_SHA256
```

---

# 26. GOVERNANCE STATES

The engine may output only:

```text
PROMOTE
REPAIR
REJECT
RESEARCH
STOP
```

### PROMOTE

Only if all mandatory gates pass.

### REPAIR

Known defect exists and has a defined repair path.

### REJECT

The formalized/source claim is unacceptable as currently stated.

### RESEARCH

Question cannot currently be resolved but remains within legitimate research scope.

### STOP

The verification process cannot continue safely or reproducibly.

### Critical rule

> Recorded failure ≠ passed gate.

A failed gate may be documented perfectly and still prevent PROMOTE.

---

# 27. TRUST STATEMENT

The report begins with exactly one concise trust statement.

Template:

> **Trust Statement.** The formal result was checked using Lean [VERSION] under the pinned project environment [ENVIRONMENT/COMMIT]. The theorem [CLAIM-ID] was kernel-checked with axiom footprint [AXIOMS]. Independent checking status is [STATUS]. Computational/adversarial testing produced [RESULT]. The remaining trust limitations are [LIMITATIONS]. This report does not claim that computational testing constitutes formal proof or that formalization alone establishes the truth of the original informal statement.

This paragraph must be factual and restrained.

No:

> "Fully verified!"

unless the defined scope actually supports that phrase.

---

# 28. LIMITATIONS TABLE

The report must contain a table like:

| Claim        | Formal Proof | Axiom Audit | Independent Check | Computational Test | Semantic Match | Limitation                     |
| ------------ | ------------- | ------------ | ------------------- | -------------------- | ---------------- | ------------------------------- |
| Lemma 1      | PASS          | PASS         | PASS                | N/A                   | MATCH             | None                             |
| Lemma 2      | PASS          | PASS         | N/A                 | PASS                  | MATCH             | Checker unavailable              |
| Main theorem | PASS          | PASS         | FAIL                | PASS                  | MATCH             | Independent check unavailable    |

This table is mandatory.

---

# 29. PROOF OUTLINE

The report must use the source's mathematical structure.

If the source contains:

```text
Lemma 2.2
Proposition 2.3
Theorem 2.4
```

the report uses those names.

It must NOT present only:

```text
theorem_foo
lemma_bar
auxiliary_17
```

Lean identifiers may appear as cross-references, but they are subordinate to the mathematical structure.

---

# 30. SEMANTIC-BRIDGE SECTION

Every theorem gets:

## Semantic Bridge

Required subsections:

### Informal Statement

What the source says.

### Normalized Statement

What the mathematics means after disambiguation.

### Lean Statement

What was actually formalized.

### Differences

Every structural difference.

### Justification

Why the difference does or does not preserve meaning.

### Verdict

```text
FAITHFUL
FAITHFUL WITH EXPLICIT REPRESENTATIONAL DIFFERENCE
PARTIAL
MISMATCH
```

No silent equivalence claims.

---

# 31. EXAMPLE OF REQUIRED BRIDGE DISCLOSURE

If the source says:

$$
\operatorname{Card}(\Omega)
=
301994a+17087915b+85137581c
$$

but Lean represents \(\Omega\) using an injective encoding, the report must explicitly state:

1. what \(\Omega\) means informally;
2. what Lean's type represents;
3. why the encoding is injective;
4. where cardinality is preserved;
5. whether the equality is literal or transported through an equivalence;
6. what assumptions make the translation valid.

This is exactly the kind of semantic issue a mathematician needs exposed.

---

# 32. MATHEMATICIAN-FACING LATEX

The final report uses standard mathematical paper conventions.

Required packages include:

```latex
\usepackage{amsmath}
\usepackage{amssymb}
\usepackage{amsthm}
\usepackage{mathtools}
\usepackage{booktabs}
\usepackage{graphicx}
\usepackage{tikz}
\usepackage{hyperref}
\usepackage{longtable}
\usepackage{array}
```

The report should use:

```latex
\newtheorem{theorem}{Theorem}
\newtheorem{lemma}[theorem]{Lemma}
\newtheorem{proposition}[theorem]{Proposition}
\newtheorem{corollary}[theorem]{Corollary}
\newtheorem{definition}[theorem]{Definition}
\newtheorem{remark}[theorem]{Remark}
```

The document should read like a mathematical paper with an explicit verification appendix, not like an engineering dashboard.

---

# 33. REQUIRED REPORT STRUCTURE

```text
TITLE

AUTHORS / VERSION / DATE

TRUST STATEMENT

ABSTRACT

1. MATHEMATICAL STATEMENT

2. DEFINITIONS AND ASSUMPTIONS

3. PROOF OUTLINE

4. PROOF DEPENDENCY DIAGRAM

5. FORMALIZATION

6. SEMANTIC BRIDGE

7. LEAN ENVIRONMENT

8. FORMAL VERIFICATION

9. AXIOM AUDIT

10. INDEPENDENT CHECK

11. COMPUTATIONAL / ADVERSARIAL TESTS

12. VERIFICATION LIMITATIONS

13. VERIFICATION MATRIX

14. TRUST / VERIFICATION CHAIN

15. REPRODUCIBILITY INSTRUCTIONS

16. CORRECTION LEDGER

17. CONCLUSION

APPENDIX A — LEAN SOURCE

APPENDIX B — TESTS

APPENDIX C — EVIDENCE RECEIPT

REFERENCES
```

---

# 34. REPRODUCIBILITY SECTION

The reader must receive actual commands.

Minimum example:

```bash
git clone <repository>
cd <repository>

cat lean-toolchain
lake --version
lean --version

lake build
```

For a theorem:

```lean
#print axioms theoremName
```

The report records:

* repository URL;
* commit;
* Lean version;
* Lake version;
* Mathlib revision;
* checker version;
* operating environment;
* dependencies;
* commands;
* expected result.

The reader must not have to trust:

> "The proof was successfully checked."

They must be given the means to reproduce that statement.

---

# 35. REPRODUCIBILITY LEVELS

Each artifact receives:

```text
R0 — Not reproducible
R1 — Source reproducible
R2 — Build reproducible
R3 — Formal verification reproducible
R4 — Independent verification reproducible
R5 — Full package reproducible
```

The report states the achieved level.

---

# 36. SECURITY BASELINE

The engine records:

```text
LEAN_VERSION
LAKE_VERSION
MATHLIB_COMMIT
CHECKER_VERSION
OS
ARCHITECTURE
GIT_COMMIT
SOURCE_HASH
GRAPH_HASH
```

The engine must flag known security-relevant toolchain issues.

Lean 4.32.2 fixed a kernel soundness vulnerability involving nested inductive types and phantom type parameters that could allow a malicious meta program to produce an invalid proof accepted by the kernel.

Therefore:

```text
SECURITY_STATUS =
    CURRENT
    OUTDATED
    VULNERABLE
    UNKNOWN
```

The system must not silently upgrade a project's environment to resolve this.

Instead:

```text
PROJECT ENVIRONMENT
        +
SECURITY ASSESSMENT
```

are reported separately.

---

# 37. CLEAN-ROOM BUILD

Where practical:

```bash
lake clean
lake build
```

The result must be recorded separately from an incremental build.

This detects reliance on stale build artifacts.

---

# 38. NO-SORRY POLICY

Search source:

```bash
grep -R "sorry\|admit" .
```

But text matching alone is insufficient.

The Lean environment must also be inspected for actual unresolved proof obligations.

A theorem cannot receive formal PASS merely because its source file contains no obvious `sorry`.

---

# 39. SOURCE-TRUTH AUDIT

Formal verification answers:

> Does Lean prove the formal proposition?

It does NOT automatically answer:

> Was the formal proposition the proposition the mathematician intended?

Therefore the engine requires a separate:

```text
SOURCE-MATHEMATICAL-CRITIQUE
```

This checks:

* statement coherence;
* assumptions;
* definitions;
* quantifiers;
* domains;
* notation;
* proof outline;
* dependency consistency;
* obvious contradiction;
* circularity;
* missing hypotheses;
* known edge cases.

---

# 40. CIRCULARITY CHECK

The engine must identify whether:

```text
THEOREM
   ↓
LEMMA
   ↓
THEOREM
```

or another dependency cycle exists.

A formal proof that imports the theorem itself or an equivalent theorem must be flagged.

---

# 41. DEPENDENCY CLOSURE

The engine reports not merely:

```text
Main theorem: PASS
```

but:

```text
Main theorem
├── Lemma A
├── Lemma B
│   ├── Definition X
│   └── Proposition Y
├── Lemma C
└── Mathlib dependency closure
```

The dependency closure must be recorded.

This is particularly important for large real-analysis or topology imports.

---

# 42. HEAVY-CLOSURE RISK

Before execution, the theorem plan should estimate whether formalization likely introduces a large dependency closure.

Flags include:

```text
REAL_ANALYSIS
MEASURE_THEORY
TOPOLOGY
INFINITE_CARDINALS
ADVANCED_ALGEBRA
CATEGORY_THEORY
QUOTIENTS
CLASSICAL_REASONING
LARGE_MATHLIB_IMPORT
```

This is a planning signal, not a correctness judgment.

---

# 43. COST LEDGER

Every run records:

```text
HUMAN_TIME
MACHINE_TIME
LEAN_BUILD_TIME
COMPUTATIONAL_TEST_TIME
MODEL_CALL_COUNT
MODEL_COST
CHECKER_TIME
LATEX_BUILD_TIME
TOTAL_COST
```

Optional:

```text
TOKENS
API_COST
ENERGY_ESTIMATE
WALL_CLOCK_TIME
```

This allows later comparison:

> How expensive was formal verification of this class of theorem?

---

# 44. MODEL ROLE SEPARATION

If LLMs are used, roles must be separated.

Minimum roles:

```text
FORMALIZER
SEMANTIC_AUDITOR
ADVERSARIAL_CRITIC
RECONSTRUCTOR
DOCUMENT_AUDITOR
SYNTHESIS
```

No model may certify its own proposal.

Model output is always:

```text
PROPOSED
```

until independently checked.

---

# 45. DISAGREEMENT HANDLING

Models do not vote.

If two models disagree:

```text
DISAGREEMENT
     ↓
NEW TEST
     ↓
EVIDENCE
     ↓
RESOLUTION
```

A majority vote cannot substitute for evidence.

---

# 46. CORRECTION LEDGER

Every correction records:

```text
CORRECTION_ID
ORIGINAL_CLAIM
ERROR
DETECTION_METHOD
ROOT_CAUSE
REPAIR
RECHECK
RESULT
DATE
HASH
```

Corrections remain in history.

They are never silently overwritten.

---

# 47. FAILURE PROPAGATION

If an upstream claim changes:

```text
CLAIM A
  ↓
LEMMA B
  ↓
THEOREM C
```

and Claim A changes, the engine marks dependent artifacts:

```text
STALE
```

They must be rechecked.

No downstream PASS survives an invalidated dependency automatically.

---

# 48. FINAL RECEIPT

Every completed theorem receives:

```text
verification-receipt.md
```

Minimum fields:

```text
THEOREM ID
SOURCE HASH
CLAIM
NORMALIZED CLAIM
LEAN STATEMENT
LEAN VERSION
MATHLIB VERSION
BUILD RESULT
AXIOM FOOTPRINT
INDEPENDENT CHECK
COMPUTATIONAL TEST
COUNTEREXAMPLE SEARCH
SEMANTIC MATCH
REPRODUCIBILITY LEVEL
GRAPH HASH
COST
FINAL DECISION
LIMITATIONS
```

A mathematician should be able to understand the result from this receipt without opening the graph.

---

# 49. REQUIRED ARTIFACT TREE

```text
verification/
│
├── source/
│   ├── original.*
│   └── source-metadata.json
│
├── plan/
│   └── THEOREM-PLAN.md
│
├── claims/
│   ├── claims.json
│   └── assumptions.json
│
├── normalized/
│   └── normalized-claim.md
│
├── lean/
│   ├── lean-toolchain
│   ├── lakefile.toml
│   ├── lake-manifest.json
│   └── theorem/
│
├── computational/
│   ├── model/
│   ├── tests/
│   └── results/
│
├── evidence/
│   ├── evidence-graph.json
│   ├── event-ledger.jsonl
│   └── hashes.json
│
├── report/
│   ├── report.tex
│   ├── report.pdf
│   └── figures/
│
├── receipt/
│   ├── verification-receipt.md
│   ├── correction-ledger-entry.md
│   └── cost-ledger-entry.md
│
└── README.md
```

---

# 50. PUBLIC DELIVERABLE

The public mathematician-facing package should contain:

```text
PDF
LaTeX source
Lean source
reproduction instructions
verification receipt
limitations table
proof dependency diagram
trust/verification chain
references
```

Internal machinery may contain:

```text
graph JSON
event ledger
model outputs
diagnostics
cost records
failure records
machine logs
```

The public report should not expose private model chain-of-thought.

---

# 51. LATEX COMPILATION REQUIREMENT

The report is not complete until:

```bash
pdflatex report.tex
pdflatex report.tex
```

both succeed.

Required:

```text
0 fatal errors
0 unresolved cross-references
0 missing citations
0 missing figures
```

Warnings must be classified.

No:

> "It compiled, so it is finished."

---

# 52. MVP ACCEPTANCE TEST

The engine is not considered implemented until it successfully completes:

```text
ONE THEOREM
ONE SOURCE
ONE LEAN PROJECT
ONE NORMALIZED CLAIM
ONE ASSUMPTION AUDIT
ONE CLEAN BUILD
ONE AXIOM AUDIT
ONE SEMANTIC RE-AUDIT
ONE COUNTEREXAMPLE ATTEMPT
ONE INDEPENDENT CHECK ATTEMPT
ONE EVIDENCE GRAPH
ONE RECEIPT
ONE COST LEDGER
ONE LATEX REPORT
ONE PDF
```

The first successful run becomes:

```text
VCE-001
```

---

# 53. MVP PASS CONDITION

The MVP passes only if:

```text
G0 PASS
AND
G1 PASS
AND
G2 PASS
AND
G3 PASS
AND
G4 PASS
AND
G5 PASS
AND
G6 PASS
AND
G7 PASS
AND
G8 COMPLETED
AND
G9 COMPLETED OR N/A WITH REASON
AND
G10 PASS
AND
G11 PASS
AND
G12 PASS
AND
G13 GOVERNANCE DECISION
```

Critically:

```text
DOCUMENTED FAILURE
≠
PASS
```

---

# 54. WHAT "VERIFIED" MEANS

The system should avoid a single unqualified word.

Instead use:

### KERNEL-VERIFIED

Lean successfully checked the formal proposition under the recorded environment.

### SEMANTICALLY MATCHED

The formal proposition was determined to match the normalized mathematical claim under the documented bridge.

### COMPUTATIONALLY SUPPORTED

Computational tests produced results consistent with the claim over the tested domain.

### INDEPENDENTLY CHECKED

A separate verification mechanism successfully reproduced the formal verification result.

### SOURCE-REVIEWED

The source mathematics was reviewed under the defined source-critique procedure.

These are separate facts.

---

# 55. EXAMPLE FINAL STATUS

Instead of:

> THEOREM VERIFIED.

Use:

```text
FORMAL PROOF:                 PASS
AXIOM AUDIT:                 PASS
SEMANTIC MATCH:              PASS
INDEPENDENT CHECK:           NOT AVAILABLE
COUNTEREXAMPLE SEARCH:       NO COUNTEREXAMPLE FOUND IN TESTED DOMAIN
COMPUTATIONAL TEST:          SUPPORTIVE
SOURCE-MATHEMATICAL REVIEW:  COMPLETE
REPRODUCIBILITY:             R3
GOVERNANCE DECISION:         PROMOTE
```

This is much more informative to an expert reader.

---

# 56. REQUIRED FILES FOR THE DOCUMENTATION LAYER

The implementation should create exactly the following foundational documents:

```text
THEOREM-PLAN-TEMPLATE.md

MATHEMATICIAN-DELIVERABLE-GUIDE.md

deliverable/
├── report-template.tex
├── verification-architecture.svg
└── proof-dependency-diagram.md
```

Additionally, implementation requires:

```text
SPECIFICATION.md
SCHEMA.md
VERIFICATION-RECEIPT-TEMPLATE.md
CORRECTION-LEDGER-TEMPLATE.md
COST-LEDGER-TEMPLATE.md
README.md
```

---

# 57. MATHEMATICIAN-DELIVERABLE-GUIDE — BINDING RULES

The public deliverable must obey these eight rules:

1. **Real mathematics before Lean.**
2. **Semantic bridge is mandatory.**
3. **Proof outline follows the source's mathematics.**
4. **Trust Statement appears first.**
5. **Reproduction instructions are exact.**
6. **Exactly two diagrams.**
7. **Limitations appear in a table.**
8. **LaTeX reads like mathematics, not an engineering status dashboard.**

These are presentation invariants.

---

# 58. THE TWO-TRACK EPISTEMIC MODEL

The architecture is:

```text
                CLAIM
                  │
          ┌───────┴────────┐
          │                │
       FORMAL           EMPIRICAL
          │                │
        LEAN           EXPERIMENT
          │                │
      KERNEL           DATA/TEST
          │                │
       AXIOMS          ANALYSIS
          │                │
   INDEPENDENT        BOUNDED
      CHECK            RESULT
          │                │
          └───────┬────────┘
                  │
          SEMANTIC BRIDGE
                  │
             FINAL REPORT
```

The two branches must not be conflated.

---

# 59. DESIGN INVARIANTS

The engine must enforce these invariants:

### INV-01

Original source is immutable.

### INV-02

Every claim has a unique ID.

### INV-03

Every claim has a type.

### INV-04

Every formal claim has an explicit normalized form.

### INV-05

Every formalization has a semantic comparison.

### INV-06

Every formal proof has an axiom audit.

### INV-07

Every computational test is labeled computational evidence.

### INV-08

Counterexample absence is never proof.

### INV-09

Model output is never automatically evidence.

### INV-10

Failures remain in the ledger.

### INV-11

Changed dependencies invalidate downstream results.

### INV-12

PROMOTE requires mandatory gates to PASS.

### INV-13

The public report contains exactly two diagrams.

### INV-14

Every final report is reproducible from the recorded environment.

### INV-15

No compiled PDF means no completed mathematician-facing deliverable.

---

# 60. IMPLEMENTATION PRIORITY

Do NOT build the entire automation system first.

Build in this order:

```text
1. VCE-001 manual execution
        ↓
2. Evidence schema
        ↓
3. Claim/assumption extraction
        ↓
4. Lean execution wrapper
        ↓
5. Axiom audit
        ↓
6. Semantic comparison
        ↓
7. Computational backend
        ↓
8. Independent checker
        ↓
9. Evidence graph
        ↓
10. Automated receipt
        ↓
11. Automated LaTeX report
        ↓
12. Batch theorem execution
```

The first objective is not scale.

It is proving that one complete verification path works.

---

# 61. FINAL ACCEPTANCE TEST

The system is considered real only when a mathematician can receive:

```text
report.pdf
```

and answer, without speaking to the builder:

1. What exactly is being claimed?
2. What assumptions are required?
3. What does the Lean theorem actually say?
4. Does it match the mathematics?
5. What exactly did Lean prove?
6. What axioms were used?
7. Was an independent check performed?
8. What computational tests were performed?
9. What did those tests NOT establish?
10. What remains uncertain?
11. Can I reproduce the result?
12. What is the exact final status?

If the report cannot answer those twelve questions, the deliverable is incomplete.

---

# 62. FINAL ARCHITECTURAL STATEMENT

The Formal Claim Verification Engine is therefore not:

> "Put theorem into Lean and see if it compiles."

It is:

> **A provenance-preserving claim-integrity system that separates source meaning, mathematical interpretation, formal proof, computational evidence, independent checking, reproducibility, and governance while preserving the complete evidence path between them.**

Its central invariant is:

$$
\boxed{
\text{CLAIM}
\rightarrow
\text{INTERPRETATION}
\rightarrow
\text{FORMALIZATION}
\rightarrow
\text{PROOF}
\rightarrow
\text{EVIDENCE}
\rightarrow
\text{REPRODUCTION}
\rightarrow
\text{DECISION}
}
$$

And the governing rule is:

$$
\boxed{
\text{The model can propose. The formal system can check. The experiment can challenge. The evidence decides.}
}
$$
