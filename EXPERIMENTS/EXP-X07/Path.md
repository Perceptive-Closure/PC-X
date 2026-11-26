# EXP-X07 execution record

## 1. Assignment and source

- Experiment EXP-X07, Security diagnosis reversal. Assigned agent `exp_x07` and independent custodian `root`.
- Starting revision `6361fcdfd31cfbd042e6ab9751900e962b467c39`. Source charter pp. 5–10, 15–17 and 34–36, SHA-256 `3110e8020cc1b86cdf7ba389602fb0ce0b941be84dfdef05d3eeb5580dec06bc`.
- Plan and protocol in [WorkPlan.md](WorkPlan.md) and [protocol.json](configs/protocol.json). The initial pre-measurement protocol entered Git locally at `02f1d075a517dc88e1b199024425841cac71bcc8`.
- Before any push, REST and GraphQL identified the GitHub repository as public. Writes were held until the user explicitly authorized that visibility. The disclosure and authorization preceded the registration at `d41bcbb09015eeb097c7e70f9c25e15d56f80c76`. Only the repository-visibility wording changed. Protocol SHA-256 `a6ee54b0ffd7b0fd630022b5e596418dc3d89514c4dde3782ad0b76cd767bce4`.
- Pinned prerequisite X03 `d85fe1cdb76cbc6d03e58e34f320c4c58a3f243c`. Its exact solver and independent partition checker agreed with exhaustive X07 subset checks for the uniform and four realized scopes. The [proof record](evidence/certificate.json) holds the selected queries, conflict witnesses, minima and reference-source hashes.

## 2. Target and audit boundary

Initial evidence contains a generic rejection using an unrelated test root and no intermediate under the frozen time, hostname and server purpose. It admits four completion classes for the uninspected signed bytes and fixture chain. When the approved local root and supplied intermediate are correctly provisioned, the certificate profile and direct-signature witness support a pass precisely for approved binding and an in-window leaf. Unknown or inconsistent inputs cannot supply a certificate. The forecast applies to a new evaluation on the same leaf bytes with only the declared local trust metadata changed.

The two queries observe approved issuer binding and leaf validity. The uniform optimum costs 4 declared units and requires both. The respective realized costs for approved/current, approved/expired, other/current and other/expired are 4, 1, 3 and 1. Empty observation is ambiguous. Each single-query omission leaves a target-distinct pair with the same observed answer, making the uniform audit inaccessible through that reduced interface.

## 3. Implementation and development checks

- Configured OpenSSL 3.2.4 verification with a fixed UTC timestamp, hostname, purpose, strict CA and leaf checks, and fixture-only anchors. Actual verification uses the native executable. The independent audit uses the public certificates' direct chain signatures and validity intervals.
- Used in-process signing keys and public certificate serialization for separate development fixtures. Initial native diagnostics on one development exemplar per completion gave error 20 at depth 0. A development valid control passed, an expired control returned error 10, and supplying the unrelated anchor returned error 20. The development keys and observations are distinct from the randomized prospective sample.
- Reproduced the exact finite proof against hash-pinned X03 code. Checked pre-outcome rule errors, ambiguity/refusal, score accounting and altered forecast receipts using the local unit tests.
- The prospective stages use exact GitHub source archives without Git metadata. Custody commands and evidence promotion are described in [README.md](README.md).

## 4. Pre-outcome custody and forecast

- Executable scope registered at `4933d82cab463dfee60b18843acc4d7b524fe90a`. The independent custodian retrieved the exact GitHub source ZIP without Git metadata, SHA-256 `5b5f23f92703a26be5bccbc84b221f81101360486594818f95c11e1f38d4d76c`, and registered it at `2026-11-26T15:47:52.6492071Z`. Five unit tests passed from a separate extraction.
- The custodian replayed the X03 comparison, generated balanced opaque fixture assignments and committed the reveal before diagnostics. The seal is `e179b42c8bd144dfd38ba15a35a85d203e0f1b7f81f5c6431894679f2025e98d`. The [commitment](evidence/pre-outcome/commitment.json) binds the timing, protocol and exact public certificate bytes.
- Initial native diagnostics and the independent signed-byte audit precede the [forecast](evidence/pre-outcome/prediction.json), SHA-256 `ee54cc6983d920468d480663cf7d084df3a3334db6707ac30a450c0f4393e1ac`. In both ambiguity witnesses the original native verification rejected with the same code at depth 0. The audit predicts failure for `case03` and success for `case07` after provisioning the approved metadata.
- Both probes identify all eight outcomes and predict two passes and six failures. The coarse baseline predicts eight failures. The native field baseline predicts the same labels as the audit. The no-audit comparator abstains in all eight cases. Each single-query omission forecasts four failures and abstains in the other four cases.
