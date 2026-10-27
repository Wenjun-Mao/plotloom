/** F5 receiving requirements over trusted, frozen canonical dialogue minima. */
import { createHash } from 'node:crypto';

const assert = (condition, message) => { if (!condition) throw new Error(message); };
const textHash = value => createHash('sha256').update(value, 'utf8').digest('hex');
const canonical = value => JSON.stringify(sort(value));
function sort(value) {
  if (Array.isArray(value)) return value.map(sort);
  if (value && typeof value === 'object') return Object.fromEntries(Object.keys(value).sort().map(key => [key, sort(value[key])]));
  return value;
}
const coordinate = (ep, scene, flow) => `${ep}/${scene}/${flow}`;

function sourceDuration(seconds) {
  assert(typeof seconds === 'number' && Number.isFinite(seconds) && seconds > 0, 'Source cut seconds must be finite and positive');
  assert(!Number.isInteger(seconds) || Number.isSafeInteger(seconds), 'Source cut seconds exceed exact integer capacity');
  const [, whole, fraction = '', exponent = '0'] = String(seconds).match(/^(\d+)(?:\.(\d+))?(?:e([+-]?\d+))?$/) ?? [];
  assert(whole !== undefined, 'Source cut seconds cannot be represented exactly');
  const power = 3 + Number(exponent) - fraction.length;
  const coefficient = BigInt(whole + fraction);
  // Raw F5 retains decimal precision. Bridge alone owns integer-ms conversion.
  return { coefficient: coefficient * 10n ** BigInt(Math.max(power, 0)), scale: Math.max(-power, 0) };
}

const integerDuration = coefficient => ({ coefficient, scale: 0 });
function alignedCoefficient(duration, scale) {
  return duration.coefficient * 10n ** BigInt(scale - duration.scale);
}
function addDuration(left, right) {
  const scale = Math.max(left.scale, right.scale);
  return { coefficient: alignedCoefficient(left, scale) + alignedCoefficient(right, scale), scale };
}
function fitsDuration(minimum, available) {
  const scale = Math.max(minimum.scale, available.scale);
  return alignedCoefficient(minimum, scale) <= alignedCoefficient(available, scale);
}

export function frozenF5DialogueTiming(request) {
  assert(request?.stage === 'storyboard', 'Frozen storyboard request is required');
  const inputs = request.inputArtifacts, admission = inputs?.['storyboard-admission.json'];
  const script = inputs?.['script.json'], timing = inputs?.['dialogue-timing-contract.json'];
  assert(admission && script && timing?.version === 'plotloom.f5-dialogue-timing.v1', 'Frozen canonical dialogue timing contract is required');
  const { contentHash, ...payload } = timing;
  assert(contentHash === textHash(canonical(payload)), 'Frozen canonical dialogue timing content hash differs');
  assert(timing.profileVersion === 'dialogue.default.v1' && typeof timing.language === 'string' && timing.language.trim(), 'Canonical dialogue timing profile/language is invalid');
  assert(timing.scriptContentHash === admission.scriptContentHash && admission.scriptRevision === request.source?.acceptedScriptRevision && admission.scriptContentHash === request.source?.acceptedScriptContentHash, 'Canonical dialogue timing Script identity differs');
  assert(Number.isSafeInteger(admission.scriptRevision) && admission.scriptRevision > 0
    && typeof admission.scriptContentHash === 'string' && /^[a-f0-9]{64}$/.test(admission.scriptContentHash), 'Frozen Script identity is required');
  assert(Array.isArray(admission.sectionBindings) && admission.sectionBindings.every(item =>
    typeof item?.sectionId === 'string' && item.sectionId.trim() && Number.isSafeInteger(item.episode) && item.episode > 0), 'Frozen section mapping is required');
  assert(Array.isArray(admission.completeRouteSectionIds) && admission.completeRouteSectionIds.every(route =>
    Array.isArray(route) && route.every(id => typeof id === 'string'))
    && Array.isArray(admission.routeOnlySectionIds) && admission.routeOnlySectionIds.every(id => typeof id === 'string'), 'Frozen complete routes are required');
  assert(Number.isSafeInteger(admission.targetPlaythroughSeconds) && admission.targetPlaythroughSeconds > 0, 'Author playthrough maximum must be a safe positive integer');
  assert(Array.isArray(timing.lines), 'Canonical dialogue timing lines are required');
  const source = [];
  for (const episode of script.episodes ?? []) {
    (episode.scenes ?? []).forEach((scene, si) => (scene.flow ?? []).forEach((flow, fi) => {
      if (typeof flow?.line === 'string') source.push({
        episode: episode.ep, sceneIndex: si + 1, flowIndex: fi + 1, textHash: textHash(flow.line),
      });
    }));
  }
  assert(source.length === timing.lines.length, 'Canonical dialogue timing must cover every source line exactly');
  const minima = new Map();
  timing.lines.forEach((line, index) => {
    const expected = source[index];
    assert(Object.keys(expected).every(key => expected[key] === line[key]), 'Canonical dialogue timing source coordinates/text differ');
    assert(['measured', 'natural', 'brisk'].includes(line.delivery) && Number.isSafeInteger(line.minimumDurationUnits) && line.minimumDurationUnits > 0, 'Canonical dialogue timing minimum/pace is invalid');
    const key = coordinate(line.episode, line.sceneIndex, line.flowIndex);
    assert(!minima.has(key), 'Canonical dialogue timing source coordinates repeat');
    minima.set(key, BigInt(line.minimumDurationUnits));
  });
  assert(admission.reviewTiming, 'Frozen review timing is required');
  for (const key of ['minCutSeconds', 'maxCutSeconds', 'maxSegmentSeconds']) sourceDuration(admission.reviewTiming[key]);
  return { admission, minima };
}

