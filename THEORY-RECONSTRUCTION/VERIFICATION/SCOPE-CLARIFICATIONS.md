# Scope clarifications raised during review

The neutral statement seals and the original mathematical record remain available at their exact Git revisions. The statements below remove ambiguities surfaced by independent and hostile analysis. Review adjudicates the corrected scope. These boundaries apply to the accepted statements if their proofs pass all gates.

## T03.2 · One observation-consistent action map

The map at each public observation is injective on the union of action identities relevant there. Matching each physical state's enabled menu by a restriction of a common many-to-one function is insufficient. Two aliased states can have disjoint one-action menus on the left and a shared action on the right, while such a function matches both local menus. The known-observation bijection in the surviving argument is interpreted on the declared action interface. The conclusion is proved by whole-belief coverage, rather than arbitrary pairing of successors or per-state policy choice. A scoped boundary replay has costs infinity and 1. [First independent comparison](initial/COMPARISON.md)

## T12 · Support minimization has a budget coordinate

Choose minimal policy supports within a fixed residual budget. A smaller support at a higher cost can fail the actual bound and must not prune a larger feasible support at a lower cost. Equivalently retain joint cost–support dominance. The original exact proof and first comparison already use the fixed-budget hypothesis. The boundary replay contains supports at costs 5 and 9 and an overall optimum of 9. [T12 proof](../THEOREMS/T12/PROOF.md) · [Boundary replay](initial/boundary_replay.py)

## T18 · Surviving common mass and valid factors

All component loss allowances in the product expression lie in [0,1]. A vacuous unsupported row can use loss 1. A lower mass such as 1 less an unbounded formal allowance cannot be multiplied as a probability factor. If the audited conditional primitive laws coincide exactly over all relevant represented checkpoints and lawful histories, choose those exact normalized laws as the common lower factors. The resulting common mass is one. An arbitrary looser lower envelope can still give mass below one even when the actual row laws coincide. The exact conclusion uses the verified values and the trusted common event map. [T18 proof](../THEOREMS/T18/PROOF.md)

## T22 · Stop and condition on everything observed

Let $H_0$ be the initialization visible to the auditor. Under the stipulated stopping, integrability, absolute continuity and common protocol factor assumptions, the stopped chain rule reads
$$
D(P^\sigma\|Q^\sigma)
 = D(P(H_0)\|Q(H_0)) + \mathbb E_P\sum_{t\le\tau}D(P_t(\cdot\mid H_{t-1},q_t)\|Q_t(\cdot\mid H_{t-1},q_t)).
$$
The initialization can instead be an explicit first response in the sum. The reset allocation lower bound uses non-strict constraints, each count-weighted divergence sum at least the required threshold after accounting for initialization. The count-only reset allocation uses the equal-law, zero-information initialization or subtracts the initial information term before imposing the relevant constraint. Different deterministic initial labels can perfectly distinguish the hypotheses with zero probes, so omitting that contribution would be false. The changed-measure inequality itself is standard. [T22 proof](../THEOREMS/T22/PROOF.md)

## T23 · Two distinct confidence constructions

**T23.a** uses the reference mixture likelihood ratio to maintain a time-valid confidence set. On its simultaneous coverage event, nonempty target-homogeneous issuance is correct at every chosen stop. No fixed cap for decisiveness follows from this in general.

**T23.b** applies to a separate procedure with a fixed number of independent draws per resettable categorical query. Its candidate set is built from the uniform distance of each registered cell probability to the corresponding empirical proportion. If opposite targets differ by at least $\Delta$ in some registered probability and $n>2\log(2K/\delta)/\Delta^2$, the simultaneous Hoeffding radius is less than $\Delta/2$. The truth survives on the coverage event and no opposite-target pair can also survive. This assertion is about the histogram confidence procedure under those hypotheses.

The stronger reading that the *same mixture rule* becomes decisive by the histogram cap is false. Take one binary query, opposite targets, $P_0$ deterministic 0 and $P_1$ fair, $\delta=1/10$ and mixture weight $w_0=2^{-33}$. At $t\le32$, under $P_0$ the transcript is always $0^t$. Its mixture ratio against $P_1$ is $1+w_0(2^t-1)<3/2$ and the ratio against $P_0$ is at most 1. Both candidates survive the threshold 10. Yet $K=2,\Delta=1/2,n=32$ meet the separate histogram bound. [T23 proof with both procedures](../THEOREMS/T23/PROOF.md)

## T24 · Joint observed law in the impossibility direction

Choose compatible admissible Bernoulli responders whose **entire** initial observation and **joint conditional law** of each response record (score plus any retained metadata) agree under both completions along their reachable histories. Independently common auxiliary marginals do not suffice: if the fair score is $Z$ and a separately fair field is $H$, set $H=Z$ in one completion and $H=1-Z$ in the other. One joint draw distinguishes both even though the component marginals and score interval match. The obstruction applies automatically when only the score and the auditor's independent coins are observed and the declared stationary common responders are allowed. The sufficient martingale construction continues to need only the stated uniform score-mean bounds as it may disregard other fields. [T24 proof](../THEOREMS/T24/PROOF.md)

## T30.S · Conditional source evidence, implemented choices and audit scope

The independent stage correspondence verifies a conditional rule over **all** compatible installed modes. Given a mode, it certifies the enabledness, tariff, extensional resource-effect and actual job row for each relevant checkpoint. Checking this conditional rule is distinct from learning the installed bit. Any already public information such as the actual enabled menu restricts the initial evidence before prices are computed. For one stage with $a=w=B=1$, a free declaration of current fast availability resolves the deadline at zero external cost instead of the unit-priced readback. The acquisition separation applies to the named pure-read interface without that free revelation.

Each chosen canonical action must have a **common public callable lift** across every relevant hidden checkpoint and compatible completion permitted at its observation and action history. Actual public commands can themselves be the abstract identities, or the anchor supplies a public lift and proves legality for all appropriate physical states. Merely projecting enabled classes does not give this. A one-stage hidden left/right fixture has public commands L/R both mapping to fast, but only L is legal on the left and only R on the right. S is the common slow command. Both menus project to {fast,slow}, although the common fast policy cannot execute. With costs 1 and 2 and deadline 1, the projected verdict is false in the concrete system. Complete interface anchors include this visibility and lift requirement.

All base and slow-increment service tariffs are positive integers in the stated capped-grid algorithm. For exact rational input the same arithmetic can use a common denominator and a scaled numerical budget, which need not be polynomial in the input bit length.

A full-menu collision concerns only fixed pure external readbacks, including their adaptive selection. Taking useful actions to reveal a signal, using a changing query menu, or feeding the hidden installation identity into a policy is a different acquisition/control model. Under the repaired assumption the proof's stage schedule invokes the common lift and the lower bound uses completeness of the projected exposed menu. [T30 proof](../THEOREMS/T30/PROOF.md)

The split-command counterexample admits a single concrete entry. A first mandatory stage is lawfully finished at tariff 1 and has positive support on both aliased stage-2 states. If the deadline is 2, canonical fast/fast costs 2, but the only common concrete stage-2 command is the slow one, yielding exact cost 3.
