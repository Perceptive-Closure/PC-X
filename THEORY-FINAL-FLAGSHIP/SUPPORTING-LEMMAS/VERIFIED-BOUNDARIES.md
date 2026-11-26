# Additional checked failure boundaries

The following are direct consequences of the sealed proof models and the independent hostile counterexamples. They preserve the scopes of the principal statements.

## Finite-prefix continuity blocks even nonuniform stopping at a threshold

In the P3 diagnostic interface, let an admitted positive world \(w_0\) at the threshold have the same exact full report tuple as negative worlds \(w_n\). Assume the complete initial pre-verdict information is matched and there are no additional channels beyond the declared diagnostic laws. Suppose all diagnostic mean vectors converge to the one for \(w_0\). For any fixed finite step \(H\), couple the controller's seed and each drawn bit at a common record. The probability of any mismatch by \(H\) is at most \(H\max_j|m_j(w_n)-m_j(w_0)|\). Exact report fields and shared timing preserve the coupling. Therefore the event \(A_H\) of positive issuance by \(H\) has \(\Pr_{w_n}(A_H)\to\Pr_{w_0}(A_H)\).

Any uniform false positive issuance guarantee \(\Pr_{w_n}(I)\le\delta\) for all \(n\) implies \(\Pr_{w_0}(A_H)\le\delta\) for every \(H\). Since finite issuance is the increasing union over \(H\), \(\Pr_{w_0}(I)\le\delta\). A procedure which stops almost surely at \(w_0\) and charges wrong or abstaining decisions as failure would instead need \(\Pr_{w_0}(I)\ge1-\delta\). The requirements are incompatible for \(\delta<1/2\). The argument does not assume a uniform horizon. It is consistent with P3's sufficient separated joint margin because this opposite sequence violates that margin. Threshold equality of a protected control bound alone is not a failure of identification when admitted opposite laws are separated.

## An exact activation ROC and a selective risk tradeoff

In an opposite U.4 pair with the same route and responder type, the pre-decision record, including a retained independent controller seed, has law likelihood ratio \(dP_-/dP_+\) equal to \(1\) on skip and to \(1/3\) or \(3\) on the possible dry outcomes. Earlier actions and nuisance data have the same conditional likelihood. Let \(q_+=P_+(I)\), \(q_-=P_-(I)\). Using the lower ratio on \(I\) and the upper ratio on its complement gives
\[
q_-\ \ge\ \max\bigl(q_+/3,\ 3q_+-2\bigr).
\]
This holds under every legal adaptive policy. As a bound over record tests without additional cost or work constraints it is attained. Pay once and accept a randomized portion of the dry zero for \(q_+\le3/4\). For \(q_+\ge3/4\) accept all dry zeros and a randomized portion of dry ones. The two ends have respective ratios \(1/3\) and \(3\). Some points of this curve violate a tighter joint physical requirement. Exactness here is a statement about the observable experiment.

The base U.4 negative world has unconditional live-event risk \(3q_-/4\ge q_+/4\). If a proposed negative-world selective requirement is
\[
 P_-(V\cap I)\le (2/5)q_-+\xi,
\]
then \(\xi\ge (7/20)\max(q_+/3,3q_+-2)\ge7q_+/60\). Thus even approximate conditional guarantees have quantitative costs in useful coverage. The base result's impossibility for exact uniform selective risk is the zero-slack specialization. This bound does not replace the stagewise actual event check.

[Scope reconciliations](../VERIFICATION/SCOPE-ADDENDUM.md) · [Original U proof](../T30-U/PROOFS.md) · [Original P proof](../T30-P/PROOFS.md)
