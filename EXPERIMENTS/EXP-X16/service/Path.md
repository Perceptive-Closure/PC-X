# EXP-X16 native service

## Replay

From `EXPERIMENTS/EXP-X16`, run `node service/native.mjs request.json response.json` with Node.js 22. The request contains absolute `catalogue`, `authority`, and `workspace` paths and an ordered `tasks` array. Each task supplies the installed accepting path to the native service. The service checks that every edge starts at the vertex reached by the preceding edge and that the final vertex accepts.

The seal contains the SHA-256 of the exact catalogue file bytes. Verify the official GitHub release and freeze pins to establish the authority's public-key identity. The CLI verifies Ed25519 over `PCX-X16-authority-v1`, the lower-case catalogue SHA-256, the lower-case source commit SHA, and the lower-case frozen manifest SHA-256, each followed by LF and encoded as ASCII. Use the exact Git blob for an official catalogue when the checkout converts LF to CRLF. A rejected batch seal exits with code 1 before writing a response or a work artifact.

`op: "static"` accepts either `queries: ["guard-1", ...]` or `static_policy: {"ask": "guard-1", "next": {"fresh": node, "stale": node}}`. A static terminal is `{}` or `{"verdict":"YES"}` or `{"verdict":"NO"}`. Responses carry `answers`, the query ID `sequence`, each `{id,answer,paid}` in `steps`, and `paid` as the sum. Static queries have a separate read-only driver. Online policies can choose from the current quoted commands through their complete public receipts.

## Source guard and tariffs

The installed representation is an ordered array of one revision SHA-256 per phase of the input document. A fresh phase refers to the normalized input. A stale phase refers to the same normalized document with `\n[earlier revision]\n` appended to its body. Both SHA-256 values hash the encoded document object described below. The array position identifies the phase whose binding is being compared. R compares the entire encoded array for exact equality.

On the final candidate successor of a fast atom, the service refreshes the current phase's binding to the normalized input revision. Earlier successors preserve all bindings. Slow jobs resolve the stage work from the source or previous artifact and preserve the installed bindings on every successor. The service evaluates each candidate's actual before and after array and rejects the entire atom if any pair differs. This check runs before looking up the chosen tape index and before any stage writes. The inventory provides `representation_before` and `representation_before_sha256` on each row, and `representation_after`, `representation_after_sha256`, and the byte equality result `r_changed` on each outcome. The inventory uses the fixed probe document in `native.mjs`. It lists the meter reached on entry to stage zero and the meters reached by lawful prior jobs and supported reads. It includes the full raw support of freeze-removed jobs and applies the exact residual work quota when a run calls a job.

Fast and slow jobs use the declared base and base-plus-premium work tariffs with zero paid charge. A read uses the installed native paid quote and zero work. A move is one completed authorized job or read. At the boundary the service checks the horizon, whole-atom guard, residual budget, and tape index. After a receipt it looks up the complete literal `obs|meter` key. An absent branch stops at `missing-branch` with the authorized receipt and artifact already recorded. A denied call returns its reason without adding a move or artifact. A policy terminal at the horizon can stop and record its verdict.

The `split-calls` command for fast is only the installed literal, alongside the common `job.slow`. The `free-guard` initial observation is `fresh` or `stale` for stage 1. In `hidden-carry`, committing an earlier edge with `carry:true` adds 4 to a later `ask.flag` quote and preserves the public meter. In `changed-instrument`, `ask.flag` marks the run's routing choice as `quarantine` while returning the standard read result and quote. The feedback-suppression case uses the signed constant meter. Cartesian edges and missing-LONG support are changes to comparator models. The native service enforces the signed graph and full receipt support.

## Durable work format

All hashes are lowercase SHA-256 in hex. An encoded object or array is `Buffer.from(JSON.stringify(value) + '\n', 'utf8')`. Artifacts contain exactly those bytes. The canonical source document copies, in order, `id`, `title`, `category`, and `body`. Its hash is `input_sha256` in each record and `truth.document_sha256` in the run result.

The normalized document uses the same property order. Its `id` comes directly from the input. Its `title` is NFKC-normalized and trimmed, with each sequence of JavaScript whitespace replaced by one space. Its `category` is NFKC-normalized and lowercased. Each run of characters outside ASCII `a-z` or `0-9` becomes a hyphen. The service trims edge hyphens, truncates to 64 characters, trims any trailing hyphen again, and substitutes `uncategorized` if empty. The `body` converts CRLF and CR to LF.

Each product has ordered fields `document`, `reviews`, `destination`. `receive` and `receive-route` produce the normalized document with an empty review list. `review-N` reads the preceding durable product and appends `{task,min_length,term_count,terms}`. It lowercases the normalized body, finds contiguous sequences of Unicode letters or numbers, selects terms at least `N` Unicode code points long, deduplicates them, and sorts them in JavaScript default string order. Its `min_length` is `N` and `term_count` is the length of its term list. `route` carries the preceding durable product into its destination. The product's `destination` is null on intermediate stages, `routed/category-<normalized category>` on ordinary final stages, and `quarantine` on a disturbed final stage.

The `task.id` is the run directory under the selected workspace. Use a fresh ID matching `[A-Za-z0-9][A-Za-z0-9._-]{0,127}`. Trailing dots and reserved Windows device names are invalid. A run claims its directory exclusively on its first authorized job. Read-only and stopped-before-work runs write zero artifacts. Intermediate jobs persist `stages/<stage padded to at least three digits>.json`. The final job persists `<actual_destination>/document.json`. Each record is flushed and atomically published under its final name. The service reads the prior record's bytes before computing the next stage's work and validates every record's digest and chain at termination.

The job record's property order is listed here for byte replay.

```text
schema, profile, stage, task, edge, action, receipt, work, paid, input_sha256,
prior_output_sha256, source_document, representation_before,
representation_before_sha256, representation_after, representation_after_sha256,
product, catalogue_sha256, source_commit, frozen_manifest_sha256
```

`schema` equals 1. `receipt` has ordered `obs`, `meter` fields. `stage` is zero-based. `prior_output_sha256` is null on stage zero and hashes the previous exact stage file bytes otherwise. `source_document` contains the original canonical input on stage zero and is null afterward. The three final fields come from the verified seal. An authorized job's representation arrays match. The public step names the corresponding stage file relative to the run. Reads return `artifact:null`.

`truth.done` is the number of verified completed stages. `truth.complete` requires the full stage chain and the correct input-derived physical destination. `truth.artifact_paths` lists each stage artifact in order and `truth.artifact_sha256` maps its relative path to the actual byte digest. `truth.expected_destination` identifies the ordinary destination for the input. `truth.actual_destination` is the final occupied directory relative to the run, or null before routing. A policy verdict and a verified document outcome are separately recorded.

## Public training results

On 27 November 2026 Asia/Karachi, `node service/training.mjs` passed 28 signed tasks and rejected both deliberately altered batch seals on Node.js v22.15.0. The harness creates a temporary workspace, a demo Ed25519 key pair in memory, a dummy all-zero source commit and a manifest digest of a labelled training string. It independently rehashes the staged document bytes and representation arrays, and checks normalized output, work and paid quotas, both complete meter receipts, static sequence and stopping, invalid graph, split literal calls, effect of receipt suppression and initial disclosure, hidden carry, and quarantined output. The alternate stale training catalogue deliberately combines an unchanged and a changed fast successor. Both fast attempts are refused and either slow branch completes. The altered-signature and altered-catalogue batches create zero work artifacts. The harness prints the generated request and evidence directory for direct inspection.
