# Normalized Claim: CLAIM-001 (Eliahou's Theorem 1.1)

This statement must be understandable without reading any Lean code.

## Objects and domains

- $T : \mathbb{N} \to \mathbb{N}$, $T(n) = \begin{cases} n/2 & n \text{ even} \\ (3n+1)/2 & n \text{ odd} \end{cases}$ — the "compressed" Collatz map (odd step and the forced halving folded into one step).
- For $n \in \mathbb{N}$, the **trajectory** $\Omega(n) = \{n, T(n), T^{(2)}(n), \dots\} \subseteq \mathbb{N}$ (a *set*, not a sequence).
- $\Omega$ is a **cycle of length $k$** if $T^{(k)}(x) = x$ for every $x \in \Omega$, where **$k$ is defined to equal $\mathrm{Card}\,\Omega$** — this is a definitional identity in the source, not a separately-proved fact.
- $\Omega_1 := \{x \in \Omega : x \text{ odd}\}$.
- The **trivial cycle** is $\Omega(1) = \{1, 2\}$; a cycle is **nontrivial** iff it is not this set.
- $\theta := \log_2(3) \in \mathbb{R}$, irrational (elementary: $3$ is not a power of $2$).
- $(p_n/q_n)_{n \ge 0}$: the principal convergents to $\theta$ from its continued-fraction expansion, via the standard recursion $p_n = a_n p_{n-1} + p_{n-2}$, $q_n = a_n q_{n-1} + q_{n-2}$.
- Two fractions $(p/q), (p'/q')$ (nonnegative integers) form a **Farey pair** if $pq' - p'q = \pm 1$.

## The claim

**Given**: $\Omega$ a nontrivial cycle of $T$, with $\min \Omega > 2^{40}$.

**Conclusion**: there exist nonnegative integers $a, b, c$ with $b > 0$ and $ac = 0$ such that
$$
\mathrm{Card}\,\Omega = 301994\,a + 17087915\,b + 85137581\,c.
$$

The three constants are not arbitrary — they are specific convergents of $\theta = \log_2 3$: $p_{13} = 301994$, $p_{15} = 17087915$, $p_{16} = 85137581$.

## Why this is true (the actual argument, normalized)

1. From an earlier result (the "sandwich inequality", $\mathrm{Card}\,\Omega / \mathrm{Card}\,\Omega_1 \in (\log_2(3+1/M), \log_2(3+1/m)]$ where $m=\min\Omega, M=\max\Omega$), and the hypothesis $\min\Omega > 2^{40}$, one gets $k/l \in [\log_2 3,\ \log_2(3+2^{-40})]$ where $k=\mathrm{Card}\,\Omega,\ l=\mathrm{Card}\,\Omega_1$.
2. Numerically (via the continued-fraction machinery), that whole interval is sandwiched strictly between three specific convergents: $p_{16}/q_{16} < \log_2 3 < p_{15}/q_{15} < \log_2(3+2^{-40}) < p_{13}/q_{13}$.
3. So $k/l$ must land in one of exactly three places relative to those convergents, and a general lemma about Farey pairs (any fraction strictly between two Farey-paired fractions $p/q, p'/q'$ has the form $(ap+bp')/(aq+bq')$ for positive integers $a,b$) forces $k$ into one of three linear forms:
   - between $p_{16}/q_{16}$ and $p_{15}/q_{15}$: $k = 17087915\,b + 85137581\,c$
   - exactly $p_{15}/q_{15}$: $k = 17087915\,b$
   - between $p_{15}/q_{15}$ and $p_{13}/q_{13}$: $k = 301994\,a + 17087915\,b$
4. Every case includes a nonzero $b$-term (hence $b>0$ always), and no case ever produces both a nonzero $a$ and a nonzero $c$ (hence $ac=0$). Combining the three cases into one statement gives exactly the claimed form.

## Important disambiguation (not obvious from the statement alone)

- "$\mathrm{Card}\,\Omega$" is genuinely a **set cardinality** — $\Omega$ is a set of distinct positive integers, and the cycle "length" $k$ is *defined* to be that cardinality, not an independently-chosen index count that merely happens to match it. Any formalization that represents a cycle via an indexed sequence of length $L$ must separately establish that the sequence is injective before $L$ can be identified with $\mathrm{Card}\,\Omega$ — this is not free.
- Yoneda's computational verification of the Collatz conjecture up to $2^{40}$ (cited only in the paper's introduction) is **not** a hypothesis of this theorem's proof. It explains why "$\min\Omega > 2^{40}$" is the interesting remaining case, but the proof of Theorem 1.1 does not depend on that computation being correct.

## Status

**MATCH** — this normalization is a direct, complete restatement of the source's Theorem 1.1 and its proof (Sections 2-4 of the paper), independently re-derived from the primary source text (all 12 pages read), not copied from any secondary description (Lean repo README, prior AI summary, etc.). No part of the source's argument was found incoherent, circular, or underspecified.
