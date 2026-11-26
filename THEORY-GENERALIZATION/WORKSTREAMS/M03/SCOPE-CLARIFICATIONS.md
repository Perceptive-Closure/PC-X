# M03 scope clarification · Reference rows

The reference row condition in [the neutral statement](STATEMENTS.md) uses a fixed finite coefficient matrix H_{dx} and fixed finite vector h_{dx} in each mode, run, and context after the relevant evidence is supplied. These are numerical input, not optimization variables or a nonlinear constraint description. The coefficients can differ by mode and by realized anchor outcome. Rational coefficients, costs and thresholds are needed for the stated exact rational computation.

On positive occupancy w the homogeneous row inequality is H_{dx}s_{dx}≤h_{dx}w. On w=0 the normalization forces s_{dx}=0 and both sides vanish. The polyhedrality, attainment and mode-wise interval claims use this explicit constraint class. A jointly uncertain coefficient matrix, or a nonlinear cross-row identity, calls for a distinct verified lift or an outer-bound reading. [Proof](PROOF.md)
