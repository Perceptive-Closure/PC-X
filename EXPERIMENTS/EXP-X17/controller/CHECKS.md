# Reproduce the X17 controller evidence

From the repository root, use Python 3.13 or compatible and Lean 4.21 with bundled Std. The code requires the Python standard library only.

~~~powershell
python -B EXPERIMENTS/EXP-X17/tests/controller_exact.py
lean EXPERIMENTS/EXP-X17/formal-checks/controller_price.lean
python -B EXPERIMENTS/EXP-X17/controller/forecast.py 33/256 3/512 1 7 pcx
python -B -c 'import sys; sys.path.insert(0,"EXPERIMENTS/EXP-X17"); from controller.benchmark import main; main()'
~~~

The five exact tests verify policy entropy and route choices, algebraic forecasts against independently enumerated true outcomes, count/lift preservation on nonconstant policies, mesh certificates and changed-information examples. The Lean certificate checks the scaled base, low/skip, tightened and extended-menu inequalities. No external solver tolerance or native stochastic trials are involved.

The benchmark builds actual graph nodes/edges. Its small complete-history reference enumerates terminal public bit records and both actual routes, then evaluates the same rational finite grid certification on those records. Runtime and peak traced Python allocations are measured in separate calls so tracing does not inflate the timed run. Recorded times vary by host and load; exact sizes, coefficient bit lengths and optimization values are replayable. On large \(N\), the explicit timing is null. This is neither native source performance nor a benchmark of the independent role's separately written general solver. [Recorded measurement artifact](../comparators/count-flow-measurements.json)


In the recorded run at \(N=6\), exact grid checking took 269.1 ms counted and 1,191.2 ms explicit. At \(N=1\) the corresponding times were 37.7 and 40.1 ms, and the actual count graph used more peak traced bytes to compile than the explicit word list. At \(N=256\) the measured count graph had 33,153 nodes, and its exact per-history factor required up to 4,353 bits. No explicit \(N=256\) job was run. The JSON records unrounded durations, allocation measurements, grid extrema and coefficient certificates.
