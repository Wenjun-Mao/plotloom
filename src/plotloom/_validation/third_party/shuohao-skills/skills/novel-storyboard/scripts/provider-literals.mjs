/** Exact source-bound spans; a caller must supply its frozen source context. */
import { createHash } from 'node:crypto';
import { readFileSync } from 'node:fs';
const hash = text => createHash('sha256').update(text).digest('hex');
const sort = value => Array.isArray(value) ? value.map(sort) : value && typeof value === 'object'
  ? Object.fromEntries(Object.keys(value).sort().map(key => [key, sort(value[key])])) : value;
const digest = value => hash(JSON.stringify(sort(value)));
const assert = (ok, message) => { if (!ok) throw new Error(message); };
function leaves(value, path = '$', result = new Map()) {
  if (typeof value === 'string') result.set(path, value);
  else if (Array.isArray(value)) value.forEach((item, i) => leaves(item, `${path}[${i}]`, result));
  else if (value && typeof value === 'object') Object.keys(value).sort().forEach(key => {
    assert(!/[.\[\]]/.test(key), 'Literal paths require schema keys'); leaves(value[key], `${path}.${key}`, result);
  });
  return result;
}
function span(value, fields, expectedHash) {
  assert(value && Object.keys(value).sort().join() === 'end,path,start,text', 'Literal span shape differs');
  const text = fields.get(value.path), points = typeof text === 'string' ? Array.from(text) : [];
  assert(typeof text === 'string' && hash(text) === expectedHash && Number.isSafeInteger(value.start)
    && Number.isSafeInteger(value.end) && value.start >= 0 && value.start < value.end && value.end <= points.length
    && points.slice(value.start, value.end).join('') === value.text, 'Literal Unicode span/hash differs');
}
export function literalPath(stage, path, role) {
  if (stage === 'characters') return role === 'literal_visible_text' && /^\$\.characters\[\d+\]\.image\.(prompt|sheet|negativePrompt|tags\[\d+\])$/.test(path);
  if (stage === 'art') return role === 'literal_visible_text' && /^\$\.(scenes|props)\[\d+\]\.(image\.(prompt|sheet|negativePrompt|tags\[\d+\])|(lighting|states)\[\d+\]\.prompt)$/.test(path);
  return stage === 'storyboard' && (role === 'spoken_dialogue' ? /^\$\.episodes\[\d+\]\.segments\[\d+\]\.h3Prompt$/ : /^\$\.episodes\[\d+\]\.segments\[\d+\]\.(h3Prompt|cuts\[\d+\]\.frame)$/).test(path);
}
export function literalResiduals(doc, context = null, stage) {
  const claims = doc?.providerLiterals ?? [];
  assert(Array.isArray(claims) && claims.length <= 256, 'Literal claims must be a bounded array');
  if (!context) { assert(!claims.length, 'Literal claims require frozen source context'); return (_path, text) => text; }
  const { contentHash, ...payload } = context;
  assert(context.version === 'plotloom.provider-literals.v2' && context.stage === stage && digest(payload) === contentHash
    && context.helperHash === hash(readFileSync(new URL(import.meta.url))),
    'Frozen literal context identity differs');
  const source = new Map(Object.entries(context.sources).map(([path, item]) => {
    assert(typeof item.text === 'string' && hash(item.text) === item.sha256, 'Literal source identity differs'); return [path, item.text];
  }));
  const fields = leaves(doc), owned = new Map(), facts = new Map(context.facts.map(item => [item.id, item]));
  for (const claim of claims) {
    assert(claim && Object.keys(claim).every(key => ['role','candidateSpan','sourceSpan','candidateFieldHash','sourceFieldHash','sourceFactId'].includes(key)), 'Literal claim has unowned members');
    assert(['literal_visible_text','spoken_dialogue'].includes(claim.role), 'Literal role differs');
    span(claim.candidateSpan, fields, claim.candidateFieldHash); span(claim.sourceSpan, source, claim.sourceFieldHash);
    const a = claim.candidateSpan, b = claim.sourceSpan;
    assert(a.text === b.text && literalPath(stage, a.path, claim.role), 'Literal channel/source differs');
    const spans = owned.get(a.path) ?? [];
    assert(!spans.some(([start,end]) => a.start < end && start < a.end), 'Literal spans overlap');
    spans.push([a.start,a.end]); owned.set(a.path, spans);
    if (claim.sourceFactId != null) {
      const fact = facts.get(claim.sourceFactId);
      assert(fact && fact.role === claim.role && digest(fact.sourceSpan) === digest(b) && fact.sourceFieldHash === claim.sourceFieldHash,
        'Literal differs from established fact');
    }
  }
  return (path, text) => residual(text, owned.get(path) ?? []);
}
export function residual(text, spans) {
  const points = Array.from(String(text ?? ''));
  for (const [start,end] of spans) for (let i = start; i < end; i++) points[i] = ' ';
  return points.join('');
}
export class ScriptDialogueError extends Error {}
export function scriptDialogueSpans(prompt, script, episode, sceneIndex, cuts) {
  const scene = script?.episodes?.find(item => item.ep === episode)?.scenes?.[sceneIndex - 1];
  const allowed = [];
  (scene?.flow ?? []).forEach((flow, index) => {
    if (typeof flow?.line !== 'string' || !cuts.some(cut => cut.beats?.[0] <= index + 1 && index + 1 <= cut.beats?.[1])) return;
    const language = flow.language ?? script.lang ?? 'zh';
    const label = ({'zh':'Chinese','zh-CN':'Chinese','en':'English','en-US':'English'})[language];
    if (label) allowed.push({text: flow.line, label, sourcePath: `$.inputs.script_json.episodes[${script.episodes.indexOf(script.episodes.find(item => item.ep === episode))}].scenes[${sceneIndex - 1}].flow[${index}].line`});
  });
  const spans = [];
  for (const match of String(prompt).matchAll(/<d>\[([^\]]+)\]([\s\S]*?)<\/d>/g)) {
    const found = allowed.find(item => item.label === match[1] &&
      (match[2] === item.text || match[2] === ` ${item.text}` || match[2] === `${item.text} ` || match[2] === ` ${item.text} `));
    if (!found) throw new ScriptDialogueError('Spoken block differs from exact Script-owned dialogue');
    const offset = match.index + match[0].indexOf(']') + 1 + (match[2].startsWith(found.text) ? 0 : 1);
    const start = Array.from(String(prompt).slice(0, offset)).length;
    spans.push([start, start + Array.from(found.text).length, found.sourcePath, found.text]);
  }
  const tags = String(prompt).match(/<\/?d>/g) ?? [];
  if (tags.length !== spans.length * 2) throw new ScriptDialogueError('Malformed or unowned spoken block');
  return spans;
}
