# Perceptive Closure X

**Mathematical Foundations for AI Assurance under Incomplete Understanding**

Saif Malik · 27 November 2026 · [Main paper with references (23 pages)](PC-X-MAIN-PAPER.pdf) · [Full manuscript (131 pages)](PC-X-FULL-PAPER.pdf) · [Editable LaTeX](manuscript/main.tex)

How much must we understand about an AI system to justify a particular deployment decision? This edition develops the distinction between identifying the relevant property, acquiring trustworthy evidence at a stated price, and finding one lawful policy that can deliver the promised work. Both editions contain the main argument on pages 1–21 and all 25 references on pages 22–23. Appendix links in the standalone edition open the corresponding pages of the full manuscript, where the contents are on page 24 and the eight appendices start on page 25.

| For readers looking for | Where to go |
| --- | --- |
| What the paper contributes and which techniques have close predecessors | [Contribution and novelty assessment](NOVELTY-AND-CLAIMS.md) |
| A theorem, complete proof, source line or governing revision | [Paginated theorem crosswalk](THEOREM-CROSSWALK.md) · [Source manifest](SOURCE-MANIFEST.md) |
| Definitions, permissions, scores and prices | [Notation registry](NOTATION-REGISTRY.md) |
| What all seventeen studies observed, including competing results and inconclusive comparisons | [Evidence and reproduction map](EXPERIMENTAL-EVIDENCE-MAP.md) |
| What changed in this edition and why | [Revision ledger](refinement/REVISION-LEDGER.md) · [Work plan](refinement/WorkPlan.md) · [Execution record](refinement/Path.md) |
| Mathematical scope and scientific objections | [Fidelity report](refinement/review/math/MATHEMATICAL-FIDELITY.md) · [Hostile scientific review](refinement/review/math/HOSTILE-SCIENTIFIC-REVIEW.md) |
| What a fresh reader could explain from the main text | [Eighteen-question reader report](refinement/review/reader/READER-COMPREHENSION.md) |
| Disposition and verification of this edition | [Final acceptance](refinement/FINAL-ACCEPTANCE.md) |

This refinement is based directly on the [accepted manuscript](https://github.com/Perceptive-Closure/PC-X/tree/664f90e2d2e2c941bed36e43240811cfc33ef0ac/PAPER). The [subsequent authorship edition](https://github.com/Perceptive-Closure/PC-X/tree/18fb9aec42897e8fc466abf81b741c7665d6bac2/PAPER) supplies Saif Malik's byline. The [original internal reviews](review/FINAL-ACCEPTANCE.md), [original work plan](WorkPlan.md) and [original execution record](Path.md) document the earlier 125-page edition.

## Rebuild from the editable source

Run the following from the repository root with Tectonic. The verified build used version 0.17.0+20260731. Its first run can download the TeX bundle. The five vector figures are included. Editing or redrawing the figures requires Python and Matplotlib. [Figure source](manuscript/figures/draw.py)

```sh
mkdir -p build/pcx-paper
SOURCE_DATE_EPOCH=1795737600 tectonic --keep-logs --keep-intermediates --outdir build/pcx-paper PAPER/manuscript/main.tex
```

On PowerShell use the following commands.

```powershell
New-Item -ItemType Directory -Force build/pcx-paper | Out-Null
$env:SOURCE_DATE_EPOCH = '1795737600'
tectonic --keep-logs --keep-intermediates --outdir build/pcx-paper PAPER/manuscript/main.tex
```

The build writes `build/pcx-paper/main.pdf`. To check its labels, destinations, bibliography, local theorem index and figure inputs, run the following with Python 3.10 or newer and the `pypdf` package. Different TeX engines, bundles, metadata or resource paths can yield different PDF bytes. The SHA-256 of the distributed PDF is `e5d66ff327525237290516354e75b1d59beebb551158a26e60815f63bb43f248`.

```sh
python PAPER/review/check_manuscript.py --pdf build/pcx-paper/main.pdf --aux build/pcx-paper/main.aux
```

To refresh the diagrams, run `python PAPER/manuscript/figures/draw.py` before compiling again. The X17 risk plot uses the archived issued-run intervals. Appendix H and the evidence map give immutable, study-specific replay instructions. The original D-35 source was anonymous. This edition discloses the model, access conditions and remit of its internal reviewers in the linked reports.
