# T24 · Identifiability against history-dependent conditional-mean nuisance

## An exact obstruction

Suppose two target-distinct candidates have intersecting certified intervals for every lawful q. For each q pick one \(m_q\) in the intersection. In each model use the admissible responder that, conditional on any history and chosen q, draws a fresh Bernoulli bit of mean \(m_q\). By the richness premise this pair of responders is permitted. Independently observable auxiliary fields must also have common law along these responses. All mounted response rows are then equal, and T15 applies to the entire adaptive audit. T21 rules out a uniform failure guarantee below one-half. If interval richness fails, the intervals may be coarse marginal summaries of different allowed joint laws and the obstruction does not follow just from overlap.

## Bounded response concentration at an adaptively selected count

Let q be fixed. Write \(N_q(t)=\sum_{i\le t}1_{\{q_i=q\}}\) and \(S_q(t)=\sum_{i\le t:q_i=q}(Z_i-\mu_i)\), where \(\mu_i\) is the genuine expectation conditional on the auditor history and the selected query, before the response. Conditioning also on the query at each draw respects predictable selection. Each \(Z_i\) lies in [0,1]. The conditional Hoeffding lemma gives
$
L_t(\lambda)=\exp[\lambda S_q(t)-\lambda^2 N_q(t)/8]
$
as a nonnegative supermartingale, for every fixed real λ. For completeness, the log moment generating function of a variable in [0,1] under exponential tilting has second derivative the tilted variance, at most 1/4. Centering gives value and first derivative zero at λ=0, and integrating twice yields the conditional bound \(\log\mathbb E[e^{\lambda(Z_i-\mu_i)}\mid\text{history and query}]\le\lambda^2/8\). The query indicator selects either this factor or one. If the query is randomized, take the subsequent expectation over that already selected action. No independence or reset of responder memory is used.

Let \(\tau_n\) be the first time q has n samples. Stop \(L_t\) at \(\tau_n\) or a deterministic cap m. Its mean is at most one. The event \(\tau_n\le m\) and \(S_q(\tau_n)\ge nu\) gives stopped value at least \(\exp(n\lambda u - n\lambda^2/8)\) for λ>0. Take λ=4u and let m increase to infinity. Use negative λ for the lower tail. It follows that
$
\Pr\big(\tau_n<\infty,\ |S_q(\tau_n)|/n>u\big)\le 2e^{-2nu^2}.
$
At the radius in STATEMENTS, summing over q and n spends total error at most δ because \(\sum_{n\ge1}1/[n(n+1)]=1\). For the true candidate each conditional \(\mu_i\) on q lies in its closed certified interval, hence so does their average at a sampled count. The observed mean lies within b(n) of that interval on the simultaneous event. This is true on the entire sampled timeline under every permitted responder, including interventions chosen in response to earlier bits.

## Adaptive rule, cost and soundness

Maintain the nested set of all candidates satisfying the interval-distance tests at all completed sample counts. Issue only from a nonempty homogeneous set. An empty set yields abstention. While there is an opposite-target pair, pick an authorized query with disjoint intervals for that pair. Any q already at n_q cannot separate a remaining pair: if both survived its nth test, each interval would be within b(n_q) of the same sample mean, and their distance would therefore be at most 2b(n_q), contradicting their gap at least g_q. Thus the selected query still has budget. Advance its count to n_q unless a terminal set appears sooner. After that, q is no longer useful for an opposite-target pair. Finitely many q give deterministic stopping and the stated sum of costs, even on a bad sampling event. On the simultaneous event the true candidate survives, the set is nonempty, and the only possible terminal decision is its correct target. Hence wrong decision or abstention has probability ≤δ. If no target-distinct pair exists, no sampling is needed. The bound is a worst path cost and therefore also bounds this procedure's expected cost. It is not an optimized expected cost, nor the statistical risk attained by every fixed budget smaller than it.

## A separate score anchor

If the honest bit V has conditional mean in the checked interval [a,b] and a trusted account controls \(\Pr(Z\ne V\mid h,q)\le\eta\), then
$
|\mathbb E[Z\mid h,q]-\mathbb E[V\mid h,q]|\le\mathbb E[|Z-V|\mid h,q]\le\eta.
$
This gives the clipped interval [a−η,b+η] even if the mismatch gate is correlated with the honest score and all prior activity. Source inspection must establish that the honest scoring mechanism samples the intended condition and that measured mismatch or hardware support enforces the bound on each covered history, including non-cold starts if those are legal. In a fixture, an independently held fresh uniform ticket under a calibrated threshold can fix a and b, while a separate bounded-loss instrument identifies the rate of departures. A dependence on the evaluated process's unsupported assertion of honesty would not supply this premise.

For a small positive schedule, take two probes and four onboarded modes with nominal honest mean pairs (1/5,1/2) and (1/2,1/5) for two safe modes, (1/2,4/5) and (4/5,1/2) for two unsafe modes. These are predeclared characteristics of an independent trial mechanism and an already defined deployment target. If its mismatch is at most 1/20 conditionally on every admitted history, the expanded intervals separate every opposite-target pair somewhere. Each probe still aliases at least one opposite-target pair. The theorem applies even when the perturbation responds to the earlier outcomes. Such an instrument can be built in the restricted model by a signed threshold register and a separately audited response gate. This example only needs the sufficient direction. Its score classes and deployment labels require independent source justification. It is a mathematical fixture, not a new experiment.

If the nuisance class is more restricted than the stipulated rich class, even overlapping one-step mean intervals can permit recovery. For example, in two fixed two-draw laws, the second bit repeats the first in one and flips it in the other, with fair marginal bits throughout. Both fit the common coarse interval [0,1] at every history. The permitted two-draw relation still distinguishes them exactly. Stationary indistinguishable laws are not in that narrower class. Conversely, a calibration valid only before carry cannot supply the conditional intervals in a later state. X09's scripted cue and reset system gives controlled examples and its two alternate scoring rules produce false favorable verdicts when the independent score anchor is omitted. It is no evidence of the complete interval-martingale theorem against real adversaries. [Time-valid martingale comparison](https://arxiv.org/abs/1810.08240) · [Observed evaluation-awareness study](https://openai.com/safety-alignment/eval-production-behavior-gap/)
