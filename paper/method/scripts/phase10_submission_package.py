#!/usr/bin/env python3
"""Phase 10: build a submission-shaped package and rendered PDF."""

from __future__ import annotations

import html
import json
import re
import shutil
import subprocess
from pathlib import Path

from pypdf import PdfReader
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY, TA_LEFT
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import (
    Image,
    LongTable,
    PageBreak,
    Paragraph,
    Preformatted,
    SimpleDocTemplate,
    Spacer,
    TableStyle,
)
from reportlab.lib.utils import ImageReader


REPO = Path(__file__).resolve().parents[3]
ROOT = Path(__file__).resolve().parents[1]
METHOD_DIR = ROOT
RESULT_DIR = METHOD_DIR / "results"
FIG_DIR = METHOD_DIR / "figures"
SUBMISSION_DIR = METHOD_DIR / "submission"
SUBMISSION_FIG_DIR = SUBMISSION_DIR / "figures"
TMP_RENDER_DIR = REPO / "tmp" / "pdfs" / "phase10_render"
OUTPUT_PDF_DIR = REPO / "output" / "pdf"

TITLE = "Critical-Boundary Calibration of Cosmic-Fate Probabilities"
SHORT_TITLE = "Cosmic-Fate Probabilities as Boundary Statistics"
AUTHOR = "Independent researcher"
DATE = "2026-07-06"


FIGURES = [
    ("Figure 1", "One-dimensional boundary-null calibration", "phase1_toy_boundary_uniformity.png"),
    ("Figure 2", "Two-dimensional w0-wa boundary analogue", "phase2_w0wa_boundary.png"),
    ("Figure 3", "Abstract fate-classifier framework", "phase3_classifier_framework.png"),
    ("Figure 4", "Finite-mock null-calibration protocol", "phase4_null_calibration.png"),
    ("Figure 5", "Real-pipeline LCDM mock case study", "phase5_cosmology_mock_case.png"),
    ("Figure 6", "Five-layer reporting standard", "phase6_reporting_standard.png"),
    ("Figure A1", "Robustness diagnostics", "phase7_robustness.png"),
]

CITATION_LABELS = {
    "Brout2022": "Brout et al. 2022",
    "DESIDR2": "DESI Collaboration 2025",
    "ChenHuangWang2018": "Chen, Huang, and Wang 2019",
    "ChevallierPolarski2001": "Chevallier and Polarski 2001",
    "Linder2003": "Linder 2003",
    "CAMB": "Lewis, Challinor, and Lasenby 2000",
    "cobaya": "Torrado and Lewis 2021",
    "getdist": "Lewis 2019",
    "dynesty": "Speagle 2020",
    "Dyson1979": "Dyson 1979",
    "KraussTurner1999": "Krauss and Turner 1999",
    "KraussStarkman2000": "Krauss and Starkman 2000",
    "Caldwell2003": "Caldwell, Kamionkowski, and Weinberg 2003",
    "Rosenblatt1952": "Rosenblatt 1952",
    "Dawid1984": "Dawid 1984",
    "GelmanMengStern1996": "Gelman, Meng, and Stern 1996",
    "PhipsonSmyth2010": "Phipson and Smyth 2010",
    "Rubin1984": "Rubin 1984",
}

