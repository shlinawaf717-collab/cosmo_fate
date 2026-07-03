"""Unit tests for the §5 fate classifier. Run: .venv/bin/python pipeline/test_fate.py

Known, documented limitations of the FROZEN §5 criteria (not bugs, no amendment):
constant-w curves (wa == 0 exactly) are measure-zero in the CPL posterior and
partly land in OTHER — e.g. wCDM w=-0.98 (quasi-Lambda, neither DS-tight nor
decaying at a_max) and wCDM w=-1.2 (power-law phantom: true finite-time rip,
but tail convergence at a_max=1e4 is slower than the frozen rip_rel=1e-3).
Both go to OTHER -> manual-audit channel; posterior mass in the |wa|<3e-4 band
is ~1e-3, within the 1% OTHER budget of §5. If real-data OTHER > 1%, §5 itself
triggers the revision process.
"""

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from pipeline.fate import Background, classify

CASES = [
    # (name, params, expected_label, expected_boundary_or_None=any)
    ("LCDM",             dict(omegam=0.31, H0=67.7, w0=-1.0, wa=0.0),   "DS", False),
    ("phantom wa>0",     dict(omegam=0.31, H0=67.7, w0=-1.0, wa=0.5),   "RIP", None),
    ("DR2 best fit",     dict(omegam=0.311, H0=67.6, w0=-0.854, wa=-0.520), "DECAY", None),
    ("mild thaw",        dict(omegam=0.31, H0=67.7, w0=-1.0, wa=-0.1),  "DECAY", None),
    ("closed + decay",   dict(omegam=0.31, H0=67.7, omk=-0.2, w0=-0.8, wa=-0.5), "CRUNCH", None),
    ("near-DS boundary", dict(omegam=0.31, H0=67.7, w0=-1.007, wa=0.0), "DS", True),
    # frozen-criterion limitation cases (documented above):
    ("wCDM -0.98 (audit)", dict(omegam=0.31, H0=67.7, w0=-0.98, wa=0.0), "OTHER", None),
    ("wCDM -1.2  (audit)", dict(omegam=0.31, H0=67.7, w0=-1.2, wa=0.0),  "OTHER", None),
]

fails = 0
for name, kw, want, want_b in CASES:
    lab, b = classify(Background(**kw))
    ok = lab == want and (want_b is None or b == want_b)
    fails += (not ok)
    print(f"{'PASS' if ok else 'FAIL'}  {name:22s} -> {lab}{' [boundary]' if b else ''}"
          f"  (want {want}{'' if want_b is None else ', boundary=' + str(want_b)})")
print("ALL PASS" if fails == 0 else f"{fails} FAILURES")
sys.exit(1 if fails else 0)
