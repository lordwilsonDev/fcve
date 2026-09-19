# Gate 4: Lean Formalization Comparison — CLAIM-002

| Human mathematics (normalized) | Lean |
|---|---|
| $f(n) = n/2$ if even, $3n+1$ if odd | `def collatzStep (n : ℕ) : ℕ := if n % 2 = 0 then n / 2 else 3 * n + 1` |
| $\forall k,\ \exists m,\ f^{(m)}(2^k)=1$ | `theorem powers_of_two_reach_one : ∀ k : ℕ, ∃ m : ℕ, (collatzStep^[m]) (2 ^ k) = 1` |
| Induction on $k$, base case $2^0=1$, step: $2^{k+1}\to 2^k$ via one even step | `induction k with | zero => exact ⟨0, rfl⟩ | succ n ih => ...` — identical structure |

## Checklist

| Check | Finding |
|---|---|
| Stronger/weaker | Neither — exact match |
| Altered domain | No |
| Missing/extra hypothesis | None |
| Changed quantifier | No |
| Changed function | No — `collatzStep` is exactly $f$ as normalized |
| Coercion | None needed (pure ℕ arithmetic throughout) |
| Finite/infinite mismatch | No |

This is the simplest possible Gate 4 outcome: the Lean statement is a direct
transliteration of the normalized claim, and the proof's induction structure
matches the normalized proof step-for-step (base case `k=0`, inductive step
using `Function.iterate_succ` to peel off exactly one application of
`collatzStep`, matching the normalized argument's "$f(2^{k+1})=2^k$, then
apply the inductive hypothesis").

## Status: MATCH