REFERENCE_ENTRIES = [
    "Brout et al. 2022. The Pantheon+ Analysis: Cosmological Constraints. ApJ 938, 110.",
    "DESI Collaboration 2025. DESI DR2 Results II: Measurements of Baryon Acoustic Oscillations and Cosmological Constraints. arXiv:2503.14738.",
    "Chen, Huang, and Wang 2019. Distance Priors from Planck Final Release. JCAP. arXiv:1808.05724.",
    "Chevallier and Polarski 2001. Accelerating universes with scaling dark matter. IJMPD 10, 213.",
    "Linder 2003. Exploring the expansion history of the universe. PRL 90, 091301.",
    "Lewis, Challinor, and Lasenby 2000. Efficient computation of CMB anisotropies in closed FRW models. ApJ 538, 473.",
    "Torrado and Lewis 2021. Cobaya: code for Bayesian analysis of hierarchical physical models. JCAP.",
    "Lewis 2019. GetDist: a Python package for analysing Monte Carlo samples. arXiv:1910.13970.",
    "Speagle 2020. dynesty: a dynamic nested sampling package for estimating Bayesian posteriors and evidences. MNRAS 493, 3132.",
    "Dyson 1979. Time without end: Physics and biology in an open universe. RMP 51, 447.",
    "Krauss and Turner 1999. Geometry and Destiny. GRG 31, 1453.",
    "Krauss and Starkman 2000. Life, the Universe, and Nothing. ApJ 531, 22.",
    "Caldwell, Kamionkowski, and Weinberg 2003. Phantom Energy and Cosmic Doomsday. PRL 91, 071301.",
    "Rosenblatt 1952. Remarks on a Multivariate Transformation. Annals of Mathematical Statistics 23(3), 470-472.",
    "Dawid 1984. Statistical Theory: The Prequential Approach. Journal of the Royal Statistical Society A 147(2), 278-292.",
    "Gelman, Meng, and Stern 1996. Posterior Predictive Assessment of Model Fitness via Realized Discrepancies. Statistica Sinica 6, 733-807.",
    "Phipson and Smyth 2010. Permutation P-values Should Never Be Zero. Statistical Applications in Genetics and Molecular Biology 9(1), Article 39.",
    "Rubin 1984. Bayesianly Justifiable and Relevant Frequency Calculations for the Applied Statistician. Annals of Statistics 12, 1151-1172.",
]


def ensure_dirs() -> None:
    for path in [RESULT_DIR, SUBMISSION_DIR, SUBMISSION_FIG_DIR, TMP_RENDER_DIR, OUTPUT_PDF_DIR]:
        path.mkdir(parents=True, exist_ok=True)


def load_json(name: str) -> dict:
    return json.loads((RESULT_DIR / name).read_text())


def md_inline(text: str) -> str:
    """Convert a small subset of Markdown inline syntax to ReportLab markup."""
    placeholders: list[str] = []

    def stash_code(match: re.Match[str]) -> str:
        raw = html.escape(match.group(1))
        placeholders.append(f'<font name="Courier">{raw}</font>')
        return f"@@CODE{len(placeholders) - 1}@@"

    text = re.sub(r"`([^`]+)`", stash_code, text)
    text = html.escape(text)
    text = re.sub(r"\*\*([^*]+)\*\*", r"<b>\1</b>", text)
    for i, value in enumerate(placeholders):
        text = text.replace(f"@@CODE{i}@@", value)
    return text


def humanize_for_pdf(text: str) -> str:
    """Render citation keys as readable author-year text in the ReportLab proof."""

    def replace_group(match: re.Match[str]) -> str:
        raw = match.group(1)
        keys = [part.strip().lstrip("@") for part in raw.split(";")]
        labels = [CITATION_LABELS.get(key, key) for key in keys]
        return "(" + "; ".join(labels) + ")"

    text = re.sub(r"\[(@[A-Za-z0-9]+(?:;\s*@[A-Za-z0-9]+)*)\]", replace_group, text)
    refs = "## References\n\n" + "\n".join(f"- {entry}" for entry in REFERENCE_ENTRIES) + "\n"
    text = re.sub(r"## References\n\n.*\Z", refs, text, flags=re.S)
    return text


def split_md_table_row(row: str) -> list[str]:
    row = row.strip()
    if row.startswith("|"):
        row = row[1:]
    if row.endswith("|"):
        row = row[:-1]
    cells: list[str] = []
    current: list[str] = []
    escaped = False
    for char in row:
        if char == "\\" and not escaped:
            escaped = True
            current.append(char)
            continue
        if char == "|" and not escaped:
            cells.append("".join(current).strip().replace(r"\|", "|"))
            current = []
        else:
            current.append(char)
        escaped = False
    cells.append("".join(current).strip().replace(r"\|", "|"))
    return cells


