# Definitions

## D-35 typed authorization contract

A complete authorization contract is
$$
C=(X,U_H,\sim,S,s_0,H,P_R,\Lambda,\omega,Q,\mathrm{Succ}^+,Y,c,A_\Pi,\mathrm{Atom}).
$$
$X$ is a finite latent world set, $U_H$ is a set of normalized history representatives, and $\sim\subseteq X\times U_H$ is compatibility. The finite checkpoint set is $S$ with entry $s_0$. Maps $H:S\to U_H$, $P_R:S\to\operatorname{Eq}(U_H)$, $\Lambda:S\to\mathcal A$ and $\omega:S\to\mathcal O$ give admission, the certificate equality relation, extensional authority and controller observation. The authorization target $A_\Pi:X\to\mathcal D$ is sealed. An $H(s)$ representative may name a cell even when it has no directly compatible world.

The source exposes a declared set of atomic action identities. $Q(s)$ is exactly the source-available candidate set filtered by ordinary preconditions and extensional authority. A positive-support edge of $q\in Q(s)$ reaches some $s'\in\mathrm{Succ}^+(s,q)$, a nonempty set. Its outcome class $Y(s,q,s')$ is controller-visible. Cost $c(q)$ is finite and nonnegative. The atomic boundary records source event groups and their pre/post checkpoint locators. Grouping or splitting those events may change the domain.

Let
$$
C_R(s)=\{x\in X:\exists h\in[H(s)]_{P_R(s)}\ x\sim h\}.
$$
Well-formedness requires $C_R(s)\ne\varnothing$ on every reachable checkpoint. Closure is constancy of $A_\Pi$ on this set. A controller does not read $H$ or $P_R$ unless that access is in its observation interface. The resource mask $T_s(q)$ contains E, R, A respectively when some supported successor changes $H$, $P_R$, $\Lambda$ extensionally. Freeze $F$ deletes all whole occurrences $(s,q)$ with $T_s(q)\cap F\ne\varnothing$, leaving the other supported edges intact.

A visible history begins with the initial $\omega$ and interleaves actions, outcome labels and subsequent observations. Its nonempty belief is the set of compatible checkpoints or completion-tagged checkpoints. A proper policy is a finite observation-history tree. An action at a reached node must be legal throughout the belief. Each reached stopping node has only closed physical checkpoints, or satisfies an explicitly separate common-label reporting rule. Use the maximum cost over positive-support paths. Write $\kappa^{\neg F}_{\Pi,C}$ for its minimum and $+\infty$ when no proper closing policy exists. The eight-coordinate signature $K_{\Pi,C}$ indexes all subsets of $\{E,R,A\}$ in the original order. The R penalty is defined only at finite unrestricted cost. [Parent derivation and proof-audit details](VERIFICATION/PARENT-FOUNDATION-DERIVATION.md)

## Evidence, completion, and legal audits

A declared class $\mathfrak C$ specifies well-formed complete contracts. Governing source evidence $\Omega$ is a predicate on $\mathfrak C$ plus fixed source locator anchors. The realizations of common task/action locators may depend on a completion. A field that has no common source locator cannot be substituted by a guessed coordinate. Let $C_\Omega=\{c:c\models\Omega\}$. For target $\Psi:\mathfrak C\to\mathcal Y$, take the exact image $\mathcal I_\Psi(\Omega)=\Psi[C_\Omega]$.

Inconsistency means $C_\Omega$ is empty. Singleton nonempty target image means point identification. Several possible target values give set/decision ambiguity, possibly with much else known about the contract. Audit inaccessibility is an impossibility for a specified lawful observation menu. Computationally unresolved means a witness or a lower bound was not established. An accurate algorithm for a single supplied completion does not by itself identify the source-relative image.

A deterministic query $q$ returns a typed answer $\gamma_q:C_\Omega\to V_q$. Query families can use different answer types. Its fixed price is the legitimate acquisition cost, distinct from run cost. A pure readback intersects the completion set with its answer fiber and leaves the target and other responses intact. A bundle jointly observes several facts only if the source permits that bundle. An answer is a lawful independent measurement or explicitly permitted fact about the source, rather than a target oracle by definition. The realized certificate uses the observed cell through the true completion. A uniform static certificate covers every answer cell. An adaptive tree selects a query from its authorized history, and its worst cost and realized costs are different objectives.

## Stochastic operational contracts

Extend the completion with physical/memory state, a controller and its admitted observations, authority and atomic actions, environment kernels and contexts, a separate evaluator, permitted adaptive experiments and stops, a monitor, and an independently justified event instrument. Each audit protocol $e$ induces a law $P_C^e$ on the entire evaluator-visible transcript. This includes randomized query choices, accepted history-dependent response kernels, stopping, and informative initialization when present. Past private state or seeds affecting response correlations belong in the physical model. The monitor's public output and the trusted scored event are distinct objects.

A declared deployment family $\mathcal D$ associates a process or contextual mixture with each $d$. Let $V=1$ denote a frozen actual violation, and $r(C,d)=\Pr_C(V=1\mid d)$. A worst contextual risk is $r(C)=\sup_{d\in\mathcal D}r(C,d)$ and the threshold target is $1\{r(C)\le\varepsilon\}$. Pair the actual reference and deployment contexts explicitly when using transport. A derived law on an unauthorized or disturbed probe is a different observable object even when its nominal labels look the same. [Typed deployment statements](WORKSTREAMS/deployment/STATEMENTS.md)

A timed safety-and-work target is distinct from risk alone. In a finite supported synthesis game, good plant progress or task completion is a designated observable or checkable goal, and safe supported execution is a separate invariant. A shared policy must satisfy both for all compatible completion-tagged initial states under the declared horizon/cost. Refusal can be safe and still fail the goal. A deployment policy success region comprises the completions on which the same policy succeeds. These regions can overlap. [Governance statements](WORKSTREAMS/governance/STATEMENTS.md)

## Original PC as an operational special case

Take the original physical checkpoints as the plant and expose exactly the original $Q$, $\omega$ and $Y$. Include the resource mask in action admission. Choose any coherent conditional laws giving strictly positive probability to every declared supported transition. In the stopping rule, count missing closure, illegal action and cost-budget failure as violation. For a fixed finite tree, zero failure probability under this support is equivalent to every supported branch satisfying the original proper closure and budget test. The minimum feasible budget recovers $\kappa^{\neg F}$ for each of the eight interventions, with no feasible budget giving $+\infty$. The image of the tuple over anchored source completions recovers $K_{\Pi,\Omega}$. This specialization keeps the original admitted fibers and resource types. It does not replace authorization closure by an untyped behavior criterion.
