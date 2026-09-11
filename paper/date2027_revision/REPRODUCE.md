# Reproducing the DATE 2027 revision

The revision is additive. It reads frozen qualified evidence elsewhere in the
repository and writes only beneath `paper/date2027_revision/` (plus a local
Matplotlib cache under `tmp/`). It does not rerun synthesis, physical design,
formal proof, or power analysis.

## Prerequisites

- Python 3 with Matplotlib
- A LaTeX installation providing `pdflatex`, `bibtex`, `IEEEtran`, `amsmath`,
  `booktabs`, `cite`, `graphicx`, `microtype`, and `url`
- Poppler tools (`pdfinfo`, `pdftoppm`, and `pdffonts`) for submission checks

## Regenerate claims, figures, tables, and provenance

From the repository root:

```powershell
python paper/date2027_revision/scripts/build_revision.py
```

The builder imports the already qualified Revision-3 arithmetic, redirects all
generated outputs to this revision directory, redraws the identity framework,
and emits `RESULT_PROVENANCE.csv`. It verifies source hashes while loading the
frozen campaign artifacts.

## Build the PDF

```powershell
Set-Location paper/date2027_revision
pdflatex -interaction=nonstopmode -halt-on-error main.tex
bibtex main
pdflatex -interaction=nonstopmode -halt-on-error main.tex
pdflatex -interaction=nonstopmode -halt-on-error main.tex
python scripts/validate_revision.py
```

Expected validator terminator:

```text
DATE2027_REVISION_VALIDATION_PASS
```

The expected artifact is `main.pdf`: six technical pages followed by one page
containing only references. The validator also checks source hashes, provenance
schema, citation closure, claim boundaries, page count, and LaTeX diagnostics.

## Repository regression suite

From the repository root, run the project-mandated checks:

```powershell
make
make test
python3 -m pytest -q
```

These commands validate repository compatibility; they are independent of the
paper-only artifact regeneration above.
