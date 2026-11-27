# Perceptive Closure X

**Mathematical Foundations for AI Assurance under Incomplete Understanding**

Saif Malik · Extended research manuscript, 27 November 2026. [Read the 125-page paper](PC-X-FULL-PAPER.pdf) · [Edit the LaTeX source](manuscript/main.tex)

A rehearsal can leave open which guard will handle a real deployment. The paper asks which observations settle the relevant property, what they cost, and whether one lawful policy can still deliver useful work. The main argument occupies pages 1–15. The mathematical and experimental appendices begin on page 19.

| Question | Where to look |
| --- | --- |
| Which accepted claim appears where? | [Theorem crosswalk with PDF pages and source lines](THEOREM-CROSSWALK.md) |
| What does a symbol or cost mean? | [Notation registry](NOTATION-REGISTRY.md) |
| Which revisions govern the paper? | [Source manifest](SOURCE-MANIFEST.md) |
| Which results were observed, and on which service? | [Experimental evidence and replay map](EXPERIMENTAL-EVIDENCE-MAP.md) |
| How does the work relate to established methods? | [Novelty and claims](NOVELTY-AND-CLAIMS.md) |
| What did the reviewers check? | [Mathematical fidelity](review/MATHEMATICAL-FIDELITY.md) · [Independent reader](review/INDEPENDENT-READER-REVIEW.md) · [Final acceptance](review/FINAL-ACCEPTANCE.md) |
| How were the manuscript and evidence assembled? | [Work plan](WorkPlan.md) · [Execution and release record](Path.md) |

The exact per-attempt price in the guarded base construction is 7/12, with a separate hard cap of one and a realized good-guard setup price of 1/4. X17's two native runs supported the declared 3/8 issued-case risk threshold in all sixteen PC-X world/run cells. Fourteen equivalence comparisons remained inconclusive, and a more informative direct observation reduced the expected price to 1/6 on its own interface. Both the costs and the evidentiary claims depend on the installed service.

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

The build writes `build/pcx-paper/main.pdf`. To check its labels, destinations, bibliography, local theorem index and figure inputs, run the following with Python 3.10 or newer and the `pypdf` package. Different TeX engines, bundles, metadata or resource paths can yield different PDF bytes. The SHA-256 of the distributed PDF is `19f7354e022fa6d5eb60b8205afb349711030c120a48d9acef71ab8373247a73`.

```sh
python PAPER/review/check_manuscript.py --pdf build/pcx-paper/main.pdf --aux build/pcx-paper/main.aux
```

To refresh the diagrams, run `python PAPER/manuscript/figures/draw.py` before compiling again. The X17 risk plot uses the archived issued-run intervals. Appendix H and the evidence map give immutable, study-specific replay instructions. The original D-35 source was anonymous, and the two internal manuscript reviews have disclosed their roles.
