# EXP-X07 — Security diagnosis reversal

## A. Scientific objective

Can a source-grounded audit correct a rejection-only explanation for offline native X.509 verification? Test a bounded empirical instance of T02, T04–T06 and T13. The hypothesis is that identical coarse native rejections can support different outcomes when approved trust metadata is properly provisioned, and some prospective evidence-supported diagnoses reverse the preregistered coarse baseline. This investigates defensive diagnosis in controlled fixtures. It provides no estimate of the prevalence of the mistaken baseline in operators or of ecosystem security.

## B. Scope

Write in `EXPERIMENTS/EXP-X07/`. Use offline OpenSSL certificate verification with inert public test certificates and an approved test root, local trust metadata and fixed evaluation time. Use synthetic certificates only as inputs to the real native validator. No endpoint traffic, weakening verification, operational trust-store changes, exploit or vulnerability reproduction. Test fixture signing keys are temporary and stay out of evidence and Git. [OpenSSL verify documentation](https://docs.openssl.org/master/man1/openssl-verify/).

## C. Mathematical specification

Hold bytes and verification scope fixed per intervention. Let the target distinguish whether the unchanged leaf is valid under the correctly provisioned and approved test CA metadata at the frozen time. Define initial evidence from a coarse generic rejection and fixed scope, then construct more than one compatible reason for that rejection. Freeze auditable independently observable facts such as issuer/anchor fingerprints, chain availability, validity windows or an official binding. Compare the exact minimum cost with X03. Evidence acquisition must not invoke the held-out verification command nor read its result. A richer native-diagnostics baseline must also be measured and its limitations reported.

## D. Methodology

Use the parent as independent custodian of randomized held-out fixture assignments. Generate ephemeral signing keys in isolated temp storage or use documented authorized public certificate artifacts. Preserve public certificates, hashes, original native outcomes and frozen commands. Include clear-positive valid-chain and clear-negative expired or independently invalid-for-scope controls, a no-audit comparator, wrong-endorsed-anchor/control, and remove-one-query or missing-metadata ablation. Precommit baseline decision mapping, all accepted diagnoses and criteria, and open the actual verified result after a remotely verified prediction. Require positive and negative held-out diagnostic conditions so an always-reverse strategy can fail.

## E. Implementation

Provide versioned native verifier invocation and fixed-time flags, fixture/setup provenance, scoped diagnostic and independent audit witness checker, field-derived baseline scripts, controls, result processing and reproduction instructions. Preserve irreplaceable raw native outcomes and public cert material only.

## F. Acceptance

Require independently valid initial ambiguity; correct selected-probe sufficiency; prediction-commit-before-opening; actual native confirmation; and correct retention of at least one negative diagnosis, subject to the hypothesis result. Quantify improvement, failure and abstention over both declared baselines. If stronger native diagnostics already resolve the condition, state the limit. A null result or mismatch stays recorded.

## G. Execution phases

| Phase | Work and evidence | Verification |
| --- | --- | --- |
| 1 | Freeze local test policy, baseline, fixture classes, cost and timing | Validate OpenSSL options and pin X03 reference. |
| 2 | Establish compatible diagnoses, audit proof and independent test evidence | Validate public provenance, no direct target query, and no test key persistence. |
| 3 | Commit predictions and open native validation | Record rejection reason, trust effects, raw outcomes and controls. |
| 4 | Verify and publish bounded results | Replay native validation from clean checkout and report chronology, all deviations and limitations. |
