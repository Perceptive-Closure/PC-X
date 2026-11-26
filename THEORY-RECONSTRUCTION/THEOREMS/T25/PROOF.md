
# T25 · Exact monitor-table recovery

## Scope and data validation

For one context write $\mu_z=P(Z=z)$ and require $\mu_z\ge0$, with sum one. For each cell, trusted positive and negative labelled masses $p_z,n_z$ are nonnegative and $p_z+n_z\le \mu_z$. Incompatible records give an empty model. The residual mass $r_z=\mu_z-p_z-n_z$ is assigned hidden truth by arbitrary splitting within the cell. The monitor remains the fixed function $M(Z)$. The encoder preserves known trusted labels and all visible masses. This is exact partial identification with no further hidden-label restrictions.

## T25.a · Identified set and attaining witnesses

Put arbitrary mass $x_z\in[0,r_z]$ of the residual block on $V=1$ and $r_z-x_z$ on $V=0$. Every such split is realized by at most two latent subatoms of that residual block, keeping its entire visible transcript fixed. No other joint law is possible under the declared data because in each cell all new positive mass must come from its residual block.

For either alarm value $m_0$, the sum of positive masses in its cells ranges from $l_{m_0}=\sum_{z:M(z)=m_0}p_z$ to $u_{m_0}=\sum_{z:M(z)=m_0}(p_z+r_z)$. Every intermediate value is attainable. Starting with all $x_z=0$, allocate the desired increment successively up to each cell's residual mass until the increment is exhausted. The two alarm groups contain disjoint cells, so the complete pair range is the Cartesian rectangle, including all corners. Endpoints of the total risk are attained by setting both coordinates to their lower or upper endpoints. The missed event is the second coordinate. With no audited labels, that coordinate can be anything from zero to all nonalarm mass. Both extremal completions give exactly the same distribution of $Z$.

## T25.b · Sharp restrictions from additional trusted guarantees

Let $t=P(V=1,M=1)$ and $m=P(V=1,M=0)$. False positive mass is $a_1-t$. A validated floor $f$ therefore clips the upper endpoint for $t$ to $u=\min(u_1,a_1-f)$. The cap on the fraction of violations missed is the inequality $m\le\beta(t+m)$ when $P(V)>0$. It also holds at $(t,m)=(0,0)$. That boundary supplies no value for the conditional probability. Rearrangement gives $m\le kt$ with $k=\beta/(1-\beta)$.

A candidate's only additional compatibility restrictions are these inequalities. The rectangle construction realizes every point of the intersection. If $u<l_1$ or $l_0>ku$ the intersection is empty. Otherwise $(u,l_0)$ is feasible. When a trusted miss cap $\eta$ is supplied, replace $u_0$ by $\min(u_0,\eta)$ and also require $u_0\ge l_0$. The miss maximum is attained at $(u,\min(u_0,ku))$ and its minimum at $(u,l_0)$. At fixed $t$ the largest risk is $t+\min(u_0,kt)$, nondecreasing in $t$. This proves the asserted upper risk. For the minimum, lowering $m$ toward $l_0$ can only relax the cap. With $m=l_0$, the least compatible $t$ is $\max(l_1,l_0/k)$ for $k>0$. With $k=0$, consistency forces $m=0$, so the minimum is $l_1$. Subsidiary cases $f=0$ or $\eta\ge u_0$ just omit the corresponding extra cut. A point-mass violating label has a constructive two-subatom witness in each residual split.

The charter's simpler bounds follow directly from $P(V)=t+m$, $t\le a_1$, and either $m\le\eta$ or $(1-\beta)P(V)\le t$. Clip to 1. A validated floor on false positives can improve either bound by reducing the available true-positive mass. The exact extrema here can improve both, since they use all audited masses at once.

For finitely many contexts, event risks do not need an independence premise to justify $\sup_d r_d\le \max_d U_d$. Each feasible value also has worst-context risk at least $\max_d L_d$. Under the stated joint realizability premise we can take each context's lower endpoint together and can attain the upper endpoint in a maximizing context, giving sharp extrema. Correlated context assignments require a joint completion check for sharpness.

## Certificate and operational meaning

A certificate lists the visible masses, the exact audited submasses and their provenance, any validated caps, and the arithmetic extrema with attaining splits. Sweeping the cells and extrema requires a linear number of rational operations in the supplied table. Query acquisition cost and statistical confidence in estimated masses are separate problems. A gate requiring risk at most its threshold passes when the upper endpoint is at most the threshold, fails when the lower endpoint is strictly greater, and otherwise remains unresolved. An empty set is inconsistent. Equal alarm laws and readback labels of the wrong intervention do not certify this input table.
