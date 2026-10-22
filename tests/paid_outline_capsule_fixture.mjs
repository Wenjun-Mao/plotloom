// Synthetic external tools only; all capsule/helper code is the actual bundle.
import fs from 'node:fs/promises';
import { spawn } from 'node:child_process';
import crypto from 'node:crypto';
const [root, python, nativeFixture, source, mode] = process.argv.slice(2);
const B = root + '/bundle', F = root + '/phase';
const packet = JSON.parse(await fs.readFile(root + '/transport.json'));
const { Capsule } = await import(B + '/capsule.mjs');
const { dispatch, moduleIdentity } = await import(B + '/node_helper.mjs');
const plan = JSON.parse(packet.planText), anchor = JSON.parse(packet.anchorText);
const calls = []; let child, terminal, complete;
const tools = {
  mcp__node_repl__js: async args => {
    const mark = '\n  })(', suffix = '); nodeRepl.write(JSON.stringify(capsuleReply));';
    const start = args.code.lastIndexOf(mark);
    if (start < 0 || !args.code.endsWith(suffix)) throw Error('unexpected fixed bootstrap');
    const req = JSON.parse(args.code.slice(start + mark.length, -suffix.length));
    if (req.capsuleSource !== Function.prototype.toString.call(Capsule)) throw Error('capsule source drift');
    calls.push(req.action);
    const value = await dispatch(req);
    return { content: [{ type: 'text', text: JSON.stringify({ ...value, verification: {
      moduleOrigin: moduleIdentity.origin, evaluationId: moduleIdentity.evaluationId,
      sourceControlsSha256: anchor.controlsSha256, sourceRootIdentity: anchor.sourceIdentity } }) }] };
  },
  exec_command: async args => {
    if (!child) {
      if (Object.keys(args).sort().join('|') !== Object.keys(plan.execArgs).sort().join('|')
        || Object.keys(plan.execArgs).some(key => args[key] !== plan.execArgs[key])) throw Error('non-registered native command');
      calls.push(mode === 'pair-transport' ? 'SYNTHETIC_registered_pair_launch' : 'SYNTHETIC_registered_paid_launch');
      child = spawn(python, ['-B', nativeFixture, 'outer', '--case-root', root, '--source-root', source, '--mode', mode],
        { stdio: ['ignore', 'pipe', 'pipe'] });
      let output = '';
      child.stdout.on('data', chunk => { output += chunk; }); child.stderr.on('data', chunk => { output += chunk; });
      complete = new Promise((resolve, reject) => {
        child.on('error', reject);
        child.on('exit', code => { terminal = { code, output }; resolve(terminal); });
      });
      return { output: '', chunk_id: 'synthetic-source-test', session_id: 42 };
    }
    const launch = JSON.parse(await fs.readFile(F + '/launch.json'));
    const tree = JSON.parse(await fs.readFile(F + '/driver-process.json'));
    if (args.cmd !== `ps -p ${tree.launcher.pid},${tree.driver.pid} -o pid=,ppid=,pgid=,lstart=,command=`) throw Error('non-exact observation');
    calls.push('SYNTHETIC_process_observation');
    const qa = JSON.parse(await fs.readFile(B + '/qa-interpreter.json'));
    const commands = [launch.execArgv.join(' '), [qa.allowedInnerExecutables[0], ...launch.execArgv.slice(5)].join(' ')];
    const output = [tree.launcher, tree.driver].map((row, index) =>
      `${row.pid} ${row.ppid} ${row.pgid} ${row.birthStart} ${commands[index]}`).join('\n') + '\n';
    return { output, exit_code: 0 };
  }
};
let outcome;
if (mode === 'prepare-only') {
  calls.push('prepare');
  outcome = await dispatch({ action: 'prepare', capsuleSource: Function.prototype.toString.call(Capsule),
    planText: packet.planText, anchorText: packet.anchorText, anchorSha: packet.anchorSha256 });
} else outcome = await Capsule(tools, packet.planText, packet.anchorText, packet.anchorSha256);
if (complete) await complete;
const result = { syntheticEvidence: true, qualification: false, providerAuthority: false, productionAuthority: false,
  outcome, calls, actualFixtureChildTerminal: terminal ?? null,
  sourceSha256: crypto.createHash('sha256').update(Function.prototype.toString.call(Capsule)).digest('hex') };
try { result.driverLog = await fs.readFile(F + '/driver.log', 'utf8'); } catch (error) { if (error.code !== 'ENOENT') throw error; }
await fs.writeFile(root + '/capsule-result-' + mode + '.json', JSON.stringify(result, null, 2) + '\n', { flag: 'wx', mode: 0o600 });
if (terminal?.output) process.stdout.write(terminal.output);
