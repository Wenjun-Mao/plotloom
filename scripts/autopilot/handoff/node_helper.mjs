import fsDefault from 'node:fs/promises';
import { constants as C } from 'node:fs';
import crypto from 'node:crypto';
import os from 'node:os';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

export const moduleIdentity = Object.freeze({ origin: import.meta.url,
  builtinImports: ['node:fs/promises', 'node:fs', 'node:crypto', 'node:os', 'node:path', 'node:url'],
  evaluationId: crypto.randomUUID() });

export async function dispatch(request, syntheticIO = null) {
  // Test injection is explicit, direct-call only, and requires a synthetic anchor.
  // The capsule's fixed bootstrap never supplies this argument.
  const fs = syntheticIO?.fs ?? fsDefault;
  const now = syntheticIO?.now ?? Date.now;
  const pause = syntheticIO?.pause ?? (ms => new Promise(resolve => setTimeout(resolve, ms)));
  const B = path.dirname(fileURLToPath(import.meta.url));
  let R, qa;
  const registry = { handoff_proof_only: 'proof_launch.py', paid_outline: 'paid_launch.py', qualification_pair: 'pair_launch.py' };
  const receivers = { handoff_proof_only: 'proof_receiver.py', paid_outline: 'paid_receiver.py', qualification_pair: 'pair_receiver.py' };
  const sha = value => crypto.createHash('sha256').update(value).digest('hex');
  const need = (value, message) => { if (!value) throw Error(message); };
  const hash = value => typeof value === 'string' && /^[a-f0-9]{64}$/.test(value);
  const stable = value => {
    if (typeof value === 'number') need(Number.isSafeInteger(value), 'unsafe JSON number');
    if (Array.isArray(value)) return '[' + value.map(stable).join(',') + ']';
    if (value && typeof value === 'object') return '{' + Object.keys(value).sort()
      .map(key => JSON.stringify(key) + ':' + stable(value[key])).join(',') + '}';
    return JSON.stringify(value);
  };
  const same = (a, b) => stable(a) === stable(b);
  const bytes = value => Buffer.from(stable(value) + '\n');
  const keys = (value, names) => need(value && !Array.isArray(value)
    && same(Object.keys(value).sort(), [...names].sort()), 'unexpected fields');
  const parse = raw => {
    const data = Buffer.isBuffer(raw) ? raw : Buffer.from(raw);
    const value = JSON.parse(data.toString('utf8'));
    need(bytes(value).equals(data), 'noncanonical or duplicate JSON');
    return value;
  };
  const fileIdentity = s => [s.dev, s.ino, s.uid, s.mode, s.nlink, s.size, String(s.mtimeMs), String(s.ctimeMs)];
  const rootIdentity = s => [s.dev, s.ino, s.uid];
  const isRootIdentity = v => Array.isArray(v) && v.length === 3 && v.every(n => Number.isSafeInteger(n) && n >= 0);
  const uid = os.userInfo().uid;
  let plan, phase, anchor, controls;
  const safeRoot = async root => {
    need(typeof root === 'string' && path.isAbsolute(root) && path.normalize(root) === root, 'absolute canonical root');
    let current = '/';
    for (const part of root.split('/').filter(Boolean)) {
      current = path.join(current, part);
      const s = await fs.lstat(current);
      need(s.isDirectory() && !s.isSymbolicLink(), 'linked directory');
    }
    const s = await fs.lstat(root);
    need(s.uid === uid && (s.mode & 0o777) === 0o700, 'private owned root required');
    return s;
  };
  const read = async (file, privateMode = true) => {
    const before = await fs.lstat(file);
    const limit = privateMode ? 1000000 : 200000000;
    need(before.isFile() && !before.isSymbolicLink() && (before.uid === uid || (!privateMode && before.uid === 0)) && before.nlink === 1
      && before.size <= limit && (privateMode ? (before.mode & 0o777) === 0o600 : (before.mode & 0o022) === 0), 'unsafe regular file');
    const fd = await fs.open(file, C.O_RDONLY | C.O_NOFOLLOW | C.O_NONBLOCK);
    try {
      need(same(fileIdentity(before), fileIdentity(await fd.stat())), 'open identity changed');
      const raw = await fd.readFile();
      need(raw.length <= limit && same(fileIdentity(before), fileIdentity(await fd.stat()))
        && same(fileIdentity(before), fileIdentity(await fs.lstat(file))), 'read identity changed');
      return { raw, sha256: sha(raw), identity: fileIdentity(before) };
    } finally { await fd.close(); }
  };
  const assertRoot = async () => need(same(rootIdentity(await safeRoot(plan.phaseRoot)), plan.phaseIdentity), 'runtime root identity changed');
  const write = async (name, raw) => {
    need(path.basename(name) === name, 'unbound record path');
    await assertRoot();
    const target = path.join(plan.phaseRoot, name);
    const fd = await fs.open(target, C.O_WRONLY | C.O_CREAT | C.O_EXCL | C.O_NOFOLLOW, 0o600);
    let before;
    try { before = await fd.stat(); await fd.writeFile(raw); await fd.sync(); }
    finally { await fd.close(); }
    const directory = await fs.open(plan.phaseRoot, C.O_RDONLY | C.O_DIRECTORY | C.O_NOFOLLOW);
    try { await directory.sync(); } finally { await directory.close(); }
    await assertRoot();
    const actual = await read(target);
    need(actual.identity[0] === before.dev && actual.identity[1] === before.ino && actual.raw.equals(raw), 'publication readback');
    return actual.sha256;
  };
  const record = async name => {
    await assertRoot();
    const prefix = name + '.ready-';
    const names = (await fs.readdir(plan.phaseRoot)).filter(n => n.startsWith(prefix));
    if (!names.length) return null;
    need(names.length === 1 && hash(names[0].slice(prefix.length)), 'bad record marker');
    const marker = await read(path.join(plan.phaseRoot, names[0]));
    need(marker.raw.length === 0, 'record marker not empty');
    const data = await read(path.join(plan.phaseRoot, name));
    need(data.sha256 === names[0].slice(prefix.length), 'record hash mismatch');
    const final = (await fs.readdir(plan.phaseRoot)).filter(n => n.startsWith(prefix));
    need(same(final, names), 'record authority set changed during payload read');
    need(same(marker.identity, fileIdentity(await fs.lstat(path.join(plan.phaseRoot, names[0])))), 'record marker identity changed');
    await assertRoot();
    return { value: parse(data.raw), sha256: data.sha256 };
  };
  const gate = launch => {
    const current = now();
    need(Number.isSafeInteger(launch.startedWallMs) && current >= launch.startedWallMs
      && current < launch.startedWallMs + 60000, 'attachment deadline');
  };
  const waitRecord = async (name, launch) => {
    const until = now() + 10000;
    while (true) {
      if (launch) gate(launch);
      const result = await record(name);
      if (result) { if (launch) gate(launch); return result; }
      need(now() < until, 'record wait expired');
      await pause(20);
    }
  };
  const rows = text => text.trim().split('\n').filter(Boolean).map(line => {
    const m = line.trim().match(/^(\d+)\s+(\d+)\s+(\d+)\s+(\w+\s+\w+\s+\d+\s+\d+:\d+:\d+\s+\d+)\s+(.+)$/);
    need(m, 'incomplete process row');
    return { pid: Number(m[1]), ppid: Number(m[2]), pgid: Number(m[3]),
      birthStart: m[4].replace(/\s+/g, ' '), commandSha256: sha(m[5]) };
  });
  const intentValue = () => ({ version: 3, phaseSha256: plan.phaseSha256, planSha256: anchor.planSha256,
    anchorSha256: request.anchorSha, authority: plan.authority, capsuleSha256: anchor.capsuleSha256,
    controlsSha256: plan.controlsSha256, helperSha256: anchor.helperSha256,
    argvSha256: plan.argvSha256, allocationSha256: plan.allocationSha256, invocationCount: 1 });
  const load = async () => {
    const launch = await waitRecord('launch.json'); gate(launch.value);
    const tree = await waitRecord('driver-process.json', launch.value);
    const intent = await record('invocation-intent.json');
    need(intent && same(intent.value, intentValue()) && launch.value.phaseSha256 === plan.phaseSha256
      && launch.value.intentSha256 === intent.sha256 && tree.value.launchSha256 === launch.sha256, 'record authority mismatch');
    keys(tree.value, ['launcher', 'driver', 'launchSha256']);
    const a = tree.value.launcher, b = tree.value.driver;
    for (const row of [a, b]) {
      keys(row, ['pid', 'ppid', 'pgid', 'birthStart', 'commandSha256']);
      need([row.pid, row.ppid, row.pgid].every(v => Number.isSafeInteger(v) && v > 0)
        && typeof row.birthStart === 'string' && row.birthStart && hash(row.commandSha256), 'invalid process fields');
    }
    need(a.pid === launch.value.pid && a.pgid === a.pid && a.pgid === launch.value.pgid
      && a.birthStart === launch.value.birthStart && b.pid !== a.pid && b.ppid === a.pid && b.pgid === a.pgid, 'exact process topology');
    const expectedExec = ['/opt/homebrew/bin/uv', 'run', '--locked', '--no-sync', 'python', '-B',
      B + '/' + receivers[plan.kind],
      '--phase-root', plan.phaseRoot, '--phase-sha', plan.phaseSha256];
    need(same(launch.value.execArgv, expectedExec) && a.commandSha256 === sha(expectedExec.join(' '))
      && qa.allowedInnerExecutables.some(exe => b.commandSha256 === sha([exe, ...expectedExec.slice(5)].join(' '))), 'process argv identity');
    gate(launch.value);
    return { launch, tree, intent };
  };
  const boundPayload = records => {
    need(Number.isSafeInteger(request.originalHandle) && request.originalHandle > 0, 'invalid original handle');
    return { version: 3, authority: plan.authority, phaseSha256: plan.phaseSha256, phaseKind: phase.kind,
      namespace: phase.namespace, nonce: phase.nonce, intentSha256: records.intent.sha256,
      planSha256: anchor.planSha256, anchorSha256: request.anchorSha, argvSha256: plan.argvSha256,
      launchSha256: records.launch.sha256, driverProcessSha256: records.tree.sha256,
      controlsSha256: plan.controlsSha256, capsuleSha256: anchor.capsuleSha256, helperSha256: anchor.helperSha256,
      allocationSha256: plan.allocationSha256, nativeExecHandle: request.originalHandle, observedTree: records.tree.value };
  };
  const payload = (records, observation) => {
    const observed = rows(observation);
    need(observed.length === 2 && observed.some(v => same(v, records.tree.value.launcher))
      && observed.some(v => same(v, records.tree.value.driver)), 'observed identity mismatch');
    gate(records.launch.value);
    return boundPayload(records);
  };
  try {
    const extra = { capability: [], prepare: [], records: ['originalHandle'], validate: ['originalHandle', 'observationOutput'],
      publish: ['originalHandle', 'observationOutput'], witness: ['originalHandle', 'attendanceSha256'] };
    need(Object.hasOwn(extra, request.action), 'unknown action');
    keys(request, ['action', 'capsuleSource', 'planText', 'anchorText', 'anchorSha', ...extra[request.action]]);
    need(hash(request.anchorSha) && typeof request.anchorText === 'string'
      && sha(request.anchorText) === request.anchorSha, 'independent anchor pin');
    anchor = parse(request.anchorText);
    keys(anchor, ['version', 'kind', 'authority', 'sourceRoot', 'sourceIdentity', 'capsuleSha256', 'planSha256',
      'controlsSha256', 'helperSha256', 'phaseSha256', 'allocationSha256']);
    need(anchor.version === 3 && anchor.kind === 'capsule_plan_anchor.v3' && typeof request.capsuleSource === 'string'
      && sha(request.capsuleSource) === anchor.capsuleSha256 && typeof request.planText === 'string'
      && sha(request.planText) === anchor.planSha256, 'capsule/plan identity');
    plan = parse(request.planText);
    keys(plan, ['version', 'authority', 'kind', 'sourceRoot', 'sourceIdentity', 'controlsSha256', 'phaseRoot',
      'phaseIdentity', 'phaseSha256', 'allocationSha256', 'namespace', 'nonce', 'argv', 'argvSha256', 'execArgs']);
    need(plan.version === 3 && ['capability_check', 'synthetic_unit', 'provider_free_handoff', 'paid_outline_once', 'qualification_pair_once'].includes(plan.authority)
      && anchor.authority === plan.authority && (!syntheticIO || plan.authority === 'synthetic_unit'), 'authority class');
    need(plan.sourceRoot === B && anchor.sourceRoot === B && isRootIdentity(plan.sourceIdentity)
      && same(plan.sourceIdentity, anchor.sourceIdentity) && same(rootIdentity(await safeRoot(B)), plan.sourceIdentity), 'source root binding');
    need(isRootIdentity(plan.phaseIdentity) && same(rootIdentity(await safeRoot(plan.phaseRoot)), plan.phaseIdentity)
      && plan.phaseRoot !== B && !plan.phaseRoot.startsWith(B + '/') && !B.startsWith(plan.phaseRoot + '/'), 'runtime/source separation');
    need(hash(plan.controlsSha256) && plan.controlsSha256 === anchor.controlsSha256
      && hash(plan.phaseSha256) && plan.phaseSha256 === anchor.phaseSha256, 'plan/control/phase pins');
    need(plan.allocationSha256 === anchor.allocationSha256
      && ((plan.kind === 'paid_outline' && plan.authority === 'paid_outline_once' && hash(plan.allocationSha256))
        || (plan.kind === 'qualification_pair' && plan.authority === 'qualification_pair_once' && hash(plan.allocationSha256))
        || (plan.kind === 'handoff_proof_only' && !['paid_outline_once','qualification_pair_once'].includes(plan.authority) && plan.allocationSha256 === null)),
      'proof/paid allocation authority substitution');
    const controlRaw = await read(B + '/source-controls.json');
    need(controlRaw.sha256 === plan.controlsSha256, 'source controls hash'); controls = parse(controlRaw.raw);
    keys(controls, ['version', 'kind', 'sourceRoot', 'sourceIdentity', 'sourceRevision', 'sourceTree', 'files', 'registry',
      'builtinImports', 'capsuleSourceSha256', 'helperExportSha256']);
    need(controls.version === 3 && controls.kind === 'capsule_source_controls.v3' && controls.sourceRoot === B
      && same(controls.sourceIdentity, plan.sourceIdentity) && same(controls.registry, registry)
      && same(controls.builtinImports, moduleIdentity.builtinImports)
      && controls.capsuleSourceSha256 === anchor.capsuleSha256 && controls.files['node_helper.mjs'] === anchor.helperSha256
      && controls.helperExportSha256 === sha(Function.prototype.toString.call(dispatch)), 'source controls contract');
    need(same((await fs.readdir(B)).sort(), [...Object.keys(controls.files), 'source-controls.json'].sort()), 'source closure inventory');
    for (const [name, expected] of Object.entries(controls.files)) {
      need(path.basename(name) === name && hash(expected) && (await read(B + '/' + name)).sha256 === expected, 'source closure drift: ' + name);
    }
    qa = JSON.parse((await read(B + '/qa-interpreter.json')).raw);
    need(qa.kind === 'plotloom.qa-project-interpreter.v1' && typeof qa.projectRoot === 'string'
      && path.isAbsolute(qa.projectRoot) && typeof qa.entrypoint === 'string' && path.isAbsolute(qa.entrypoint)
      && same(qa.majorMinor, [3, 12]) && qa.implementation === 'cpython', 'checked QA pin contract');
    R = qa.projectRoot;
    for (const [name, expected] of Object.entries(qa.identities)) {
      need(path.isAbsolute(name) && !/[\n\r\0]/.test(name), 'QA identity path');
      const actual = await fs.lstat(name);
      if (expected.kind === 'symlink') need(actual.isSymbolicLink() && await fs.readlink(name) === expected.target, 'QA alias drift');
      else { const value = await read(name, false); need(expected.kind === 'regular' && value.sha256 === expected.sha256
        && value.raw.length === expected.bytes, 'QA binary/config drift'); }
    }
    const descriptor = await read(plan.phaseRoot + '/phase.json');
    need(descriptor.sha256 === plan.phaseSha256, 'phase hash'); phase = parse(descriptor.raw);
    keys(phase, ['version', 'kind', 'authority', 'phaseRoot', 'rootIdentity', 'sourceRoot', 'sourceIdentity', 'namespace', 'nonce',
      'sourceRevision', 'sourceTree', 'controlsSha256', 'capsuleSha256', 'helperSha256', 'qaPinSha256', 'allocationSha256', 'entryArgvTemplate', 'settlementAuthority']);
    need(phase.version === 3 && Object.hasOwn(registry, phase.kind) && phase.kind === plan.kind && phase.authority === plan.authority
      && phase.phaseRoot === plan.phaseRoot && same(phase.rootIdentity, plan.phaseIdentity)
      && phase.sourceRoot === B && same(phase.sourceIdentity, plan.sourceIdentity)
      && phase.namespace === path.basename(plan.phaseRoot) && phase.namespace === plan.namespace
      && typeof phase.nonce === 'string' && /^[a-z0-9-]{16,100}$/.test(phase.nonce) && phase.nonce === plan.nonce
      && typeof phase.sourceRevision === 'string' && /^[a-f0-9]{40}$/.test(phase.sourceRevision)
      && typeof phase.sourceTree === 'string' && /^[a-f0-9]{40}$/.test(phase.sourceTree)
      && controls.sourceRevision === phase.sourceRevision && controls.sourceTree === phase.sourceTree
      && phase.controlsSha256 === plan.controlsSha256 && phase.capsuleSha256 === anchor.capsuleSha256
      && phase.helperSha256 === anchor.helperSha256 && phase.qaPinSha256 === controls.files['qa-interpreter.json']
      && phase.allocationSha256 === plan.allocationSha256
      && phase.settlementAuthority === (phase.kind === 'handoff_proof_only' ? 'none' : 'hold_only'), 'descriptor binding');
    need(Object.hasOwn(controls.files, registry[phase.kind]), 'actual registered entry unavailable');
    const ownerSource = parse((await read(B + '/source-identity.json')).raw);
    keys(ownerSource, ['version','kind','repositoryRoot','revision','tree','files','closureSha256','committed']);
    need(ownerSource.version === 1 && ownerSource.kind === 'plotloom.handoff-source.v1'
      && ownerSource.repositoryRoot === R && ownerSource.revision === phase.sourceRevision && ownerSource.tree === phase.sourceTree
      && hash(ownerSource.closureSha256) && ownerSource.closureSha256 === sha(bytes(ownerSource.files))
      && typeof ownerSource.committed === 'boolean', 'actual owner source manifest');
    if (phase.kind === 'qualification_pair') {
      need(ownerSource.committed === true && controls.files['pair-allocation.json'] === phase.allocationSha256, 'pair allocation/source pin');
      const raw = await read(B + '/pair-allocation.json'); need(raw.sha256 === phase.allocationSha256, 'pair allocation body drift');
      const a = parse(raw.raw);
      keys(a, ['version','authority','allocationId','nonce','workRoot','bundleRoot','phaseRoot','ownerMarker','source','validatorRuntime','inputs',
        'serial','parallel','textAttemptCeiling','imageOutputCeiling','retries','extraArms']);
      need(a.version === 'plotloom.qualification-pair-once.v1' && a.authority === 'qualification_pair_once' && a.nonce === phase.nonce
        && a.bundleRoot.path === B && a.phaseRoot.path === plan.phaseRoot && a.textAttemptCeiling === 18 && a.imageOutputCeiling === 64
        && a.retries === 0 && a.extraArms === 0 && a.source.revision === ownerSource.revision && a.source.tree === ownerSource.tree
        && a.validatorRuntime.qaPinSha256 === controls.files['qa-interpreter.json'], 'pair finite authority differs');
      need(same(rootIdentity(await safeRoot(a.workRoot.path)), [a.workRoot.device,a.workRoot.inode,a.workRoot.uid]), 'pair work identity');
      const expected = ['plan.json','prepared_inputs.json','preservation_inputs.json','current_source.json','serial/plan.json','parallel/plan.json'].map(n => a.workRoot.path + '/' + n);
      need(Array.isArray(a.inputs) && same(a.inputs.map(x => x.path).sort(), expected.sort()), 'pair fixed input inventory');
      need(a.ownerMarker.path === a.workRoot.path + '/owner.json', 'pair fixed owner marker');
      for (const file of [...a.inputs,a.ownerMarker]) {
        need(file.path.startsWith(a.workRoot.path + '/'), 'pair input escaped work root');
        const item = await read(file.path); need(item.sha256 === file.sha256 && item.raw.length === file.size
          && same(item.identity.slice(0,3), [file.device,file.inode,file.uid]), 'pair input changed');
      }
    }
    if (phase.kind === 'paid_outline') {
      need(ownerSource.committed === true && controls.files['paid-allocation.json'] === phase.allocationSha256,
        'paid committed source/allocation pin');
      const allocationFile = await read(B + '/paid-allocation.json');
      need(allocationFile.sha256 === phase.allocationSha256, 'paid allocation body drift');
      const a = parse(allocationFile.raw);
      keys(a, ['version','authority','allocationId','nonce','dataRoot','ownerMarker','bundleRoot','phaseRoot','projectHome',
        'projectManifest','projectDatabase','applicationDatabase','namespace','namespaceBindingSha256','source','validatorRuntime',
        'claimEdges','expectedCheckpointRevision','policyHash','briefHash','materialClosure','briefRevision','lifecycleRevision',
        'applicationEntries','initialAdmissions','imageAdmissions','retries','settlementAuthority','canonicalAdoption','laterStages']);
      const uuid = v => typeof v === 'string' && /^[a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12}$/.test(v);
      const positive = v => Number.isSafeInteger(v) && v > 0;
      const pathPin = (v, file = false) => {
        keys(v, ['path','device','inode','uid','mode', ...(file ? ['sha256','size'] : [])]);
        need(typeof v.path === 'string' && path.isAbsolute(v.path) && path.normalize(v.path) === v.path
          && Number.isSafeInteger(v.device) && v.device >= 0 && positive(v.inode) && v.uid === uid
          && Number.isSafeInteger(v.mode) && !(v.mode & 0o022) && v.mode <= 0o777, 'strict allocation path identity');
        if (file) need(hash(v.sha256) && positive(v.size), 'strict allocation file identity');
      };
      for (const key of ['dataRoot','bundleRoot','phaseRoot','projectHome','projectDatabase','applicationDatabase']) pathPin(a[key]);
      for (const key of ['ownerMarker','projectManifest']) pathPin(a[key], true);
      keys(a.source, ['revision','tree','workflowClosureSha256','bundleSourceIdentitySha256']);
      keys(a.validatorRuntime, ['root','interpreter','identityHash','qaPinSha256']);
      keys(a.claimEdges, ['pausedClaim','receiverClaim','pausedRevision','claimedRevision','resumedRevision']);
      const ns = a.namespace, edges = a.claimEdges;
      keys(ns, ['version','namespaceId','applicationRoot','outputsRoot','privateRoot','sourceRoot','database','executable','profile','limits','attempt']);
      for (const key of ['applicationRoot','outputsRoot','privateRoot','sourceRoot','database']) pathPin(ns[key]);
      pathPin(ns.executable, true);
      keys(ns.limits, ['maxProcesses','maxTextProcesses','maxImageProcesses','maxQueuedJobs']);
      need(Object.values(ns.limits).every(v => v === 1), 'one-attempt allocation limits');
      const job = ns.attempt;
      keys(job, ['attemptId','runId','projectId','jobId','operationKey','domain','requestHash','packageHash','profileHash',
        'plotloomCodeRevision','validationPlanHash','reservedImageOutputs','imageBudgetState','state','sessionId','processId',
        'processGroupId','processBirthIdentity','processExitCode','terminalResult','remoteToolState','evidenceHash','outputHash','remoteOutputHash']);
      const profileFields = ['backend','contractVersion','executableSha256','cliVersion','model','reasoningEffort','capabilities',
        'instructionHash','validatorHash','authenticationStore','permissionProfile','toolProfile','textValidatorRuntimeProfile',
        'maxRuntimeSeconds','maxEventBytes','maxOutputBytes','maxImageOutputs','maxProcesses','maxTextProcesses','maxImageProcesses',
        'maxQueuedJobs','apiFallback','externalMcpServers','nestedDispatch'];
      const hasCorrectionLimit = Object.hasOwn(ns.profile, 'textCorrectionLimit');
      keys(ns.profile, [...profileFields, ...(hasCorrectionLimit ? ['textCorrectionLimit'] : [])]);
      need(!hasCorrectionLimit || ns.profile.textCorrectionLimit === null || ns.profile.textCorrectionLimit === 1,
        'strict optional text correction limit');
      need(a.version === 'plotloom.paid-outline-once.v1' && a.authority === 'paid_outline_once' && uuid(a.allocationId)
        && ns.version === 'plotloom.exec-one-attempt.v1' && ns.namespaceId === a.allocationId && a.nonce === phase.nonce
        && a.initialAdmissions === 1 && a.imageAdmissions === 0 && a.retries === 0 && a.settlementAuthority === 'hold_only'
        && a.canonicalAdoption === false && a.laterStages === false && a.bundleRoot.path === B && a.phaseRoot.path === plan.phaseRoot
        && same([a.bundleRoot.device,a.bundleRoot.inode,a.bundleRoot.uid], plan.sourceIdentity)
        && same([a.phaseRoot.device,a.phaseRoot.inode,a.phaseRoot.uid], plan.phaseIdentity)
        && uuid(job.attemptId) && uuid(job.runId) && uuid(job.projectId) && job.operationKey === 'outline' && job.domain === 'text'
        && job.state === 'reserved' && job.reservedImageOutputs === 0 && job.imageBudgetState === 'none'
        && job.plotloomCodeRevision === ownerSource.revision && hash(job.validationPlanHash)
        && ['requestHash','packageHash','profileHash'].every(k => hash(job[k]))
        && ['sessionId','processId','processGroupId','processBirthIdentity','processExitCode','terminalResult',
          'remoteToolState','evidenceHash','outputHash','remoteOutputHash'].every(k => job[k] === null)
        && ns.profile.backend === 'codex_exec' && ns.profile.contractVersion === 'plotloom.codex-exec.v8'
        && job.profileHash === sha(stable(ns.profile)) && ns.profile.executableSha256 === ns.executable.sha256
        && ['maxProcesses','maxTextProcesses','maxImageProcesses','maxQueuedJobs'].every(k => ns.profile[k] === 1)
        && ns.profile.apiFallback === false && ns.profile.externalMcpServers === false && ns.profile.nestedDispatch === false
        && hash(a.namespaceBindingSha256) && hash(a.policyHash) && hash(a.briefHash) && hash(a.materialClosure)
        && positive(a.expectedCheckpointRevision) && positive(a.briefRevision) && positive(a.lifecycleRevision)
        && positive(edges.pausedRevision) && edges.claimedRevision === edges.pausedRevision + 1
        && edges.resumedRevision === edges.claimedRevision + 1 && /^[a-f0-9]{32}$/.test(edges.pausedClaim)
        && /^[a-f0-9]{32}$/.test(edges.receiverClaim) && edges.pausedClaim !== edges.receiverClaim
        && a.source.revision === ownerSource.revision && a.source.tree === ownerSource.tree
        && a.source.workflowClosureSha256 === ownerSource.closureSha256
        && a.source.bundleSourceIdentitySha256 === controls.files['source-identity.json']
        && a.validatorRuntime.qaPinSha256 === phase.qaPinSha256 && hash(a.validatorRuntime.identityHash)
        && a.validatorRuntime.interpreter !== qa.entrypoint && a.validatorRuntime.root !== qa.prefix
        && ns.sourceRoot.path === R && Array.isArray(a.applicationEntries) && a.applicationEntries.every(v => typeof v === 'string'),
        'strict paid allocation identity/permissions/revisions');
      need(ns.applicationRoot.path === path.join(a.dataRoot.path, 'application')
        && ns.outputsRoot.path === path.join(a.dataRoot.path, 'outputs') && ns.privateRoot.path === path.join(a.dataRoot.path, 'private')
        && path.dirname(a.projectHome.path) === ns.outputsRoot.path && a.ownerMarker.path === path.join(a.dataRoot.path, 'owner.json')
        && a.projectManifest.path === path.join(a.projectHome.path, 'project.json')
        && a.projectDatabase.path === path.join(a.projectHome.path, 'project.sqlite3')
        && a.applicationDatabase.path === path.join(ns.applicationRoot.path, 'application.sqlite3'), 'paid confined allocation paths');
    }
    const template = [qa.entrypoint, '-B', B + '/' + registry[phase.kind], '--phase-root', plan.phaseRoot, '--phase-sha', '@PHASE_SHA256@'];
    const argv = template.map(v => v === '@PHASE_SHA256@' ? plan.phaseSha256 : v);
    const execArgs = { cmd: argv.map(v => "'" + v.replace(/'/g, "'\\''") + "'").join(' '), workdir: R,
      shell: '/bin/zsh', login: false, yield_time_ms: 250, max_output_tokens: 1000 };
    need(same(phase.entryArgvTemplate, template) && same(plan.argv, argv) && plan.argvSha256 === sha(bytes(argv))
      && same(plan.execArgs, execArgs) && argv.every(v => !/[\n\r\0]/.test(v)), 'exact registered argv');
    const reply = data => ({ kind: 'capsule_handoff.v3', status: 'OK', action: request.action,
      anchorSha256: request.anchorSha, planSha256: anchor.planSha256, phaseSha256: plan.phaseSha256, ...data });
    if (request.action === 'capability') return reply({ capability: { ...moduleIdentity, sourceRoot: B,
      sourceIdentity: plan.sourceIdentity, controlsSha256: plan.controlsSha256, capsuleSha256: anchor.capsuleSha256,
      helperSha256: anchor.helperSha256, helperExportSha256: controls.helperExportSha256, argvSha256: plan.argvSha256 } });
    need(plan.authority !== 'capability_check', 'capability cannot create intent or dispatch');
    if (request.action === 'prepare') {
      await assertRoot(); need(same((await fs.readdir(plan.phaseRoot)).sort(), ['phase.json']), 'runtime already consumed or contaminated');
      const intentSha256 = await write('invocation-intent.json', bytes(intentValue()));
      await write('invocation-intent.json.ready-' + intentSha256, Buffer.alloc(0));
      return reply({ intentSha256, execArgs });
    }
    const records = await load();
    if (request.action === 'records') return reply({ observationCommand: 'ps -p ' + records.tree.value.launcher.pid + ','
      + records.tree.value.driver.pid + ' -o pid=,ppid=,pgid=,lstart=,command=' });
    if (request.action === 'validate') { payload(records, request.observationOutput); return reply({}); }
    if (request.action === 'publish') {
      const value = payload(records, request.observationOutput);
      const attendanceSha256 = await write('attendance.json', bytes(value)); gate(records.launch.value);
      await write('attendance.commit-' + attendanceSha256, Buffer.alloc(0)); gate(records.launch.value);
      return reply({ attendanceSha256 });
    }
    need(hash(request.attendanceSha256), 'invalid attendance pin');
    const accepted = await waitRecord('receiver-accepted.json', records.launch.value);
    const witness = accepted.value;
    const base = boundPayload(records);
    // Rebind committed records without constructing a process observation.
    const markers = (await fs.readdir(plan.phaseRoot)).filter(n => n.startsWith('attendance.commit-'));
    need(same(markers, ['attendance.commit-' + request.attendanceSha256]), 'attendance commit authority');
    const marker = await read(plan.phaseRoot + '/' + markers[0]);
    const attendance = await read(plan.phaseRoot + '/attendance.json');
    need(marker.raw.length === 0 && attendance.sha256 === request.attendanceSha256
      && same(parse(attendance.raw), base), 'committed attendance binding');
    need(same((await fs.readdir(plan.phaseRoot)).filter(n => n.startsWith('attendance.commit-')), markers)
      && same(marker.identity, fileIdentity(await fs.lstat(plan.phaseRoot + '/' + markers[0]))), 'attendance authority changed');
    delete base.observedTree;
    const witnessExpected = { ...base, sourceRoot: B, phaseRoot: plan.phaseRoot, attendanceSha256: request.attendanceSha256,
      productionAuthority: false, providerAuthority: false, syntheticEvidence: plan.authority === 'synthetic_unit' };
    keys(witness, [...Object.keys(witnessExpected), 'acceptedMonotonicNs', 'deadlineMonotonicNs']);
    need(same(Object.fromEntries(Object.keys(witnessExpected).map(k => [k, witness[k]])), witnessExpected)
      && typeof witness.acceptedMonotonicNs === 'string' && /^[1-9][0-9]*$/.test(witness.acceptedMonotonicNs)
      && typeof witness.deadlineMonotonicNs === 'string' && /^[1-9][0-9]*$/.test(witness.deadlineMonotonicNs)
      && BigInt(witness.deadlineMonotonicNs) === BigInt(records.launch.value.startedMonotonicNs) + 60000000000n
      && BigInt(witness.acceptedMonotonicNs) >= BigInt(records.launch.value.startedMonotonicNs)
      && BigInt(witness.acceptedMonotonicNs) < BigInt(witness.deadlineMonotonicNs), 'committed witness authority');
    gate(records.launch.value);
    return reply({ witness });
  } catch (error) {
    return { kind: 'capsule_handoff.v3', status: 'HELD', action: request.action,
      anchorSha256: request.anchorSha ?? null, phaseSha256: plan?.phaseSha256 ?? null,
      reason: String(error?.message ?? error) };
  }
}
