#!/usr/bin/env python3
"""Scan a lean4export .export file for huge natural-number literals.

Usage: export-literal-scan.py FILE.export
First output line (machine-readable): MAX_NATVAL_DIGITS=<n> COUNT_OVER_1000=<k> [WARN ...]

Why: nat literals with millions of digits (decide/norm_num over huge exponents) make lean4export's printing and
nanoda's parsing QUADRATIC unless the fast-literal patches in ../patches/ are applied. This is the diagnosed cause of
the VCE-001 Gate 9 stall (25.6M-digit literals) -- not a 'memoization' bug. Read the number before calling a stall
a tool limitation.
"""
import re, sys
rx = re.compile(rb'"natVal":"(\d+)"')
mx = over = 0
with open(sys.argv[1], "rb") as f:
    for line in f:
        if b'"natVal"' in line:
            m = rx.search(line)
            if m:
                n = len(m.group(1)); mx = max(mx, n); over += n > 1000
warn = ""
if mx > 100_000:
    warn = " WARN=huge-literals: unpatched lean4export/nanoda are quadratic here; use the patched builds (patches/) and disclose them"
print(f"MAX_NATVAL_DIGITS={mx} COUNT_OVER_1000={over}{warn}")
