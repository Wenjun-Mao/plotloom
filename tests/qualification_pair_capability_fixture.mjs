// Pure structural helper capability for a test-owned fake source/CLI allocation.
import fs from 'node:fs/promises';
const [root] = process.argv.slice(2);
const packet = JSON.parse(await fs.readFile(root + '/transport.json','utf8'));
const { Capsule } = await import(root + '/bundle/capsule.mjs');
const { dispatch } = await import(root + '/bundle/node_helper.mjs');
const reply = await dispatch({ action: 'capability', capsuleSource: Function.prototype.toString.call(Capsule),
  planText: packet.planText, anchorText: packet.anchorText, anchorSha: packet.anchorSha256 });
console.log(JSON.stringify({ syntheticEvidence: true, qualification: false, reply }));
if (reply.status !== 'OK') process.exitCode = 1;
