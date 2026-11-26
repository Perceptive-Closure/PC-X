# M02 · Clarifications to the seals

## Cost representation of a checked whole-occurrence mask

In the fixed intervention claim of [M02.1](STATEMENTS.md#m021--exact-staged-audit-over-correlated-source-facts), the mask is a Boolean interface input. The expression DAG has extended-nonnegative-integer leaves. For each optional source occurrence \(e=(z,q)\), a fixed checked encoding maps keep bit \(u_e=1\) to cost \(0\) and \(u_e=0\) to cost \(+\infty\). Undeletable occurrences have constant zero. The command expression adds this encoded switch cost to the source price and the maximum continuation. For a disabled occurrence the expression is therefore \(+\infty\). After this input encoding the only internal cost operations are \(\min\), \(\max\) and addition, with \(+\infty\) absorbing for addition. An equivalent implementation uses an explicit two-branch Boolean-to-cost switch. Raw arithmetic on a \(0/1\) value does not implement this gate. The encoding adds one constant-size leaf per removable occurrence, so the stated size and complexity are unchanged.

## Scope of reductions

The adaptive compiler's parties observe their own query and response history. Realized menus and costs are equal for histories with the same checked public state. The masked occurrence universe may be all public commands or a specified subset with the remaining commands always kept. A reported support in the latter case is projected onto the removable occurrences.

In the routed claim the “cheaper” inspection implements a price **at most as high** as the corresponding archive price. Equality is allowed by the sealed inequality. The strict-gap family uses genuinely lower inspection prices.
