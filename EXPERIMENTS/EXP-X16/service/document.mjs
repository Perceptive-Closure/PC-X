import {
  closeSync, fsyncSync, linkSync, mkdirSync, openSync, readFileSync, realpathSync, unlinkSync, writeFileSync,
} from 'node:fs';
import { dirname, join, posix } from 'node:path';
import { digest, encode } from './source.mjs';

const fields = ['id', 'title', 'category', 'body'];

export function intake(source) {
  if (!fields.every((key) => typeof source?.[key] === 'string')) return null;
  const input = Object.fromEntries(fields.map((key) => [key, source[key]]));
  const category = input.category.normalize('NFKC').toLowerCase()
    .replace(/[^a-z0-9]+/gu, '-').replace(/^-+|-+$/gu, '')
    .slice(0, 64).replace(/-+$/u, '') || 'uncategorized';
  const normalized = {
    id: input.id,
    title: input.title.normalize('NFKC').trim().replace(/\s+/gu, ' '),
    category,
    body: input.body.replace(/\r\n?/gu, '\n'),
  };
  return {
    input, normalized,
    expectedDestination: 'routed/category-' + category,
    sha256: digest(encode(input)),
    current: digest(encode(normalized)),
    earlier: digest(encode({ ...normalized, body: normalized.body + '\n[earlier revision]\n' })),
  };
}

export function validRunId(id) {
  return typeof id === 'string' && /^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$/u.test(id) && !id.endsWith('.') &&
    !/^(?:con|prn|aux|nul|com[1-9]|lpt[1-9])(?:\.|$)/iu.test(id);
}

function claimRun(journal) {
  if (journal.directory) return true;
  mkdirSync(journal.workspace, { recursive: true });
  const directory = join(realpathSync(journal.workspace), journal.id);
  try {
    mkdirSync(directory);
  } catch (error) {
    if (error.code === 'EEXIST') return false;
    throw error;
  }
  journal.directory = directory;
  return true;
}

function persist(file, bytes) {
  mkdirSync(dirname(file), { recursive: true });
  const pending = file + '.pending';
  const handle = openSync(pending, 'wx');
  try {
    try {
      writeFileSync(handle, bytes);
      fsyncSync(handle);
    } finally {
      closeSync(handle);
    }
    linkSync(pending, file);
  } finally {
    unlinkSync(pending);
  }
}

function loadRecord(journal, reference) {
  const bytes = readFileSync(join(journal.directory, reference.path));
  if (digest(bytes) !== reference.sha256) throw new Error('Stored stage bytes changed: ' + reference.path);
  return JSON.parse(bytes);
}

function workProduct(task, document, previous, destination) {
  if (task === 'receive' || task === 'receive-route') {
    return { document: document.normalized, reviews: [], destination };
  }
  if (task === 'route') {
    return { document: previous.document, reviews: previous.reviews, destination };
  }
  const minLength = Number(task.slice('review-'.length));
  const words = previous.document.body.toLowerCase().match(/[\p{L}\p{N}]+/gu) ?? [];
  const terms = [...new Set(words.filter((word) => [...word].length >= minLength))].sort();
  const reviewed = { task, min_length: minLength, term_count: terms.length, terms };
  return { document: previous.document, reviews: [...previous.reviews, reviewed], destination };
}

export function completeJob(journal, seal, installation, source, state, row, command, outcome) {
  const { stage, quarantined } = state;
  const task = installation.profile.stages[stage].task;
  const previous = journal.artifacts.at(-1);
  const previousProduct = previous ? loadRecord(journal, previous).product : null;
  const destination = stage === installation.profile.stages.length - 1
    ? (quarantined ? 'quarantine' : source.expectedDestination)
    : null;
  const product = workProduct(task, source, previousProduct, destination);
  const record = {
    schema: 1,
    profile: installation.profile.id,
    stage,
    task,
    edge: installation.edges[stage].id,
    action: command.id,
    receipt: { obs: outcome.obs, meter: outcome.meter },
    work: command.work,
    paid: command.paid,
    input_sha256: source.sha256,
    prior_output_sha256: previous?.sha256 ?? null,
    source_document: stage === 0 ? source.input : null,
    representation_before: row.representation_before,
    representation_before_sha256: row.representation_before_sha256,
    representation_after: outcome.representation_after,
    representation_after_sha256: outcome.representation_after_sha256,
    product,
    catalogue_sha256: seal.catalogue_sha256,
    source_commit: seal.source_commit,
    frozen_manifest_sha256: seal.frozen_manifest_sha256,
  };
  const path = destination
    ? posix.join(destination, 'document.json')
    : posix.join('stages', String(stage).padStart(3, '0') + '.json');
  if (!claimRun(journal)) return null;
  const bytes = encode(record);
  persist(join(journal.directory, path), bytes);
  journal.artifacts.push({ path, sha256: digest(bytes) });
  return path;
}

export function readTruth(journal, source, installation) {
  let previousHash = null;
  let actualDestination = null;
  for (const [stage, artifact] of journal.artifacts.entries()) {
    const record = loadRecord(journal, artifact);
    const phase = installation.profile.stages[stage];
    if (
      record.stage !== stage || record.task !== phase.task ||
      record.edge !== installation.edges[stage].id ||
      record.input_sha256 !== source.sha256 || record.prior_output_sha256 !== previousHash
    ) {
      throw new Error('Stored stage chain disagrees with completed work: ' + artifact.path);
    }
    previousHash = artifact.sha256;
    if (record.product.destination !== null) {
      if (posix.dirname(artifact.path) !== record.product.destination) {
        throw new Error('Stored destination disagrees with routed artifact: ' + artifact.path);
      }
      actualDestination = posix.dirname(artifact.path);
    }
  }
  return {
    complete: journal.artifacts.length === installation?.profile.stages.length &&
      actualDestination === source?.expectedDestination,
    done: journal.artifacts.length,
    expected_destination: source?.expectedDestination ?? null,
    actual_destination: actualDestination,
    artifact_paths: journal.artifacts.map((artifact) => artifact.path),
    artifact_sha256: Object.fromEntries(journal.artifacts.map(({ path, sha256 }) => [path, sha256])),
    document_sha256: source?.sha256 ?? null,
  };
}