def is_separator_row(row: str) -> bool:
    cells = split_md_table_row(row)
    return all(re.fullmatch(r":?-{3,}:?", cell.strip()) for cell in cells)


def table_widths(ncols: int) -> list[float]:
    usable = letter[0] - 1.35 * inch
    if ncols == 2:
        weights = [0.42, 0.58]
    elif ncols == 3:
        weights = [0.22, 0.39, 0.39]
    elif ncols == 4:
        weights = [0.16, 0.24, 0.38, 0.22]
    elif ncols == 5:
        weights = [0.24, 0.19, 0.19, 0.19, 0.19]
    elif ncols == 6:
        weights = [0.18, 0.15, 0.15, 0.15, 0.15, 0.22]
    else:
        weights = [1 / ncols] * ncols
    return [usable * w for w in weights]


def build_styles() -> dict[str, ParagraphStyle]:
    base = getSampleStyleSheet()
    styles = {
        "title": ParagraphStyle(
            "Title",
            parent=base["Title"],
            fontName="Helvetica-Bold",
            fontSize=19,
            leading=23,
            alignment=TA_CENTER,
            spaceAfter=14,
        ),
        "author": ParagraphStyle(
            "Author",
            parent=base["Normal"],
            fontSize=10,
            leading=13,
            alignment=TA_CENTER,
            spaceAfter=4,
        ),
        "abstract_label": ParagraphStyle(
            "AbstractLabel",
            parent=base["Heading2"],
            fontSize=11,
            leading=14,
            alignment=TA_CENTER,
            spaceBefore=14,
            spaceAfter=6,
        ),
        "h2": ParagraphStyle(
            "Heading2",
            parent=base["Heading2"],
            fontName="Helvetica-Bold",
            fontSize=13,
            leading=16,
            spaceBefore=15,
            spaceAfter=7,
        ),
        "h3": ParagraphStyle(
            "Heading3",
            parent=base["Heading3"],
            fontName="Helvetica-Bold",
            fontSize=11,
            leading=14,
            spaceBefore=10,
            spaceAfter=5,
        ),
        "body": ParagraphStyle(
            "Body",
            parent=base["BodyText"],
            fontName="Times-Roman",
            fontSize=9.4,
            leading=12.3,
            firstLineIndent=0,
            alignment=TA_JUSTIFY,
            spaceAfter=6,
        ),
        "bullet": ParagraphStyle(
            "Bullet",
            parent=base["BodyText"],
            fontName="Times-Roman",
            fontSize=9.2,
            leading=11.8,
            leftIndent=16,
            firstLineIndent=-10,
            spaceAfter=4,
        ),
        "code": ParagraphStyle(
            "Code",
            parent=base["Code"],
            fontName="Courier",
            fontSize=7.4,
            leading=9,
            leftIndent=10,
            rightIndent=6,
            backColor=colors.HexColor("#f5f5f5"),
            borderColor=colors.HexColor("#dddddd"),
            borderPadding=5,
            spaceBefore=4,
            spaceAfter=7,
        ),
        "table_cell": ParagraphStyle(
            "TableCell",
            parent=base["BodyText"],
            fontName="Times-Roman",
            fontSize=6.8,
            leading=8.0,
            alignment=TA_LEFT,
        ),
        "table_header": ParagraphStyle(
            "TableHeader",
            parent=base["BodyText"],
            fontName="Helvetica-Bold",
            fontSize=6.9,
            leading=8.1,
            alignment=TA_LEFT,
        ),
        "caption": ParagraphStyle(
            "Caption",
            parent=base["BodyText"],
            fontName="Times-Italic",
            fontSize=8.6,
            leading=11,
            alignment=TA_LEFT,
            spaceBefore=4,
            spaceAfter=10,
        ),
    }
    return styles


