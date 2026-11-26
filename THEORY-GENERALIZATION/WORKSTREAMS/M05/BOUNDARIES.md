# Attaining models and obstruction cases

## T25.J · Correlated truth with fixed visible laws

In each of two populations \(j=0,1\) a fair route flag selects either alarm or silence. Conditional on either flag, there are four equally frequent paired route tickets. Independently checked score-card semantics say that every silent violation in population 0 forces an alarm violation on the same ticket, and population 1's true label is the complement of population 0's on the corresponding flag and ticket. These are relations on actual labels under a declared common-ticket construction. The controller sees the flag and receives only the permitted acknowledgement. In population 0 an independent check validates an alarm violation on the first ticket and an alarm nonviolation on the second. The other labels can vary through the permitted paired outcome rows. Here the alarm function remains the route flag on every path.

Write \(a=\Pr_0(V=1,M=1)\) and \(b=\Pr_0(V=1,M=0)\). Every law satisfies

$$
1/8\le a\le 3/8,\qquad 0\le b\le a,\qquad
(t_1,m_1)=(1/2-a,1/2-b).
$$

All such values are attainable under the declared source option to randomize permitted outcomes per ticket. Keep the first ticket's alarm truth one and the second's zero. Allocate \(a-1/8\) additional alarm-positive mass across the third and fourth tickets, each of capacity \(1/8\). On every alarm-positive atom set the matched silent truth one with conditional probability \(b/a\). On an alarm-negative atom the silent truth is zero. Generate population 1 by the certified complement correspondence. This physical pairing retains all alarm/ticket masses. The audit conditions concern exact submasses, and none of these calculations requires arbitrary independent truth splits across contexts.

The attained miss maxima for populations 0 and 1 are \(3/8\) and \(1/2\). Their actual risks have ranges \([1/8,3/4]\) and \([1/4,7/8]\). The ranges of false negatives conditional on a violation are \([0,1/2]\) and \([1/2,4/5]\), with all denominators positive. To see the second lower endpoint, \(1/2-b\ge1/2-a\) implies the conditional miss fraction is at least \(1/2\), attained at \(a=b\). At any fixed \(a\) the fraction is nonincreasing in \(b\), since its derivative is \((a-1/2)/(1-a-b)^2\). At \(b=0\) it is maximized by \(a=3/8\). The lower and upper extrema of the worst-context actual risk are \(1/2\) and \(7/8\). Here \(r_0+r_1=1\) in every completion, and \(a=b=1/4\) gives balanced risk. Taking the two correct marginal lower endpoints separately would give only \(1/4\). With the same audited submasses but freely splittable labels in every flag cell, T25's rectangle allows a population 0 miss mass \(1/2\). The new constraint rules that allocation out and increases the worst-context lower bound. [Exact finite checks](CHECKS.md).

### Discrete mode choice and the undefined denominator

Take three mutually exclusive installations with the same fair monitor flag and same complete visible records. The first installation has \(V=M\), the second \(V=1-M\), and the third \(V=0\) always. A trusted rule within each installation defines the fixed truth. The three observable tapes have the same law. The defined false-negative rates are \(0\) and \(1\), and the third completion has no conditional rate. A convex mixture of the first two modes would report possible rate \(1/2\); the declared installation can select only one mode. The risk range as a set is \(\{0,1/2\}\). The inequality \(m-\beta r\le0\) on the third installation certifies no numerical rate for that installation. A monitor observation is an alarm function even when the ground-truth scorer disagrees with it.

### Fixed continuous parameter outside the finite union

Suppose two successive stochastic source moves generate two independent Bernoulli draws conditional on one installation parameter \(p\in[0,1]\), fixed for both moves. The pair of linear law statistics \((\Pr(X_1=1),\Pr(X_1=X_2=1))\) ranges over \(\{(p,p^2):0\le p\le1\}\). Every nontrivial segment between two distinct points of this graph leaves the graph, by strict convexity of the square. Any convex subset of the exact graph thus has at most one point. A finite union of polytopes with affine projections cannot describe the exact identified set. Replacing the shared conditional probabilities by independent interval rows, or mixing \(p=0\) and \(p=1\) within an installation, would admit the extraneous point \((1/2,1/2)\). A continuum of fixed implementation parameters requires a compatible non-affine or alternative exact representation.

## T26.C · Fidelity outside a common-policy comparison

Two finite dispatch policies each complete one qualified job by the deadline. Legally callable commands \(U,V\) select distinct station assignments. The original policy always selects \(U\) and its corresponding station at the second step. The probed policy lawfully receives one extra display bit at the first step and selects \(U\) or \(V\) according to that bit. It selects the corresponding station at the second step. The two named source moves have distinct resource or authority effects confirmed by the native rows, and the intervened policy uses the new observation. Each branch submits the qualified job. The independently scored target is a recorded quality fault with conditional probability \(1/4\) at the final step for either branch and station. Each native row retains the station, the true work and the fault. The final conditional row may use the same four-ticket fault source in the paired test, independently of earlier probe display bits. Synchronizing this last ticket gives terminal disagreement zero by a valid conditional-row certificate. Thus the named policies and native plants differ while their target risk is exactly \(1/4\) in both. The accepted T26 common-policy premise cannot compare these policies directly. A comparison preserving complete station fields can have positive first-state mismatch even though all terminal fault labels in this coupling agree.

### Terminal coupling can conceal a history violation

