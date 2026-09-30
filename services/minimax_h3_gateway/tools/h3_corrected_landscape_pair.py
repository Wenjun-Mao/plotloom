#!/usr/bin/env python3
"""Owner-approved two-call correction; never overwrite the original trial."""
from __future__ import annotations

import argparse
import json

import h3_runtime_qualification as study
from h3_prompt_robustness_study import RECIPES, render_workflow
from PIL import Image

ORIGINAL = study.WORK
EXPERIMENT = 'h3-runtime-038-corrected-landscape-2026-09-30'
WORK = study.ROOT / 'experiments' / EXPERIMENT
CANDIDATE_USER = ORIGINAL / 'candidate-user'
IMAGE_NAME = f'experiments/{EXPERIMENT}/landscape.png'
PROMPT = (
    'Visual: cinematic realism, one continuous medium close-up. A female astronaut '
    'in a white spacesuit and helmet is seated inside a spacecraft cabin. Earth '
    'is visible through the window beside her. She turns slightly toward the camera, '
    'takes a calm breath and speaks. Preserve the first-frame person, spacesuit '
    'and cabin. Locked-off camera, natural breathing and subtle movement. '
    'No scene transition, no new captions, subtitles, titles or typography.\n'
    'Audio: she says softly in Mandarin, with relief: “我们回家吧。” '
    'The dialogue is spoken, not displayed.\nSound: gentle spacecraft room tone.'
)


def configure() -> None:
    study.EXPERIMENT = EXPERIMENT
    study.WORK = WORK


def freeze() -> None:
    path = WORK / 'cases.json'
    if path.exists():
        raise RuntimeError('Corrected cases already exist; refuse to overwrite')
    image_path = study.INPUT / IMAGE_NAME
    with Image.open(image_path) as image:
        if image.size != (1280, 704):
            raise RuntimeError('Reviewed landscape geometry mismatch')
    template = json.loads(study.TEMPLATE.read_text())['prompt']
    graph = render_workflow(template, recipe=RECIPES[1], prompt=PROMPT,
        seed=20260930, input_name=IMAGE_NAME, output_prefix='__OUTPUT__',
        width=1280, height=704, frame_count=124)
    study.save(path, {
        'caseCount': 1, 'templateSha256': study.digest(study.TEMPLATE),
        'inputReview': 'Operator inspected actual pixels: seated astronaut, white helmet, spacecraft, Earth; no padding or scene inset.',
        'inputProvenance': {'source': 'candidate_landscape_00001_.mp4 from original experiment',
                            'frameIndex': 62, 'preparation': 'Exact frame extraction, no resize/crop/padding'},
        'cases': [{'id': 'landscape', 'graph': graph, 'graphSha256': study.graph_hash(graph),
                   'width': 1280, 'height': 704, 'inputSha256': study.digest(image_path)}],
    })
    print('Frozen reviewed landscape input/prompt; one call per runtime', flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=['freeze', 'baseline', 'candidate', 'baseline-inventory', 'candidate-inventory'])
    args = parser.parse_args()
    configure()
    if args.action == 'freeze':
        freeze()
    elif args.action.endswith('-inventory'):
        study.inventory(args.action.split('-')[0], candidate_user=CANDIDATE_USER)
    else:
        study.run(args.action, call_cap=1, candidate_user=CANDIDATE_USER)
