# T22 · Stopped adaptive change of measure

## What counts as a response row

Start with the same empty audit record and common independent auditor draws. Every model-dependent piece of initial information belongs to a recorded compulsory initial response row at time zero or appears as a separate initial KL term. If the starting observation/registration data are conditioned on and common across completions, the initial KL is zero. With this convention the published stopped identity accounts for every way the stopped transcript distinguishes the completions. The resettable allocation formula as written applies when there is no extra informative initialization. If such information is available, retain its contribution against each competing model or model it explicitly as one required observation. The [clarifications](../../WORKSTREAMS/deployment/STATEMENT-CLARIFICATIONS.md) preserve the prior statement seal.

## Likelihood and lower bound

For a fixed finite stopped history h, write its probability as the product of initial, query-selection, response, and stop/decision terms. The protocol factors for the same recorded history and independent coins are equal on both sides. Absolute continuity along P-positive paths and finite almost-sure stopping therefore give the stopped likelihood ratio as the product of the genuine conditional response likelihood ratios, including an informative initialization if present. For countable histories this follows directly by summing cylinder probabilities of the complete stopped paths. If common independent coins are represented by a separate atomless source, condition on those coins first. Their conditional measures are common at initialization, so their densities cancel with respect to the same base law and the outgoing response support remains as stated.

Taking logs converts this product into the sum of log ratios. The assumed absolute integrability allows expectation and summation to be interchanged. Conditional on the pre-response information and selected q, the stopping protocol has already determined whether this round is made. The conditional P-expectation of its log ratio is the conditional response KL. Thus the expected sum of conditional row divergences equals stopped KL. If on a P-positive row the Q probability of a P-positive continuation is zero, the stopped likelihood can be singular and KL infinite. That case is not needed for the finite equality statement.

Let A be issuing the true P target. δ-correctness counting abstention as failure gives P(A)≥1−δ and Q(A)≤δ. Grouping the path law into A and its complement by the log-sum inequality yields
$
D_{\mathrm{KL}}(P_{\mathrm{stop}}\Vert Q_{\mathrm{stop}})
\ge \mathrm{kl}(P(A),Q(A))\ge \mathrm{kl}(1-\delta,\delta).
$
For p>q the binary KL is increasing in p and decreasing in q, as seen from the derivatives log(p(1−q)/(q(1−p))) and (q−p)/(q(1−q)). Endpoints follow by lower limits; a Q-null event with positive P mass yields infinity.

Under true independent resets, for each legal action the genuine response law does not depend on the previous history and the conditional sum can be grouped as \(\sum_q \mathbb E_P N_q D_{\mathrm{KL}}(P_q\Vert Q_q)\). The expectation is taken under P, not Q. For every target-opposite Q, a δ-correct procedure gives the corresponding inequality. Its expected cost is the weighted sum of its expected counts, so these counts are feasible in the allocation relaxation and the optimum lower bounds the cost. In history-dependent systems, the summands are evaluated at histories drawn under P. Even with equal one-step marginals, the conditional and actual transcript KL may be positive. Neither lower bound converts a feasible vector of expected counts into an adaptive algorithm or gives a worst-path or fixed-budget guarantee. [Kaufmann, Cappé and Garivier, Lemma 1](https://jmlr.org/papers/v17/kaufman16a.html) · [Nitinawarat and Veeravalli on controlled Markov observations and cost](https://arxiv.org/abs/1310.1844)
