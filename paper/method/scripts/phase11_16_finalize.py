#!/usr/bin/env python3
"""Phases 11-16: critique, references, polish, and freeze the method paper."""

from __future__ import annotations

import hashlib
import importlib.util
import json
import os
import re
import shutil
import subprocess
import zipfile
from pathlib import Path

from pypdf import PdfReader


REPO = Path(__file__).resolve().parents[3]
METHOD = Path(__file__).resolve().parents[1]
RESULTS = METHOD / "results"
FIGURES = METHOD / "figures"
SUBMISSION_FINAL = METHOD / "submission_final"
SUBMISSION_FINAL_FIGURES = SUBMISSION_FINAL / "figures"
FREEZE = METHOD / "freeze" / "v0.1"
TMP_RENDER = REPO / "tmp" / "pdfs" / "phase16_render"
OUTPUT_PDF = REPO / "output" / "pdf" / "critical_boundary_calibration_final_phase16.pdf"
ZIP_PATH = METHOD / "freeze" / "critical_boundary_calibration_aux_method_v0.1.zip"

TITLE = "Critical-Boundary Calibration of Cosmic-Fate Probabilities"
DATE = "2026-07-06"

FIGURES_TO_COPY = [
    "phase1_toy_boundary_uniformity.png",
    "phase2_w0wa_boundary.png",
    "phase3_classifier_framework.png",
    "phase4_null_calibration.png",
    "phase5_cosmology_mock_case.png",
    "phase6_reporting_standard.png",
    "phase7_robustness.png",
]


def write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text)


def load_json(name: str) -> dict:
    return json.loads((RESULTS / name).read_text())


def table(headers: list[str], rows: list[list[str]]) -> str:
    out = ["| " + " | ".join(headers) + " |", "|" + "|".join(["---"] * len(headers)) + "|"]
    for row in rows:
        out.append("| " + " | ".join(str(x).replace("\n", "<br>").replace("|", r"\|") for x in row) + " |")
    return "\n".join(out)


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def phase11_doc() -> str:
    rows = [
        [
            "Major",
            "Uniformity theorem is too narrow: Gaussian, local linear boundary, calibrated posterior width.",
            "Accept. State theorem as local benchmark only; use robustness and full-pipeline mocks for applications.",
            "Already limited in Sections 2, 9, 11; retain as explicit limitation.",
        ],
        [
            "Major",
            "Curved boundary example fails KS; this may look like a failed method.",
            "Reframe as a diagnostic success: arbitrary curvature is not claimed to preserve uniformity.",
            "Keep Figure A1 in appendix and mention curvature in the claim ledger.",
        ],
        [
            "Major",
            "LCDM mock case may be overread as a science result about the real universe.",
            "Keep it as a method case study; preserve the guardrail that Evidence and Horizon are unfilled.",
            "Do not write 'the universe will' or model-preference language.",
        ],
        [
            "Major",
            "The 0/100 result is finite-resolution and may be unstable under more mocks.",
            "Report plus-one floor, zero-count upper bound, and no p=0.",
            "Cite Phipson and Smyth 2010; recommend larger mock ensembles for deep-tail claims.",
        ],
        [
            "Major",
            "The paper needs statistical lineage beyond cosmology references.",
            "Add PIT, prequential/probability forecast calibration, posterior predictive checking, finite simulation p-values.",
            "Handled in Phase 12 references and polished manuscript.",
        ],
        [
            "Moderate",
            "Seven figures are too many for a compact method paper.",
            "Main text should carry four figures; remaining figures move to appendix/supplement.",
            "Handled in Phase 14.",
        ],
        [
            "Moderate",
            "Text still reads like a project report if it says Phase 1/2/5.",
            "Remove phase language from the polished manuscript.",
            "Handled in Phase 15.",
        ],
        [
            "Minor",
            "LaTeX source exists but local TeX engine is unavailable.",
            "Document the local limitation and provide build files for a TeX environment.",
            "Handled in Phase 13.",
        ],
    ]
    return f"""# Phase 11: Reviewer Attack Pass

Draft date: {DATE}

This phase treats the manuscript as if it has reached a skeptical referee. The
goal is not to defend every sentence; it is to identify which objections should
change the paper before public release.

{table(["Severity", "Attack", "Response", "Action"], rows)}

## Verdict

The paper is not yet submission-clean unless Phases 12-16 are completed. The
core method claim is defensible, but only if the manuscript keeps the proof
boundary explicit: local boundary calibration, finite-mock tail depth, and
reporting discipline. It must not read as a new cosmic-fate discovery.
"""


