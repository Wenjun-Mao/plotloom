#!/usr/bin/env node
/** Script's normal upstream issue result; thrown/input/runtime failures stay terminal. */
import { readFileSync } from 'node:fs';
import { createHash } from 'node:crypto';
import { isDeepStrictEqual } from 'node:util';
import { dirname, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';
import { paramsOf, validateScript } from '../third_party/shuohao-skills/skills/novel-script/scripts/novel-script.mjs';

export function scriptContentResult(candidate, request) {
  if (request.stage !== 'script' || request.contentValidationContract !== 'plotloom.typed-content-result.v1') {
    throw new Error('Script typed validation requires its frozen capability');
  }
  const artifacts = request.inputArtifacts;
  if (!artifacts?.['outline.json'] || !artifacts?.['art.json']) throw new Error('Frozen Script context unavailable');
  if (request.textCorrection) {
    const prior = request.textCorrection.priorCandidateJson;
    if (typeof prior !== 'string' || createHash('sha256').update(prior).digest('hex') !== request.textCorrection.rejection?.candidateHash) {
      throw new Error('Script correction prior bytes differ');
    }
    if (!isDeepStrictEqual(paramsOf(candidate), paramsOf(JSON.parse(prior)))) {
      throw new Error('Script correction cannot change effective estimator parameters');
    }
  }
  const problems = validateScript(candidate, { outline: artifacts['outline.json'], art: artifacts['art.json'] });
  if (!Array.isArray(problems) || problems.some(p => typeof p !== 'string')) throw new Error('Script content API changed');
  return { issues: problems.length ? [{ code: 'candidate_content_invalid', fieldPaths: ['$'], repairFacts: {} }] : [],
    displayDiagnostics: problems.slice(0, 16).map(p => p.slice(0, 500)) };
}

function main(args) {
  if (args.length !== 2) throw new Error('Use script-content-validation.mjs candidate.json request.json');
  const raw = readFileSync(args[0]);
  const request = JSON.parse(readFileSync(args[1], 'utf8'));
  for (const [name, value] of Object.entries(request.inputArtifacts ?? {})) {
    if (!/^[A-Za-z0-9_.-]+\.json$/.test(name) || name.startsWith('.')) throw new Error('Invalid frozen input name');
    if (!isDeepStrictEqual(JSON.parse(readFileSync(resolve(dirname(args[1]), 'inputs', name), 'utf8')), value)) {
      throw new Error('Frozen Script input differs from request');
    }
  }
  const result = scriptContentResult(JSON.parse(raw.toString('utf8')), request);
  if (result.issues.length) {
    process.stdout.write(JSON.stringify({ contract: 'plotloom.typed-content-result.v1',
      candidateHash: createHash('sha256').update(raw).digest('hex'), ...result }));
    process.exitCode = 42;
  } else process.stdout.write('Valid candidate content\n');
}

if (process.argv[1] && resolve(process.argv[1]) === fileURLToPath(import.meta.url)) {
  try { main(process.argv.slice(2)); }
  catch (error) { console.error(error.message); process.exitCode = 1; }
}
