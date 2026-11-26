# EXP-X01 — Exact finite completion recovery

This package compares a finite Perceptive Closure solver with independently enumerated observation-measurable policy trees. It checks all eight resource freezes and recovers the exact signature set in a supplied finite completion catalog. The cases are constructed from explicit source graphs and semantic assumptions.

## Reproduce

Use CPython 3.13.7. The standard library supplies every runtime dependency. From a checkout of this experiment's recorded GitHub revision, run these commands in `EXPERIMENTS/EXP-X01`.

```powershell
python -B -m unittest discover -s tests -v
python -B -m src.run --check
```

The second command reruns the entire frozen corpus, rechecks all witnesses against the reference, verifies the canonical summary and checks the SHA-256 of the regenerated full evidence. `--details <path>` writes the complete observation and falsification ledger when needed. `--timing` reports wall time and `--memory` measures traced Python allocations. Both measurements are excluded from the evidence hash.

- [WorkPlan.md](WorkPlan.md) and [configs/protocol.json](configs/protocol.json) define the requirements, seed schedule, case factors and acceptance gates.
- [Path.md](Path.md) records the mathematical model, exact controls, results, limitations and persistence.
- [results/summary.json](results/summary.json) and [results/manifest.json](results/manifest.json) record metrics and frozen evidence digests.

## Model and exact evaluation

`src.model` defines a finite checkpoint graph, a sealed class for every latent world, its compatibility relation with normalized histories, and extensional certificate partitions and authority scopes. A candidate's ordinary precondition is represented by its presence in a state's source candidate table. The authority set determines whether the listed action interface is enabled. Source IDs, action costs, observations and positive-support outcome labels are explicit.

An action survives a freeze only when every positive-support successor preserves the frozen coordinates. A controller at a belief can choose an action only when it survives at every possible checkpoint. The outcome label and following observation select the next set of possible checkpoints. A proper policy reaches closure in finitely many actions on every supported branch. Its cost is the largest accumulated cost of those branches. The freeze order is empty, E, R, A, ER, EA, RA, ERA. The JSON token `"inf"` denotes structural impossibility certified by exact finite evaluation.

The main solver labels closed beliefs with zero. An action produces a finite candidate label when it has labels at every supported successor. Its candidate is the action cost plus its largest successor label. The heap finalizes the least candidate first. Each finalized candidate realizes a finite proper policy tree. An optimal tree of lower cost would contain a deepest unlabeled belief below it whose children were finalized and whose action would have supplied a lower heap entry. This is valid with zero-cost actions because readiness still requires every successor to have a finite witness. A cycle alone cannot create such a witness.

The reference reconstructs availability, full pairwise representation equivalence, touch, closure and observation branches from the raw records. It exhausts attainable support-maximum costs over proper policy trees with no repeated belief on a path. Replacing the path between repeated equal beliefs by the suffix policy retains admissibility and cannot increase worst cost. This yields a finite search for the reference even on cyclic graphs.

## Reuse the exact controls

The public constructor in `src.fixtures` builds one shared-source E/R pair for a fallback cost of four. The only difference between the fast actions is the admissible interpretation of the evidence and representation boundary. A fallback cost of `None` removes the fallback action. The main and independent evaluators expose separate paths.

```python
from src.fixtures import source_boundary
from src.model import Evidence, identify, signature, source_sha256
from src.reference import reference_signature, verify_certificate

completions = (source_boundary('E', 4, 0), source_boundary('R', 4, 0))
evidence = Evidence(source_sha256(completions[0]))
certificate = identify(completions, evidence)
assert verify_certificate(completions, evidence, certificate)
assert signature(completions[0]) == reference_signature(completions[0])
```

The certificate enumerates compatible completion IDs and every distinct signature. It includes one independently checkable completion witness for each signature. Its coverage depends on the supplied finite catalog and frozen source projection. An empty catalog is inconsistent. The verifier checks the catalog, membership and all reported signatures and witnesses. Exact symbolically represented completion domains and claims beyond these bounded controls require separate verification.