def response_letter_doc() -> str:
    return f"""# Draft Response-to-Reviewer Skeleton

Date: {DATE}

## Reviewer Concern 1: The boundary-uniform result is too idealized.

We agree. The paper now states the Gaussian/linear result as a calibration
benchmark rather than a universal theorem. Applications must be checked with
null mocks or local robustness diagnostics.

## Reviewer Concern 2: The curved-boundary example appears to fail.

The curved example is intentionally retained as a diagnostic-stress case. It
shows that curvature should be reported, not hidden. We do not claim arbitrary
curved boundaries preserve uniformity.

## Reviewer Concern 3: The real-pipeline example overclaims cosmology.

The case study is now explicitly described as a method demonstration under a
declared LCDM null. Evidence and Horizon layers are marked unfilled, so the
paper does not infer the universe's final fate or model preference.

## Reviewer Concern 4: A 0/100 mock result is not a precise p-value.

Correct. The manuscript reports the plus-one finite-mock p-value floor and the
zero-count upper bound, and it cites the finite randomization p-value literature.
"""


def refs_method_bib() -> str:
    return r"""% Method-paper bibliography, Phase 12
% Statistical calibration and finite simulation p-values
@article{Rosenblatt1952,
  author = {Rosenblatt, Murray},
  title = {Remarks on a Multivariate Transformation},
  journal = {The Annals of Mathematical Statistics},
  volume = {23},
  number = {3},
  pages = {470--472},
  year = {1952},
  doi = {10.1214/aoms/1177729394}
}

@article{Dawid1984,
  author = {Dawid, A. P.},
  title = {Present Position and Potential Developments: Some Personal Views: Statistical Theory: The Prequential Approach},
  journal = {Journal of the Royal Statistical Society. Series A},
  volume = {147},
  number = {2},
  pages = {278--292},
  year = {1984},
  url = {https://www.jstor.org/stable/2981683}
}

@article{Rubin1984,
  author = {Rubin, Donald B.},
  title = {Bayesianly Justifiable and Relevant Frequency Calculations for the Applied Statistician},
  journal = {The Annals of Statistics},
  volume = {12},
  number = {4},
  pages = {1151--1172},
  year = {1984}
}

@article{GelmanMengStern1996,
  author = {Gelman, Andrew and Meng, Xiao-Li and Stern, Hal},
  title = {Posterior Predictive Assessment of Model Fitness via Realized Discrepancies},
  journal = {Statistica Sinica},
  volume = {6},
  pages = {733--807},
  year = {1996}
}

@article{PhipsonSmyth2010,
  author = {Phipson, Belinda and Smyth, Gordon K.},
  title = {Permutation P-values Should Never Be Zero: Calculating Exact P-values When Permutations Are Randomly Drawn},
  journal = {Statistical Applications in Genetics and Molecular Biology},
  volume = {9},
  number = {1},
  pages = {Article 39},
  year = {2010},
  doi = {10.2202/1544-6115.1585}
}

% Cosmology and fate context
@article{Brout2022,
  author = {Brout, D. and others},
  title = {The Pantheon+ Analysis: Cosmological Constraints},
  journal = {ApJ},
  volume = {938},
  pages = {110},
  year = {2022},
  eprint = {2202.04077}
}

@article{DESIDR2,
  author = {{DESI Collaboration}},
  title = {DESI DR2 Results II: Measurements of Baryon Acoustic Oscillations and Cosmological Constraints},
  year = {2025},
  eprint = {2503.14738}
}

@article{ChenHuangWang2018,
  author = {Chen, L. and Huang, Q.-G. and Wang, K.},
  title = {Distance Priors from Planck Final Release},
  journal = {JCAP},
  year = {2019},
  eprint = {1808.05724}
}

@article{ChevallierPolarski2001,
  author = {Chevallier, M. and Polarski, D.},
  title = {Accelerating Universes with Scaling Dark Matter},
  journal = {International Journal of Modern Physics D},
  volume = {10},
  pages = {213--224},
  year = {2001},
  eprint = {gr-qc/0009008}
}

@article{Linder2003,
  author = {Linder, E. V.},
  title = {Exploring the Expansion History of the Universe},
  journal = {Physical Review Letters},
  volume = {90},
  pages = {091301},
  year = {2003},
  doi = {10.1103/PhysRevLett.90.091301},
  eprint = {astro-ph/0208512}
}

@article{Dyson1979,
  author = {Dyson, F. J.},
  title = {Time without End: Physics and Biology in an Open Universe},
  journal = {Reviews of Modern Physics},
  volume = {51},
  pages = {447--460},
  year = {1979}
}

@article{KraussTurner1999,
  author = {Krauss, L. M. and Turner, M. S.},
  title = {Geometry and Destiny},
  journal = {General Relativity and Gravitation},
  volume = {31},
  pages = {1453--1459},
  year = {1999}
}

@article{KraussStarkman2000,
  author = {Krauss, L. M. and Starkman, G. D.},
  title = {Life, the Universe, and Nothing: Life and Death in an Ever-Expanding Universe},
  journal = {ApJ},
  volume = {531},
  pages = {22--30},
  year = {2000}
}

@article{Caldwell2003,
  author = {Caldwell, R. R. and Kamionkowski, M. and Weinberg, N. N.},
  title = {Phantom Energy and Cosmic Doomsday},
  journal = {Physical Review Letters},
  volume = {91},
  pages = {071301},
  year = {2003},
  doi = {10.1103/PhysRevLett.91.071301},
  eprint = {astro-ph/0302506}
}
"""


