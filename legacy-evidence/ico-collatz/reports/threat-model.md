# Threat Model (Phase 4)

Defined before inspecting any target proof. The Lean kernel itself is part of the
trusted computing base — Lean 4.32.2 fixed a kernel soundness bug where a malicious
metaprogram could make the kernel accept a proof of `False`, and its release notes
recommend keeping independent checkers (e.g. `nanoda`) updated when checker
independence matters. That single fact is why this project treats "compiles" and
"is trustworthy" as different claims.

| ID  | Threat                        | Description |
|-----|--------------------------------|--------------|
| T1  | Ordinary proof error           | The mathematical reasoning is wrong. |
| T2  | Formalization mismatch         | The Lean theorem proves something different from the paper's claim. |
| T3  | Hidden axiom                   | The theorem depends on an axiom not disclosed by the headline claim. |
| T4  | `sorry`                        | An incomplete proof is present. |
| T5  | Dependency contamination       | The theorem depends on another result whose trust assumptions aren't understood. |
| T6  | Kernel vulnerability           | The checker accepts an invalid proof due to a kernel defect. |
| T7  | Independent checker vulnerability | The second checker has its own defect. |
| T8  | Build contamination            | The result depends on cached/environment-specific artifacts that can't be reconstructed. |
| T9  | Semantic ambiguity             | The theorem is technically true but doesn't establish the intended proposition. |
| T10 | Malicious proof construction   | The proof intentionally targets checker weaknesses. |

Each threat gets an explicit test in Phase 17 (Adversarial Verification) and a row
in the Proof Trust Matrix (Phase 19). A threat with no corresponding test is an
open gap, not a passed gate.
