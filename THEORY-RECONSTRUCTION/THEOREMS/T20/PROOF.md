# T20 · Uncovered conditional mass and sharp worst risk

For each deployment d the law of total probability gives
$
r_d = \sum_{x\in S}w_d(x)p_x+\sum_{x\notin S}w_d(x)p_x,
$
where p_x is the actual contextual violation risk. The conditional definition can be restricted to positive weight cells. Since weights are nonnegative, substituting the lower covered endpoints and zero uncovered values gives a lower bound. The upper follows by substituting the upper covered endpoints and one on the uncovered set. This holds even when the compatible contextual risk vector is constrained across cells. A known upper bound on missing mass can replace exact mass in a conservative upper bound if the remaining covered weights and their bounds are properly justified. An unknown alternative weighting scheme cannot be silently inserted.

Suppose the vectors consisting jointly of all lower and of all upper endpoints are admissible. Their mixed risks simultaneously attain the corresponding endpoints for every d. Taking suprema over d, including a supremum that may be unattained in d, proves sharpness of both worst-risk bounds across compatible completions. Without joint feasibility, separately attainable infima may be too low for the worst risk. For example take two contexts, both point masses allowed as deployments. Compatible vectors are (0,1) and (1,0). Both coordinate infima are zero but each completion's worst risk is one. The same observation applies when comparing an outer interval to the exact image of the threshold.

To prove the uncovered obstruction, choose two admissible completions with the same covered kernels, instrument and evaluation rules, and no allowed audit that ever instantiates the uncovered region. Let one assign no violations there and the other assign violations surely, using the same action interface and target rule. T15 gives equal full evaluation laws. Their context-mixture risks differ by exactly the missing mass, and if an allowed deployment places its entire mass there then the second worst risk is one. Any guard on unseen outcomes stronger than this must arise from further source, support or validated transport restrictions.
