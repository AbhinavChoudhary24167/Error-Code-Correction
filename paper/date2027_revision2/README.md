# DATE 2027 Revision 2 manuscript

This namespace is independent of `paper/date2027/` and does not overwrite Revision 1.

Authoritative numerical source:

`docs/date2027/revision2/results/REV2_MANUSCRIPT_EVIDENCE.json`

Regenerate tables, figures, and TeX macros:

```text
python3 scripts/build_artifacts.py
```

Build sequence:

```text
pdflatex -interaction=nonstopmode -halt-on-error -jobname=date2027_submission_v2 main.tex
bibtex date2027_submission_v2
pdflatex -interaction=nonstopmode -halt-on-error -jobname=date2027_submission_v2 main.tex
pdflatex -interaction=nonstopmode -halt-on-error -jobname=date2027_submission_v2 main.tex
```

The reported frequency is a signed-setup-slack-derived estimate for the fixed implementation optimized under the 10 ns constraint. It is not a frequency sweep.