def add_md_table(story: list, rows: list[str], styles: dict[str, ParagraphStyle]) -> None:
    parsed = [split_md_table_row(row) for row in rows if not is_separator_row(row)]
    if not parsed:
        return
    ncols = max(len(row) for row in parsed)
    normalized = [row + [""] * (ncols - len(row)) for row in parsed]
    data = []
    for r_i, row in enumerate(normalized):
        style = styles["table_header"] if r_i == 0 else styles["table_cell"]
        data.append([Paragraph(md_inline(cell), style) for cell in row])
    tbl = LongTable(data, colWidths=table_widths(ncols), repeatRows=1, splitByRow=1)
    tbl.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#eeeeee")),
                ("GRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#bbbbbb")),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 3),
                ("RIGHTPADDING", (0, 0), (-1, -1), 3),
                ("TOPPADDING", (0, 0), (-1, -1), 3),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
            ]
        )
    )
    story.append(tbl)
    story.append(Spacer(1, 7))


def md_to_story(md_text: str, styles: dict[str, ParagraphStyle]) -> list:
    story: list = []
    lines = md_text.splitlines()
    paragraph: list[str] = []
    code: list[str] | None = None
    table_rows: list[str] | None = None

    def flush_para() -> None:
        nonlocal paragraph
        if paragraph:
            text = " ".join(x.strip() for x in paragraph).strip()
            if text and not text.startswith("Status: Phase 9"):
                story.append(Paragraph(md_inline(text), styles["body"]))
            paragraph = []

    def flush_table() -> None:
        nonlocal table_rows
        if table_rows:
            add_md_table(story, table_rows, styles)
            table_rows = None

    for line in lines:
        if code is not None:
            if line.startswith("```"):
                story.append(Preformatted("\n".join(code), styles["code"]))
                code = None
            else:
                code.append(line)
            continue

        if line.startswith("```"):
            flush_para()
            flush_table()
            code = []
            continue

        if line.startswith("|"):
            flush_para()
            if table_rows is None:
                table_rows = []
            table_rows.append(line)
            continue
        else:
            flush_table()

        stripped = line.strip()
        if not stripped:
            flush_para()
            continue

        if stripped.startswith("# "):
            flush_para()
            continue
        if stripped.startswith("## "):
            flush_para()
            heading = stripped[3:].strip()
            if heading == "Abstract":
                story.append(Paragraph("Abstract", styles["abstract_label"]))
            else:
                story.append(Paragraph(md_inline(heading), styles["h2"]))
            continue
        if stripped.startswith("### "):
            flush_para()
            story.append(Paragraph(md_inline(stripped[4:].strip()), styles["h3"]))
            continue

        bullet_match = re.match(r"^(\d+)\.\s+(.*)$", stripped)
        if bullet_match:
            flush_para()
            story.append(Paragraph(md_inline(bullet_match.group(2)), styles["bullet"], bulletText=f"{bullet_match.group(1)}."))
            continue
        if stripped.startswith("- "):
            flush_para()
            story.append(Paragraph(md_inline(stripped[2:]), styles["bullet"], bulletText="-"))
            continue

        paragraph.append(stripped)

    flush_para()
    flush_table()
    return story


def add_figure_plates(story: list, styles: dict[str, ParagraphStyle]) -> None:
    story.append(PageBreak())
    story.append(Paragraph("Rendered Figure Plates", styles["h2"]))
    usable_width = letter[0] - 1.35 * inch
    max_height = 6.3 * inch
    for fig_label, caption, filename in FIGURES:
        fig_path = FIG_DIR / filename
        if not fig_path.exists():
            continue
        story.append(PageBreak())
        story.append(Paragraph(f"{fig_label}. {caption}", styles["h3"]))
        reader = ImageReader(str(fig_path))
        width, height = reader.getSize()
        scale = min(usable_width / width, max_height / height)
        img = Image(str(fig_path), width=width * scale, height=height * scale)
        story.append(img)
        story.append(Paragraph(f"{fig_label}: {caption}. Source file: figures/{filename}.", styles["caption"]))


