"""Capture existing qualified Spark environments; never install/download models.

Run after installing the same Voice Lab wheel into all three engine environments.
The resulting private runtime manifest pins local files and package inventories.
"""

import argparse
import hashlib
import json
import subprocess
from pathlib import Path

ROOT = Path('/home/wjmao')
SERVICES = ROOT / 'services'
MODELS = ROOT / 'models'
PYTHONS = {
    'qwen_design': SERVICES / 'qwen3-tts-trial/.venv/bin/python',
    'moss_design': SERVICES / 'moss-voicegenerator-trial/.venv-arm64/bin/python',
    'qwen_base': SERVICES / 'qwen3-tts-trial/.venv/bin/python',
    'index_base': SERVICES / 'index-tts2-trial/.venv/bin/python',
}
MODEL_DIRS = {
    'qwen_design': MODELS / 'qwen3-tts/voice-design-1.7b',
    'moss_design': MODELS / 'moss-voicegenerator',
    'qwen_base': MODELS / 'qwen3-tts/base-1.7b',
    'index_base': MODELS / 'index-tts2/2.0',
}
SUFFIXES = {'.safetensors', '.pt', '.pth', '.bin', '.json', '.yaml', '.model', '.txt', '.py', '.jinja', '.fst', '.so'}


def digest(path):
    value = hashlib.sha256()
    with path.open('rb') as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b''): value.update(chunk)
    return value.hexdigest()


def checked_files(directory):
    return [path for path in directory.rglob('*') if path.is_file()
            and path.suffix in SUFFIXES and not {'.cache', '.git', '__pycache__'}.intersection(path.parts)]


def inventory(python, env):
    import os
    code = """import importlib.metadata as m,json
d=m.distribution('plotloom-voice-lab')
print(json.dumps({'packages':{name:m.version(name) for name in sorted({x.metadata['Name'] for x in m.distributions()})},
 'files':[str(d.locate_file(f)) for f in d.files if str(f).startswith('plotloom_voice_lab/') and str(f).endswith('.py')]}))"""
    return json.loads(subprocess.check_output([str(python), '-c', code], text=True, env={**os.environ, **env}))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', required=True, type=Path)
    parser.add_argument('--inventory-dir', required=True, type=Path)
    args = parser.parse_args()
    args.inventory_dir.mkdir(parents=True, exist_ok=True)
    config = {}; hashes = {}
    for engine, python in PYTHONS.items():
        runtime = {'python': str(python), 'modelDir': str(MODEL_DIRS[engine]),
                   'minAvailableGiB': 20 if engine == 'moss_design' else (24 if engine == 'index_base' else 12),
                   'resourceWaitSeconds': 1800, 'timeoutSeconds': 900,
                   'comfyQueueUrl': 'http://127.0.0.1:8188/queue', 'env': {}}
        directories = [MODEL_DIRS[engine]]
        if engine == 'moss_design':
            runtime['codecDir'] = str(MODELS / 'moss-audio-tokenizer')
            runtime['sourceDir'] = str(SERVICES / 'moss-voicegenerator-trial/source')
            directories += [Path(runtime['codecDir']), Path(runtime['sourceDir'])]
        if engine == 'index_base':
            prefix = SERVICES / 'index-tts2-trial/linux-normalizer'
            source = SERVICES / 'index-tts2-trial/source'
            runtime['sourceDir'] = str(source)
            runtime['env'] = {'PYTHONPATH': f'{prefix}/lib/python3.12/site-packages:{source}',
                              'LD_LIBRARY_PATH': str(prefix / 'lib'), 'C_INCLUDE_PATH': str(prefix / 'include/python3.12')}
            runtime['auxPaths'] = {
                'w2v_bert': str(MODEL_DIRS[engine] / 'hf_cache/w2v-bert-2.0'),
                'semantic_codec': str(MODEL_DIRS[engine] / 'hf_cache/semantic_codec_model.safetensors'),
                'campplus': str(MODEL_DIRS[engine] / 'hf_cache/campplus_cn_common.bin'),
                'bigvgan': str(MODEL_DIRS[engine] / 'hf_cache/bigvgan'),
            }
            directories += [source, prefix / 'lib/python3.12/site-packages/tn', prefix / 'lib/python3.12/site-packages/pynini']
        installed = inventory(python, runtime['env'])
        files = [Path(p) for p in installed['files']]
        for directory in directories: files += checked_files(directory)
        if engine == 'index_base':
            files += list((prefix / 'lib/python3.12/site-packages').glob('_pynini*.so'))
            files += list((prefix / 'lib').glob('libfst*.so*'))
        for path in files:
            if str(path) not in hashes: hashes[str(path)] = digest(path)
        runtime['fileChecks'] = {str(path): hashes[str(path)] for path in sorted(set(files))}
        runtime['packages'] = installed['packages']
        config[engine] = runtime
        (args.inventory_dir / f'{engine}.json').write_text(json.dumps(runtime, sort_keys=True, indent=2) + '\n')
        (args.inventory_dir / f'{engine}-requirements.txt').write_text(
            ''.join(f'{name}=={version}\n' for name, version in sorted(runtime['packages'].items())))
        print(f'{engine}: {len(runtime["fileChecks"])} pinned files, {len(runtime["packages"])} packages', flush=True)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(config, sort_keys=True, indent=2) + '\n')
    args.output.chmod(0o600)
    native = SERVICES / 'index-tts2-trial/linux-normalizer/conda-meta'
    (args.inventory_dir / 'index-native-conda.json').write_text(json.dumps([
        json.loads(path.read_text()) for path in sorted(native.glob('*.json'))], sort_keys=True, indent=2) + '\n')


if __name__ == '__main__': main()