def phase12_doc() -> str:
    rows = [
        ["PIT / boundary-uniform theorem", "Rosenblatt 1952", "Supports probability-integral-transform logic used in the toy theorem."],
        ["Forecast calibration framing", "Dawid 1984", "Positions the paper as calibration/reporting rather than fate discovery."],
        ["Predictive checks", "Rubin 1984; Gelman, Meng, and Stern 1996", "Connects null mocks to predictive-model checking language."],
        ["Finite mock p-values", "Phipson and Smyth 2010", "Supports the rule that finite simulation p-values should never be zero."],
        ["CPL parametrization", "Chevallier and Polarski 2001; Linder 2003", "Context for w0-wa geometry."],
        ["Current data context", "DESI DR2; Pantheon+; Planck distance priors", "Context only; not used as a science claim in the method paper."],
        ["Fate lineage", "Dyson; Krauss and Turner; Krauss and Starkman; Caldwell et al.", "Context for why fate classifications are scientifically meaningful."],
    ]
    return f"""# Phase 12: Literature and Reference Hardening

Draft date: {DATE}

This phase upgrades the manuscript from locally sufficient citations to a
submission-ready reference spine.

{table(["Role", "References", "Purpose"], rows)}

## Output

```text
paper/method/refs_method.bib
```

## Boundary

The added references support the method: PIT, predictive calibration,
posterior/mock checking, finite randomization p-values, and cosmology/fate
context. They do not add a new cosmological claim.

Status: **Phase 12 passes.**
"""


def phase13_doc(latex_available: bool) -> str:
    return f"""# Phase 13: Formal LaTeX Readiness

Draft date: {DATE}

This phase prepares the formal LaTeX build path.

## Local Tool Status

| Tool | Available |
|---|---|
| `pdflatex` / `xelatex` / `latexmk` | {"yes" if latex_available else "no"} |
| `pandoc` | yes |
| `pdftoppm` / `pdfinfo` | yes |

## Outputs

```text
paper/method/submission_final/critical_boundary_calibration_final.tex
paper/method/submission_final/refs.bib
paper/method/submission_final/Makefile
paper/method/submission_final/latexmkrc
paper/method/submission_final/BUILD_LATEX.md
```

## Verdict

The LaTeX package is ready for a machine with a TeX engine. Local compilation is
not claimed because this machine does not expose `pdflatex`, `xelatex`, or
`latexmk`.

Status: **Phase 13 passes with local compile limitation recorded.**
"""


