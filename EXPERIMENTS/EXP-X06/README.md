# EXP-X06 held-out authorization system

Can a separately measured admission fact resolve an initially ambiguous representation-freeze prediction before native authorization outcomes open? The test covers eight paired wrapper instances with fixed inert Open Policy Agent inputs. [Frozen protocol](Protocol.md) · [Execution record](Path.md) · [Original work plan](WorkPlan.md)

## Environment and pinned inputs

Use Python 3.13.7 and the [official OPA v1.22.4 Windows AMD64 release binary](https://github.com/open-policy-agent/opa/releases/download/v1.22.4/opa_windows_amd64.exe). The runner checks its SHA-256, reported version and platform, and hashes the verbatim upstream tutorial policy and license before measurement. The release binary is obtained separately from the GitHub package. Reproduction commands use only local files after acquisition. The Rego policy is an unmodified excerpt of the upstream HTTP API tutorial under the included Apache 2.0 [license](vendor/LICENSE). [Provenance and reference pins](config/provenance.json)

Download GitHub zip archives for the X01 and X03 revisions in `config/provenance.json`. Place their extracted archive roots in `scratch/deps/X01` and `scratch/deps/X03`, such that each contains its top-level `EXPERIMENTS` directory, or use `--deps` and `PCX_X06_DEPS` to name another dependency directory. For the parent’s custody, obtain separate immutable GitHub archives for the freeze and forecast. The repo root of each archive has no Git metadata. In each archive invoke stages from `EXPERIMENTS/EXP-X06`. All disposable outputs, dependencies and the executable live in ignored experiment scratch. On Windows set `TEMP` and `TMP` to an experiment-owned directory before commands that create temporary files.

## Parent custody and opening

1. Independently retrieve the exact preaudit revision from GitHub. Run `python -B -m unittest discover -s tests -v` and `python -B x06.py preaudit --check --deps <deps>`. Only preflight and separately labeled development controls may run here.
2. Run `python -B x06.py seal --dir <custody> --freeze-commit <preauditSHA>`. Keep `assignment.json` inside the parent’s custody directory until opening. Preserve `commitment.json`.
3. Run `python -B x06.py audit --dir <custody>`. Send the experiment agent only `audit-receipt.json`. Run `python -B x06.py forecast --receipt <audit-receipt>` in the experiment branch. Commit the receipt bytes and generated `results/forecast.json` and push.
4. Independently verify the forecast revision exists at the remote branch, its parent is the frozen revision, and the only intervening path changes are the receipt and the forecast. Download that exact revision and run `python -B x06.py authorize --dir <custody> --frozen-root <preaudit/EXPERIMENTS/EXP-X06> --forecast-commit <forecastSHA>` from the forecast archive. This checks the saved receipt bytes, unchanged runner, exact preaudit and forecast before writing `authorization.json`. Opening remains pending until authorization.
5. Run `python -B x06.py open --dir <custody> --opa <verified-exe> --temp <temp-dir>`. It records the raw native decisions in `native.json`, independently reconstructed status in `summary.json` and the opening information in `release.json`. A failed attempt preserves `failure.json` and any available raw evidence. A completed attempt retains mismatches in `summary.json` before acceptance. The agent records the three opening files in `results` and verifies the terminal GitHub evidence.

## Reproduce after opening

From a fresh checkout or GitHub archive of the terminal evidence commit, with dependencies and the official binary acquired as above, run:

```powershell
python -B -m unittest discover -s tests -v
python -B x06.py preaudit --check --deps <deps>
python -B x06.py check-evidence
python -B x06.py replay --opa <verified-exe> --temp <temp-dir>
```

The last stage replay compares every native raw input/output and checkpoint against the preserved SHA-256-bound trace. The evidence-only stage checks the commitment, receipt, forecast, authorization order and exact reconstruction independently of OPA. The native binary may also be exercised on the disjoint development controls with `python -B x06.py development --opa <verified-exe> --temp <temp-dir>`.
