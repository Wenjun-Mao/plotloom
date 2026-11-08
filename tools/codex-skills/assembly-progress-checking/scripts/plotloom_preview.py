#!/usr/bin/env python3
"""Check bindings on the retained early E1 preview; do not re-export or decode."""
import json
from pathlib import Path
from progress import sha

PROJECT = Path(__file__).resolve().parents[4]
P = PROJECT / 'docs/roadmap/别叫我的名字-shuohao-production'
D = P / 'exports/episode1-preview-v1'


def check(path, expected):
    return path.is_file() and sha(path) == expected


def main():
    delivery = json.loads((D / 'delivery-review.json').read_text())
    manifest = json.loads((D / 'early-episode-assembly-manifest.json').read_text())
    output = manifest['output']
    selection = json.loads((D / 'episode1-selection.json').read_text())
    bindings = {
        'deliveryMedia': check(Path(delivery['file']), delivery['sha256']),
        'selection': check(Path(delivery['selectionFile']), delivery['selectionSha256']),
        'manifest': check(Path(delivery['assemblyManifestFile']), delivery['assemblyManifestSha256']),
        'pictureReview': check(Path(delivery['actualPictureReviewFile']), delivery['actualPictureReviewSha256']),
        'viewerProof': check(Path(delivery['actualNativeViewerProofFile']), delivery['actualNativeViewerProofSha256']),
        'outputMatchesManifest': check(Path(output['file']), output['sha256']),
        'selectedMediaAndReviews': all(check(Path(c['packet']) / 'output/original-native-av.mp4', c['nativeSha256']) and
                                       check(Path(c['packet']) / 'clip-review.json', c['reviewSha256'])
                                       for c in selection['clips']),
        'orderedSelectionMatchesReceipt': [c['segmentId'] for c in selection['clips']] == output['sourceSegments'],
        'sourceHashesAgree': selection['storyboardSha256'] == manifest['storyboardSha256'] == delivery['sourceSha256'],
        'manifestSelectionHashAgrees': manifest['selectionSha256'] == delivery['selectionSha256'],
    }
    current = sha(P / 'storyboard.json')
    print(json.dumps({'bindings': bindings, 'historicalBindingsIntact': all(bindings.values()),
        'historicalSourceSha256': delivery['sourceSha256'], 'currentSourceSha256': current,
        'wholeSourceStillCurrent': current == delivery['sourceSha256'],
        'retainedClaims': {'frames': output['nativeFrames'], 'decodedFrameOrderEqual': output['allDecodedVideoFramesEqual'],
                           'nativePcmSamples': output['nativeCount'], 'tailZeroSamples': output['newZeroSamples'],
                           'slotSamples': output['slotCount'], 'audioExport': output['audioExport']},
        'limits': 'Hash-checked retained claims, not a fresh frame/PCM/timeline verification or perceptual audio review. '
                  'Current whole-source hash differs when wholeSourceStillCurrent is false.'}, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
