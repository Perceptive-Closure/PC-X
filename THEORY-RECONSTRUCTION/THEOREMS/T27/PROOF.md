
# T27 · Quantitative composition from distinct checks

Fix the declared context and put $A=G\setminus\bigcup_iL_i$. Every occurrence of $G$ is either in $A$ or in the local union. The ordinary finite union bound yields
$P(G)\le P(A)+\sum_iP(L_i)
          \le e+\sum_i \min\{1,p_i+d_i\}.$
Clipping at one gives the claim. If exact overlap data are already trusted, the separate estimate $P(G)\le P(A)+P(\bigcup_iL_i)$ may be tighter. No independence assumption is needed for either inequality.

## Sharpness of the abstract budget bound

Write $a_i=\min(1,p_i+d_i)$. Allocate successive disjoint atoms until their masses total $s=\min(1,e+\sum_i a_i)$, with each mass at most one of the available $n+1$ allowances $e,a_1,\ldots,a_n$. This is accomplished by allocating the lesser of the remaining mass and the next allowance. Let the exceptional atom have mass $a_0'\le e$ and the local atoms have masses $a_i'\le a_i$. Add one residual atom of mass $1-s$. Let $L_i$ be its associated local atom and $G$ the union of all allocated atoms. Then $P(G)=s$ and the uncovered part of $G$ has mass $a_0'$. Set $Q_i(E_i)=\min(p_i,a_i')$ on an isolated two-point space. This respects the isolated cap, and $P(L_i)-Q_i(E_i)=(a_i'-p_i)_+\le d_i$. When using a compared local event bit, the two Bernoulli marginals admit a coupling with mismatch equal to this difference. Hence neither the clipping nor the sum can be improved from these budgets alone. The construction need not meet extra physical constraints or observed overlaps from a particular system.

## Separate validation of the premises

For a finite horizon with event source automata or event bits in the state, propagate joint reachable support through the authorized graph. Attach a bit for each event verified along the physical trace. Search supported terminals with the global bit set and all local bits clear. One such terminal gives a concrete supported violation of pathwise containment. No reachable such terminal gives pathwise containment under the checked support. With an exact joint probability law, summing the corresponding terminal probabilities gives the quantitative exception bound instead. Prefix testing alone is inadequate when a local event found later covers an earlier global event. An arbitrary non-finite-trace objective needs a separate monitor argument.

For local preservation in the actual joint setting, verify the projection and semantic endpoint event onto the isolated setting. One route is a controlled comparison using T26.a's hypotheses with the joint setting as the instrumented plant and the relevant local component of the policy as the transferred policy. If its state transition tables after projection, allowed actions and event mapping satisfy that certificate, its resulting discrepancy bound gives a valid $d_i$. Direct independent scoring of joint and isolated marginals on compatible contexts can also supply the directed event bound. Proof of that premise must come from the actual joint mechanism and common event definition. Separate accountability for plant safety, service and admission remains necessary. Model-only containment and empirical confidence in a measured marginal have different assumptions.