For one native arm the first tick draws a fair bit \(X_1\) and the second tick retains it. Its terminal truth equals \(X_1\). The other first tick carries a constant observation and physical state, and the second tick draws a fair bit \(Y_2\). Its terminal truth equals \(Y_2\). The two true risks are both \(1/2\). Coupling terminal bits alone could yield perfect agreement. Any coupling satisfying the sealed conditional rows must have \(Y_2\) fair conditional on each positive paired prefix at tick one. Since \(X_1\) is already determined at those prefixes, the mismatch probability is exactly \(1/2\) there and in total. A proposed coupling with \(Y_2=X_1\) violates the second arm's conditional row. This also shows that existence of a zero-disagreement coupling is stronger than equality of native risks.

### Accuracy can survive a destructive intervention

Original and probed machines can both acknowledge one job but have distinct service rows. Let the original always complete a work unit. Let a probe reserve the only service slot and faithfully report that the original request remained unserved. For its own law the probe label has zero scoring error. The original and probed risks of actual underwork are \(0\) and \(1\). Another probe could preserve the exact native state and policy and record a constant display in a genuinely stochastic system. It would have full fidelity and provide only that constant for measurement. These illustrate the need to establish the probe's real readout and its fidelity through separate checks.

### Adaptive policy and pruning witnesses

Even identical plant rows under every callable action allow a risk change from zero to one if an original policy always takes a lawful safe action and a probe policy uses an extra constant feature to always take a lawful dangerous action. The original-policy clone on the probe still has risk zero. The compared laws must use the policies actually named in the claim.

For an infeasible downstream row, let two arms draw fair bits at step one and deterministically copy them at step two. A pairing contract requiring equality of the final copied values forbids every second-step transition on off-diagonal first draws. Those paired prefixes have empty rows. The root retains its two fair marginals on diagonal pairs and is feasible. If physical paired support instead requires the two first draws opposite, the root is infeasible. Dropping the first-choice restriction or filling an empty required row with an unconstrained continuation would admit impossible histories.

## T27.J · A stateful shared-ticket composition

Consider eight equiprobable shared workload tickets, independently fixed by a checked common source at the first move. Controllers use the authorized dispatch record to attempt one qualified job each. Their intervention remains lawfully callable in every declared mode. A trusted global ledger records a timeout bit on tickets 1 and 2. On those tickets the shared dispatch resource delays both completions and both local underwork events are set at the final move. On ticket 3 the global ledger records an actual shared-lease collision with conditional probability \(\theta\in[0,1]\), while both jobs still complete. There are no other violations. The global predicate is timeout or collision. Each independently audited isolated native reference has the same ticket law and a local underwork event exactly on ticket 1. The source comparison shares the first ticket and leaves the isolated continuation intact at every paired prefix. The uncertain lease row on ticket 3 is the only extra paired branch. Any value of \(\theta\) is an admitted conditional row and has a realized joint law.

The actual local violation events coincide with probability \(1/4\). The three relevant disjoint joint patterns \((G,L_1,L_2)\) have masses

| Pattern | Mass |
| --- | --- |
| \(111\) | \(1/4\) |
| \(100\) | \(\theta/8\) |
| \(000\) | \(3/4-\theta/8\) |

The actual global range is \([1/4,3/8]\), the uncovered range is \([0,1/8]\), and the two directed retention differences equal \(1/8\). Every endpoint is attained. T27's separate abstract budgets allow \(1/8+2(1/8+1/8)=5/8\). At global tolerance \(1/2\), the joint constraints certify passage. Exact containment and zero drift both fail as universal properties in the same class. The physical invariant establishes overlap and distinguishes those ancillary claims from the global threshold.

On the paired prefix for ticket 1 the isolated conditional risk is one even though the unconditional cap is \(1/8\). On ticket 2 the isolated risk is zero and both actual local events are certain, so a positive directed drift can arise in a prefix class where the unconditional drift looks small. The initial timeout precedes the final local underwork scorer; reading only the early bits would incorrectly count both timeout tickets as uncovered. Positive shared workload coupling and local-risk retention supply different obligations.

The same plant can demonstrate the three calculations on one completion. Suppose a public monitor flags ticket 1 only. A paired diagnostic plant forces collision on ticket 3, preserves the other target labels, and reports its own terminal true event faithfully. Its native rows and same first-ticket source are independently checked. Its actual risk is \(3/8\). For the original plant, the missed mass is \((1+\theta)/8\) and the conditional false-negative rate is \((1+\theta)/(2+\theta)\), with attained range \([1/2,2/3]\). The probe-only disagreement has mass \((1-\theta)/8\), the original-only mass is zero, and the actual global event outside the local union has mass \(\theta/8\). Both latter upper endpoints are \(1/8\) and their sum is exactly \(1/8\) throughout the common completion class. This relationship uses one physical pairing and one joint flow. Substituting the probe's score for the original event, or optimizing each discrepancy allowance as if its maximum occurred alongside the others, loses that joint information.

### Local and pairwise summaries can both be insufficient

Under two fair-bit physical policies, suppose the two local violation events are the same bit. Then global union risk is \(1/2\). A second compatible resource mechanism uses opposite bits, producing global union risk one with the same two local marginals and exact containment. Independent labels would give \(3/4\), a distinct value. Observing matching one-tick local marginals, or keeping the same authorized log, cannot establish which global law applies.

For three fair local bits, specify that every pair is opposite almost surely. Each pair has a valid two-variable law with the same one-variable marginals. No triple simultaneously realizes the three pair constraints, since opposition between bits 1 and 2 and between 2 and 3 forces equality between 1 and 3. A full joint flow reports inconsistency.

One can also retain all local isolated risk bounds while the global event has mass one due to an unmodelled resource collision. Conversely exact event containment can hold while actual local risks grow from zero to one because every source-checked joint job loses access to the only service slot. These expose separate invalid inferences from isolated audits and from event semantics. A joint flow needs source support even when an external monitor prints the same acknowledgements in both cases.
