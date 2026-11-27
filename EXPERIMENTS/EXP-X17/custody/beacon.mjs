import { createHash } from 'node:crypto';
import { readFileSync, writeFileSync } from 'node:fs';
import { createRequire } from 'node:module';
import { resolve } from 'node:path';

const quicknet = {
    public_key: '83cf0f2896adee7eb8b5f01fcad3912212c437e0073e911fb90022d3e760183c8c4b450b6a0a6c3ac6a5776a2d1064510d1fec758c921cc22b0e17e63aaf4bcb5ed66304de9cf809bd274ca73bab4af5a6e9c76a4bc09e76eae8991ef5ece45a',
    period: 3,
    genesis_time: 1692803367,
    hash: '52db9ba70e0cc0f6eaf7803dd07447a1f5477735fd3f661792ba94600c84e971',
    groupHash: 'f477d5c89f21a17c863a7f937c6a6d15859414d2be09cd448d4279af331c5d3e',
    schemeID: 'bls-unchained-g1-rfc9380',
    metadata: {beaconID: 'quicknet'},
};
const relays = ['https://api.drand.sh', 'https://drand.cloudflare.com'];
const leadRounds = 180;
const selector = 'PCX-X17-draw-v1';
const read = path => JSON.parse(readFileSync(path, 'utf8'));
const write = (path, value) => writeFileSync(path, JSON.stringify(value, null, 2) + '\n', {flag:'wx'});
const digest = path => createHash('sha256').update(readFileSync(path)).digest('hex');
const epoch = round => (quicknet.genesis_time + (round - 1) * quicknet.period) * 1000;
const utc = () => new Date().toISOString();
const urlFor = (relay, suffix) => relay + '/' + quicknet.hash + suffix;
const timestamp = (value, relation, round) => {
    const parsed = Date.parse(value);
    return Number.isFinite(parsed) && relation(parsed, epoch(round));
};
const earlier = (left, right) => left < right;
const later = (left, right) => left >= right;

const [mode, deps, ...args] = process.argv.slice(2);
if (!deps) throw new Error('pinned dependency directory required');
const { fetchBeacon } = createRequire(resolve(deps, 'package.json'))('drand-client');

function checkChain(info) {
    for (const key of ['public_key', 'period', 'genesis_time', 'hash', 'groupHash', 'schemeID']) {
        if (info?.[key] !== quicknet[key]) throw new Error('incorrect quicknet chain field ' + key);
    }
    if (info.metadata?.beaconID !== quicknet.metadata.beaconID) throw new Error('incorrect beacon identity');
}

async function request(relay, suffix) {
    const url = urlFor(relay, suffix);
    const response = await fetch(url, {
        cache: 'no-store', redirect: 'error', signal: AbortSignal.timeout(15000),
    });
    const witness = {
        url, status: response.status, http_date: response.headers.get('date'), observed_utc: utc(),
    };
    if (!response.ok) {
        witness.reason = (await response.text()).trim();
        return {witness};
    }
    return {witness, body: await response.json()};
}

async function verifyRound(beacon, round) {
    if (!Number.isSafeInteger(round) || round < 1 || beacon?.round !== round ||
        !/^[a-f0-9]{64}$/.test(beacon.randomness) || !/^[a-f0-9]{96}$/.test(beacon.signature) ||
        createHash('sha256').update(Buffer.from(beacon.signature, 'hex')).digest('hex') !== beacon.randomness) {
        throw new Error('malformed Quicknet round or randomness');
    }
    await fetchBeacon({
        get: async () => beacon,
        chain: () => ({info: async () => quicknet}),
        options: {disableBeaconVerification: false},
    }, round);
}

function checkPending(receipts, round) {
    if (receipts?.length !== relays.length) throw new Error('missing exact-round relay receipts');
    for (const [i, receipt] of receipts.entries()) {
        const status = i === 0
            ? receipt.status === 425 && /^Requested future beacon\b/.test(receipt.reason ?? '')
            : receipt.status === 404;
        if (receipt.url !== urlFor(relays[i], '/public/' + round) || !status ||
            !timestamp(receipt.http_date, earlier, round) || !timestamp(receipt.observed_utc, earlier, round)) {
            throw new Error('fixed round unavailability failed verification');
        }
    }
}

