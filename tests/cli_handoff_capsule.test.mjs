import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs/promises';
import { B, Capsule, dispatch, fixture, faultIO, raw, sha, stable, exclusive } from './cli_handoff_fixtures.mjs';

test('actual capsule source includes one fixed file import and no executable free loader', () => {
  const text = Function.prototype.toString.call(Capsule);
  assert.equal((text.match(/await import\('file:/g) ?? []).length, 1);
  assert.ok(text.includes("await import('file://" + B + "/node_helper.mjs')"));
  assert.ok(text.includes('Function.prototype.toString.call(Capsule)'));
  assert.doesNotMatch(text, /\beval\s*\(|new Function|import\(request\.|import\(plan\./);
});

test('capability scope verifies actual helper and capsule without intent or fake native calls', async () => {
  const c = await fixture('capability_check'), tools = c.tools();
  const result = await Capsule(tools, c.planText, c.anchorText, c.anchorSha);
  assert.equal(result.status, 'CAPABILITY_VERIFIED');
  assert.equal(result.nativeDispatches, 0); assert.equal(result.invocationIntentCreated, false);
  assert.deepEqual(tools.calls, ['capability','capability']); assert.deepEqual(await fs.readdir(c.root), ['phase.json']);
  assert.equal(result.capabilities.length, 2); assert.equal(result.actionVerifications.length, 2);
  assert.deepEqual(result.actionVerifications.map(v => v.action), ['capability','capability']);
  assert.equal((await c.call('prepare')).status, 'HELD');
});

test('canonical nested key order accepts exactly equivalent prepared command', async () => {
  const c = await fixture(), tools = c.tools();
  assert.notDeepEqual(Object.keys(JSON.parse(c.planText).execArgs), ['cmd','workdir','shell','login','yield_time_ms','max_output_tokens']);
  const result = await Capsule(tools, c.planText, c.anchorText, c.anchorSha);
  assert.equal(result.status, 'RECEIVER_ACCEPTED'); assert.equal(result.evidenceClass, 'synthetic_unit');
  assert.equal(result.qualification, false); assert.equal(result.nativeTerminalObserved, false);
  assert.equal(result.witness.syntheticEvidence, true); assert.equal(result.witness.providerAuthority, false);
  assert.deepEqual(tools.calls, ['prepare','FAKE_native_launch','records','FAKE_process_observation','validate','publish','witness']);
});

for (const scenario of ['capsule','anchor-pin','plan-bytes','anchor-self-claim']) {
  test('independent identity refusal: ' + scenario, async () => {
    const c = await fixture(), req = c.request('capability');
    if (scenario === 'capsule') req.capsuleSource += ' ';
    if (scenario === 'anchor-pin') req.anchorSha = '0'.repeat(64);
    if (scenario === 'plan-bytes') req.planText += ' ';
    if (scenario === 'anchor-self-claim') { const a = JSON.parse(req.anchorText); a.claimedAnchorSha = req.anchorSha; req.anchorText = raw(a).toString(); req.anchorSha = sha(req.anchorText); }
    assert.equal((await dispatch(req)).status, 'HELD'); assert.deepEqual(await fs.readdir(c.root), ['phase.json']);
  });
}

for (const scenario of ['extra-field','boolean-version','fractional-number','wrong-argv','shell','source-root','runtime-identity','nonce']) {
  test('canonical but invalid authoritative plan: ' + scenario, async () => {
    const c = await fixture();
    await c.bind(p => {
      if (scenario === 'extra-field') p.moduleURI = 'file:///unapproved';
      if (scenario === 'boolean-version') p.version = true;
      if (scenario === 'fractional-number') p.execArgs.yield_time_ms = 250.5;
      if (scenario === 'wrong-argv') p.argv[2] = c.root + '/launch.py';
      if (scenario === 'shell') p.execArgs.shell = '/bin/sh';
      if (scenario === 'source-root') p.sourceRoot += '-other';
      if (scenario === 'runtime-identity') p.phaseIdentity[1]++;
      if (scenario === 'nonce') p.nonce = 'other-synthetic-nonce';
    });
    assert.equal((await c.call('prepare')).status, 'HELD'); assert.deepEqual(await fs.readdir(c.root), ['phase.json']);
  });
}

for (const scenario of ['whitespace','duplicate']) {
  test('plan exact canonical bytes refuse ' + scenario, async () => {
    const c = await fixture(), req = c.request('prepare'), a = JSON.parse(c.anchorText);
    req.planText = scenario === 'whitespace' ? c.planText + ' ' : c.planText.replace('"version":3', '"version":3,"version":3');
    a.planSha256 = sha(req.planText); req.anchorText = raw(a).toString(); req.anchorSha = sha(req.anchorText);
    assert.equal((await dispatch(req)).status, 'HELD');
  });
}

test('actual registered paid entry refuses proof authority substitution', async () => {
  const c = await fixture(); c.phase.kind = 'paid_outline'; c.phase.settlementAuthority = 'hold_only';
  c.phase.entryArgvTemplate[2] = B + '/paid_launch.py'; await c.bind();
  const result = await c.call('prepare'); assert.equal(result.status, 'HELD');
  assert.match(result.reason, /proof\/paid allocation authority substitution/);
  assert.equal((await fs.readdir(B)).includes('paid_launch.py'), true);
});

test('entry inside runtime remains refused despite matching plan bytes', async () => {
  const c = await fixture(); c.phase.entryArgvTemplate[2] = c.root + '/launch.py'; await c.bind();
  assert.match((await c.call('prepare')).reason, /registered argv/);
});

test('runtime contamination refuses before exclusive intent', async () => {
  const c = await fixture(); await exclusive(c.root + '/unowned-extra', '');
  assert.match((await c.call('prepare')).reason, /consumed or contaminated/);
  assert.equal((await fs.readdir(c.root)).includes('invocation-intent.json'), false);
});

test('source controls drift refuses without changing immutable source', async () => {
  const c = await fixture(); assert.match((await c.call('prepare', {}, faultIO(c, 'controls'))).reason, /controls hash/);
});

test('legitimate fractional filesystem timestamps retain full stat representation', async () => {
  const c = await fixture(), io = { ...fs };
  const adjusted = s => Object.assign(Object.create(Object.getPrototypeOf(s)), s, { mtimeMs: 1234.125, ctimeMs: 5678.875 });
  io.lstat = async p => adjusted(await fs.lstat(p));
  io.open = async (...args) => { const fd = await fs.open(...args); return { close: () => fd.close(),
    stat: async () => adjusted(await fd.stat()), readFile: () => fd.readFile(), writeFile: v => fd.writeFile(v), sync: () => fd.sync() }; };
  assert.equal((await c.call('capability', {}, { fs: io })).status, 'OK');
});

test('fractional timestamp drift during descriptor read is refused', async () => {
  const c = await fixture(), io = { ...fs }; let checks = 0;
  io.open = async (...args) => { const fd = await fs.open(...args); return { close: () => fd.close(),
    stat: async () => { const s = await fd.stat(); if (args[0].endsWith('/phase.json') && ++checks === 2)
      return Object.assign(Object.create(Object.getPrototypeOf(s)), s, { mtimeMs: s.mtimeMs + 0.125 }); return s; },
    readFile: () => fd.readFile(), writeFile: v => fd.writeFile(v), sync: () => fd.sync() }; };
  assert.match((await c.call('prepare', {}, { fs: io })).reason, /read identity changed/);
});

test('uncertain intent commit consumes attempt without authorizing retry', async () => {
  const c = await fixture(), tools = c.tools({ io: faultIO(c, 'intent-marker') });
  const result = await Capsule(tools, c.planText, c.anchorText, c.anchorSha);
  assert.equal(result.status, 'HELD'); assert.equal(result.invocationMayBeConsumed, true);
  assert.equal(result.retryAuthorized, false); assert.deepEqual(tools.calls, ['prepare']);
  assert.match((await c.call('prepare')).reason, /consumed or contaminated/);
});

for (const [scenario, value, original] of [
  ['contradictory', { output: '', session_id: 42, exit_code: 0 }, 42],
  ['tool error with handle', { output: '', session_id: 42, isError: true }, 42],
  ['missing output', { session_id: 42 }, 42],
  ['unknown', { output: '' }, null],
]) test('malformed original return preserves only genuine handle: ' + scenario, async () => {
  const c = await fixture(), tools = c.tools({ launch: value }); const result = await Capsule(tools, c.planText, c.anchorText, c.anchorSha);
  assert.equal(result.status, 'HELD'); assert.equal(result.originalHandle, original); assert.equal(result.retryAuthorized, false);
  assert.equal(tools.calls.includes('publish'), false);
});

test('direct terminal is not reported attached or qualified', async () => {
  const c = await fixture(), tools = c.tools({ launch: { output: '', exit_code: 0 } });
  const r = await Capsule(tools, c.planText, c.anchorText, c.anchorSha);
  assert.equal(r.status, 'TERMINAL_WITHOUT_HANDOFF'); assert.equal(r.originalHandle, null); assert.equal(r.qualification, false);
});

test('observation handle is separate and never substitutes original', async () => {
  const c = await fixture(), tools = c.tools({ observation: { output: '', session_id: 99 } });
  const r = await Capsule(tools, c.planText, c.anchorText, c.anchorSha);
  assert.equal(r.originalHandle, 42); assert.equal(r.observationHandle, 99); assert.equal(r.status, 'HELD');
  assert.equal(tools.calls.includes('publish'), false);
});

test('wrong actual process rows refuse publication', async () => {
  const c = await fixture(), tools = c.tools({ observation: { output: '100 1 100 wrong-row\n', exit_code: 0 } });
  const r = await Capsule(tools, c.planText, c.anchorText, c.anchorSha);
  assert.equal(r.status, 'HELD'); assert.equal(tools.calls.includes('publish'), false);
});

for (const fault of ['partial','file-sync','readback','after-marker']) test('publication uncertainty remains UNKNOWN: ' + fault, async () => {
  const c = await fixture(), tools = c.tools({ io: faultIO(c, fault) });
  const r = await Capsule(tools, c.planText, c.anchorText, c.anchorSha);
  assert.equal(r.status, 'POSSIBLY_COMMITTED_UNKNOWN'); assert.equal(r.originalHandle, 42);
  assert.equal(r.retryAuthorized, false); assert.equal(r.admission, 'not inferred');
});

test('tool rejection at publish is UNKNOWN before acknowledgement', async () => {
  const c = await fixture(), tools = c.tools({ throwAction: 'publish' }); const r = await Capsule(tools, c.planText, c.anchorText, c.anchorSha);
  assert.equal(r.status, 'POSSIBLY_COMMITTED_UNKNOWN'); assert.equal(r.retryAuthorized, false);
});

test('second record marker during actual read refuses attached records', async () => {
  const c = await fixture(), tools = c.tools({ io: faultIO(c, 'second-record-marker') });
  const r = await Capsule(tools, c.planText, c.anchorText, c.anchorSha);
  assert.equal(r.status, 'HELD'); assert.equal(tools.calls.includes('publish'), false);
});

test('witness wrong original/authority remains UNKNOWN and unqualified', async () => {
  const c = await fixture(), tools = c.tools({ witness: w => { w.nativeExecHandle = 99; } });
  const r = await Capsule(tools, c.planText, c.anchorText, c.anchorSha);
  assert.equal(r.status, 'POSSIBLY_COMMITTED_UNKNOWN'); assert.equal(r.qualification, false);
});

for (const different of [false, true]) test('synthetic capability actions retain diagnostic IDs, changed=' + different, async () => {
  const c = await fixture('capability_check'); let action = 0;
  const tools = c.tools({ reply: v => {
    action++;
    const id = different && action === 2 ? 'synthetic-second-evaluation' : 'synthetic-first-evaluation';
    v.verification.evaluationId = id; v.capability.evaluationId = id; return v;
  } });
  const r = await Capsule(tools, c.planText, c.anchorText, c.anchorSha);
  assert.equal(r.status, 'CAPABILITY_VERIFIED'); assert.equal(r.nativeDispatches, 0);
  assert.equal(r.invocationIntentCreated, false); assert.equal(r.evidence.length, 2);
  assert.deepEqual(r.actionVerifications.map(v => v.evaluationId),
    ['synthetic-first-evaluation', different ? 'synthetic-second-evaluation' : 'synthetic-first-evaluation']);
  assert.deepEqual(r.capabilities.map(v => v.evaluationId), r.actionVerifications.map(v => v.evaluationId));
  assert.deepEqual(tools.calls, ['capability','capability']); assert.deepEqual(await fs.readdir(c.root), ['phase.json']);
});

test('synthetic handoff accepts independently bound actions with distinct diagnostic IDs', async () => {
  const c = await fixture(); let action = 0;
  const tools = c.tools({ reply: v => { v.verification.evaluationId = 'synthetic-evaluation-' + ++action; return v; } });
  const r = await Capsule(tools, c.planText, c.anchorText, c.anchorSha);
  assert.equal(r.status, 'RECEIVER_ACCEPTED'); assert.equal(r.qualification, false);
  assert.deepEqual(r.actionVerifications.map(v => v.action), ['prepare','records','validate','publish','witness']);
  assert.equal(new Set(r.actionVerifications.map(v => v.evaluationId)).size, 5);
});

for (const id of ['', null, 42]) test('invalid diagnostic evaluation ID still refuses: ' + String(id), async () => {
  const c = await fixture('capability_check'), tools = c.tools({ reply: v => { v.verification.evaluationId = id; return v; } });
  const r = await Capsule(tools, c.planText, c.anchorText, c.anchorSha);
  assert.equal(r.status, 'HELD'); assert.match(r.reason, /module verification binding/);
  assert.deepEqual(tools.calls, ['capability']); assert.deepEqual(await fs.readdir(c.root), ['phase.json']);
});

for (const field of ['moduleOrigin','sourceControlsSha256','sourceRootIdentity']) test('source verification drift refuses even with equal IDs: ' + field, async () => {
  const c = await fixture(), tools = c.tools({ reply: (v, action) => {
    if (action === 'records') v.verification[field] = 'synthetic-wrong-binding'; return v;
  } });
  const r = await Capsule(tools, c.planText, c.anchorText, c.anchorSha);
  assert.equal(r.status, 'HELD'); assert.equal(r.originalHandle, 42); assert.equal(tools.calls.includes('publish'), false);
  const ids = r.evidence.filter(v => v.action === 'prepare' || v.action === 'records')
    .map(v => JSON.parse(v.raw.content[0].text).verification.evaluationId);
  assert.equal(ids.length, 2); assert.equal(ids[0], ids[1]);
});

for (const fault of ['capsule','anchor','plan','controls','closure']) test('per-action authority drift refuses even with equal IDs: ' + fault, async () => {
  const c = await fixture(), tools = c.tools({ request: req => {
    if (req.action !== 'records') return;
    if (fault === 'capsule') req.capsuleSource += ' ';
    if (fault === 'anchor') req.anchorSha = '0'.repeat(64);
    if (fault === 'plan') req.planText += ' ';
  }, io: action => action === 'records' && ['controls','closure'].includes(fault) ? faultIO(c, fault) : null });
  const r = await Capsule(tools, c.planText, c.anchorText, c.anchorSha);
  assert.equal(r.status, 'HELD'); assert.equal(r.originalHandle, 42); assert.equal(tools.calls.includes('publish'), false);
  const replies = r.evidence.filter(v => v.action === 'prepare' || v.action === 'records').map(v => JSON.parse(v.raw.content[0].text));
  assert.equal(replies.length, 2); assert.equal(replies[0].verification.evaluationId, replies[1].verification.evaluationId);
  assert.equal(replies[1].status, 'HELD'); assert.equal(r.actionVerifications.length, 1);
});

test('deadline spends original interval and never restarts while waiting records', async () => {
  const c = await fixture(); assert.equal((await c.call('prepare')).status, 'OK'); await c.launchFixture();
  const r = await c.call('records', { originalHandle: 42 }, { now: () => c.launch.startedWallMs + 60000 });
  assert.equal(r.status, 'HELD'); assert.match(r.reason, /attachment deadline/);
});
