import { createHash } from 'node:crypto';
import { readFileSync, writeFileSync } from 'node:fs';
import { createRequire } from 'node:module';
import { resolve } from 'node:path';

const pins = {
    public_key: '83cf0f2896adee7eb8b5f01fcad3912212c437e0073e911fb90022d3e760183c8c4b450b6a0a6c3ac6a5776a2d1064510d1fec758c921cc22b0e17e63aaf4bcb5ed66304de9cf809bd274ca73bab4af5a6e9c76a4bc09e76eae8991ef5ece45a',
    period: 3,
    genesis_time: 1692803367,
    hash: '52db9ba70e0cc0f6eaf7803dd07447a1f5477735fd3f661792ba94600c84e971',
    groupHash: 'f477d5c89f21a17c863a7f937c6a6d15859414d2be09cd448d4279af331c5d3e',
    schemeID: 'bls-unchained-g1-rfc9380',
    metadata: {beaconID: 'quicknet'},
};
const relays = ['https://api.drand.sh', 'https://drand.cloudflare.com'];
const json = path => JSON.parse(readFileSync(path, 'utf8'));
const write = (path, value) => writeFileSync(path, JSON.stringify(value, null, 2) + '\n');
const digest = path => createHash('sha256').update(readFileSync(path)).digest('hex');
const roundEpoch = round => (pins.genesis_time + (round - 1) * pins.period) * 1000;
const iso = epoch => new Date(epoch).toISOString();

const [mode, deps, ...args] = process.argv.slice(2);
if (!deps) throw new Error('pinned dependency installation directory required');
const { fetchBeacon } = createRequire(resolve(deps, 'package.json'))('drand-client');

function checkChain(chain) {
    for (const key of ['public_key', 'period', 'genesis_time', 'hash', 'groupHash', 'schemeID']) {
        if (chain[key] !== pins[key]) throw new Error('unrecognized quicknet network field ' + key);
    }
    if (chain.metadata.beaconID !== pins.metadata.beaconID) throw new Error('beacon ID mismatch');
}

async function request(relay, suffix) {
    const uri = relay + '/' + pins.hash + suffix;
    const response = await fetch(uri, {cache:'no-store',signal:AbortSignal.timeout(15000)});
    const witness = {url:uri,status:response.status,
        http_date:response.headers.get('date'), observed_utc:new Date().toISOString()};
    if (!response.ok) {
        witness.reason = (await response.text()).trim();
        return {witness};
    }
    return {witness, value:await response.json()};
}

async function verifyRound(value, round) {
    if (value?.round !== round || !/^[0-9a-f]{64}$/.test(value.randomness) ||
        typeof value.signature !== 'string' ||
        createHash('sha256').update(Buffer.from(value.signature, 'hex')).digest('hex') !== value.randomness) {
        throw new Error('malformed exact randomness round');
    }
    const client = {
        get: async () => value,
        chain: () => ({info:async () => pins}),
        options: {disableBeaconVerification: false},
    };
    await fetchBeacon(client, round);
    return value;
}

function isPending(witness, round) {
    const suffix = '/' + pins.hash + '/public/' + round;
    if (witness.url === relays[0] + suffix) {
        return witness.status === 425 && /^Requested future beacon\b/.test(witness.reason ?? '');
    }
    return witness.url === relays[1] + suffix && witness.status === 404;
}

async function pending(draw) {
    checkDraw(draw);
    if (Date.now() >= roundEpoch(draw.round)) throw new Error('locked round time already arrived');
    const checks = await Promise.all(relays.map(relay => request(relay, '/public/' + draw.round)));
    for (const {witness} of checks) {
        if (!isPending(witness, draw.round) || !Number.isFinite(Date.parse(witness.http_date)) ||
            Date.parse(witness.http_date) >= roundEpoch(draw.round) ||
            Date.parse(witness.observed_utc) >= roundEpoch(draw.round)) {
            throw new Error('could not establish that the fixed round was still unavailable');
        }
    }
    return checks.map(x => x.witness);
}

