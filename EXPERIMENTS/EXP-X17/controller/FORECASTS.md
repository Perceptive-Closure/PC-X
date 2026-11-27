# X17 pre-opening mathematical forecasts

These forecasts cover every admitted rational installation \((\theta,\beta,m,k,B,N)\) of the matched base service. This is a deterministic parameter-to-forecast registration. No installed holdout identities, sampled paths or empirical outcomes were opened to make it. The authorized world and phase contracts appear in the [interface](../INTERFACE.md) and [accepted generalized flagship](https://github.com/Perceptive-Closure/PC-X/blob/109eac055f466c609c0dcb9ba880827a0fde675f/THEORY-FLAGSHIP-GENERALIZATION/FINAL-GENERALIZED-FLAGSHIP.md).

## Input, policy and exact endpoints

The pure controller gets only the arm, delivered prelude \(v_1,\ldots,v_N\), detached authenticated route receipt, current literal and its actual response at declaration, and a separate private random generator. The registration fixes random draws in the respective arm as the indicated integer lotteries. At a paid result the declaration is positive exactly on zero. At a skip it is a private fair declaration. The chosen literal has the actual route suffix `:L` or `:R`. Probability checking in the forecast is distinct from native authentication, exact implementation of the source and the private draw.

Write \(p=(1+(-1)^m\theta(1-\theta))/2\) for the conditional stay probability. The parity of flips gives
\[
\Pr(a=1)=\frac{1-(-1)^m(2p-1)^N}{2}=\bar a,\qquad
\rho=\theta/4+\bar a/16+\beta .
\]
The registered arm overlooks prelude contents in choosing quality and ignores them in the positive decision. Its randomization and paid response law are independent of the prelude conditional on the installed world. The issued proposal distribution is therefore the same as the carried proposal distribution in the formula, with \(a=m\oplus v_N\) committed before the protected draw.

| Arm | Quality lottery | \(q=\Pr(I)\) | Expected paid probe cost | Hard supported probe cost |
| --- | --- | --- | --- | --- |
| `pcx` | Low \(2/3\), high \(1/3\) | \(5/6-2\theta/3\) | \(7/12\) | \(1\) |
| `high_skip` | High \(2/3\), fair skip \(1/3\) | \(5/6-2\theta/3\) | \(2/3\) | \(1\) |
| `low_only` | Always low | \(3/4-\theta/2\) | \(3/8\) | \(3/8\) |
| `always_high` | Always high | \(1-\theta\) | \(1\) | \(1\) |
| `no_paid` | Always skip and declare fairly | \(1/2\) | \(0\) | \(0\) |

Let \(Y=1\) on the lower accepted band. With safe intake, every violation counted by these exact forecasts occurs on an issued attempt. Therefore
\[
\begin{array}{rl}
I&=q,\\
V=VI&=q\rho,\\
\operatorname{wrong}&=Y(1-q)+(1-Y)q,\\
G&=1/2+Yq(1-\rho)/2,\\
Z&=q(\rho-3/8).
\end{array}
\]
The equalities concern expectations of the named per-attempt indicators, earnings and signed endpoint. Expected cost follows the table. \(\Pr(V\mid I)=\rho\) when \(q>0\). This risk includes every actual activated attempt including an erroneous positive on a negative world. Violation and utility labels come from actual source predicates and durable work in the validation. The formulas have no claim when those mechanisms fail.

In every good world \(\beta\in[0,1/32]\), a reached finalizer has risk between \(1/32\) and \(5/16\). The upper bound is \(5/32\) on true positives. The primary \(q\) intervals are \([2/3,3/4]\) on positives and \([1/4,1/3]\) on negatives. Thus primary wrong is at most \(1/3\), all-world exposure at least \(1/4\), positive exposure at least \(2/3\), and positive \(G\ge25/32\). Real intake gives at least \(1/2\) everywhere. `always_high` has wrong at most \(1/4\), positive exposure at least \(3/4\), and positive \(G\ge209/256\), with all-world exposure at least \(1/8\). All arms have the same conditional finalizer risk at a fixed matched world and genuine useful finalization obeys the same artifact predicate.

Pair actual and nominal with the same fixed world and all common draws through the committed finalizer proposal. At the issued cut use the same uniform draw. The difference in \(VI\) is exactly \(\beta q\), and true decoded complete-law TV is bounded by \(\beta q\le1/32\) on the declared matched fields. Nominal \(G\) exceeds actual \(G\) by \(Y\beta q/2\) in this particular scoring model. The ordinary intrinsic protocol carries risk \(\theta\) and is a different source.

## Use after authenticated opening

Call `controller.forecast.forecast(theta, beta, m, N, arm)` with the actual registered values and exact string, integer or fraction inputs. Use \(\beta=0\) for the matched nominal finalizer at the same installation facts. No route argument is required in these numerical formulas because the two routes have the same checked laws, with different actual callable literals. The return keys `I,V,VI,wrong,G,cost,Z` are exact `Fraction` units. The supplied CLI outputs exact rational strings. This algorithm applies without retraining, selecting cells or refitting after opening. [Pure policy](policy.py) · [Exact forecast executable](forecast.py) · [Controls](CONTROL-FORECASTS.md)
