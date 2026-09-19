#!/usr/bin/env python3
"""Independent brute-force check: does f(n)=n/2 (even) or 3n+1 (odd),
iterated from 2^k, actually reach 1, for a range of k including boundary
cases (k=0) and larger values? This is a computational sanity check, not a
proof -- but it's a genuine independent computation, in a different language
runtime, with no shared code path with the Lean proof.
"""

def f(n):
    return n // 2 if n % 2 == 0 else 3 * n + 1

def steps_to_reach_one(start, max_steps=10000):
    n = start
    for m in range(max_steps + 1):
        if n == 1:
            return m
        n = f(n)
    return None  # did not reach 1 within max_steps -- would be a real problem

print("k, 2^k, steps_to_reach_1")
all_ok = True
for k in list(range(0, 21)) + [50, 100, 500, 1000]:
    start = 2 ** k
    m = steps_to_reach_one(start)
    ok = m is not None
    all_ok &= ok
    print(f"{k}, {start if k <= 20 else f'2^{k}'}, {m if ok else 'DID NOT REACH 1 -- FAILURE'}")

# Sanity: for k>=1, expect exactly k steps (each step just halves 2^k until reaching 1)
print("\n--- Sanity check: for k>=0, steps should be exactly k (2^k -> 2^(k-1) -> ... -> 2^0=1) ---")
for k in range(0, 15):
    m = steps_to_reach_one(2 ** k)
    expected = k
    match = (m == expected)
    all_ok &= match
    print(f"k={k}: steps={m}, expected={expected} -> {'MATCH' if match else 'MISMATCH'}")

print(f"\nOVERALL: {'ALL CHECKS PASS' if all_ok else 'FAILURE FOUND'}")
