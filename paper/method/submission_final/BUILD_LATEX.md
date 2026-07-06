# LaTeX Build Notes

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
