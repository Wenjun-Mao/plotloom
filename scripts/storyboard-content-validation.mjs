#!/usr/bin/env node
/** Normal Storyboard API issues only; thrown/frozen/receiving failures stay terminal. */
import { readFileSync } from 'node:fs';
import { createHash } from 'node:crypto';
import { isDeepStrictEqual } from 'node:util';
import { dirname, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';
import { validateStoryboard } from '../third_party/shuohao-skills/skills/novel-storyboard/scripts/novel-storyboard.mjs';
import { frozenF5DialogueTiming } from './storyboard-dialogue-timing.mjs';

export async function storyboardContentResult(candidate, request) {
  if (request?.stage !== 'storyboard' || request.contentValidationContract !== 'plotloom.typed-content-result.v1') {
    throw new Error('Storyboard typed validation requires its frozen capability');
  }
  const inputs = request.inputArtifacts;
  if (!inputs?.['script.json'] || !inputs['outline.json'] || !inputs['cast.json']) {
    throw new Error('Frozen Storyboard context unavailable');
  }
  const { admission } = frozenF5DialogueTiming(request);
  if (!Object.entries(admission.reviewTiming).every(([key, value]) => candidate.params?.[key] === value)
      || !isDeepStrictEqual(candidate.episodes?.map(ep => ep.ep), admission.sectionBindings?.map(item => item.episode))) {
    throw new Error('Storyboard candidate changed frozen timing or section authority');
  }
  if (request.textCorrection) {
    const prior = request.textCorrection.priorCandidateJson;
    if (typeof prior !== 'string' || createHash('sha256').update(prior).digest('hex') !== request.textCorrection.rejection?.candidateHash) {
      throw new Error('Storyboard correction prior bytes differ');
    }
    JSON.parse(prior); // Parser failures never become correction authority.
  }
  const style = inputs['storyboard-style-contract.json'];
  if (style && style.authority !== 'saved_brief') throw new Error('Unsupported frozen Storyboard style authority');
  let ctx, receive;
  if (style?.authority === 'saved_brief') {
    const route = await import('./brief-storyboard-style.mjs');
    ctx = route.briefStoryboardContext(candidate, request);
    receive = route.validateBriefStoryboard;
  } else {
    const route = await import('./storyboard-receiving.mjs');
    ctx = { script: inputs['script.json'], outline: inputs['outline.json'], cast: inputs['cast.json'], art: inputs['art.json'] };
    receive = route.validateReceivedStoryboard;
  }
  const problems = validateStoryboard(candidate, ctx);
  if (!Array.isArray(problems) || problems.some(p => typeof p !== 'string')) throw new Error('Storyboard content API changed');
  if (!problems.length) receive(candidate, request); // Keep all existing receiving exceptions ineligible.
  return { issues: problems.length ? [{ code: 'candidate_content_invalid', fieldPaths: ['$'], repairFacts: {} }] : [],
    displayDiagnostics: problems.slice(0, 16).map(p => p.slice(0, 500)) };
}

async function main(args) {
  if (args.length !== 2) throw new Error('Use storyboard-content-validation.mjs candidate.json request.json');
  const raw = readFileSync(args[0]), request = JSON.parse(readFileSync(args[1], 'utf8'));
  for (const [name, value] of Object.entries(request.inputArtifacts ?? {})) {
    if (!/^[A-Za-z0-9_.-]+\.json$/.test(name) || name.startsWith('.')) throw new Error('Invalid frozen input name');
    if (!isDeepStrictEqual(JSON.parse(readFileSync(resolve(dirname(args[1]), 'inputs', name), 'utf8')), value)) {
      throw new Error('Frozen Storyboard input differs from request');
    }
  }
  const result = await storyboardContentResult(JSON.parse(raw.toString('utf8')), request);
  if (result.issues.length) {
    process.stdout.write(JSON.stringify({ contract: 'plotloom.typed-content-result.v1',
      candidateHash: createHash('sha256').update(raw).digest('hex'), ...result }));
    process.exitCode = 42;
  } else process.stdout.write('Valid candidate content\n');
}

if (process.argv[1] && resolve(process.argv[1]) === fileURLToPath(import.meta.url)) {
  try { await main(process.argv.slice(2)); }
  catch (error) { console.error(error.message); process.exitCode = 1; }
}