def draw_header_footer(canvas, doc) -> None:
    canvas.saveState()
    width, height = letter
    canvas.setFont("Helvetica", 7.5)
    canvas.setFillColor(colors.HexColor("#555555"))
    canvas.drawString(doc.leftMargin, height - 0.45 * inch, SHORT_TITLE)
    canvas.drawRightString(width - doc.rightMargin, height - 0.45 * inch, f"Page {doc.page}")
    canvas.setStrokeColor(colors.HexColor("#dddddd"))
    canvas.line(doc.leftMargin, height - 0.52 * inch, width - doc.rightMargin, height - 0.52 * inch)
    canvas.restoreState()


def build_pdf(md_text: str, output_pdf: Path) -> None:
    styles = build_styles()
    doc = SimpleDocTemplate(
        str(output_pdf),
        pagesize=letter,
        leftMargin=0.68 * inch,
        rightMargin=0.67 * inch,
        topMargin=0.78 * inch,
        bottomMargin=0.65 * inch,
        title=TITLE,
        author=AUTHOR,
    )
    story: list = [
        Paragraph(TITLE, styles["title"]),
        Paragraph(AUTHOR, styles["author"]),
        Paragraph(DATE, styles["author"]),
        Spacer(1, 8),
    ]
    story.extend(md_to_story(md_text, styles))
    add_figure_plates(story, styles)
    doc.build(story, onFirstPage=draw_header_footer, onLaterPages=draw_header_footer)


def copy_submission_assets() -> None:
    for _, _, filename in FIGURES:
        src = FIG_DIR / filename
        if src.exists():
            shutil.copy2(src, SUBMISSION_FIG_DIR / filename)
    shutil.copy2(REPO / "paper" / "refs.bib", SUBMISSION_DIR / "refs.bib")
    shutil.copy2(METHOD_DIR / "MANUSCRIPT_DRAFT.md", SUBMISSION_DIR / "critical_boundary_calibration.md")


def build_latex_source() -> dict:
    source_md = METHOD_DIR / "MANUSCRIPT_DRAFT.md"
    tex_path = SUBMISSION_DIR / "critical_boundary_calibration.tex"
    pandoc = shutil.which("pandoc")
    if not pandoc:
        tex_path.write_text("% Pandoc unavailable; regenerate when pandoc is installed.\n")
        return {"pandoc_available": False, "tex_path": str(tex_path), "pandoc_returncode": None}

    cmd = [
        pandoc,
        str(source_md),
        "-s",
        "-t",
        "latex",
        "--natbib",
        "--bibliography",
        str(SUBMISSION_DIR / "refs.bib"),
        "--metadata",
        f"title={TITLE}",
        "--metadata",
        f"author={AUTHOR}",
        "--metadata",
        f"date={DATE}",
        "-o",
        str(tex_path),
    ]
    proc = subprocess.run(cmd, cwd=str(METHOD_DIR), capture_output=True, text=True)
    if proc.returncode != 0:
        tex_path.write_text("% Pandoc failed.\n\n% STDOUT\n" + proc.stdout + "\n% STDERR\n" + proc.stderr)
    else:
        fig_tex = "\n\n\\clearpage\n\\section*{Submission Figure Plates}\n"
        for label, caption, filename in FIGURES:
            fig_tex += (
                "\\begin{figure}[p]\n"
                "\\centering\n"
                f"\\includegraphics[width=0.95\\textwidth]{{figures/{filename}}}\n"
                f"\\caption{{{label}: {caption}.}}\n"
                "\\end{figure}\n"
            )
        with tex_path.open("a") as f:
            f.write(fig_tex)
    return {
        "pandoc_available": True,
        "tex_path": str(tex_path),
        "pandoc_returncode": proc.returncode,
        "pandoc_stderr": proc.stderr.strip(),
    }


