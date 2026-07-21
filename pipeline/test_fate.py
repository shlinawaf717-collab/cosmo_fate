"""Unit tests for the §5/A-005 fate classifier.

Run: .venv/bin/python pipeline/test_fate.py

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
    # A-005: finite-limit epsilon is a flag only, never a fate label.
    ("finite phantom near boundary",
     dict(omegam=0.31, H0=67.7, w0=-1.007, wa=0.0, w_inf=-1.007), "RIP", True),
    ("finite quintessence near boundary",
     dict(omegam=0.31, H0=67.7, w0=-0.993, wa=0.0, w_inf=-0.993), "DECAY", True),
    ("finite exact Lambda",
     dict(omegam=0.31, H0=67.7, w0=-1.0, wa=0.0, w_inf=-1.0), "DS", True),
    # frozen-criterion limitation cases (documented above):
    ("wCDM -0.98 (audit)", dict(omegam=0.31, H0=67.7, w0=-0.98, wa=0.0), "OTHER", None),
    ("wCDM -1.2  (audit)", dict(omegam=0.31, H0=67.7, w0=-1.2, wa=0.0),  "OTHER", None),
]

def evaluate_cases():
    results = []
    for name, kw, want, want_b in CASES:
        lab, boundary = classify(Background(**kw))
        ok = lab == want and (want_b is None or boundary == want_b)
        results.append((name, lab, boundary, want, want_b, ok))
    return results


def test_frozen_classifier_cases():
    failures = [row for row in evaluate_cases() if not row[-1]]
    assert not failures, failures


def main():
    results = evaluate_cases()
    for name, lab, boundary, want, want_b, ok in results:
        print(f"{'PASS' if ok else 'FAIL'}  {name:22s} -> {lab}{' [boundary]' if boundary else ''}"
              f"  (want {want}{'' if want_b is None else ', boundary=' + str(want_b)})")
    failures = sum(not row[-1] for row in results)
    print("ALL PASS" if failures == 0 else f"{failures} FAILURES")
    return 1 if failures else 0


if __name__ == '__main__':
    raise SystemExit(main())
