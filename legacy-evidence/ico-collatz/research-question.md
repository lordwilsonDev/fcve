# Research Questions

## Central

Can an ICO-governed verification pipeline distinguish a formally compiled Lean result
from a sufficiently independently verified mathematical result?

## Secondary

1. What exactly does the formalization prove?
2. Does the theorem correspond to the claimed mathematical proposition?
3. Which axioms does the theorem depend on?
4. Does it contain `sorry` or an equivalent escape mechanism?
5. Which Lean version was used?
6. Which Mathlib revision was used?
7. Which dependencies are imported?
8. Can the project be reconstructed from a clean environment?
9. Does the current Lean kernel accept the proof?
10. Does an independent checker accept it?
11. Does the result depend on implementation-specific behavior?
12. Can an adversarially constructed proof exploit a checker weakness?
13. Can the verification chain be independently reproduced?
14. What evidence is sufficient to classify the result as TRUSTED, PROVISIONAL,
    UNRESOLVED, or REJECTED?

## Success condition

A reproducible evidence chain answering, in order: what was claimed → what was
formalized → what environment accepted it → what axioms it uses → what dependencies
it uses → whether it can be rebuilt → whether it can be checked independently →
whether the formal statement matches the mathematical claim → what adversarial
testing found → what governance decision follows → what can actually be claimed.
