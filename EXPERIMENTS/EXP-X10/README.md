# EXP-X10 — Monitor blind spots

The executed offline tray-routing harness supplies a disclosed, complete monitor-visible transcript. An independently read partner route card supplies the expected tray. The task is an inert controlled fixture. See [the work plan](WorkPlan.md), [frozen protocol](Protocol.md) and [execution record](Path.md).

## Reproduce

Use Python 3.13.7 and its standard library, from this experiment directory in a clean GitHub checkout or archive. Point TMP and TEMP at an experiment-owned scratch directory when running tests. The outcome runner itself needs no Git metadata or network access.

~~~powershell
python -B -m unittest discover -s tests -v
python -B src/x10.py replay
~~~

Replay verifies the complete committed result manifest, independently rechecks every finite candidate and released record, reconstructs all raw episodes from the opened fixture and seed, and compares the raw bytes and measured statistics. To write a new analysis file, pass a fresh `replay --output PATH`. To rerun only exact finite comparisons, use `python -B src/x10.py exact --output NEW_PATH`. The original compressed raw record is retained in the experiment branch.

## Staged prospective workflow

1. Retrieve the exact pre-audit revision independently. A custodian runs `src/x10.py reserve --pre-audit-commit REV --private PRIVATE --receipt PUBLIC` from that revision. Keep PRIVATE in the independent custodian's scratch area. This stage queries only a sentinel outside the trial population.
2. The forecaster runs `src/x10.py predict --receipt PUBLIC --output NEW_FORECAST` and publishes the unchanged public receipt and forecast. The forecast commit must descend from the immutable runner revision.
3. The custodian checks branch head, ancestry, exact forecast content and unchanged executable study files at that head through GitHub. The custodian then executes the pinned outcome runner with the verified UTC timestamp.

~~~powershell
python -B src/x10.py release --private PRIVATE --receipt PUBLIC --forecast VERIFIED_FORECAST --forecast-commit REV --remote-tip VERIFIED_REV --verified-at-utc STAMP --output NEW_DIRECTORY
~~~

4. Retain the opened commitment, canonical summary and gzip-compressed traces. For reproduction of finished evidence, use `replay`; fresh randomized custody cannot reproduce the single original holdout.

The runner validates the receipt, nonce-backed commitment, externally asserted current forecast tip, UTC ordering and forecast bytes. An independent parent checks GitHub chronology before outcome execution. The published package lets an independent verifier repeat that chronology check. Parent and forecaster use separate checkouts on one shared filesystem. Synthetic route-card evidence supports only this finite controlled fixture.
