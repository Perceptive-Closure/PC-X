# X17 independent custody commands

The verifier pins the Quicknet hash, scheme, genesis and period. Install the archived X16 drand-client@1.4.2 and checked npm lock into a disposable directory containing the two package files with npm ci --ignore-scripts --no-audit --no-fund. Keep the dependency directory outside the study registration. The historical X16 code is the source for this adaptation. [X16 immutable precedent](https://github.com/Perceptive-Closure/PC-X/blob/a6bf9cefb59f63b8c9dea59daf7e588a82ba07eb/EXPERIMENTS/EXP-X16/custody/beacon.mjs)

Run from the X17 directory after each authorized gate. The first command checks both latest chain and beacon responses, uses 180 periods after the newest verified reference, and insists that both relays observe the target unavailable before its scheduled time. Only choose a target after the parent-authorized freeze. Check unavailability again after publishing forecasts and capturing both roles' immutable pre-opening readbacks. Authorize actual opening after confirming the registered schedule.

    node custody/beacon.mjs prepare DEPS SOURCE_SHA FROZEN_MANIFEST custody/roster-domain.json DRAW
    node custody/beacon.mjs pending DEPS DRAW PRERELEASE_PENDING
    node custody/beacon.mjs open DEPS DRAW PRERELEASE_PENDING VERIFIED_BEACON
    node custody/beacon.mjs verify DEPS DRAW PRERELEASE_PENDING VERIFIED_BEACON
    python custody/selector.py custody/roster-domain.json DRAW VERIFIED_BEACON OPENING

The selector consumes an authenticated beacon archive and emits its linked digest, exact round and a worlds list. Fields are id, rational strings theta and beta, integers m and N, route k and good revision B. The paired IDs s01 and s02 have theta 1/4 and 3/4, with common randomized route, mode, surcharge endpoint and depth. Extreme IDs s03 and s04 use 1/8 and 7/8, opposite nuisance endpoints and a disjoint depth choice. The four interior IDs choose uniformly within their labeled candidate lists via SHA-256 rejection draws. These are stratified, intentionally coupled roster rows. The fixed independent seed is separate from selection and released only after verified opening.

Use python custody/readback.py SPEC OUTPUT --before-draw DRAW for byte-specific GitHub receipts. The input contains an objects array. Each row names the expected exact commit, a label name, optional branch to verify an exact live ref, and files mapping paths relative to EXP-X17 to their expected SHA-256, or null to record the discovered hash. The command authenticates commit, tree, file blobs, GitHub response Date and request IDs and independently observed UTC. Readback during the designated window is evidence against retrospective sealing. It does not change the status of the parent publication gate.
