# Guarded source fixture

This is a finite, constructed service for the calibrated inspection and delivery of inventory reports. A stock snapshot is useful because it returns a checked count for a current order even when its separate calibration field is erased. Deployment is a regulated dispatch of a new inventory record. A wrong record actually written to a dispatch output is a violation; a correct dispatched record completes the job. The prototype is an exact finite source fixture, with no claim of field testing or measured production risk.

## Physical source and callable commands

The two allowed installations bind an immutable table and an order-number namespace to the same installed register. The allowed profile pairs are \((+,k_0)\) and \((-,k_1)\), with no other combinations. The key namespace is not read by the controller and creates no visible difference in the installed receipt interface. The frozen installed binding, representation and persistent authority registry are checked before each command. Physical stage effects can enable or disable an occurrence under that registry, and the compiler records each extensional availability change. The controller submits one of these literal commands.

| Literal | Effect | Optional price |
|---|---|---:|
| \(\texttt{stock/economy}\) | Deliver the next order's stock snapshot, with a protected calibration field revealed on a fair coin | 1 |
| \(\texttt{stock/full}\) | Deliver the next order's stock snapshot, with its protected calibration field delivered | 3 |
| \(\texttt{monitor/report}\) | Publish an ordinary responder report | 0 |
| \(\texttt{issue/positive}\) | Announce the positive result to the responder and authorize the linked dispatch | separate |
| \(\texttt{issue/negative}\) or \(\texttt{stop}\) | End without dispatch | separate |
| \(\texttt{stock/dispatch}\) | Dispatch the regulated inventory record after the matching direct or issued authorization | separate |

Each audit command advances exactly one counter where a finite horizon is used. Each stock command fills the current order with the exact count from a read-only inventory source, and writes its own completion record. An erasure affects only the attached calibration field. These commands create no dispatch artifact and cannot trigger the deployment violation. The deployment order and its execution authority are reserved independently of the optional stock orders. Stage, paid budget, separate completed work and all extensional effects are tracked. The fixture admits evidence additions for authentic stock order observations. Auxiliary reports are lawful decision records and have no authority over the installed binding, event predicate or clock. Each route and all its raw successors preserve the declared frozen values. There is no setup disclosure of which type is installed.

The sealed table is a hidden bitmask of four words. In type \(+\), membership in \(F_+^{-1}(1)\) is the single word \(0\). In type \(-\), it is words \(0,1,2\). Each optional stock command draws \(U\) uniformly from \(0,1,2,3\) and independently generates the reveal gate at its protected cut, after responder moves. On reveal, the actual authenticated field is \(F_\theta(U)\). Otherwise the field is \(*\). It goes privately to the controller. The responder sees which command is invoked, and may infer information from the controller's later public actions, but cannot read the private field or its latent word.

## Private memory and the two protocols

One concrete pair of admissible programs has a persistent bit \(m\), initially zero. At each evaluation move it receives a newly delivered private fair bit \(J\) and the actual command cue. It can choose an ordinary flag \(f\in\{0,1\}\) and update \(m\) to \(m\mathbin{\mathrm{xor}}J\mathbin{\mathrm{xor}}f\). The ordinary audit report can be a function of the pre-draw view and \(f\); the paired programs use the same function and actions while auditing. They may use the evaluation cue to follow an evaluation-specific reporting path. The same installed program persists at issuance with its own \(m\) and receives that issuance signal. At dispatch it proposes \(a\in\{0,1\}\) using the current physical phase, \(m\), and the delivered current authorization cue. It cannot read \(U,Z\) at that cut. For example, the program with \(f=m\) at optional moves can take \(a=m\) after positive issuance and \(a=0\) under direct authorization. There is a warm-start history of positive mass where its extra failure fraction is \(1/4\) although its direct run's extra fraction is zero. Another admissible program chooses \(a=1\mathbin{\mathrm{xor}}m\) after issuance. Constant authorized proposals zero and one can attain each extreme. General admissible versions can depend on their entire lawful history, subject to the physical guard and allowed outcome tables. The pairs used for law obstructions are specific fixed programs in this class.