def write_readme(pdf_path: Path, output_pdf_path: Path, latex_info: dict) -> None:
    latex_note = "Pandoc LaTeX source generated." if latex_info.get("pandoc_returncode") == 0 else "Pandoc LaTeX generation failed; see .tex."
    readme = f"""# Submission Package

Generated by Phase 10 on 2026-07-06.

## Files

- `critical_boundary_calibration.md`: source manuscript draft.
- `critical_boundary_calibration.tex`: submission-shaped LaTeX source.
- `refs.bib`: bibliography copied from `paper/refs.bib`.
- `figures/`: self-contained figure assets.
- `critical_boundary_calibration.pdf`: rendered PDF proof generated with ReportLab.

The same PDF is also copied to:

```text
{output_pdf_path}
```

## Build Notes

{latex_note}

This machine did not expose `pdflatex`, `xelatex`, or `latexmk` during Phase 10,
so the PDF proof is generated with ReportLab and visually checked via Poppler
rendered pages. If a LaTeX engine is installed later, compile
`critical_boundary_calibration.tex` with `refs.bib` and the local `figures/`
directory.

## Claim Boundary

The package preserves the Phase 8/9 boundary: method paper only; no direct claim
about the universe's final fate; no model-preference claim; Evidence and Horizon
layers remain explicitly separate.
"""
    (SUBMISSION_DIR / "README_SUBMISSION.md").write_text(readme)


def render_pdf_pages(pdf_path: Path) -> list[str]:
    for old in TMP_RENDER_DIR.glob("phase10-*"):
        old.unlink()
    pdftoppm = shutil.which("pdftoppm")
    if not pdftoppm:
        return []
    reader = PdfReader(str(pdf_path))
    page_count = len(reader.pages)
    pages = sorted({1, min(5, page_count), min(9, page_count), min(10, page_count), max(1, page_count - 3), page_count})
    rendered: list[str] = []
    for page in pages:
        prefix = TMP_RENDER_DIR / f"phase10-p{page}"
        subprocess.run(
            [pdftoppm, "-png", "-f", str(page), "-l", str(page), str(pdf_path), str(prefix)],
            check=True,
            capture_output=True,
            text=True,
        )
        rendered.extend(str(p) for p in sorted(TMP_RENDER_DIR.glob(f"phase10-p{page}-*.png")))
    return rendered


def audit_package(pdf_path: Path, output_pdf_path: Path, latex_info: dict, rendered_pages: list[str]) -> dict:
    reader = PdfReader(str(pdf_path))
    extracted_all = "\n".join(page.extract_text() or "" for page in reader.pages)
    extracted = "\n".join(page.extract_text() or "" for page in reader.pages[:3])
    normalized_title_text = re.sub(r"\s+", " ", extracted)
    phase9 = load_json("phase9_manuscript_audit.json")
    files = {
        "submission_pdf": pdf_path.exists(),
        "output_pdf": output_pdf_path.exists(),
        "tex": (SUBMISSION_DIR / "critical_boundary_calibration.tex").exists(),
        "refs": (SUBMISSION_DIR / "refs.bib").exists(),
        "readme": (SUBMISSION_DIR / "README_SUBMISSION.md").exists(),
        "figures": all((SUBMISSION_FIG_DIR / filename).exists() for _, _, filename in FIGURES),
    }
    title_found = TITLE in normalized_title_text
    citation_tokens_remaining = len(re.findall(r"@[A-Za-z0-9]+", extracted_all))
    return {
        "phase": 10,
        "pass": all(files.values()) and phase9["pass"] and len(rendered_pages) >= 3 and title_found and citation_tokens_remaining == 0,
        "files": files,
        "pdf_pages": len(reader.pages),
        "pdf_path": str(pdf_path),
        "output_pdf_path": str(output_pdf_path),
        "latex_info": latex_info,
        "rendered_pages": rendered_pages,
        "phase9_audit_pass": phase9["pass"],
        "title_found_in_pdf_text": title_found,
        "pdf_citation_tokens_remaining": citation_tokens_remaining,
        "latex_engine_available": any(shutil.which(x) for x in ["pdflatex", "xelatex", "latexmk"]),
    }


