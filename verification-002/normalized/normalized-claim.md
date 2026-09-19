# Normalized Claim: CLAIM-002

## Objects and domains

- $f : \mathbb{N} \to \mathbb{N}$, $f(n) = \begin{cases} n/2 & n \text{ even} \\ 3n+1 & n \text{ odd} \end{cases}$ — the **standard** (uncompressed) Collatz map. (Note: this is a different map from Eliahou's compressed $T$ used in VCE-001, which folds the forced halving after an odd step into one combined step. $f$ and $T$ are related but not identical.)
- $f^{(m)}$ denotes $f$ composed with itself $m$ times.

## The claim

**Given**: $k \in \mathbb{N}$.

**Conclusion**: $\exists\, m \in \mathbb{N}$ such that $f^{(m)}(2^k) = 1$.

## Why this is true

By induction on $k$.
- **Base case** ($k=0$): $2^0 = 1$, so $m=0$ works trivially.
- **Inductive step**: assume $f^{(m)}(2^k) = 1$ for some $m$. Since $2^{k+1}$ is even, $f(2^{k+1}) = 2^{k+1}/2 = 2^k$. So $f^{(m+1)}(2^{k+1}) = f^{(m)}(f(2^{k+1})) = f^{(m)}(2^k) = 1$.

This is a completely elementary, fully constructive argument — no case analysis beyond parity, no external results needed.

## Status

**MATCH** — direct restatement, nothing to disambiguate.