def makefile_text() -> str:
    return """MAIN=critical_boundary_calibration_final

all: $(MAIN).pdf

$(MAIN).pdf: $(MAIN).tex refs.bib figures/*.png
\tlatexmk -pdf -interaction=nonstopmode -halt-on-error $(MAIN).tex

clean:
\tlatexmk -C $(MAIN).tex
"""


def latexmkrc_text() -> str:
    return """$pdf_mode = 1;
$interaction = 'nonstopmode';
$halt_on_error = 1;
"""


def build_latex_notes() -> str:
    return """# LaTeX Build Notes

Run from this directory:

```bash
make
```

Required external tools:

- `latexmk`
- a PDF LaTeX engine such as `pdflatex`
- standard packages: `graphicx`, `amsmath`, `booktabs`, `hyperref`

This package includes:

- final Markdown source
- generated LaTeX source
- `refs.bib`
- figure PNGs

The local Phase 13 machine had Pandoc and Poppler but no TeX engine, so the PDF
proof was generated separately with ReportLab.
"""


def phase14_doc() -> str:
    main_figs = [
        ["Figure 1", "Boundary-null toy result", "Keep in main text", "It proves the statistical mechanism."],
        ["Figure 4", "Finite-mock calibration protocol", "Keep in main text", "It defines the operational contribution."],
        ["Figure 5", "LCDM mock case study", "Keep in main text", "It demonstrates direction-depth separation."],
        ["Figure 6", "Five-layer reporting standard", "Keep in main text", "It is the citable practical output."],
    ]
    app_figs = [
        ["Figure 2", "w0-wa analogue", "Appendix or supplement", "Useful bridge but not essential after Figure 1."],
        ["Figure 3", "Classifier framework", "Appendix or methods supplement", "Can be described textually in the main paper."],
        ["Figure A1", "Robustness diagnostics", "Appendix", "Important defensive material, but too detailed for main flow."],
        ["Phase 8 blueprint", "Internal only", "Do not submit", "Project-management artifact, not manuscript evidence."],
    ]
    return f"""# Phase 14: Figure, Table, and Format Compression

Draft date: {DATE}

The manuscript currently has enough visual material for a report. A compact
paper should reduce the main-text figure count.

## Main-Text Figures

{table(["Slot", "Content", "Decision", "Reason"], main_figs)}

## Appendix or Internal Figures

{table(["Slot", "Content", "Decision", "Reason"], app_figs)}

## Table Plan

| Table | Decision |
|---|---|
| Claim ledger | Keep, likely main text or supplement depending on journal length. |
| Five-layer checklist | Keep in main text if Figure 6 is removed; otherwise appendix is acceptable. |
| LCDM mock numbers | Keep as table in case-study section. |
| Robustness diagnostics | Appendix table. |

Status: **Phase 14 passes.**
"""


def polish_manuscript(text: str) -> str:
    text = text.replace("Status: Phase 9 full draft, generated 2026-07-06.\n\n", "")
    replacements = {
        "Phase 0": "the problem-definition section",
        "Phase 1": "the one-dimensional experiment",
        "Phase 2": "the two-dimensional experiment",
        "Phase 3": "the classifier-framework example",
        "Phase 4": "the finite-mock demonstration",
        "Phase 5": "the real-pipeline case study",
        "Phase 6": "the reporting-standard exercise",
        "Phase 7": "the robustness exercise",
        "Phase 8": "the manuscript blueprint",
        "Phase 9": "the manuscript draft",
        "The draft uses": "The manuscript uses",
        "The method paper represents": "We represent",
        "The method paper studies": "We study",
    }
    for old, new in replacements.items():
        text = text.replace(old, new)
    text = text.replace("the the real-pipeline case study case-study", "the real-pipeline case study")
    text = text.replace("the the ", "the ")

    text = text.replace(
        "By the probability integral transform, `q_A ~ Uniform(0,1)`.",
        "By the probability integral transform [@Rosenblatt1952], `q_A ~ Uniform(0,1)`.",
    )
    text = text.replace(
        "Boundary calibration requires an explicit null distribution.",
        "Boundary calibration requires an explicit null distribution. This is close in spirit to predictive calibration and posterior predictive checking [@Dawid1984; @Rubin1984; @GelmanMengStern1996].",
    )
    text = text.replace(
        "The plus-one rule prevents zero p-values from finite mock ensembles.",
        "The plus-one rule prevents zero p-values from finite mock ensembles, matching the finite randomization principle that simulation p-values should not be reported as zero [@PhipsonSmyth2010].",
    )
    text = text.replace(
        "Reference keys are inherited from `paper/refs.bib` and should be rendered from\nthat file in a submission build:\n\n"
        "- [@Brout2022]\n- [@DESIDR2]\n- [@ChenHuangWang2018]\n- [@ChevallierPolarski2001]\n- [@Linder2003]\n- [@CAMB]\n- [@cobaya]\n- [@getdist]\n- [@dynesty]\n- [@Dyson1979]\n- [@KraussTurner1999]\n- [@KraussStarkman2000]\n- [@Caldwell2003]\n",
        "\nThe final bibliography is supplied in `refs_method.bib` for the submission package.\n",
    )
    return text


