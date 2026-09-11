# Page and Format Compliance

Artifact audited: `DATE2027_MANUSCRIPT_BLIND.pdf`  
SHA-256: `e4debf727603555bdf1f1f74c8bc04d53b7de44b07f1c72e0d995076c2b386db`

| Requirement | Evidence | Result |
|---|---|---|
| PDF only | Compiled PDF present | PASS |
| Maximum six technical pages | Technical sections end on page 6 | PASS |
| Page 7 references only | Extracted page text contains References and no technical section heading | PASS |
| Seven pages maximum | `pdfinfo` and `pypdf`: 7 | PASS |
| Letter or A4 | 612 x 792 pt (US Letter) | PASS |
| Double column / single spaced | IEEEtran conference class | PASS |
| Times/equivalent, minimum 10 pt | IEEEtran 10 pt; Times text family | PASS |
| No Type-3 fonts | Recursive PDF resource audit finds only Type0 and Type1 | PASS |
| No baseline compression | No baseline-stretch override | PASS |
| No page numbers | Visual inspection of all seven rendered pages | PASS |
| No copyright notice | Text and visual inspection | PASS |
| No overfull horizontal boxes | Final LaTeX log | PASS |
| Visual integrity | All pages rendered at 140 dpi and inspected; no clipping, overlap, or unreadable plot text | PASS |

The 1.74733-pt vertical balancing diagnostic on page 6 was visually inspected; no text crosses the text block or clips, and the two technical columns are balanced. It is not a font-size or spacing compression.
