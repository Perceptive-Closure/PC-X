# Recorded randomization and measurable transcript scope

The proof-blind late comparison exposed a defect in a literal atom-probability reading of T15 and T23.a. The observed prefix can contain an independently sampled $U\sim\operatorname{Uniform}[0,1]$. Then every particular recorded $(U,h)$ has joint atom probability zero even under its actual model. A rule dropping every prefix of atom probability zero discards the truth. A countable observation model or a measurable formulation is required. The original likelihood arguments on finite categorical transcripts are still valid.

## T15 with randomized audits

For the discrete proof use the finite or countable declared observation/action alphabet and a common predictable action/stop kernel. No unrecorded model-dependent selection may be added. Raw private random seeds need not be part of the transcript if their effects are completely described by that common kernel and the plant responses depend only on the stipulated history and action.

For general observed standard Borel records, use regular conditional kernels. Fix an allowed randomized protocol. Require the same initial record law and, after each common policy action, the same complete conditional response law almost surely with respect to the common preceding history and action law. This condition concerns an entire jointly exercised record, including any explicitly retained randomness and the stop convention. Equality at time $t$ gives the common marginal $\lambda_t$. Integrating either response/decision kernel against $\lambda_t$ yields the same probability for every cylinder at time $t+1$. Induction gives equality of all finite padded transcript laws. Since they determine the generated sequence law, all events used by the selected protocol have the same probabilities. This a.s. condition avoids requiring positive atom probability when the visible history is continuous. Under equality of joint laws the regular conditional versions agree almost surely on that law, without a conclusion for unsupported histories. [Earlier discrete proof](../THEOREMS/T15/PROOF.md)

## T23.a with measurable likelihood ratios

Fix a common allowed audit protocol with its full recorded filtration $(\mathcal F_t)$ and resulting padded path laws $P_i$, one per finite candidate. The same protocol's own randomization, initialization and observed effects belong in these laws. Choose fixed positive weights summing to one and the mixture $M=\sum_i w_iP_i$. Set $p_{i,t}=d(P_i|_{\mathcal F_t})/d(M|_{\mathcal F_t})$, which exists because $P_i\ll M$. On $\{p_{i,t}>0\}$ put $Z_{i,t}=1/p_{i,t}$ and use zero elsewhere. The zero set is $P_i$-null. This definition is the reciprocal density on the supported part, rather than a ratio of two zero atom probabilities.

The restrictions give $p_{i,t}=\mathbb E_M[p_{i,t+1}\mid\mathcal F_t]$ almost surely. Thus $\{p_{i,t}=0\}$ implies $p_{i,t+1}=0$ up to an $M$-null set. For every $A\in\mathcal F_t$,
$$
\mathbb E_{P_i}[1_A Z_{i,t+1}]
= M(A\cap\{p_{i,t+1}>0\})
\le M(A\cap\{p_{i,t}>0\})
= \mathbb E_{P_i}[1_A Z_{i,t}].
$$
The equality comes from integration against the restriction of $P_i$ using the density at the same index. Hence $Z_i$ is a nonnegative supermartingale with initial mean at most 1 even if the initial record is informative. Ville's inequality gives $P_i(\sup_t Z_{i,t}\ge1/\delta)\le\delta$. There are countably many sampling opportunities, so all $P_i$-null support conditions can be imposed simultaneously. Keep a candidate when its prefix density is positive and its reciprocal is below $1/\delta$. The true candidate survives every such time with probability at least $1-\delta$. A nested intersection of these sets has the same simultaneous validity. Nonempty target-homogeneous issuance then has the same joint wrong-issuance bound at every stopping time in scope. In a discrete law $p_{i,t}=P_i(h)/M(h)$ on a supported prefix, so this reduces to the likelihood-ratio algorithm originally intended.

This extension is a mathematical coverage result. Computability of the density, calibration of continuum observations and a finite stopping guarantee require further conditions. T23.b is still the distinct independent reset categorical histogram procedure. [Original proof](../THEOREMS/T23/PROOF.md) · [Other scope fixes](SCOPE-CLARIFICATIONS.md)