export function validateF5ReceivingTiming(board, request) {
  const { admission, minima } = frozenF5DialogueTiming(request);
  const mapping = admission.sectionBindings;
  assert(Array.isArray(mapping) && canonical(board.episodes?.map(ep => ep.ep)) === canonical(mapping.map(item => item.episode)), 'Storyboard episodes must exactly match frozen F4 mapping');
  assert(admission.reviewTiming && Object.entries(admission.reviewTiming).every(([key, value]) => board.params?.[key] === value), 'Storyboard params must match frozen review timing');
  const minimumCut = sourceDuration(admission.reviewTiming.minCutSeconds);
  const maximumCut = sourceDuration(admission.reviewTiming.maxCutSeconds);
  const maximumSegment = sourceDuration(admission.reviewTiming.maxSegmentSeconds);
  const assigned = new Map(), durations = new Map();
  board.episodes.forEach((episode, index) => {
    let episodeUnits = integerDuration(0n);
    for (const segment of episode.segments ?? []) {
      let segmentUnits = integerDuration(0n);
      for (const cut of segment.cuts ?? []) {
        const units = sourceDuration(cut.seconds);
        assert(fitsDuration(minimumCut, units) && fitsDuration(units, maximumCut), 'Cut duration violates frozen review timing');
        segmentUnits = addDuration(segmentUnits, units);
        const [start, end] = cut.beats ?? [];
        assert(Number.isInteger(start) && Number.isInteger(end) && start >= 1 && end >= start, 'Cut beats must identify an ordered source range');
        let total = 0n;
        for (let flow = start; flow <= end; flow++) {
          const key = coordinate(episode.ep, segment.sceneIndex, flow);
          if (!minima.has(key)) continue;
          total += minima.get(key);
          assigned.set(key, (assigned.get(key) ?? 0) + 1);
        }
        assert(fitsDuration(integerDuration(total), units), 'Canonical dialogue minima must fit their owning cut duration');
      }
      assert(fitsDuration(segmentUnits, maximumSegment), 'Segment duration violates frozen review timing');
      episodeUnits = addDuration(episodeUnits, segmentUnits);
    }
    durations.set(mapping[index].sectionId, episodeUnits);
  });
  assert([...minima.keys()].every(key => assigned.get(key) === 1), 'Every canonical dialogue line must belong to exactly one cut');
  const footage = new Set(admission.completeRouteSectionIds.flat().filter(id => !admission.routeOnlySectionIds.includes(id)));
  assert(footage.size === durations.size && [...durations].every(([id, units]) => footage.has(id) && units.coefficient > 0n), 'Storyboard timing must cover every footage section exactly');
  assert(Number.isSafeInteger(admission.targetPlaythroughSeconds) && admission.targetPlaythroughSeconds > 0, 'Author playthrough maximum must be a safe positive integer');
  const maximum = integerDuration(BigInt(admission.targetPlaythroughSeconds) * 1000n);
  assert(admission.completeRouteSectionIds.every(route => fitsDuration(route.reduce((sum, id) => addDuration(sum, durations.get(id) ?? integerDuration(0n)), integerDuration(0n)), maximum)), 'Complete storyboard route exceeds author playthrough maximum');
}
