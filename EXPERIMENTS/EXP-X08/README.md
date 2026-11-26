# EXP-X08 — Evaluation-equivalent AI agents

This experiment tests threshold identification in an executed, offline virtual parcel-routing sandbox. The benchmark permits history-dependent normal/rush requests and displays every selected lane and simulator retry. The independent audit measures routing preference without exercising the delivery outcome. See the [work plan](WorkPlan.md), [frozen protocol](Protocol.md) and [execution record](Path.md).

## Requirements and pre-audit checks

Use Python 3.13.7 with its standard library. Use Git and an account with access to `Perceptive-Closure/PC-X` for the original staged GitHub proceedings. From this experiment directory:

```sh
python -B -m unittest discover -s tests -v
python -B src/x08.py exact --output pre-audit-replay.json
```

Compare the output with [results/pre-audit.json](results/pre-audit.json). The checks compare the exact conditional laws with every native ticket pair in the reachable support and compare two independently structured risk calculations. Tests replay deliberately public development fixtures.

## Original held-out workflow

A custodian uses a clean checkout at the published pre-audit commit. From this experiment directory in that checkout, run `src/x08.py reserve` with `--pre-audit-commit`, `--private` and `--receipt`. Both file destinations should be outside the checkout and inside the experiment scratch directory. Keep the private file concealed from the forecaster until the trial opening. Deliver the audit receipt to the forecaster, who runs `src/x08.py predict --receipt PATH --output results/forecast.json` and pushes that forecast to the experiment branch. In the unchanged pre-audit checkout, the custodian runs `src/x08.py release` with `--private`, `--receipt`, `--forecast-commit` and `--output` pointing to a new observation directory. The tool validates the exact GitHub branch revision before executing any held-out trials. It writes the opening, experimental run summaries and raw JSONL. It accepts the expected revision checks only while the branch points at the relevant staged commit.

The predictor and observer are separate processes and roles in a shared workspace. The design records custody and cryptographic commitments without claiming operating system isolation between the agents. Commitments protect the chronology through later verification. The fixed seed reveals only after the forecast reaches GitHub. Do not run a new custody operation to reproduce a finished result.

## Offline reproduction after opening

From a clean checkout of the finalized experiment package, execute:

```sh
python -B -m unittest discover -s tests -v
python -B src/x08.py replay --output repro-x08
```

Use a fresh output directory. Replay checks the exact audit analysis, independently recalculates the forecast from its receipt, verifies that the disclosed seed and configuration open the original commitment, reproduces all 8,192 measured episodes, and checks the full raw-episode SHA-256 and summaries against the custodian's record. Keep the scratch directory in the isolated experiment environment. Reported intervals concern modeled independent ticket draws and resets. This finite sandbox supplies no claim about actual facilities or general evaluation-to-deployment transport.
