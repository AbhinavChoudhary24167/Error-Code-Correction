# DATE 2027 manuscript package

Selected working title: **Implementation Identity Matters: Post-Route Trade-offs in Memory ECC Hardware**

The submission source is anonymous and uses IEEE conference formatting compatible with the DATE 2027 instructions: double column, 10 pt, no page numbers, six manuscript pages plus one references-only page.

## Ranked title candidates

1. Implementation Identity Matters: Post-Route Trade-offs in Memory ECC Hardware
2. Beyond Coding Strength: Cross-Layer Evaluation of ECC Hardware Implementations
3. From Correction Capability to Physical Feasibility: Evaluating ECC Hardware
4. Post-Route Trade-offs in Correctness-Qualified ECC Hardware
5. ECC Microarchitecture Matters: A Cross-Layer Physical Evaluation
6. Physical-Design Trade-offs Across Memory ECC Implementations
7. Cross-Layer Reliability and Cost Analysis of ECC Hardware
8. Correction Strength and Physical Feasibility in Memory ECC Hardware

## Build

From the repository root:

```text
python3 paper/date2027/scripts/build_artifacts.py
python3 paper/date2027/scripts/validate_manuscript_numbers.py
cd paper/date2027
pdflatex -interaction=nonstopmode -halt-on-error main.tex
bibtex main
pdflatex -interaction=nonstopmode -halt-on-error main.tex
pdflatex -interaction=nonstopmode -halt-on-error main.tex
```

The final submission PDF is copied to `output/pdf/date2027_submission.pdf` by `scripts/package_pdf.py` after validation.

## Evidence and traceability

- Authoritative numerical source: `docs/date2027/rigour_gate_07/GATE07_MANUSCRIPT_EVIDENCE.json` and its frozen companion files.
- Generated claim macros: `data/generated_claims.tex`.
- Generated tables: `tables/generated_table_i.tex` and `tables/generated_table_ii.tex`.
- Figure/table provenance: `data/traceability.json`.
- Numerical validator: `scripts/validate_manuscript_numbers.py`.
- External literature audit: `../../GATE08_RELATED_WORK_AUDIT.md`.
- Final audit and hashes: `../../DATE2027_FINAL_AUDIT.md` and `../../DATE2027_MANUSCRIPT_FREEZE.json`.

No RTL, ECC algorithm, physical policy, or frozen evidence is modified by this package.

