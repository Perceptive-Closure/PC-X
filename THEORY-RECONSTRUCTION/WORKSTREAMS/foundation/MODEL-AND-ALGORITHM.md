# Typed PC model and exact finite policy evaluation

D-35 pp. 2–5 and p. 11 provide the complete contract. PC-X charter pp. 2–7 separates closure from identification across complete contracts. [Frozen statements](STATEMENTS.md)

| Field | Type and role |
| --- | --- |
| $X,U,S,s_0$ | Finite worlds, normalized-history carrier, finite checkpoints, distinguished entry. |
| $\sim\ \subseteq X\times U$ | Source compatibility of worlds and normalized histories. |
| $H:S\to U$ | Representative of the admitted-history certificate cell. |
| $P:S\to\mathrm{Eq}(U)$ | Extensional certificate partitions. |
| $\Lambda:S\to\mathcal A$ | Extensional authority operators on the declared interface. |
| $\omega:S\to O$ | The controller's checkpoint observation. |
| $Q(s),N(s,q)$ | Enabled source actions and their nonempty positive-support successor sets. |
| $y(s,q,u)$ | Controller-visible outcome on every enabled supported edge. |
| $c(q),a(x)$ | Finite nonnegative costs of source atoms and sealed target classes. |
| $\mathrm{Atom}$ | Declared source partition into actions and checkpoint locators. |

At each reachable $s$, $C(s)=\{x:\exists u\in[H(s)]_{P(s)}\ (x\sim u)\}$ is nonempty. Closure is $|a[C(s)]|=1$. The representative only names the cell. Another representative in that cell may be the compatible witness. Requiring direct compatibility of the chosen representative with a world changes the type ledger and can rule out T02's pure-R witness.

Ordinary source preconditions and the authority operator determine $Q(s)$. A change specific to authority-admissibility with all other inputs fixed is an extensional authority change. Ordinary eligibility may vary while authority is constant. Renaming representation values preserves $P$ when the same pairs remain equivalent. The certificate partition, admitted-history representative, raw runtime memory and controller observations have different mathematical roles.

The touch of an enabled source atom is the union of the changes in $(H,P,\Lambda)$, labeled $E,R,A$, over every positive-support successor. Equality may be computed from explicit finite extensional terms or supplied by a justified equality decision. A freeze removes the whole state/action location if its union intersects the mask. A source atom may survive at one checkpoint and be removed at another. The controller must respect every compatible checkpoint. Splitting or batching a source atom changes the interface relative to which the freeze is defined.

## Observable information and source evidence

The full visible history records the entry observation and appends the selected action, visible outcome and next observation. Its information set is the collection of all current physical states realizing that history. A deterministic observation-based policy chooses one action or stop at each observable history. A current-observation-only strategy is a restricted policy language. The T03 argument transports either language under its declared consistently indexed maps.

A finite proper policy stops with all physical leaves closed. Closed classes may differ among states with the same visible history. A separate task requiring the controller to name the unique target class needs an additional stopping condition that the information set's closed labels agree. D-35 Eq. (2) and the X01 different-class test use physical checkpoint closure. T03 preserves either stopping condition.

The represented world fiber $C(s)$ is specific to a checkpoint. The controller's information set is a set of possible checkpoints in one complete contract. The investigator's completion class $\mathcal C(\Omega)$ is a set of complete contracts satisfying source evidence. Any observed trace constrains the investigator's class only through a declared observation projection. The signature identified set is the image of $\mathcal C(\Omega)$ under the eight-coordinate value map, evaluated at each realization of the entry locator. A finite catalog supplies completeness relative to its declared represented domain and its no-omitted-completion premise. Empty compatible classes give inconsistent evidence.

## Exact recursion for proper closing

Fix a freeze. At a nonempty belief $B$, let $Q_F(B)$ intersect the surviving menus of its members. For each $q\in Q_F(B)$ let $B[q,v,o]$ be all its supported successors with outcome $v$ and next observation $o$, using all members of $B$. Only nonempty children enter evaluation. The stopping condition $Z(B)$ holds when all members close. Unfolding the visible trace proves the tree semantics: every possible physical extension enters its corresponding child and every state in a child realizes such an extension. Consequently every subtree must work for the full child belief.

The Boolean iteration starts with $W_0=\{B:Z(B)\}$. It adjoins beliefs with a common surviving action whose nonempty children are all in the preceding set. By induction $W_t$ consists exactly of beliefs with a legal proper tree of height at most $t$. At the finite least fixed point, any belief outside has, for every available action, a possible child outside. Following those choices through any proposed finite tree either reaches an illegal dead end or a nonempty belief containing an open physical leaf.

For costs, start at $V_0(B)=0$ on $Z$ and $+\infty$ elsewhere. Each height update keeps zero on $Z$ and otherwise takes
$
V_{t+1}(B)=\min_{q\in Q_F(B)}\left(c(q)+\max_{v,o:B[q,v,o]\ne\varnothing}V_t(B[q,v,o])\right).
$
The empty menu has value $+\infty$. For each finite height there are finitely many observation trees. The recurrence follows by taking a minimizing continuation at each child and evaluating the largest resulting branch cost. A proper randomized policy cannot improve worst positive support. Choosing one supported permitted action at each reached visible history and retaining its full supported outcome tree leaves a deterministic proper subtree with weakly lower worst cost.

If a proper tree repeats the same belief on a path, replace the earlier subtree with a copy of the later continuation. The common belief has the same menus and transition map. Every copied suffix was already supported at the later occurrence, and the accumulated intervening cost removed is nonnegative. Every branch in the replacement is therefore legal and closes with no increase of worst cost. Size strictly decreases, so repeating this splicing yields a tree with no repeated belief on a path. The number of reachable beliefs bounds required height. This yields an attained finite optimum whenever a proper closer exists. A separate attainment argument uses the finitely many cost sums below a witnessed bound, since each positively priced action appears at most that bound divided by the smallest positive price and zero prices add nothing.

The Bellman operator fixes zero on $Z$, is monotone, and its successive values descend from $V_0$. After the finite depth bound they stabilize at the greatest nonnegative extended-real fixed point: every fixed point starts bounded by $V_0$ and hence stays bounded by each iterate. A sole open zero-cost self-loop permits every numerical fixed point at that state but has proper value $+\infty$. Least numerical fixed point is an invalid substitute for proper closure.

For $m$ reachable beliefs and $\ell$ action-child incidences including menus, graph storage is $O(m+\ell)$ aside from representation and bit sets. The direct height recursion takes $O(m(m+\ell))$ basic scan and arithmetic operations after graph construction. The number $m$ can be exponential in $|S|$. Bit complexity additionally needs an exact cost encoding. Nonfinite proper value follows from an exhaustive obstruction in the finite graph, while a timeout remains computationally unresolved. The knowledge-based construction is established theory. This is its finite min–max cost application to canonical whole-atom freezes. [Chatterjee, Doyen, Henzinger and Raskin](https://arxiv.org/abs/0706.2619)

## Signature and failure interpretations

The signature order is $(\varnothing,E,R,A,ER,EA,RA,ERA)$. Larger freezes weakly increase costs. With finite ordinary value, an R penalty of zero, finite positive, or infinite means the corresponding zero, finite or structural dependence. An infinite ordinary value makes that difference undefined. Structural impossibility concerns the declared interface and compatible model. [T03 proof](../../THEOREMS/T03/PROOF.md) · [Evidence](EVIDENCE.md)
