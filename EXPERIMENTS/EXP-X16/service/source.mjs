import { createHash, createPublicKey, verify } from 'node:crypto';
import { readFileSync } from 'node:fs';

export const encode = (value) => Buffer.from(JSON.stringify(value) + '\n', 'utf8');
export const digest = (bytes) => createHash('sha256').update(bytes).digest('hex');

export function readAuthority(cataloguePath, authorityPath) {
  const catalogueBytes = readFileSync(cataloguePath);
  const seal = JSON.parse(readFileSync(authorityPath, 'utf8'));
  if (
    seal?.schema !== 1 ||
    seal.catalogue_sha256 !== digest(catalogueBytes) ||
    typeof seal.source_commit !== 'string' || !/^[0-9a-f]{40}$/.test(seal.source_commit) ||
    typeof seal.frozen_manifest_sha256 !== 'string' || !/^[0-9a-f]{64}$/.test(seal.frozen_manifest_sha256) ||
    typeof seal.public_key_pem !== 'string' || !seal.public_key_pem.startsWith('-----BEGIN PUBLIC KEY-----') ||
    typeof seal.signature !== 'string'
  ) {
    throw new Error('Invalid authority seal or catalogue bytes');
  }
  const payload = Buffer.from([
    'PCX-X16-authority-v1', seal.catalogue_sha256,
    seal.source_commit, seal.frozen_manifest_sha256, '',
  ].join('\n'), 'ascii');
  const key = createPublicKey(seal.public_key_pem);
  const signature = Buffer.from(seal.signature, 'base64');
  if (
    key.asymmetricKeyType !== 'ed25519' ||
    signature.length !== 64 || signature.toString('base64') !== seal.signature ||
    !verify(null, payload, key, signature)
  ) {
    throw new Error('Invalid authority signature');
  }
  return { catalogue: JSON.parse(catalogueBytes), seal };
}

const amount = (value, minimum) => Number.isSafeInteger(value) && value >= minimum;
const label = (value) => typeof value === 'string' && value.length > 0 && !value.includes('|');

export function catalogueProfiles(catalogue) {
  if (catalogue?.schema !== 1 || !Array.isArray(catalogue.profiles)) throw new Error('Invalid catalogue');
  const profiles = new Map();
  for (const profile of catalogue.profiles) {
    const variants = ['standard', 'split-calls', 'free-guard', 'hidden-carry', 'changed-instrument'];
    if (
      !label(profile?.id) || profiles.has(profile.id) || !variants.includes(profile.variant) ||
      !label(profile.start) || !Array.isArray(profile.accept) || !profile.accept.every(label) ||
      !label(profile.initial_meter) || !amount(profile.deadline, 0) || !amount(profile.horizon, 0) ||
      !Array.isArray(profile.stages) || profile.stages.length === 0 ||
      (profile.variant === 'free-guard' && profile.stages.length < 2)
    ) throw new Error('Invalid native profile');

    const edgeIds = new Set();
    const queryIds = new Set();
    for (const [index, stage] of profile.stages.entries()) {
      let taskFits;
      if (profile.stages.length === 1) taskFits = stage?.task === 'receive-route';
      else if (index === 0) taskFits = stage?.task === 'receive';
      else if (index === profile.stages.length - 1) taskFits = stage?.task === 'route';
      else taskFits = /^review-[1-9][0-9]*$/u.test(stage?.task);
      if (
        !taskFits || !amount(stage.base, 1) || !amount(stage.premium, 1) ||
        !amount(stage.base + stage.premium, 2) || !Array.isArray(stage.edges) ||
        !object(stage.reads) || !Array.isArray(stage.statics)
      ) throw new Error('Invalid native stage in ' + profile.id);

      const jobs = new Set(['job.fast', 'job.slow']);
      for (const edge of stage.edges) {
        if (
          !label(edge?.id) || edgeIds.has(edge.id) || !label(edge.tail) || !label(edge.head) ||
          (edge.stale !== 0 && edge.stale !== 1) || !Array.isArray(edge.gives) || edge.gives.length === 0 ||
          !edge.gives.every((receipt) => label(receipt?.obs) && label(receipt?.meter)) ||
          (profile.variant === 'split-calls' &&
            (!label(edge.literal_fast) || edge.literal_fast === 'job.slow'))
        ) throw new Error('Invalid native edge in ' + profile.id);
        edgeIds.add(edge.id);
        if (profile.variant === 'split-calls') jobs.add(edge.literal_fast);
      }
      for (const [meter, reads] of Object.entries(stage.reads)) {
        if (!label(meter) || !object(reads)) throw new Error('Invalid native meter in ' + profile.id);
        for (const [id, read] of Object.entries(reads)) {
          if (
            !label(id) || jobs.has(id) || !amount(read?.price, 0) || !label(read.next) ||
            !['stale', 'prepared'].includes(read.observe)
          ) throw new Error('Invalid native read in ' + profile.id);
        }
      }
      for (const query of stage.statics) {
        if (
          !label(query?.id) || queryIds.has(query.id) || !['stale', 'edge'].includes(query.field) ||
          !amount(query.price, 0)
        ) throw new Error('Invalid pure query in ' + profile.id);
        queryIds.add(query.id);
      }
    }
    profiles.set(profile.id, profile);
  }
  return profiles;
}

