# Sealed M06 statements

## T29.J · Joint evidence, verdict and useful work

An instance is a finite set of hidden states tagged by an immutable completion \(\theta\), a nonempty initial belief, and a finite public meter \(p\). A tag has a fixed binary target \(f(\theta)\). Public command names designate actual callable commands. For each \((p,s,a)\), a finite exact row gives its authorization, ordinary enablement and all positive supported successors. An authorized enabled command has nonempty support. An edge outputs a public record \(y\) containing its observation, acquisition charge \(c_y\) and work charge \(w_y\). Both charges are nonnegative and branch-specific; all members of a single record group have the same charges. The public update \(p'=F(p,a,y)\) is deterministic. A hidden successor retains its completion tag. Any future availability, price, relevant safety or utility effect is captured by these rows and states. A declared resource freeze removes each source-atomic occurrence with a changing supported successor before beliefs are formed. A command can reveal evidence, perform work or change future availability.

Mark safe states/edges and useful terminal states directly in the instance. An issuing policy acts on its permitted public history and must be safe on all its supported paths. A negative verdict is lawful exactly when every surviving tag has \(f=0\). A positive verdict is lawful exactly when all surviving tags have \(f=1\) and every surviving state is a useful terminal. One budget \(b\) caps actual accumulated work charges on every supported branch. For fixed move limit \(h\), minimize the maximum supported accumulated acquisition charge among valid policies, allowing \(+\infty\) for nonexistence. Invalid initial states and empty evidence have separate unsafe/inconsistent dispositions.

Let \(B_{a,y}\) be the union of exactly the genuine successors for the recorded branch. A common candidate command is executable at every state in \(B\), every supported edge is safe, and each branch has \(w_y\le b\). The optimum is zero at a valid stop, infinite if exhausted without a valid stop, and otherwise
\[
  V_h(B,p,b)
  =\min_a\max_{y:B_{a,y}\ne\varnothing}
       \{c_y+V_{h-1}(B_{a,y},F(p,a,y),b-w_y)\}.
\]
The recurrence gives an attaining supported deterministic policy when finite and a finite decreasing-horizon refutation of every failing acquisition threshold. Randomized choice gives no improvement in this supported worst-path model. A fixed public meter and fixed budgets allow the hereditary monotonicity under shrinking the nonempty belief. The decision problem with both finite integer budgets \(B_0,C_0\) and no stated depth cap also has a finite reachability solution. In the time-homogeneous rules on \((B,p,b,c)\), every proper success has a witness of depth at most \(|P|(2^{|S|}-1)(B_0+1)(C_0+1)\), including cases with zero-cost loops. Proper success means every supported play ends at a valid stop. Intrinsic target constancy alone need not provide a common positive policy.

The exact finite correspondence requires rows implementing an observation-consistent public command mapping over the entire compatible belief and preserving options, support, costs, actual safety/work labels and completion tags. A checked forward inclusion with possibly extra abstract rows yields a sound robust policy when concretely implementable. An exact minimum in the physical protocol additionally needs preservation of all its admitted alternatives and both-way supported coverage.

## Limits under examination

Three positive completions can each pair share a useful command while the triple shares none. A hidden charge or memory affecting future availability requires an expanded public or hidden state respectively. Certifying a nonempty pure readout cell ready for external deployment is distinct from the present joint objective. Targets that change with interrogation, positive chance constraints and arbitrary continuous budget/time are separate.
