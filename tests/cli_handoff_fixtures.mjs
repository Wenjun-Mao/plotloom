import fs from 'node:fs/promises';
import path from 'node:path';
import crypto from 'node:crypto';

// Only the unit harness accepts these fixture paths. Production capsule source
// is bound once by the owned bundle builder; no runtime plan can select a URI.
export const B = process.env.PLOTLOOM_HANDOFF_TEST_BUNDLE;
export const G = process.env.PLOTLOOM_HANDOFF_TEST_ROOT;
if (!B || !G || !path.isAbsolute(B) || !path.isAbsolute(G)) throw Error('run through the repository pytest entrypoint');
export const QA = JSON.parse(await fs.readFile(B + '/qa-interpreter.json', 'utf8'));
export const R = QA.projectRoot;
export const { dispatch, moduleIdentity } = await import(B + '/node_helper.mjs');
export const { Capsule } = await import(B + '/capsule.mjs');
export const sha = v => crypto.createHash('sha256').update(v).digest('hex');
export const stable = v => Array.isArray(v) ? '[' + v.map(stable).join(',') + ']'
  : v && typeof v === 'object' ? '{' + Object.keys(v).sort().map(k => JSON.stringify(k) + ':' + stable(v[k])).join(',') + '}' : JSON.stringify(v);
export const raw = v => Buffer.from(stable(v) + '\n');
export async function exclusive(file, content) {
  const fd = await fs.open(file, 'wx', 0o600);
  try { await fd.writeFile(content); await fd.sync(); } finally { await fd.close(); }
}
export async function record(root, name, value) {
  const bytes = raw(value), hash = sha(bytes);
  await exclusive(root + '/' + name, bytes); await exclusive(root + '/' + name + '.ready-' + hash, '');
  return hash;
}

