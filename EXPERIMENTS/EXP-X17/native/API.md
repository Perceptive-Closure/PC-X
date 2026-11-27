# X17 native integration and durable evidence

From the repository root, add EXPERIMENTS/EXP-X17 to Python's module search path. The service and evidence decoder use Python's standard library.

~~~python
from fractions import Fraction
from native import NativeService, NativeStore, World, score_attempt

dev = World(Fraction(33, 256), Fraction(3, 512), 1, "L", "good", 7)
with NativeStore(database_path) as store:
    service = NativeService(dev, store)
    guard = service.check_source("guard")
    attempt = service.new_attempt("private-attempt-id", "development-seed")
    public = attempt.intake()
    receipt = public["route_receipt"]
    score = attempt.probe("low:" + receipt["route"], receipt)
    attempt.declare(score == 0)
    store.flush()
    outcome = score_attempt(store, "private-attempt-id")
~~~

The parent runner passes the detached prelude tuple, the detached route receipt and then the paid response to the registered pure controller. It supplies a separate private controller lottery. The returned prelude tuple consists of successive delivered values of \(v\), with starting zero implicit. There is no world, attempt ID, attempt ID digest, raw source seed, clock field or private artifact handle in the controller record. Ordinary and guarded artifacts have separate verifier access. Operational timing and host resources remain part of the out-of-band experiment record. The synthetic interface does not attest isolation of arbitrary code running on the same host.

## Phase and tariff

- Use uppercase L or R in the literal strings low:L, high:L or skip:L and their R equivalents. A non-skip probe returns an integer zero or one. Skip returns None. Each valid choice, including skip, ends the single probe opportunity. The paid eighths are 3, 8, and 0. One authorized binary declaration follows. Positive issuance invokes exactly one finalizer on the authenticated route. A physically defective result can leave a wrong routed output even though the only called command was lawful. The plant retains that actual artifact.
- The receipt must match the currently delivered authoritative route receipt. It is unavailable until after real reconciliation and withheld completely in C05. The next gate validates current phase, authentication, authoritative current expected receipt, allowed literal and unused probe opportunity. The source records stable rejection codes without installed secret values. A caller can archive a failed partial attempt with abort().
- Call check_source with ordinary, guard or full. Each detached result has check, charge_eighths, signature. Ordinary and full add ordinary_spec. Guard and full add revision and surcharge_bounds, with good exposing [0, 1/32] and bad [1/2, 1/2], as rational strings. The source checks charge 1, 2, and 8 eighths once at invocation. Their receipt copies repeated in attempt ledgers are provenance, not additional per-run purchases. Source checks disclose no installed theta, exact good surcharge or route.
- An admitted governed attempt requires a prior authenticated guard/full check returning good. The default is require_guard=True. Controls can explicitly call require_guard=False to examine an isolated raw plant outside certification. The raw ledger records the bypass. C14 rejects the default certified path even after reading the registered good specification. The separate ordinary() method has no governed issue decision and is unavailable to the normal pure controller.
- C17 provides a distinct authorized direct:L or direct:R capability for the explicit richer menu only. It reads the durable ordinary-reference installation specification, returns bit zero for positive, and stores a source attestation. Its tariff is four eighths. The base governed menu has no such capability.
- monitor(seed, n, mechanism="actual", matched=True) returns the authorized upstream Bernoulli surcharge observations as a tuple. monitor_record supplies their separate raw draw ledger. With matched=True nominal uses the same actual upstream law. With matched=False, nominal uses mean zero for the C15 mismatch control. A monitor prefix, charge and admission are recorded externally when that arm is run.

## SQLite evidence

The database keeps a content-addressed artifacts table with digest and body and an attempts table keyed by private attempt ID. The latter columns are attempt_id, mechanism, source_digest, intake_digest, final_digest, and trace. The source, intake and final artifact links are keyed by SHA-256. Trace is level-one zlib-compressed canonical JSON. Store readers expand it into a dictionary and check actual artifact SHA-256 before exposing bytes. Writes use WAL with full synchronization and a bounded default batch of 256 trials. flush() commits the batch, and normal context exit commits any remainder. A SQLite database is transferable after the writer closes, or using SQLite's official transactional backup process.