export function install(profile, path) {
  if (!profile || !Array.isArray(path) || path.length !== profile.stages.length) return null;
  const edges = [];
  let vertex = profile.start;
  for (const [index, stage] of profile.stages.entries()) {
    const edge = stage.edges.find((candidate) => candidate.id === path[index] && candidate.tail === vertex);
    if (!edge) return null;
    edges.push(edge);
    vertex = edge.head;
  }
  if (!profile.accept.includes(vertex)) return null;
  return { profile, edges };
}

export function initialReceipt({ profile, edges }) {
  const obs = profile.variant === 'free-guard' ? guard(edges[1]) : 'start';
  return { stage: 0, obs, meter: profile.initial_meter };
}

function guard(edge) {
  return edge.stale === 0 ? 'fresh' : 'stale';
}

export function installedRepresentation(edges, { current, earlier }) {
  return edges.map((edge) => edge.stale === 0 ? current : earlier);
}

export function sourceRow(installation, state, current) {
  const { profile, edges } = installation;
  const { stage, meter, representation } = state;
  const before = encode(representation);
  const beforeHash = digest(before);
  const phase = profile.stages[stage];
  const edge = edges[stage];
  const commands = [];
  if (phase) {
    const fastId = profile.variant === 'split-calls' ? edge.literal_fast : 'job.fast';
    for (const [id, fast] of [[fastId, true], ['job.slow', false]]) {
      const outcomes = edge.gives.map((receipt, index) => {
        // The final fast successor refreshes the installed binding. A refresh of
        // an already current binding compares equal to the previous relation.
        const after = fast && index === edge.gives.length - 1
          ? representation.with(stage, current)
          : representation;
        const bytes = encode(after);
        return {
          obs: receipt.obs,
          meter: receipt.meter,
          r_changed: !before.equals(bytes),
          representation_after: after,
          representation_after_sha256: digest(bytes),
        };
      });
      commands.push({
        id, kind: 'job', enabled: true,
        allowed: outcomes.every((outcome) => !outcome.r_changed),
        work: fast ? phase.base : phase.base + phase.premium,
        paid: 0,
        outcomes,
      });
    }
    const reads = Object.hasOwn(phase.reads, meter) ? phase.reads[meter] : {};
    for (const [id, read] of Object.entries(reads)) {
      const carry = profile.variant === 'hidden-carry' && state.carry && id === 'ask.flag';
      commands.push({
        id, kind: 'read', enabled: true, allowed: true, work: 0,
        paid: read.price + (carry ? 4 : 0),
        outcomes: [{
          obs: read.observe === 'stale' ? guard(edge) : 'prepared',
          meter: read.next === 'same' ? meter : read.next,
          r_changed: false,
          representation_after: representation,
          representation_after_sha256: beforeHash,
        }],
      });
    }
  }
  return {
    stage, edge: edge?.id ?? null, meter, commands,
    representation_before: representation,
    representation_before_sha256: beforeHash,
  };
}

export function inventory(installation, probe) {
  const initial = initialReceipt(installation);
  const { profile, edges } = installation;
  const representation = installedRepresentation(edges, probe);
  const rows = [];
  let meters = new Set([initial.meter]);
  let carry = false;
  for (let stage = 0; stage < profile.stages.length; stage += 1) {
    const nextMeters = new Set();
    // Set iteration also visits meters reached by reads at the same stage.
    for (const meter of meters) {
      const row = sourceRow(installation, { stage, meter, carry, representation }, probe.current);
      rows.push(row);
      for (const command of row.commands) {
        if (!command.enabled || !command.allowed) continue;
        const reachable = command.kind === 'job' ? nextMeters : meters;
        for (const outcome of command.outcomes) reachable.add(outcome.meter);
      }
    }
    meters = nextMeters;
    carry ||= edges[stage].carry === true;
  }
  return { initial, rows };
}

function object(value) {
  return value !== null && typeof value === 'object' && !Array.isArray(value);
}

export function pureQueries(installation, task) {
  const available = new Map();
  for (const [index, stage] of installation.profile.stages.entries()) {
    const edge = installation.edges[index];
    for (const query of stage.statics) {
      available.set(query.id, {
        id: query.id,
        paid: query.price,
        answer: query.field === 'stale' ? guard(edge) : edge.id,
      });
    }
  }
  const steps = [];
  function result(status, verdict = null, reason = null) {
    return {
      status, verdict, reason,
      answers: Object.fromEntries(steps.map(({ id, answer }) => [id, answer])),
      paid: steps.reduce((total, turn) => total + turn.paid, 0),
      sequence: steps.map(({ id }) => id),
      steps,
    };
  }

  if (Array.isArray(task.queries) && task.static_policy === undefined) {
    for (const id of task.queries) {
      if (!available.has(id)) return result('denied', null, 'unknown-static-query');
      steps.push(available.get(id));
    }
    return result('stopped');
  }
  if (task.queries !== undefined || !object(task.static_policy)) {
    return result('denied', null, 'invalid-static-driver');
  }
  let node = task.static_policy;
  while (object(node)) {
    if (node.verdict === 'YES' || node.verdict === 'NO') return result('stopped', node.verdict);
    if (Object.keys(node).length === 0) return result('stopped');
    const query = available.get(node.ask);
    if (!query) return result('denied', null, 'unknown-static-query');
    steps.push(query);
    node = object(node.next) && Object.hasOwn(node.next, query.answer) ? node.next[query.answer] : null;
  }
  return result('missing-branch');
}
