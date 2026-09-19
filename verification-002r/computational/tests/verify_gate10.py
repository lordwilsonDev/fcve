#!/usr/bin/env python3
"""Gate 10 computational check for VCE-002 (claim: for every k >= 0, iterating the standard Collatz
map f from 2^k eventually reaches 1).  Diagnostic evidence, NOT proof (spec 16, 18).

Differs from the Gate 8 script on purpose: it checks the WHOLE trajectory 2^k -> 2^(k-1) -> ... -> 1
(not just that 1 is reached), with a second, independent implementation of f, over a much larger
parameter range, and runs a CONTROL: a deliberately wrong claim ("exactly k+1 steps") that this
harness must refute, to show the harness can fail at all.
"""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "..", "scripts"))
import fcve_compute as fc

def f_arith(n):            # implementation A: arithmetic
    return n // 2 if n % 2 == 0 else 3 * n + 1

def f_bits(n):             # implementation B: independent, bit operations
    return n >> 1 if (n & 1) == 0 else (n << 1) + n + 1

def trajectory_ok(k):
    n = 1 << k
    for j in range(k, 0, -1):
        if n != (1 << j):
            return False
        a, b = f_arith(n), f_bits(n)
        if a != b or a != (1 << (j - 1)):
            return False
        n = a
    return n == 1

def steps_to_one(k, f, cap):
    n, m = 1 << k, 0
    while n != 1 and m <= cap:
        n, m = f(n), m + 1
    return m if n == 1 else None

KMAX = 5000
bad = [k for k in range(0, KMAX + 1) if not trajectory_ok(k)]
wrong_steps = [k for k in range(0, KMAX + 1, 50) if steps_to_one(k, f_arith, k + 5) != k or steps_to_one(k, f_bits, k + 5) != k]

# CONTROL: the wrong claim "reaches 1 in exactly k+1 steps" must be refuted for every tested k.
control_k = list(range(0, 51))
refuted = [k for k in control_k if steps_to_one(k, f_arith, k + 5) != k + 1]
if len(refuted) != len(control_k):
    print("HARNESS INSENSITIVE: the control (a wrong claim) was not refuted for every k", file=sys.stderr); sys.exit(2)

if bad or wrong_steps:
    fc.report("COUNTEREXAMPLE_FOUND", f"k in [0,{KMAX}]", KMAX + 1, ["minimal", "boundary", "extremal_parameters"],
              {"trajectory_failures": bad[:5], "step_count_failures": wrong_steps[:5]})
else:
    fc.report("NO_COUNTEREXAMPLE_FOUND_IN_TESTED_DOMAIN", f"every integer k in [0,{KMAX}]; full trajectory 2^k..1; two independent implementations of f",
              KMAX + 1, ["minimal", "zero", "boundary", "equality", "extremal_parameters"],
              {"control": f"wrong claim 'exactly k+1 steps' refuted for all {len(control_k)} tested k", "implementations": ["arithmetic", "bit operations"]})