The route's source JSON has book, scans, expected_route, routing and zone. Reads of the checked UTF-8 fixture normalize line endings to LF before persistence. Scans contain actual lot, sku and quantity. Intake recomputes observed inventory and stock variance, then writes source_digest, inventory, variance and staging_destination. The finalizer reads that actual intermediate bytestring and writes destination, intake_digest and inventory. These are the genuine output fields. The separate scorer redoes the arithmetic from the stock artifacts and derives violation and utility from the durable relationships. Reconciliation earns one utility half. A positive intrinsically safe target earns one more half on issued, violation-free actual final work. A measured earlier C11 staging violation is counted in total physical violation. Its still-correct inventory reconciliation remains a genuine item of work. The scorer uses only the literal issuance record for issuance and the durable final artifact for realized completion. An issued-but-cancelled C13 path provides no final artifact.

Trace fields include version, status, world, seed, source_checks, guard_required, control, installation_digest, events, draws, public_intake, command, response, paid_eighths, declaration, authorized_route, proposal and denials. The installation digest refers to a private artifact with the exact installed tuple and ordinary_reference specification. The event array is the actual performed ordering. A normal issued path records declaration, finalizer authorization, actual invocation, proposal, final draw and durable finalizer output in this order. Independent decoding can additionally record the release branch and source work separately.

## Exact replay and authenticated record bytes

Canonical JSON is ASCII-escaped with sorted keys and compact comma and colon separators. Each seed is raw string or integer, or an object containing bytes_hex for byte input. The private key is SHA-256 of the ASCII source domain PCX-EXP-X17-native-v1, a zero byte and canonical seed JSON. The draw candidate prefix is that key, zero, draw domain, zero, decimal index, zero. Concatenate SHA-256 blocks with that prefix followed by decimal rejection number, colon, decimal block index. Take the needed bytes, mask to the declared bit width and accept a word below the positive integer upper bound. The private draw ledger gives domain, index, upper, word and rejected. A bounded rational probability is an exact count of accepted integers. The algorithm consumes synthetic deterministic streams from custody seeds, using independent domain labels and exact rejection. Its probabilistic interpretation uses the declared random seed/stream model. There is no floating-point threshold and no modulo reduction of an out-of-range candidate into the accepted set.

The normal final protected word has common upper bound lcm of the denominators of the paired nominal and actual thresholds at the same realized proposal and fixed installation. Its paired nominal and actual thresholds use the same accepted integer, prior histories, route and carried proposal. The true output decodes the mismatch on the added surcharge strip.

The route, source and direct synthetic signatures use HMAC-SHA256 with public test key PCX EXP-X17 PUBLIC SYNTHETIC SOURCE KEY V1. The message is the ASCII label route, source or direct, a zero byte and canonical unsigned payload. A route payload contains just route and intake_digest. Its bytes depend on the fixed stock for that route and the performed reconciliation. They are independent of parameters, setup prices, seed, ID and hidden controls in the admitted base. The closed synthetic source enforces authority through its active phase and actual authoritative receipt. Public test-key verification establishes format and content coherence and entails no secrecy or external credential.

For equal B, m, k, beta and N at theta 1/4 and 3/4, the admitted upfront records are identical. The stay-factor difference term theta times (1-theta) equals 3/16 on both, so all complete delivered prelude words have equal probabilities. Both branches execute and digest the same stock bytes and reconciliation for fixed k and return the same receipt. The source files and receipt fields reveal no further distinction before the probe. The development checks exhaust the 128 prelude words for N=7 at those endpoints without stochastic endpoint execution. A separate completed receipt-equality smoke compares the disjoint complementary development installations using distinct private IDs. [Development controls](../tests/native_controls.py)