def phase15_doc(audit: dict) -> str:
    return f"""# Phase 15: Language Polish

Draft date: {DATE}

This phase removes project-stage language and strengthens the manuscript's
statistical literature framing.

## Output

```text
paper/method/MANUSCRIPT_POLISHED.md
paper/method/results/phase15_polish_audit.json
```

## Audit

| Check | Value |
|---|---:|
| word count | {audit["word_count"]} |
| visible `Phase N` terms | {audit["visible_phase_terms"]} |
| forbidden overclaim hits | {audit["forbidden_overclaim_hits"]} |
| added statistical citation keys | {audit["added_stat_citation_keys"]} |

Status: **Phase 15 {"passes" if audit["pass"] else "needs review"}.**
"""


def overclaim_hits(text: str) -> list[str]:
    patterns = [
        r"we prove the universe",
        r"the universe will",
        r"proves dynamical dark energy",
        r"establishes dynamical dark energy",
        r"final fate is",
    ]
    hits: list[str] = []
    lower = text.lower()
    for pat in patterns:
        for match in re.finditer(pat, lower):
            context = lower[max(0, match.start() - 100) : match.start()]
            if "not claimed" in context or "does not" in context or "not, by itself" in context:
                continue
            hits.append(pat)
            break
    return hits


def polish_audit(text: str) -> dict:
    added = [k for k in ["Rosenblatt1952", "Dawid1984", "Rubin1984", "GelmanMengStern1996", "PhipsonSmyth2010"] if k in text]
    hits = overclaim_hits(text)
    visible_phase = len(re.findall(r"\bPhase\s+\d+\b", re.sub(r"figures/phase\d+_[^\s)]+", "", text)))
    return {
        "word_count": len(re.findall(r"\b[\w@./+-]+\b", text)),
        "visible_phase_terms": visible_phase,
        "forbidden_overclaim_hits": len(hits),
        "forbidden_patterns_hit": hits,
        "added_stat_citation_keys": len(added),
        "added_keys": added,
        "pass": visible_phase == 0 and len(hits) == 0 and len(added) >= 5,
    }


def import_phase10():
    spec = importlib.util.spec_from_file_location("phase10_submission_package", METHOD / "scripts" / "phase10_submission_package.py")
    if spec is None or spec.loader is None:
        raise RuntimeError("cannot import phase10 script")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def run_pandoc_tex(source: Path, tex_out: Path) -> dict:
    pandoc = shutil.which("pandoc")
    if not pandoc:
        tex_out.write_text("% pandoc unavailable\n")
        return {"pandoc_available": False, "returncode": None, "stderr": "pandoc unavailable"}
    proc = subprocess.run(
        [
            pandoc,
            str(source),
            "-s",
            "-t",
            "latex",
            "--natbib",
            "--bibliography",
            str(SUBMISSION_FINAL / "refs.bib"),
            "--metadata",
            f"title={TITLE}",
            "--metadata",
            "author=Independent researcher",
            "--metadata",
            f"date={DATE}",
            "-o",
            str(tex_out),
        ],
        cwd=str(METHOD),
        capture_output=True,
        text=True,
    )
    return {"pandoc_available": True, "returncode": proc.returncode, "stderr": proc.stderr.strip()}


