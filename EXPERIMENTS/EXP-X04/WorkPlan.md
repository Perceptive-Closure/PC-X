# EXP-X04 — Adaptive semantic audits

## A. Scientific objective

When can an observation-only adaptive audit reduce worst-case legitimate acquisition cost over static querying? Test T05–T10, including the realizability of adaptive separation in a meaningful authorization structure. The hypothesis is exact finite minimax correctness and a cost advantage on some prespecified structured families. A null advantage on other families is informative. The generic address separation alone does not validate a scalable PC-specific extension.

## B. Scope

Write in `EXPERIMENTS/EXP-X04/`. Use finite deterministic domains, terminating decision trees, positive integer acquisition cost, and permitted queries fixed independently of any realized target. Include constructed PC-structured cases and generic controls. Pin X03 static/local reference provenance. No external data, services or operational access.

## C. Mathematical specification

Use belief update by realized query answer and stop on nonempty target-homogeneous beliefs. For heterogeneous B, minimize query cost plus the maximum successor value over attainable answers. Refuse inaccessibility when query answers leave a target-distinct pair. Compare worst-case adaptive A to max realized L and uniform static S on the same admissible families, including nonbinary answers and weighted costs. Independently validate that policies choose only from history and never use hidden completion identity. Distinguish worst-case weighted cost and measured expected cost under stated priors.

## D. Methodology

Use a finite address family as structural control and a PC workflow that routes requests to genuinely consequential domain-specific evidence, representation and authority branches under an authorized checkpoint query. Include constant, unreadable, all-query and strict/weak savings cases. Freeze widths, seeds, comparators and budgets. Compare with exact static/local costs, full acquisition, greedy partitioning, a prior-weighted cross-target edge-cut or comparable disjoint decision-region baseline, and seeded random acquisition. Validate on tractable instances with independently enumerated deterministic trees or a decision-at-budget recursion. For larger closed-form controls give algebraic checks and distinguish extrapolated values from measurements.

Decision-region precedent and the distinction between disjoint and overlapping regions are in [Javdani et al., AISTATS 2014](https://proceedings.mlr.press/v33/javdani14.html).

## E. Implementation

Provide query/contract fixture generator, exact optimizer, policy replay verifier, independent reference, baseline algorithms and pinned seeds/configs. Retain raw case outcomes, time/memory and decisions at each reachable leaf. Supply reproduction commands and explicit policy acceptance.

## F. Acceptance

Require zero unexplained reference mismatches and verify the hierarchy on all supported instances. Require sound stopping and a valid inaccessibility pair. Test deliberately corrupted leaves, unavailable queries and incorrect hidden-state selection. Record whether any strict structured advantage was observed and report the comparison denominator. A correct no-advantage finding can pass execution.

## G. Execution phases

| Phase | Work and evidence | Verification |
| --- | --- | --- |
| 1 | Freeze query interface, costs, structured and generic fixtures, baselines | Crosswalk charter pp. 10–13 and 36–37. Pin X03 evidence. |
| 2 | Build optimizer, tree verifier and independent budget/reference checks | Test branch feasibility and intentionally false policies. |
| 3 | Run corpus, replay policies and cost hierarchy for every completion | Report distributions, separate expected and worst case, preserve no-savings scenarios. |
| 4 | Package findings and reproducibility evidence | Reproduce accepted cases in independent clean checkout before cleanup. |
