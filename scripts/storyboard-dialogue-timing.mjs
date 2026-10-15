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

const zeroTime = { coefficient: 0n, scale: 0 };

function secondsTime(seconds) {
  assert(typeof seconds === 'number' && Number.isFinite(seconds) && seconds > 0, 'Source timing seconds must be finite and positive');
  const [, whole, fraction = '', exponent = '0'] = String(seconds).match(/^(\d+)(?:\.(\d+))?(?:e([+-]?\d+))?$/);
  // Match the JSON number's decimal value, including exponent notation. Raw F5
  // comparison does not convert or round that value into canonical integer ms.
  return { coefficient: BigInt(whole + fraction), scale: fraction.length - Number(exponent) };
}

function alignedTimes(left, right) {
  const scale = Math.max(left.scale, right.scale);
  return [left.coefficient * 10n ** BigInt(scale - left.scale), right.coefficient * 10n ** BigInt(scale - right.scale), scale];
}

function addTimes(left, right) {
  const [a, b, scale] = alignedTimes(left, right);
  return { coefficient: a + b, scale };
}

function atMost(left, right) {
  const [a, b] = alignedTimes(left, right);
  return a <= b;
}

export function validateF5ReceivingTiming(board, request) {
  assert(request?.stage === 'storyboard', 'Frozen storyboard request is required');
  const inputs = request.inputArtifacts, admission = inputs?.['storyboard-admission.json'];
  const script = inputs?.['script.json'], timing = inputs?.['dialogue-timing-contract.json'];
  assert(admission && script && timing?.version === 'plotloom.f5-dialogue-timing.v1', 'Frozen canonical dialogue timing contract is required');
  const { contentHash, ...payload } = timing;
  assert(contentHash === textHash(canonical(payload)), 'Frozen canonical dialogue timing content hash differs');
  assert(timing.profileVersion === 'dialogue.default.v1' && typeof timing.language === 'string' && timing.language.trim(), 'Canonical dialogue timing profile/language is invalid');
  assert(timing.scriptContentHash === admission.scriptContentHash && admission.scriptRevision === request.source?.acceptedScriptRevision && admission.scriptContentHash === request.source?.acceptedScriptContentHash, 'Canonical dialogue timing Script identity differs');
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
  const mapping = admission.sectionBindings;
  assert(Array.isArray(mapping) && canonical(board.episodes?.map(ep => ep.ep)) === canonical(mapping.map(item => item.episode)), 'Storyboard episodes must exactly match frozen F4 mapping');
  assert(admission.reviewTiming && Object.entries(admission.reviewTiming).every(([key, value]) => board.params?.[key] === value), 'Storyboard params must match frozen review timing');
  const minimumCut = secondsTime(admission.reviewTiming.minCutSeconds);
  const maximumCut = secondsTime(admission.reviewTiming.maxCutSeconds);
  const maximumSegment = secondsTime(admission.reviewTiming.maxSegmentSeconds);
  const maximumRoute = secondsTime(admission.targetPlaythroughSeconds);
  const assigned = new Map(), durations = new Map();
  board.episodes.forEach((episode, index) => {
    let episodeTime = zeroTime;
    for (const segment of episode.segments ?? []) {
      let segmentTime = zeroTime;
      for (const cut of segment.cuts ?? []) {
        const duration = secondsTime(cut.seconds);
        assert(atMost(minimumCut, duration) && atMost(duration, maximumCut), 'Cut duration violates frozen review timing');
        segmentTime = addTimes(segmentTime, duration);
        const [start, end] = cut.beats ?? [];
        assert(Number.isInteger(start) && Number.isInteger(end) && start >= 1 && end >= start, 'Cut beats must identify an ordered source range');
        let total = 0n;
        for (let flow = start; flow <= end; flow++) {
          const key = coordinate(episode.ep, segment.sceneIndex, flow);
          if (!minima.has(key)) continue;
          total += minima.get(key);
          assigned.set(key, (assigned.get(key) ?? 0) + 1);
        }
        assert(atMost({ coefficient: total, scale: 3 }, duration), 'Canonical dialogue minima must fit their owning cut duration');
      }
      assert(atMost(segmentTime, maximumSegment), 'Segment duration violates frozen review timing');
      episodeTime = addTimes(episodeTime, segmentTime);
    }
    durations.set(mapping[index].sectionId, episodeTime);
  });
  assert([...minima.keys()].every(key => assigned.get(key) === 1), 'Every canonical dialogue line must belong to exactly one cut');
  const footage = new Set(admission.completeRouteSectionIds.flat().filter(id => !admission.routeOnlySectionIds.includes(id)));
  assert(footage.size === durations.size && [...durations].every(([id, time]) => footage.has(id) && time.coefficient > 0n), 'Storyboard timing must cover every footage section exactly');
  assert(admission.completeRouteSectionIds.every(route => atMost(route.reduce((sum, id) => addTimes(sum, durations.get(id) ?? zeroTime), zeroTime), maximumRoute)), 'Complete storyboard route exceeds author playthrough maximum');
}