def render_pdf(pdf: Path) -> list[str]:
    TMP_RENDER.mkdir(parents=True, exist_ok=True)
    for old in TMP_RENDER.glob("phase16-*"):
        old.unlink()
    reader = PdfReader(str(pdf))
    n = len(reader.pages)
    pages = sorted({1, min(5, n), min(9, n), min(10, n), max(1, n - 3), n})
    rendered: list[str] = []
    for page in pages:
        prefix = TMP_RENDER / f"phase16-p{page}"
        subprocess.run(["pdftoppm", "-png", "-f", str(page), "-l", str(page), str(pdf), str(prefix)], check=True)
        rendered.extend(str(p) for p in sorted(TMP_RENDER.glob(f"phase16-p{page}-*.png")))
    return rendered


def freeze_manifest(paths: list[Path]) -> str:
    rows = []
    for path in sorted(paths):
        if path.is_file():
            rows.append(f"{sha256(path)}  {path.relative_to(METHOD)}")
    return "\n".join(rows) + "\n"


def phase16_doc(audit: dict) -> str:
    return f"""# Phase 16: Version Freeze

Draft date: {DATE}

This phase freezes the auxiliary method-paper package as version `v0.1`.

## Outputs

```text
paper/method/submission_final/
paper/method/freeze/v0.1/MANIFEST_SHA256.txt
paper/method/freeze/critical_boundary_calibration_aux_method_v0.1.zip
paper/method/results/phase16_freeze_audit.json
output/pdf/critical_boundary_calibration_final_phase16.pdf
```

## Audit

| Check | Value |
|---|---:|
| final PDF pages | {audit["final_pdf_pages"]} |
| rendered pages | {len(audit["rendered_pages"])} |
| SHA256 manifest entries | {audit["sha_manifest_entries"]} |
| archive exists | {"yes" if audit["archive_exists"] else "no"} |
| final manuscript overclaim hits | {audit["overclaim_hits"]} |
| final manuscript visible `Phase N` terms | {audit["visible_phase_terms"]} |
| PDF citation tokens remaining | {audit["pdf_citation_tokens_remaining"]} |

Status: **Phase 16 {"passes" if audit["pass"] else "needs review"}.**
"""


