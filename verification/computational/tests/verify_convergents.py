#!/usr/bin/env python3
"""Independent recomputation of the continued-fraction convergents to
log2(3), and the specific Farey identities the Lean proof relies on.

This is a THIRD independent computation of these numbers: the 1993 paper
computed them on a Toshiba 1600 via muLISP; the Lean proof re-verifies the
resulting Farey identities via norm_num inside Lean's kernel; this script
recomputes them from scratch in Python using exact rational arithmetic
(via mpmath for the initial high-precision log2(3), then exact integer
recursion for the convergents themselves -- no floating point in the
integer arithmetic once the continued-fraction terms a_n are fixed).
"""
from mpmath import mp, log, mpf
from fractions import Fraction

mp.dps = 60  # 60 decimal digits -- comfortably enough precision for n up to 20

theta = log(3) / log(2)  # log2(3), high precision

def continued_fraction_terms(x, n_terms):
    terms = []
    for _ in range(n_terms):
        a = int(x)
        terms.append(a)
        frac = x - a
        if frac == 0:
            break
        x = 1 / frac
    return terms

terms = continued_fraction_terms(theta, 20)
print(f"Continued fraction terms a_0..a_{len(terms)-1}: {terms}")

# Standard convergent recursion: p_-2=0,p_-1=1,q_-2=1,q_-1=0
p = [0, 1]
q = [1, 0]
for a in terms:
    p.append(a * p[-1] + p[-2])
    q.append(a * q[-1] + q[-2])
# p[n+2], q[n+2] correspond to convergent index n (0-based) because of the two seed values
convergents = {n: (p[n+2], q[n+2]) for n in range(len(terms))}

for n in [13, 14, 15, 16]:
    if n in convergents:
        print(f"p_{n} = {convergents[n][0]}, q_{n} = {convergents[n][1]}")

expected = {13: 301994, 15: 17087915, 16: 85137581}
print("\n--- Checking against Eliahou's paper (Table 1, p.53) ---")
all_match = True
for n, exp_p in expected.items():
    got_p = convergents[n][0]
    ok = (got_p == exp_p)
    all_match &= ok
    print(f"p_{n}: expected {exp_p}, independently recomputed {got_p} -> {'MATCH' if ok else 'MISMATCH'}")

print("\n--- Checking Farey identities used in Collatz/LinearForm.lean ---")
p13, q13 = convergents[13]
p15, q15 = convergents[15]
p16, q16 = convergents[16]

farey_15_16 = p15 * q16 - p16 * q15
farey_13_15 = p13 * q15 - p15 * q13
print(f"farey_15_16: p15*q16 - p16*q15 = {farey_15_16} (Lean claims 17087915*53715833 - 85137581*10781274 = 1)")
print(f"farey_13_15: p13*q15 - p15*q13 = {farey_13_15} (used analogously in Lean)")
all_match &= (abs(farey_15_16) == 1)
all_match &= (abs(farey_13_15) == 1)

print("\n--- Adversarial / boundary checks (exact rational vs. high-precision theta) ---")
# IMPORTANT: comparing native-float ratios against native-float theta is not
# precise enough here -- p16/q16 and log2(3) agree to ~16 significant digits
# (that's the whole point of a good convergent), which is at or past float64's
# precision limit. Using mpmath's mpf at 60 digits, and exact Fraction for the
# rational side, avoids a false "mismatch" from the test's own precision loss.
r16 = mpf(p16) / mpf(q16)
r15 = mpf(p15) / mpf(q15)
r13 = mpf(p13) / mpf(q13)
print(f"p16/q16 = {r16}")
print(f"log2(3) = {theta}")
print(f"p15/q15 = {r15}")
print(f"p16/q16 < log2(3) ? {r16 < theta}")
print(f"log2(3) < p15/q15 ? {theta < r15}")
print(f"p15/q15 < p13/q13 ? {r15 < r13}")
all_match &= (r16 < theta < r15 < r13)

print(f"\nOVERALL: {'ALL CHECKS PASS' if all_match else 'MISMATCH FOUND -- STOP'}")