The direct reference protocol uses a registered new order and direct authorization cue at its prescribed start. It does not require a test or use its outcome. The linked protocol reaches the same literal dispatch from its own physical authorization transition, carrying the actual private memory and permitted records. It always announces the positive result before the deployment proposal. The guard controls both protocols and is checked on each warm physical cut. An untrusted score from ordinary evaluation has no role in this authorization or in defining truth.

## Actual finalized work

After the proposal, the guard draws fresh independent uniform \(U,Z\) on \(0,1,2,3\). The writer accepts the correct source record if \(U\) is outside the bound table and \(Z\) is outside \(D_a\), with \(D_0=\varnothing,D_1=\{0\}\). It writes the output with its exact source count on acceptance. Otherwise it writes a wrong count into the output record for the regulated order. The independent decoder compares the actual output count with the immutable source count. The former gives genuine completion and the latter gives an actual violation. This deliberately fallible prototype admits positive risk even when the controller uses the correct authorized invocation. Extrema across the two permitted proposals are \(0,1/4\), giving actual risk ranges \([1/4,7/16]\) and \([3/4,13/16]\). At \(\varepsilon=1/2\) the bound separates both classes even for cue- and memory-dependent choices.

Equal ordinary audit record laws can be witnessed by keeping all delivered private nonces and memory updates paired. Each stock output except the calibration field is common. Conditional on a shared calibration receipt, its word is discarded from the producer's state. There is no later export of that word, and the independently chosen reveal gate does not affect a future source command. This meets the paired remainder premise for both literal probes and the monitoring command. With receipt suppression the paired entire audits agree at all designs. With the field kept, all finite exposed receipt laws overlap at every probe, so no finite path with one such report alone certifies exact identification.

To realize the same-type obstruction, change the declared proposal class to retain an additional proposal \(a=2\) with \(D_a=\{0,1\}\). It uses the same literal and actual decoder. Two fixed type-\(+\) programs with identical audit behavior can choose respectively \(a=0\) and \(a=2\) when dispatched directly, giving direct risks \(1/4\) and \(5/8\). Their after-issuance rules are separately fixed in the same programs. This supplies realizable opposite labels with equal complete audit laws even when all protected fields are exposed.

## Worked acquisition values

Let \(q=3/4\). At three optional moves and hard cost \(4\), first take the economy probe. On reveal take two more economy probes. On erasure take the full probe. Class error is \(61/256\) in the symmetric test. The completed count of revealed bits is three with probability \(1/8\), and otherwise one or two, with respective majority errors \(5/32\) and \(1/4\). Every fixed schedule at the same caps either uses at most one full and one economy probe, or at most three economy probes. In the first case its error is at least \(1/4\). In the second the error after three economy probes exceeds \(1/4\) because of the erasure-only path, even after the smaller probability of three successful reveals is taken into account. The recurrence gives \(61/256\) as the exact adaptive value. With the same budgets and a tolerance between \(61/256\) and \(1/4\), adaptive acquisition matters in this fixture.

For expected cost at \(\delta=1/5\), a private lottery uses radius \(1\) with probability \(2/3\) and radius \(2\) with probability \(1/3\). Cost is \(52/15\) per world, with exact class error \(1/5\). This uses a different cap definition from the hard optimum. At \(\delta=1/10\), radius two gives cost \(32/5\). Two hard moves fail at that confidence even with the full probe always available. Both serving and class-error guarantees are unchanged by the responder's allowed reactions to positive issuance.

## Reproduce

From the repository root run:

    python THEORY-FINAL-FLAGSHIP/T30-A/check_t30a.py

The checker treats the primitive words as exact equally likely finite tuples and verifies source-event counts, conditional next state pairing, physical effects, finite recurrence values and sequential costs. It uses rational arithmetic throughout. This evidence concerns the specified fixture.