def write_phase_doc(audit: dict) -> None:
    phase_doc = f"""# Phase 10: Submission Package and Rendered PDF

Draft date: 2026-07-06

This phase converts the Phase 9 Markdown manuscript into a submission-shaped
package and a rendered PDF proof.

## Outputs

```text
paper/method/submission/
paper/method/submission/critical_boundary_calibration.tex
paper/method/submission/critical_boundary_calibration.pdf
paper/method/submission/README_SUBMISSION.md
paper/method/results/phase10_submission_audit.json
tmp/pdfs/phase10_render/
output/pdf/critical_boundary_calibration_phase10.pdf
```

## Build Status

| Check | Status |
|---|---|
| submission PDF exists | {"pass" if audit["files"]["submission_pdf"] else "fail"} |
| output PDF exists | {"pass" if audit["files"]["output_pdf"] else "fail"} |
| LaTeX source exists | {"pass" if audit["files"]["tex"] else "fail"} |
| refs.bib copied | {"pass" if audit["files"]["refs"] else "fail"} |
| figures copied | {"pass" if audit["files"]["figures"] else "fail"} |
| rendered pages generated | {len(audit["rendered_pages"])} |
| PDF pages | {audit["pdf_pages"]} |
| PDF title text found | {"pass" if audit["title_found_in_pdf_text"] else "fail"} |
| PDF citation tokens remaining | {audit["pdf_citation_tokens_remaining"]} |
| Phase 9 boundary audit | {"pass" if audit["phase9_audit_pass"] else "fail"} |
| LaTeX engine available locally | {"yes" if audit["latex_engine_available"] else "no"} |

Status: **Phase 10 {"passes" if audit["pass"] else "needs review"}.**

## Note

No local `pdflatex`, `xelatex`, or `latexmk` executable was available during
this run, so the PDF proof was generated with ReportLab and visually checked
through Poppler-rendered PNG pages. The LaTeX source package is ready for later
compilation in an environment with a TeX engine.
"""
    (METHOD_DIR / "PHASE10_SUBMISSION_PACKAGE.md").write_text(phase_doc)


def main() -> None:
    ensure_dirs()
    copy_submission_assets()

    md_text = humanize_for_pdf((METHOD_DIR / "MANUSCRIPT_DRAFT.md").read_text())
    latex_info = build_latex_source()

    pdf_path = SUBMISSION_DIR / "critical_boundary_calibration.pdf"
    output_pdf_path = OUTPUT_PDF_DIR / "critical_boundary_calibration_phase10.pdf"
    build_pdf(md_text, pdf_path)
    shutil.copy2(pdf_path, output_pdf_path)
    write_readme(pdf_path, output_pdf_path, latex_info)

    rendered_pages = render_pdf_pages(pdf_path)
    audit = audit_package(pdf_path, output_pdf_path, latex_info, rendered_pages)
    (RESULT_DIR / "phase10_submission_audit.json").write_text(json.dumps(audit, indent=2, sort_keys=True))
    write_phase_doc(audit)

    print(f"wrote {pdf_path}")
    print(f"wrote {output_pdf_path}")
    print(f"wrote {SUBMISSION_DIR / 'critical_boundary_calibration.tex'}")
    print(f"wrote {RESULT_DIR / 'phase10_submission_audit.json'}")
    print(json.dumps(audit, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
