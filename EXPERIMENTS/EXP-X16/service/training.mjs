import assert from 'node:assert/strict';
import { spawnSync } from 'node:child_process';
import { createHash, generateKeyPairSync, sign } from 'node:crypto';
import { existsSync, mkdtempSync, readFileSync, writeFileSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import { fileURLToPath } from 'node:url';

const dir = mkdtempSync(join(tmpdir(), 'pcx-x16-public-training-'));
const native = fileURLToPath(new URL('./native.mjs', import.meta.url));
const sourceCatalogue = new URL('../cases/catalogue.json', import.meta.url);
const catalogueBytes = readFileSync(sourceCatalogue);
const digest = (bytes) => createHash('sha256').update(bytes).digest('hex');
const json = (value) => Buffer.from(JSON.stringify(value) + '\n', 'utf8');
const sourceCommit = '0'.repeat(40);
const manifest = digest('EXP-X16 PUBLIC TRAINING ONLY. No held-out key or freeze.');
const keys = generateKeyPairSync('ed25519');

function issue(name, bytes) {
  const catalogue = join(dir, name + '-catalogue.json');
  const authority = join(dir, name + '-authority.json');
  const catalogueHash = digest(bytes);
  const payload = Buffer.from('PCX-X16-authority-v1\n' + catalogueHash + '\n' + sourceCommit + '\n' + manifest + '\n', 'ascii');
  writeFileSync(catalogue, bytes);
  writeFileSync(authority, json({
    schema: 1, catalogue_sha256: catalogueHash, source_commit: sourceCommit,
    frozen_manifest_sha256: manifest, public_key_pem: keys.publicKey.export({ type: 'spki', format: 'pem' }),
    signature: sign(null, payload, keys.privateKey).toString('base64'),
  }));
  return { catalogue, authority };
}

function batch(name, paths, tasks, expected = 0) {
  const workspace = join(dir, name + '-work');
  const request = join(dir, name + '-request.json');
  const response = join(dir, name + '-response.json');
  writeFileSync(request, json({ ...paths, workspace, tasks }));
  const child = spawnSync(process.execPath, [native, request, response], { encoding: 'utf8' });
  if (child.error) throw child.error;
  assert.equal(child.status, expected, child.stderr);
  if (expected) {
    assert.equal(existsSync(response), false);
    assert.equal(existsSync(workspace), false);
    return child.stderr;
  }
  return { workspace, results: JSON.parse(readFileSync(response)).results };
}

const signed = issue('public', catalogueBytes);
const documented = {
  id: 'public-training-doc', title: '  Ｘ16  training  ',
  category: '  NOAA ／ Plans  ', body: 'Alpha plan \r\nBeta alpha!\r2026.',
};
const normalized = {
  id: documented.id, title: 'X16 training', category: 'noaa-plans', body: 'Alpha plan \nBeta alpha!\n2026.',
};
const destination = 'routed/category-noaa-plans';
const lastFile = destination + '/document.json';
const normalizedHash = digest(json(normalized));
const earlierHash = digest(json({ ...normalized, body: normalized.body + '\n[earlier revision]\n' }));
const fast = 'job.fast';
const slow = 'job.slow';
const positiveMeter = ['intake', 'route-fresh'];
const negativeMeter = ['intake', 'route-stale'];
const left = ['start-left', 'middle-left', 'route-left'];
const wrong = ['start-left', 'middle-left', 'route-right'];
const changed = ['intake-fresh', 'review', 'route'];
const controlClear = ['early-clear', 'late-fresh'];
const controlCarry = ['early-set', 'late-fresh'];

function installed(id, profile, path, extra = {}) {
  return { id, profile, path, op: 'inventory', ...extra };
}

function run(id, profile, path, actions, tape) {
  return installed(id, profile, path, { op: 'run', document: documented, actions, tape });
}

const yes = { verdict: 'YES' };
const flag = (meter) => ({ act: 'ask.flag', next: {
  ['fresh|' + meter]: { act: fast, next: { 'filed|WORK': yes } },
  ['stale|' + meter]: { verdict: 'NO' },
} });
const meterPolicy = { act: fast, next: {
  'filed|SHORT': flag('SHORT'),
  'filed|LONG': { act: 'ask.prepare', next: { 'prepared|READY': flag('READY') } },
} };
const common = batch('public', signed, [
  installed('training-meter-rows', 'meter-h3', positiveMeter),
  installed('training-left-rows', 'feedback-live', left),
  installed('training-suppressed', 'feedback-suppressed', left),
  installed('training-out-of-graph', 'feedback-live', wrong),
  installed('training-static-fixed', 'meter-h4', positiveMeter, { op: 'static', queries: ['guard-2', 'mode-1'] }),
  installed('training-static-adaptive', 'meter-h4', negativeMeter, {
    op: 'static', static_policy: { ask: 'guard-2', next: {
      fresh: yes, stale: { ask: 'mode-1', next: { intake: { verdict: 'NO' } } },
    } },
  }),
  installed('training-meter-long', 'meter-h4', positiveMeter, {
    op: 'run', document: documented, policy: meterPolicy, tape: [1],
  }),
  installed('training-meter-short', 'meter-h4', positiveMeter, {
    op: 'run', document: documented, policy: meterPolicy,
  }),
  run('training-true-route', 'feedback-live', left, [fast, fast, slow]),
  run('training-work', 'meter-h3', negativeMeter, [fast, slow]),
  run('training-horizon', 'meter-h3', positiveMeter, [fast, 'ask.prepare', 'ask.flag', fast], [1]),
  installed('training-branch', 'meter-h3', positiveMeter, {
    op: 'run', document: documented, policy: { act: fast, next: {} },
  }),
  run('training-bad-outcome', 'meter-h3', positiveMeter, [fast], [5]),
  run('training-bad-graph', 'feedback-live', wrong, [fast]),
  run('training-wrong-literal', 'split-calls', ['split-right'], ['job.fast.left']),
  run('training-right-literal', 'split-calls', ['split-right'], ['job.fast.right']),
  installed('training-free-fresh', 'free-guard', positiveMeter),
  installed('training-free-stale', 'free-guard', negativeMeter),
  run('training-control-clear', 'hidden-carry', controlClear, [fast, 'ask.flag', fast]),
  run('training-control-carry', 'hidden-carry', controlCarry, [fast, 'ask.flag', fast]),
  run('training-control-trusted', 'changed-instrument', changed, [fast, fast, fast]),
  run('training-control-altered', 'changed-instrument', changed, ['ask.flag', fast, fast, fast]),
  run('training-true-route', 'feedback-live', left, [fast, fast, slow]),
]);

const [
  meterRows, leftRows, suppressedRows, badGraph, fixed, adaptive, meterLong, meterShort,
  trueRoute, workCut, moveCut, missingBranch, badOutcome, badRunGraph, wrongLiteral, rightLiteral,
  freeFresh, freeStale, clear, carry, trusted, altered, duplicate,
] = common.results;
assert.deepEqual(meterRows.rows.map(({ stage, meter }) => [stage, meter]), [[0, 'WORK'], [1, 'SHORT'], [1, 'LONG'], [1, 'READY']]);
assert.deepEqual(meterRows.rows[0].commands[0].outcomes.map(({ obs, meter }) => [obs, meter]), [['filed', 'SHORT'], ['filed', 'LONG']]);
assert.equal(leftRows.rows[0].commands[0].outcomes[0].meter, 'LEFT');
assert.equal(suppressedRows.rows[0].commands[0].outcomes[0].meter, 'WORK');
assert.equal(badGraph.reason, 'invalid-installation');
assert.deepEqual(fixed.answers, { 'guard-2': 'fresh', 'mode-1': 'intake' });
assert.deepEqual(fixed.sequence, ['guard-2', 'mode-1']);
assert.equal(fixed.paid, 4);
assert.equal(adaptive.verdict, 'NO');
assert.deepEqual(adaptive.steps, [
  { id: 'guard-2', answer: 'stale', paid: 1 }, { id: 'mode-1', answer: 'intake', paid: 3 },
]);
assert.equal(adaptive.paid, 4);
for (const [result, work, paid, moves] of [[meterLong, 2, 2, 4], [meterShort, 2, 1, 3]]) {
  assert.equal(result.truth.complete, true);
  assert.deepEqual([result.status, result.verdict, result.work, result.paid, result.moves], ['stopped', 'YES', work, paid, moves]);
  assert.equal(result.steps.filter(({ artifact }) => artifact !== null).length, 2);
}
assert.deepEqual([workCut.status, workCut.reason, workCut.work], ['denied', 'work-deadline', 1]);
assert.deepEqual([moveCut.status, moveCut.moves, moveCut.paid], ['horizon', 3, 2]);
assert.deepEqual([missingBranch.status, missingBranch.truth.done], ['missing-branch', 1]);
assert.equal(badOutcome.reason, 'unsupported-outcome');
assert.equal(badRunGraph.reason, 'invalid-installation');
assert.equal(wrongLiteral.reason, 'unknown-command');
assert.equal(rightLiteral.truth.complete, true);
assert.equal(freeFresh.initial.obs, 'fresh');
assert.equal(freeStale.initial.obs, 'stale');
assert.deepEqual(clear.steps[1], { ...carry.steps[1], paid: 1 });
assert.equal(carry.steps[1].paid, 5);
assert.equal(trusted.truth.complete, true);
assert.equal(altered.truth.complete, false);
assert.equal(altered.truth.done, 3);
assert.equal(altered.truth.actual_destination, 'quarantine');
assert.ok(existsSync(join(common.workspace, 'training-control-altered', 'quarantine', 'document.json')));
assert.equal(duplicate.reason, 'existing-run');
for (const id of ['training-bad-outcome', 'training-bad-graph', 'training-wrong-literal', 'training-static-fixed']) {
  assert.equal(existsSync(join(common.workspace, id)), false);
}

assert.equal(trueRoute.truth.complete, true);
assert.equal(trueRoute.truth.document_sha256, digest(json(documented)));
assert.equal(trueRoute.truth.expected_destination, destination);
assert.equal(trueRoute.truth.actual_destination, destination);
assert.deepEqual(trueRoute.truth.artifact_paths, ['stages/000.json', 'stages/001.json', lastFile]);
let previousHash = null;
const expectedReviews = [{ task: 'review-1', min_length: 1, term_count: 4, terms: ['2026', 'alpha', 'beta', 'plan'] }];
for (const [phase, name] of trueRoute.truth.artifact_paths.entries()) {
  const bytes = readFileSync(join(common.workspace, 'training-true-route', name));
  const item = JSON.parse(bytes);
  assert.deepEqual(bytes, json(item));
  assert.equal(item.input_sha256, digest(json(documented)));
  assert.equal(item.prior_output_sha256, previousHash);
  assert.equal(item.source_commit, sourceCommit);
  assert.equal(item.catalogue_sha256, digest(catalogueBytes));
  assert.equal(item.edge, left[phase]);
  assert.deepEqual(item.source_document, phase === 0 ? documented : null);
  assert.deepEqual(item.representation_before, [normalizedHash, normalizedHash, earlierHash]);
  assert.deepEqual(item.representation_after, item.representation_before);
  assert.equal(item.representation_before_sha256, digest(json(item.representation_before)));
  assert.equal(item.representation_after_sha256, item.representation_before_sha256);
  assert.deepEqual(item.product, {
    document: normalized, reviews: phase ? expectedReviews : [], destination: phase === 2 ? destination : null,
  });
  previousHash = digest(bytes);
  assert.equal(trueRoute.truth.artifact_sha256[name], previousHash);
}

// The public roster already separates full receipt support and stale refresh.
// This separate dummy catalogue combines the two to exercise whole-atom denial.
const mixedProfile = structuredClone(JSON.parse(catalogueBytes).profiles.find((profile) => profile.id === 'meter-h3'));
mixedProfile.id = 'training-only-mixed-stale';
mixedProfile.deadline = 3;
mixedProfile.stages[1].edges[1].gives.push({ obs: 'filed', meter: 'OTHER' });
const mixed = batch('mixed', issue('mixed', json({ schema: 1, profiles: [mixedProfile] })), [
  installed('training-mixed-rows', mixedProfile.id, negativeMeter),
  run('training-mixed-first', mixedProfile.id, negativeMeter, [fast, fast], [0, 0]),
  run('training-mixed-last', mixedProfile.id, negativeMeter, [fast, fast], [0, 1]),
  run('training-mixed-slow-first', mixedProfile.id, negativeMeter, [fast, slow], [0, 0]),
  run('training-mixed-slow-last', mixedProfile.id, negativeMeter, [fast, slow], [0, 1]),
]);
const [mixedRows, ...mixedRuns] = mixed.results;
const short = mixedRows.rows.find(({ stage, meter }) => stage === 1 && meter === 'SHORT');
const [rawFast, rawSlow] = short.commands;
assert.equal(rawFast.allowed, false);
assert.deepEqual(rawFast.outcomes.map(({ meter, r_changed }) => [meter, r_changed]), [['WORK', false], ['OTHER', true]]);
assert.deepEqual(rawFast.outcomes[0].representation_after, short.representation_before);
assert.notDeepEqual(rawFast.outcomes[1].representation_after, short.representation_before);
assert.equal(rawFast.outcomes[1].representation_after_sha256, digest(json(rawFast.outcomes[1].representation_after)));
assert.deepEqual(rawSlow.outcomes.map(({ r_changed }) => r_changed), [false, false]);
for (const rejected of mixedRuns.slice(0, 2)) {
  assert.deepEqual([rejected.status, rejected.reason, rejected.moves, rejected.work, rejected.truth.done], ['denied', 'r-freeze', 1, 1, 1]);
}
for (const executed of mixedRuns.slice(2)) assert.equal(executed.truth.complete, true);

const changedSeal = JSON.parse(readFileSync(signed.authority));
changedSeal.source_commit = '1'.repeat(40);
const invalidAuthority = join(dir, 'invalid-authority.json');
writeFileSync(invalidAuthority, json(changedSeal));
const corruptCatalogue = join(dir, 'corrupt-catalogue.json');
writeFileSync(corruptCatalogue, Buffer.concat([catalogueBytes, Buffer.from('\n')]));
const wouldWrite = [run('training-invalid-signature', 'feedback-live', left, [fast])];
assert.match(batch('bad-signature', { ...signed, authority: invalidAuthority }, wouldWrite, 1), /authority signature/u);
assert.match(batch('bad-catalogue', { ...signed, catalogue: corruptCatalogue }, wouldWrite, 1), /catalogue bytes/u);

process.stdout.write('PUBLIC TRAINING ONLY. Passed 28 signed tasks and 2 rejected batch seals.\n');
process.stdout.write('Public training requests and durable evidence: ' + dir + '\n');