function checkDraw(draw) {
    checkChain(draw.chain);
    if (!Number.isSafeInteger(draw.round) || draw.round < 1 ||
        draw.scheduled_utc !== iso(roundEpoch(draw.round))) throw new Error('malformed round plan');
}

if (mode === 'prepare') {
    const [catalogue, source, freezeManifest, out] = args;
    if (!out || !/^[a-f0-9]{40}$/.test(source)) throw new Error('prepare: catalogue sourceCommit freezeManifest output');
    const info = await Promise.all(relays.map(relay => request(relay, '/info')));
    for (const result of info) checkChain(result.value);
    const latest = await Promise.all(relays.map(relay => request(relay, '/public/latest')));
    for (const row of latest) await verifyRound(row.value, row.value.round);
    const latestRound = Math.max(...latest.map(row => row.value.round));
    if (Math.abs(Date.now() - roundEpoch(latestRound)) > 30000) {
        throw new Error('latest verified network round is inconsistent with the local clock');
    }
    const chosen = latestRound + 120;
    const draw = {
        schema: 1, source_commit: source, catalogue_sha256: digest(catalogue),
        frozen_manifest_sha256: digest(freezeManifest), chain:pins,
        round:chosen, scheduled_utc:iso(roundEpoch(chosen)),
        selector:'PCX-X16-draw-v1', registered_utc:new Date().toISOString(),
        reference_beacons:latest.map(item=>({http:item.witness,beacon:item.value})),
    };
    draw.still_unavailable_at_commitment = await pending(draw);
    write(out, draw);
    console.log('Committed-round candidate ' + chosen + ' at ' + draw.scheduled_utc);
} else if (mode === 'pending') {
    const [plan, out] = args;
    const draw = json(plan);
    write(out, {schema:1, round: draw.round, receipts:await pending(draw)});
} else if (mode === 'open') {
    const [plan, out] = args;
    const draw = json(plan);
    checkDraw(draw);
    if (Date.now() < roundEpoch(draw.round)) throw new Error('no opening before the fixed public round');
    const values = await Promise.all(relays.map(relay => request(relay, '/public/' + draw.round)));
    const verified = await Promise.all(values.map(item => verifyRound(item.value, draw.round)));
    if (verified.some(value => value.signature !== verified[0].signature ||
                               value.randomness !== verified[0].randomness)) throw new Error('relays disagree');
    write(out, {schema:1, beacon:verified[0], fetched:values.map(x=>x.witness),
        verified_utc:new Date().toISOString()});
    console.log('Pinned quicknet BLS signature verified on both received copies for round ' + draw.round);
} else if (mode === 'verify') {
    const [plan, received] = args;
    const draw = json(plan);
    const item = json(received);
    checkDraw(draw);
    await verifyRound(item.beacon, draw.round);
    if (draw.reference_beacons?.length !== relays.length ||
        draw.still_unavailable_at_commitment?.length !== relays.length ||
        Math.max(...draw.reference_beacons.map(item => item.beacon.round)) + 120 !== draw.round ||
        !Number.isFinite(Date.parse(draw.registered_utc)) ||
        Date.parse(draw.registered_utc) >= roundEpoch(draw.round)) {
        throw new Error('unrecognized prospective round registration');
    }
    for (const [index, sample] of draw.reference_beacons.entries()) {
        if (sample.http.url !== relays[index] + '/' + pins.hash + '/public/latest' ||
            sample.http.status !== 200 || sample.beacon.round >= draw.round) {
            throw new Error('reference is not the declared latest relay result');
        }
        await verifyRound(sample.beacon, sample.beacon.round);
    }
    for (const witness of draw.still_unavailable_at_commitment) {
        if (!isPending(witness, draw.round) || !Number.isFinite(Date.parse(witness.http_date)) ||
            Date.parse(witness.http_date) >= roundEpoch(draw.round) ||
            Date.parse(witness.observed_utc) >= roundEpoch(draw.round)) {
            throw new Error('invalid pre-round receipt');
        }
    }
    console.log('Archived quicknet round and BLS signatures verified for round ' + draw.round);
} else {
    throw new Error('preparation commands: prepare, pending, open, verify');
}
