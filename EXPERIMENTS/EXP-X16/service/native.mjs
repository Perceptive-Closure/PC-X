import { readFileSync, writeFileSync } from 'node:fs';
import { isAbsolute } from 'node:path';
import {
  catalogueProfiles, encode, initialReceipt, install, installedRepresentation,
  inventory, pureQueries, readAuthority, sourceRow,
} from './source.mjs';
import { completeJob, intake, readTruth, validRunId } from './document.mjs';

const probe = intake({
  id: 'public-training-inventory-probe', title: 'EXP-X16 native row probe',
  category: 'Training probe', body: 'Public synthetic document for native inventory.\n',
});

function run(task, installation, workspace, seal) {
  const source = intake(task.document);
  const initial = installation ? initialReceipt(installation) : null;
  const journal = { workspace, id: task.id, directory: null, artifacts: [] };
  const steps = [];
  let work = 0;
  let paid = 0;
  function result(status, verdict = null, reason = null) {
    return {
      initial, status, verdict, reason, steps, work, paid, moves: steps.length,
      truth: readTruth(journal, source, installation),
    };
  }

  if (!installation) return result('denied', null, 'invalid-installation');
  if (!source || !validRunId(task.id)) return result('denied', null, 'invalid-document-or-run-id');
  const manual = Array.isArray(task.actions);
  if (
    (manual && task.policy !== undefined) ||
    (!manual && (task.actions !== undefined || !task.policy || typeof task.policy !== 'object' || Array.isArray(task.policy))) ||
    (task.tape !== undefined && !Array.isArray(task.tape))
  ) return result('denied', null, 'invalid-driver');

  const { profile, edges } = installation;
  const state = {
    stage: initial.stage, meter: initial.meter, carry: false, quarantined: false,
    representation: installedRepresentation(edges, source),
  };
  let node = task.policy;
  for (;;) {
    if (manual && steps.length === task.actions.length) return result('manual-done');
    if (!manual && (node.verdict === 'YES' || node.verdict === 'NO')) return result('stopped', node.verdict);
    if (steps.length >= profile.horizon) return result('horizon');

    const act = manual ? task.actions[steps.length] : node.act;
    const row = sourceRow(installation, state, source.current);
    const command = row.commands.find((entry) => entry.id === act);
    if (!command?.enabled) return result('denied', null, 'unknown-command');
    if (!command.allowed) return result('denied', null, 'r-freeze');
    if (command.work > profile.deadline - work) return result('denied', null, 'work-deadline');

    const outcomeIndex = task.tape && steps.length < task.tape.length ? task.tape[steps.length] : 0;
    if (!Number.isSafeInteger(outcomeIndex) || outcomeIndex < 0 || outcomeIndex >= command.outcomes.length) {
      return result('denied', null, 'unsupported-outcome');
    }
    const outcome = command.outcomes[outcomeIndex];
    let artifact = null;
    if (command.kind === 'job') {
      artifact = completeJob(journal, seal, installation, source, state, row, command, outcome);
      if (artifact === null) return result('denied', null, 'existing-run');
    }
    steps.push({
      act, stage: state.stage, meter: state.meter, obs: outcome.obs, next_meter: outcome.meter,
      work: command.work, paid: command.paid, artifact,
    });
    work += command.work;
    paid += command.paid;
    state.meter = outcome.meter;
    state.representation = outcome.representation_after;
    if (command.kind === 'job') {
      state.carry ||= edges[state.stage].carry === true;
      state.stage += 1;
    } else if (profile.variant === 'changed-instrument' && act === 'ask.flag') {
      state.quarantined = true;
    }

    if (!manual) {
      const branch = outcome.obs + '|' + outcome.meter;
      if (!node.next || !Object.hasOwn(node.next, branch)) return result('missing-branch');
      node = node.next[branch];
      if (!node || typeof node !== 'object' || Array.isArray(node)) return result('missing-branch');
    }
  }
}

function main() {
  const [requestPath, responsePath, ...extra] = process.argv.slice(2);
  if (!requestPath || !responsePath || extra.length) throw new Error('Usage: node native.mjs request.json response.json');
  const request = JSON.parse(readFileSync(requestPath, 'utf8'));
  if (
    !request || !Array.isArray(request.tasks) ||
    ![request.catalogue, request.authority, request.workspace].every((path) => typeof path === 'string' && isAbsolute(path))
  ) throw new Error('Expected a batch with absolute catalogue, authority, and workspace paths');
  const { catalogue, seal } = readAuthority(request.catalogue, request.authority);
  const profiles = catalogueProfiles(catalogue);
  const results = request.tasks.map((task) => {
    if (!task || typeof task !== 'object') return { status: 'denied', reason: 'invalid-task' };
    const installation = install(profiles.get(task.profile), task.path);
    if (task.op === 'run') return run(task, installation, request.workspace, seal);
    if (!installation) return { status: 'denied', reason: 'invalid-installation' };
    if (task.op === 'inventory') return inventory(installation, probe);
    if (task.op === 'static') return pureQueries(installation, task);
    return { status: 'denied', reason: 'unknown-operation' };
  });
  writeFileSync(responsePath, encode({ results }));
}

try {
  main();
} catch (error) {
  process.stderr.write('EXP-X16 native service: ' + error.message + '\n');
  process.exitCode = 1;
}
