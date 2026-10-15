export const Capsule = async function Capsule(tools, planText, anchorText, anchorSha) {
  // The named expression's internal identity cannot be replaced by an outer
  // source-string claim. Host/tools/Function.prototype remain trusted assumptions.
  const capsuleSource = Function.prototype.toString.call(Capsule);
  const bootstrap = String.raw`async function checkedAction(request) {
    const fs = await import('node:fs/promises');
    const { constants: C } = await import('node:fs');
    const crypto = await import('node:crypto');
    const os = await import('node:os');
    const path = await import('node:path');
    const B = '@SEALED_BUNDLE_ROOT@';
    const sha = value => crypto.createHash('sha256').update(value).digest('hex');
    const need = (v, message) => { if (!v) throw Error(message); };
    const stable = v => {
      if (typeof v === 'number') need(Number.isSafeInteger(v), 'unsafe JSON number');
      return Array.isArray(v) ? '[' + v.map(stable).join(',') + ']' : v && typeof v === 'object'
        ? '{' + Object.keys(v).sort().map(k => JSON.stringify(k) + ':' + stable(v[k])).join(',') + '}' : JSON.stringify(v);
    };
    const parse = text => { const v = JSON.parse(text); need(Buffer.from(stable(v) + '\n').equals(Buffer.from(text)), 'noncanonical JSON'); return v; };
    const keys = (v, list) => need(v && !Array.isArray(v) && stable(Object.keys(v).sort()) === stable(list.sort()), 'unexpected fields');
    const identity = s => [s.dev, s.ino, s.uid, s.mode, s.nlink, s.size, String(s.mtimeMs), String(s.ctimeMs)];
    const root = async p => {
      need(typeof p === 'string' && path.isAbsolute(p) && path.normalize(p) === p, 'absolute source root');
      let at = '/';
      for (const name of p.split('/').filter(Boolean)) { at = path.join(at, name); const s = await fs.lstat(at); need(s.isDirectory() && !s.isSymbolicLink(), 'linked ancestor'); }
      const s = await fs.lstat(p); need(s.uid === os.userInfo().uid && (s.mode & 0o777) === 0o700, 'source ownership');
      return [s.dev, s.ino, s.uid];
    };
    const read = async p => {
      const before = await fs.lstat(p);
      need(before.isFile() && !before.isSymbolicLink() && before.uid === os.userInfo().uid && before.nlink === 1
        && (before.mode & 0o777) === 0o600 && before.size <= 1000000, 'unsafe source file');
      const fd = await fs.open(p, C.O_RDONLY | C.O_NOFOLLOW | C.O_NONBLOCK);
      try {
        need(stable(identity(before)) === stable(identity(await fd.stat())), 'source open identity');
        const raw = await fd.readFile();
        need(raw.length <= 1000000 && stable(identity(before)) === stable(identity(await fd.stat()))
          && stable(identity(before)) === stable(identity(await fs.lstat(p))), 'source read identity');
        return { raw, sha256: sha(raw), identity: identity(before) };
      } finally { await fd.close(); }
    };
    try {
      need(typeof request.anchorSha === 'string' && /^[a-f0-9]{64}$/.test(request.anchorSha)
        && typeof request.anchorText === 'string' && sha(request.anchorText) === request.anchorSha, 'independent anchor pin');
      const a = parse(request.anchorText);
      keys(a, ['version','kind','authority','sourceRoot','sourceIdentity','capsuleSha256','planSha256','controlsSha256','helperSha256','phaseSha256','allocationSha256']);
      need(a.version === 3 && a.kind === 'capsule_plan_anchor.v3' && a.sourceRoot === B
        && sha(request.capsuleSource) === a.capsuleSha256 && sha(request.planText) === a.planSha256, 'capsule/plan identity');
      const p = parse(request.planText);
      keys(p, ['version','authority','kind','sourceRoot','sourceIdentity','controlsSha256','phaseRoot','phaseIdentity','phaseSha256','allocationSha256','namespace','nonce','argv','argvSha256','execArgs']);
      need(p.version === 3 && ['capability_check','synthetic_unit','provider_free_handoff','paid_outline_once'].includes(p.authority)
        && a.authority === p.authority && p.sourceRoot === B && p.controlsSha256 === a.controlsSha256
        && p.phaseSha256 === a.phaseSha256 && p.allocationSha256 === a.allocationSha256
        && stable(p.sourceIdentity) === stable(a.sourceIdentity), 'plan binding');
      const controlsFile = await read(B + '/source-controls.json');
      need(controlsFile.sha256 === a.controlsSha256, 'controls pin'); const controls = parse(controlsFile.raw.toString('utf8'));
      keys(controls, ['version','kind','sourceRoot','sourceIdentity','sourceRevision','sourceTree','files','registry','builtinImports','capsuleSourceSha256','helperExportSha256']);
      const builtins = ['node:fs/promises','node:fs','node:crypto','node:os','node:path','node:url'];
      need(controls.version === 3 && controls.kind === 'capsule_source_controls.v3' && controls.sourceRoot === B
        && stable(controls.sourceIdentity) === stable(a.sourceIdentity) && controls.capsuleSourceSha256 === a.capsuleSha256
        && controls.files['node_helper.mjs'] === a.helperSha256 && stable(controls.builtinImports) === stable(builtins), 'controls contract');
      const allowed = ['capsule.mjs','node_helper.mjs','handoff_files.py','handoff_phase.py','handoff_receiver.py','handoff_process.py','handoff_qa.py',
        'proof_launch.py','proof_receiver.py','qa-interpreter.json','paid_launch.py','paid_receiver.py','handoff_launch.py','handoff_plan.py',
        'handoff_source.py','source-identity.json','paid-allocation.json','paid_outline_contracts.py','paid_outline_prepare.py',
        'paid_outline_run.py','paid_outline_state.py','paid_outline_composition.py'];
      const closure = async () => {
        need(stable(await root(B)) === stable(a.sourceIdentity), 'source root identity');
        need(stable((await fs.readdir(B)).sort()) === stable([...Object.keys(controls.files),'source-controls.json'].sort()), 'source inventory');
        const pins = { 'source-controls.json': await read(B + '/source-controls.json') };
        need(pins['source-controls.json'].sha256 === a.controlsSha256, 'controls drift');
        for (const [name, expected] of Object.entries(controls.files)) {
          need(allowed.includes(name) && /^[a-f0-9]{64}$/.test(expected), 'undeclared source');
          pins[name] = await read(B + '/' + name); need(pins[name].sha256 === expected, 'source drift');
        }
        return Object.fromEntries(Object.entries(pins).map(([name, v]) => [name, v.identity]));
      };
      const before = await closure();
      const module = await import('file://@SEALED_BUNDLE_ROOT@/node_helper.mjs');
      need(stable(before) === stable(await closure()), 'source changed during import');
      need(module.moduleIdentity.origin === 'file://@SEALED_BUNDLE_ROOT@/node_helper.mjs'
        && stable(module.moduleIdentity.builtinImports) === stable(builtins)
        && typeof module.dispatch === 'function' && sha(Function.prototype.toString.call(module.dispatch)) === controls.helperExportSha256, 'module export/origin');
      const reply = await module.dispatch(request);
      need(stable(before) === stable(await closure()), 'source changed during action');
      return { ...reply, verification: { moduleOrigin: module.moduleIdentity.origin,
        evaluationId: module.moduleIdentity.evaluationId, sourceControlsSha256: a.controlsSha256, sourceRootIdentity: a.sourceIdentity } };
    } catch (error) { return { kind: 'capsule_handoff.v3', status: 'HELD', action: request.action,
      anchorSha256: request.anchorSha, reason: String(error?.message ?? error) }; }
  }`;
  let original = null, observation = null, publicationPossible = false, intentPossible = false;
  const evidence = [], actionVerifications = [];
  const fail = message => { throw Error(message); };
  const hash = v => typeof v === 'string' && /^[a-f0-9]{64}$/.test(v);
  const native = (value, label) => {
    if (!value || typeof value !== 'object' || (value.isError !== undefined && value.isError !== false)
      || typeof value.output !== 'string' || (value.chunk_id !== undefined && typeof value.chunk_id !== 'string')) fail(label + ': malformed native result');
    const running = Number.isSafeInteger(value.session_id) && value.session_id > 0;
    const terminal = Number.isInteger(value.exit_code);
    if (running === terminal) fail(label + ': unknown native state');
    return { running, terminal };
  };
  let plan, anchor;
  const helper = async (action, data = {}) => {
    const request = { action, capsuleSource, planText, anchorText, anchorSha, ...data };
    // This is fixed reviewed tool code plus JSON data. No file contents become
    // executable text; the only file module is the literal ordinary import above.
    const code = 'var capsuleReply = await (' + bootstrap + ')(' + JSON.stringify(request) + '); nodeRepl.write(JSON.stringify(capsuleReply));';
    const raw = await tools.mcp__node_repl__js({ code, timeout_ms: 55000, title: 'Capsule ' + action });
    evidence.push({ action, raw });
    if (!raw || (raw.isError !== undefined && raw.isError !== false) || !Array.isArray(raw.content)
      || raw.content.length !== 1 || raw.content[0].type !== 'text' || typeof raw.content[0].text !== 'string') fail(action + ': tool failure');
    let value; try { value = JSON.parse(raw.content[0].text); } catch { fail(action + ': malformed JSON'); }
    if (!value || value.kind !== 'capsule_handoff.v3' || value.status !== 'OK' || value.action !== action
      || value.anchorSha256 !== anchorSha || value.planSha256 !== anchor.planSha256 || value.phaseSha256 !== plan.phaseSha256) fail(action + ': rejected or unbound reply');
    const fields = ['kind','status','action','anchorSha256','planSha256','phaseSha256','verification'];
    const v = value.verification;
    if (!v || Object.keys(v).sort().join('|') !== ['moduleOrigin','evaluationId','sourceControlsSha256','sourceRootIdentity'].sort().join('|')
      || v.moduleOrigin !== 'file://@SEALED_BUNDLE_ROOT@/node_helper.mjs'
      || typeof v.evaluationId !== 'string' || !v.evaluationId || v.sourceControlsSha256 !== anchor.controlsSha256
      || JSON.stringify(v.sourceRootIdentity) !== JSON.stringify(anchor.sourceIdentity)) fail('module verification binding');
    if (action === 'capability') { fields.push('capability'); if (!value.capability || value.capability.capsuleSha256 !== anchor.capsuleSha256) fail('capability identity'); }
    else if (action === 'prepare') {
      fields.push('intentSha256','execArgs');
      if (!hash(value.intentSha256) || !value.execArgs || typeof value.execArgs !== 'object'
        || Object.keys(value.execArgs).sort().join('|') !== Object.keys(plan.execArgs).sort().join('|')
        || Object.keys(plan.execArgs).some(key => value.execArgs[key] !== plan.execArgs[key])) fail('exact prepared command');
    } else if (action === 'records') {
      fields.push('observationCommand');
      if (typeof value.observationCommand !== 'string' || !/^ps -p [1-9]\d*,[1-9]\d* -o pid=,ppid=,pgid=,lstart=,command=$/.test(value.observationCommand)) fail('malformed observation command');
    } else if (action === 'publish') { fields.push('attendanceSha256'); if (!hash(value.attendanceSha256)) fail('missing committed hash'); }
    else if (action === 'witness') {
      fields.push('witness');
      if (!value.witness || value.witness.phaseSha256 !== plan.phaseSha256 || value.witness.nativeExecHandle !== original
        || value.witness.anchorSha256 !== anchorSha || value.witness.planSha256 !== anchor.planSha256
        || value.witness.argvSha256 !== plan.argvSha256 || value.witness.allocationSha256 !== plan.allocationSha256) fail('unbound witness');
    }
    if (Object.keys(value).sort().join('|') !== fields.sort().join('|')) fail(action + ': unexpected reply fields');
    // Authority is checked independently on every action; instance IDs diagnose
    // host evaluation lifetime and do not substitute for pinned source checks.
    actionVerifications.push({ action, ...v });
    return value;
  };
  try {
    if (typeof planText !== 'string' || typeof anchorText !== 'string' || !hash(anchorSha)) fail('trusted invocation data required');
    // These objects cannot select code or dispatch. The Node verifier accepts
    // their exact canonical bytes and independent pin before any intent.
    plan = JSON.parse(planText); anchor = JSON.parse(anchorText);
    if (plan.authority === 'capability_check') {
      const first = await helper('capability');
      const second = await helper('capability');
      return { status: 'CAPABILITY_VERIFIED', evidenceClass: 'capability_check', capabilities: [first.capability, second.capability], actionVerifications,
        qualification: false, nativeDispatches: 0, invocationIntentCreated: false, retryAuthorized: false, evidence };
    }
    intentPossible = true;
    const ready = await helper('prepare');
    const launched = await tools.exec_command(ready.execArgs);
    evidence.push({ action: 'native_launch', raw: launched });
    if (Number.isSafeInteger(launched?.session_id) && launched.session_id > 0) original = launched.session_id;
    const state = native(launched, 'launch');
    if (state.terminal) return { status: 'TERMINAL_WITHOUT_HANDOFF', evidenceClass: plan.authority, originalHandle: null, terminal: launched,
      qualification: false, retryAuthorized: false, invocationMayBeConsumed: true, actionVerifications, evidence };
    const records = await helper('records', { originalHandle: original });
    const observed = await tools.exec_command({ cmd: records.observationCommand, workdir: ready.execArgs.workdir,
      shell: '/bin/zsh', login: false, yield_time_ms: 1000, max_output_tokens: 2000 });
    evidence.push({ action: 'process_observation', raw: observed });
    if (Number.isSafeInteger(observed?.session_id) && observed.session_id > 0) observation = observed.session_id;
    const observedState = native(observed, 'observation');
    if (observedState.running || observed.exit_code !== 0) fail('observation lacks terminal identity proof');
    await helper('validate', { originalHandle: original, observationOutput: observed.output });
    publicationPossible = true;
    const committed = await helper('publish', { originalHandle: original, observationOutput: observed.output });
    const accepted = await helper('witness', { originalHandle: original, attendanceSha256: committed.attendanceSha256 });
    if (accepted.witness.attendanceSha256 !== committed.attendanceSha256) fail('wrong committed attendance');
    return { status: 'RECEIVER_ACCEPTED', evidenceClass: plan.authority, originalHandle: original, observationHandle: null,
      witness: accepted.witness, qualification: false, nativeTerminalObserved: false, retryAuthorized: false,
      reporting: 'Original attached; natural native terminal and phase reconciliation remain pending.', actionVerifications, evidence };
  } catch (error) {
    return { status: publicationPossible ? 'POSSIBLY_COMMITTED_UNKNOWN' : 'HELD', evidenceClass: plan?.authority ?? 'unverified', originalHandle: original,
      observationHandle: observation, reason: String(error?.message ?? error), qualification: false,
      invocationMayBeConsumed: intentPossible, retryAuthorized: false, admission: 'not inferred',
      reporting: 'Preserve state and attend genuine known handles; no retry or completion inferred.', actionVerifications, evidence };
  }
};
