#!/usr/bin/env node
/** Normal content API returns are correction authority; thrown failures never are. */
import { readFileSync } from 'node:fs';
import { createHash } from 'node:crypto';
import { isDeepStrictEqual } from 'node:util';
import { resolve } from 'node:path';
import { fileURLToPath } from 'node:url';

export async function contentIssues(candidate, request) {
  let problems;
  const result = issues => {
    if (!Array.isArray(problems) || problems.some(problem => typeof problem !== 'string')) throw new Error('Content validator API changed');
    return { issues, displayDiagnostics: problems.slice(0, 16).map(problem => problem.slice(0, 500)) };
  };
  const generic = { code: 'candidate_content_invalid', fieldPaths: ['$'], repairFacts: {} };
  if (request.stage === 'outline') {
    const { validateOutline } = await import('../third_party/shuohao-skills/skills/novel-outline/scripts/novel-outline.mjs');
    problems = validateOutline(candidate);
  } else if (request.stage === 'characters') {
    const { validateCast, needsUiTranslation } = await import('../third_party/shuohao-skills/skills/novel-characters/scripts/novel-characters.mjs');
    const contract = request.inputArtifacts['cast-style-contract.json'];
    if (contract && !contract.authority) {
      const { styleContract, validateStyle } = await import('./cast-style.mjs');
      if (!isDeepStrictEqual(contract, styleContract(contract.style, contract.authorDirection))) throw new Error('Frozen character contract drift');
      problems = validateStyle(candidate, contract);
    } else {
      if (contract?.authority !== 'saved_brief') throw new Error('Unsupported character style authority');
      await import('./brief-cast-style.mjs');
      problems = [];
    }
    if (typeof request.source.text !== 'string') throw new Error('Frozen character source unavailable');
    problems.push(...validateCast(candidate.characters, request.source.text, candidate.lang, candidate.style));
    if (typeof candidate.summary !== 'string' || !candidate.summary.trim()) problems.push('summary');
    if (needsUiTranslation(candidate.lang) && !candidate.ui) problems.push('ui');
  } else if (request.stage === 'art') {
    const { validateArt, PROP_SCALES } = await import('../third_party/shuohao-skills/skills/novel-art/scripts/novel-art.mjs');
    const cast = request.inputArtifacts['cast.json'];
    if (!cast || typeof cast !== 'object') throw new Error('Frozen art cast unavailable');
    const contract = request.inputArtifacts['art-style-contract.json'];
    if (contract && !contract.authority) {
      const { styleContract, validateStyledArt } = await import('./art-style.mjs');
      if (!isDeepStrictEqual(contract, styleContract(contract.style, contract.authorDirection))) throw new Error('Frozen art contract drift');
      problems = validateStyledArt(candidate, cast, contract);
    } else {
      if (contract?.authority !== 'saved_brief') throw new Error('Unsupported art style authority');
      await import('./brief-art-style.mjs');
      problems = validateArt(candidate, { cast });
    }
    if (problems.length) {
      const scaleIssues = (Array.isArray(candidate.props) ? candidate.props : []).flatMap((prop, index) => {
        const phrase = PROP_SCALES[prop?.scale];
        if (!phrase) return [];
        const paths = ['prompt', 'sheet'].filter(field => typeof prop.image?.[field] !== 'string' || !prop.image[field].includes(phrase))
          .map(field => `props[${index}].image.${field}`);
        return paths.length ? [{ code: 'art_prop_scale', fieldPaths: paths, repairFacts: { requiredPhrase: phrase } }] : [];
      });
      return result([generic, ...scaleIssues]);
    }
  } else throw new Error('No typed content adapter for this stage');
  if (!Array.isArray(problems) || problems.some(problem => typeof problem !== 'string')) throw new Error('Content validator API changed');
  return result(problems.length ? [generic] : []);
}

async function main(args) {
  if (args.length !== 2) throw new Error('Use text-content-validation.mjs candidate.json request.json');
  const raw = readFileSync(args[0]);
  // Candidate/parser and immutable request failures remain terminal runtime failures.
  const candidate = JSON.parse(raw.toString('utf8'));
  const request = JSON.parse(readFileSync(args[1], 'utf8'));
  const { issues, displayDiagnostics } = await contentIssues(candidate, request);
  if (issues.length) {
    process.stdout.write(JSON.stringify({ contract: 'plotloom.typed-content-result.v1',
      candidateHash: createHash('sha256').update(raw).digest('hex'), issues, displayDiagnostics }));
    process.exitCode = 42;
  } else process.stdout.write('Valid candidate content\n');
}

if (process.argv[1] && resolve(process.argv[1]) === fileURLToPath(import.meta.url)) {
  main(process.argv.slice(2)).catch(error => { console.error(error.message); process.exitCode = 1; });
}