export async function fixture(authority = 'synthetic_unit') {
  const base = await fs.mkdtemp(G + '/node-'); await fs.chmod(base, 0o700);
  const bi = await fs.lstat(base);
  await exclusive(base + '/owner.json', raw({ evidenceClass: 'synthetic_unit_only', device: bi.dev, inode: bi.ino, uid: bi.uid }));
  const root = base + '/runtime'; await fs.mkdir(root, { mode: 0o700 });
  const ri = await fs.lstat(root), si = await fs.lstat(B);
  const controlsRaw = await fs.readFile(B + '/source-controls.json'), controls = JSON.parse(controlsRaw);
  const phase = { version: 3, kind: 'handoff_proof_only', authority, phaseRoot: root,
    rootIdentity: [ri.dev, ri.ino, ri.uid], sourceRoot: B, sourceIdentity: [si.dev, si.ino, si.uid], namespace: path.basename(root),
    nonce: 'synthetic-test-only-' + path.basename(base).toLowerCase(), sourceRevision: controls.sourceRevision,
    sourceTree: controls.sourceTree, controlsSha256: sha(controlsRaw),
    capsuleSha256: controls.capsuleSourceSha256, helperSha256: controls.files['node_helper.mjs'], qaPinSha256: controls.files['qa-interpreter.json'],
    entryArgvTemplate: [QA.entrypoint, '-B', B + '/proof_launch.py', '--phase-root', root, '--phase-sha', '@PHASE_SHA256@'],
    settlementAuthority: 'none', allocationSha256: null };
  let plan, anchor, planText, anchorText, anchorSha;
  const source = Function.prototype.toString.call(Capsule);
  const bind = async (mutatePlan = null) => {
    const phaseRaw = raw(phase);
    const phaseFile = root + '/phase.json';
    try { await fs.access(phaseFile); await fs.writeFile(phaseFile, phaseRaw); }
    catch (e) { if (e.code !== 'ENOENT') throw e; await exclusive(phaseFile, phaseRaw); }
    const phaseSha = sha(phaseRaw), argv = phase.entryArgvTemplate.map(v => v === '@PHASE_SHA256@' ? phaseSha : v);
    plan = { version: 3, authority: phase.authority, kind: phase.kind, sourceRoot: B, sourceIdentity: phase.sourceIdentity,
      controlsSha256: phase.controlsSha256, phaseRoot: root, phaseIdentity: phase.rootIdentity, phaseSha256: phaseSha,
      allocationSha256: phase.allocationSha256, namespace: phase.namespace, nonce: phase.nonce, argv, argvSha256: sha(raw(argv)),
      execArgs: { cmd: argv.map(v => "'" + v.replace(/'/g, "'\\''") + "'").join(' '), workdir: R,
        shell: '/bin/zsh', login: false, yield_time_ms: 250, max_output_tokens: 1000 } };
    if (mutatePlan) mutatePlan(plan);
    planText = raw(plan).toString();
    anchor = { version: 3, kind: 'capsule_plan_anchor.v3', authority: plan.authority, sourceRoot: B,
      sourceIdentity: phase.sourceIdentity, capsuleSha256: phase.capsuleSha256, planSha256: sha(planText),
      controlsSha256: plan.controlsSha256, helperSha256: phase.helperSha256,
      phaseSha256: plan.phaseSha256, allocationSha256: phase.allocationSha256 };
    anchorText = raw(anchor).toString(); anchorSha = sha(anchorText);
  };
  await bind();
  const request = (action, data = {}) => ({ action, capsuleSource: source, planText, anchorText, anchorSha, ...data });
  const call = (action, data = {}, io = null) => dispatch(request(action, data), io);
  const verify = () => ({ moduleOrigin: moduleIdentity.origin, evaluationId: moduleIdentity.evaluationId,
    sourceControlsSha256: plan.controlsSha256, sourceRootIdentity: phase.sourceIdentity });
  let launch, tree, observation;
  const launchFixture = async () => {
    const intent = raw(JSON.parse(await fs.readFile(root + '/invocation-intent.json', 'utf8')));
    const execArgv = ['/opt/homebrew/bin/uv', 'run', '--locked', '--no-sync', 'python', '-B', B + '/proof_receiver.py',
      '--phase-root', root, '--phase-sha', plan.phaseSha256];
    launch = { pid: 100, pgid: 100, birthStart: 'Thu Oct 15 06:09:00 2026',
      startedWallMs: Date.now(), startedMonotonicNs: '1000000000', phaseSha256: plan.phaseSha256, intentSha256: sha(intent), execArgv };
    const commandA = execArgv.join(' '), commandB = [QA.allowedInnerExecutables[0], ...execArgv.slice(5)].join(' ');
    tree = { launcher: { pid: 100, ppid: 1, pgid: 100, birthStart: launch.birthStart, commandSha256: sha(commandA) },
      driver: { pid: 101, ppid: 100, pgid: 100, birthStart: launch.birthStart, commandSha256: sha(commandB) },
      launchSha256: await record(root, 'launch.json', launch) };
    await record(root, 'driver-process.json', tree);
    observation = '100 1 100 ' + launch.birthStart + ' ' + commandA + '\n101 100 100 ' + launch.birthStart + ' ' + commandB + '\n';
    return { launch, tree, observation };
  };
  const syntheticWitness = async mutate => {
    const attendanceRaw = await fs.readFile(root + '/attendance.json'); const value = JSON.parse(attendanceRaw);
    const witness = { ...value }; delete witness.observedTree;
    Object.assign(witness, { sourceRoot: B, phaseRoot: root, attendanceSha256: sha(attendanceRaw),
      acceptedMonotonicNs: '1001000000', deadlineMonotonicNs: '61000000000', productionAuthority: false,
      providerAuthority: false, syntheticEvidence: true });
    if (mutate) mutate(witness);
    await record(root, 'receiver-accepted.json', witness);
  };
  const tools = (faults = {}) => {
    const calls = []; let nativeCount = 0;
    return { calls,
      mcp__node_repl__js: async args => {
        const mark = '\n  })('; const start = args.code.lastIndexOf(mark);
        if (start < 0) throw Error('unexpected bootstrap shape');
        const suffix = '); nodeRepl.write(JSON.stringify(capsuleReply));';
        if (!args.code.endsWith(suffix)) throw Error('unexpected tool suffix');
        const req = JSON.parse(args.code.slice(start + mark.length, -suffix.length));
        if (req.capsuleSource !== source) throw Error('capsule did not inspect its actual source');
        calls.push(req.action);
        if (req.action === 'witness' && !faults.noWitness) await syntheticWitness(faults.witness);
        if (faults.throwAction === req.action) throw Error('synthetic tool rejection');
        if (faults.request) faults.request(req);
        const io = typeof faults.io === 'function' ? faults.io(req.action) : faults.io;
        let value = await dispatch(req, io ?? null);
        value = { ...value, verification: verify() };
        if (faults.reply) value = faults.reply(value, req.action);
        return { content: [{ type: 'text', text: JSON.stringify(value) }] };
      },
      exec_command: async args => {
        nativeCount++; calls.push(nativeCount === 1 ? 'FAKE_native_launch' : 'FAKE_process_observation');
        if (nativeCount === 1) {
          if (faults.launch) return faults.launch;
          await launchFixture(); return { output: '', chunk_id: 'synthetic-only', session_id: 42 };
        }
        if (args.cmd !== 'ps -p 100,101 -o pid=,ppid=,pgid=,lstart=,command=') throw Error('wrong observation request');
        return faults.observation ?? { output: observation, exit_code: 0 };
      } };
  };
  return { base, root, phase, bind, request, call, tools, launchFixture, syntheticWitness, verify, source,
    get plan() { return plan; }, get anchor() { return anchor; }, get planText() { return planText; },
    get anchorText() { return anchorText; }, get anchorSha() { return anchorSha; },
    get observation() { return observation; }, get launch() { return launch; }, get tree() { return tree; } };
}

export function faultIO(c, fault) {
  const io = { ...fs };
  io.open = async (file, ...args) => {
    const fd = await fs.open(file, ...args), name = path.basename(file);
    return { stat: () => fd.stat(), close: () => fd.close(),
      readFile: async () => {
        const value = await fd.readFile();
        if (fault === 'second-record-marker' && name === 'launch.json') {
          await exclusive(c.root + '/launch.json.ready-' + '0'.repeat(64), '');
        }
        if (fault === 'second-attendance-marker' && name === 'attendance.json') {
          await exclusive(c.root + '/attendance.commit-' + '0'.repeat(64), '');
        }
        if (fault === 'readback' && name === 'attendance.json') return Buffer.from('changed');
        if (fault === 'controls' && name === 'source-controls.json') return Buffer.from('{}\n');
        if (fault === 'closure' && name === 'proof_receiver.py') return Buffer.from('# synthetic source drift\n');
        return value;
      },
      writeFile: async value => {
        if (fault === 'partial' && name === 'attendance.json') { await fd.writeFile('{'); throw Error('synthetic partial write'); }
        return fd.writeFile(value);
      },
      sync: async () => {
        if ((fault === 'file-sync' && name === 'attendance.json') || (fault === 'directory-sync' && file === c.root)
          || (fault === 'after-marker' && name.startsWith('attendance.commit-'))
          || (fault === 'intent-marker' && name.startsWith('invocation-intent.json.ready-'))) throw Error('synthetic sync fault');
        return fd.sync();
      } };
  };
  return { fs: io };
}