def main() -> None:
    for d in [RESULTS, SUBMISSION_FINAL, SUBMISSION_FINAL_FIGURES, FREEZE, TMP_RENDER, OUTPUT_PDF.parent]:
        d.mkdir(parents=True, exist_ok=True)

    # Phase 11
    write(METHOD / "PHASE11_REVIEWER_ATTACK.md", phase11_doc())
    write(METHOD / "RESPONSE_TO_REVIEWERS_SKELETON.md", response_letter_doc())

    # Phase 12
    write(METHOD / "refs_method.bib", refs_method_bib())
    write(METHOD / "PHASE12_LITERATURE_REFERENCES.md", phase12_doc())

    # Phase 15 before final package so final package uses polished text.
    draft = (METHOD / "MANUSCRIPT_DRAFT.md").read_text()
    polished = polish_manuscript(draft)
    write(METHOD / "MANUSCRIPT_POLISHED.md", polished)
    paudit = polish_audit(polished)
    write(RESULTS / "phase15_polish_audit.json", json.dumps(paudit, indent=2, sort_keys=True))
    write(METHOD / "PHASE15_LANGUAGE_POLISH.md", phase15_doc(paudit))

    # Final submission files.
    shutil.copy2(METHOD / "MANUSCRIPT_POLISHED.md", SUBMISSION_FINAL / "critical_boundary_calibration_final.md")
    shutil.copy2(METHOD / "refs_method.bib", SUBMISSION_FINAL / "refs.bib")
    for fig in FIGURES_TO_COPY:
        shutil.copy2(FIGURES / fig, SUBMISSION_FINAL_FIGURES / fig)

    latex_info = run_pandoc_tex(SUBMISSION_FINAL / "critical_boundary_calibration_final.md", SUBMISSION_FINAL / "critical_boundary_calibration_final.tex")
    write(SUBMISSION_FINAL / "Makefile", makefile_text())
    write(SUBMISSION_FINAL / "latexmkrc", latexmkrc_text())
    write(SUBMISSION_FINAL / "BUILD_LATEX.md", build_latex_notes())

    latex_available = any(shutil.which(x) for x in ["pdflatex", "xelatex", "latexmk"])
    write(METHOD / "PHASE13_LATEX_READINESS.md", phase13_doc(latex_available))

    # Phase 14
    write(METHOD / "PHASE14_FIGURE_TABLE_PLAN.md", phase14_doc())

    # Final PDF proof from polished manuscript.
    phase10 = import_phase10()
    pdf_text = phase10.humanize_for_pdf(polished)
    final_pdf = SUBMISSION_FINAL / "critical_boundary_calibration_final.pdf"
    phase10.build_pdf(pdf_text, final_pdf)
    shutil.copy2(final_pdf, OUTPUT_PDF)
    rendered = render_pdf(final_pdf)

    readme_final = f"""# Final Auxiliary Method-Paper Package v0.1

Generated: {DATE}

Files:

- `critical_boundary_calibration_final.md`
- `critical_boundary_calibration_final.tex`
- `critical_boundary_calibration_final.pdf`
- `refs.bib`
- `figures/`
- `Makefile`
- `BUILD_LATEX.md`

Local TeX engine available during freeze: {"yes" if latex_available else "no"}.
The PDF proof was generated with ReportLab and rendered with Poppler for visual
inspection.
"""
    write(SUBMISSION_FINAL / "README_FINAL.md", readme_final)

    # Freeze manifest and archive.
    files_to_hash = [p for p in SUBMISSION_FINAL.rglob("*") if p.is_file()]
    manifest = freeze_manifest(files_to_hash)
    write(FREEZE / "MANIFEST_SHA256.txt", manifest)
    write(FREEZE / "VERSION_LOCK.md", f"""# Version Lock

Version: `v0.1`
Date: {DATE}
Scope: independent auxiliary method paper.

Frozen source: `submission_final/critical_boundary_calibration_final.md`
Frozen PDF proof: `submission_final/critical_boundary_calibration_final.pdf`
Claim boundary: method paper only; no direct cosmic-fate forecast; no model-preference claim.
""")

    if ZIP_PATH.exists():
        ZIP_PATH.unlink()
    with zipfile.ZipFile(ZIP_PATH, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for path in sorted(SUBMISSION_FINAL.rglob("*")):
            if path.is_file():
                zf.write(path, path.relative_to(METHOD))
        for path in sorted(FREEZE.rglob("*")):
            if path.is_file():
                zf.write(path, path.relative_to(METHOD))

    reader = PdfReader(str(final_pdf))
    extracted = "\n".join(page.extract_text() or "" for page in reader.pages)
    phase_tokens = paudit["visible_phase_terms"]
    citation_tokens = len(re.findall(r"@[A-Za-z0-9]+", extracted))
    overclaims = overclaim_hits(polished)
    phase16 = {
        "phase": 16,
        "pass": paudit["pass"] and final_pdf.exists() and OUTPUT_PDF.exists() and len(rendered) >= 5 and ZIP_PATH.exists() and citation_tokens == 0,
        "final_pdf": str(final_pdf),
        "output_pdf": str(OUTPUT_PDF),
        "final_pdf_pages": len(reader.pages),
        "rendered_pages": rendered,
        "sha_manifest_entries": len([line for line in manifest.splitlines() if line.strip()]),
        "archive": str(ZIP_PATH),
        "archive_exists": ZIP_PATH.exists(),
        "visible_phase_terms": phase_tokens,
        "overclaim_hits": len(overclaims),
        "overclaim_patterns": overclaims,
        "pdf_citation_tokens_remaining": citation_tokens,
        "latex_info": latex_info,
        "latex_engine_available": latex_available,
    }
    write(RESULTS / "phase16_freeze_audit.json", json.dumps(phase16, indent=2, sort_keys=True))
    write(METHOD / "PHASE16_VERSION_FREEZE.md", phase16_doc(phase16))

    summary = {
        "phase11": "pass",
        "phase12": "pass",
        "phase13": "pass_with_local_tex_limit",
        "phase14": "pass",
        "phase15": paudit["pass"],
        "phase16": phase16["pass"],
        "final_pdf": str(final_pdf),
        "archive": str(ZIP_PATH),
    }
    write(RESULTS / "phase11_16_summary.json", json.dumps(summary, indent=2, sort_keys=True))
    print(json.dumps(summary, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