async function checkPlan(plan) {
    checkChain(plan.chain);
    if (plan.schema !== 1 || plan.selector !== selector || plan.lead_rounds !== leadRounds ||
        !/^[0-9a-f]{40}$/.test(plan.source_commit) ||
        !/^[0-9a-f]{64}$/.test(plan.frozen_manifest_sha256) ||
        !/^[0-9a-f]{64}$/.test(plan.domain_sha256) ||
        !Number.isSafeInteger(plan.round) || plan.round < 1 ||
        plan.scheduled_utc !== new Date(epoch(plan.round)).toISOString() ||
        !timestamp(plan.registered_utc, earlier, plan.round) ||
        plan.reference_beacons?.length !== relays.length) {
        throw new Error('inconsistent draw plan');
    }
    const references = plan.reference_beacons.map(item => item.beacon.round);
    if (Math.max(...references) + leadRounds !== plan.round) throw new Error('unexpected round derivation');
    for (const [i, sample] of plan.reference_beacons.entries()) {
        if (sample.http.url !== urlFor(relays[i], '/public/latest') || sample.http.status !== 200 ||
            !timestamp(sample.http.http_date, earlier, plan.round) ||
            !timestamp(sample.http.observed_utc, earlier, plan.round)) {
            throw new Error('latest receipt mismatch');
        }
        await verifyRound(sample.beacon, sample.beacon.round);
    }
    checkPending(plan.still_unavailable_at_commitment, plan.round);
}

async function pending(round) {
    if (Date.now() >= epoch(round)) throw new Error('future-round observation window has closed');
    const results = await Promise.all(relays.map(relay => request(relay, '/public/' + round)));
    const receipts = results.map(result => result.witness);
    checkPending(receipts, round);
    return receipts;
}

function checkOpening(opening, plan) {
    if (opening.schema !== 1 || opening.fetched?.length !== relays.length ||
        !timestamp(opening.verified_utc, later, plan.round)) throw new Error('incomplete opening');
    for (const [i, witness] of opening.fetched.entries()) {
        if (witness.url !== urlFor(relays[i], '/public/' + plan.round) || witness.status !== 200 ||
            !timestamp(witness.http_date, later, plan.round) ||
            !timestamp(witness.observed_utc, later, plan.round)) {
            throw new Error('post-round relay receipt mismatch');
        }
    }
}

if (mode === 'verify-round') {
    const [archive, round] = args;
    const value = read(archive);
    await verifyRound(value.beacon ?? value, Number(round));
    console.log('Pinned Quicknet BLS verified for archived round ' + round);
} else if (mode === 'prepare') {
    const [source, manifest, domain, output] = args;
    if (!output || !/^[0-9a-f]{40}$/.test(source)) throw new Error('prepare: sourceCommit manifest domain output');
    const info = await Promise.all(relays.map(relay => request(relay, '/info')));
    for (const result of info) checkChain(result.body);
    const latest = await Promise.all(relays.map(relay => request(relay, '/public/latest')));
    for (const result of latest) {
        await verifyRound(result.body, result.body?.round);
        if (Math.abs(Date.now() - epoch(result.body.round)) > 30000) throw new Error('stale verified latest round');
    }
    const round = Math.max(...latest.map(result => result.body.round)) + leadRounds;
    const plan = {
        schema: 1, chain: quicknet, selector, lead_rounds: leadRounds, source_commit: source,
        frozen_manifest_sha256: digest(manifest), domain_sha256: digest(domain), round,
        scheduled_utc: new Date(epoch(round)).toISOString(), registered_utc: utc(),
        reference_beacons: latest.map(result => ({http: result.witness, beacon: result.body})),
        still_unavailable_at_commitment: await pending(round),
    };
    await checkPlan(plan);
    write(output, plan);
    console.log('Prospective plan written for round ' + round + ' at ' + plan.scheduled_utc);
} else if (mode === 'pending') {
    const [planPath, output] = args;
    const plan = read(planPath);
    await checkPlan(plan);
    write(output, {schema: 1, round: plan.round, receipts: await pending(plan.round)});
} else if (mode === 'open' || mode === 'verify') {
    const [planPath, pendingPath, openingPath] = args;
    const plan = read(planPath);
    const before = read(pendingPath);
    await checkPlan(plan);
    if (before.schema !== 1 || before.round !== plan.round) throw new Error('preopening receipt round differs');
    checkPending(before.receipts, plan.round);
    if (mode === 'open') {
        if (Date.now() < epoch(plan.round)) throw new Error('the committed round has not arrived');
        const values = await Promise.all(relays.map(relay => request(relay, '/public/' + plan.round)));
        for (const item of values) await verifyRound(item.body, plan.round);
        const beacon = values[0].body;
        if (values.some(item => item.body.signature !== beacon.signature || item.body.randomness !== beacon.randomness)) {
            throw new Error('relay beacons disagree');
        }
        const opening = {schema: 1, beacon, fetched: values.map(item => item.witness), verified_utc: utc()};
        checkOpening(opening, plan);
        write(openingPath, opening);
    } else {
        const opening = read(openingPath);
        checkOpening(opening, plan);
        await verifyRound(opening.beacon, plan.round);
    }
    console.log('Verified exact Quicknet round ' + plan.round);
} else {
    throw new Error('supported modes: verify-round, prepare, pending, open, verify');
}
