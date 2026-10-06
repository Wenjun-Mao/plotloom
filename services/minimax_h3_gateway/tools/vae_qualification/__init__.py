"""Isolated Comfy custom nodes, mounted ONLY in the qualification container."""
import os

# Offline tests import contract.py directly; no Torch in the product test process.
if os.environ.get('H3_QUALIFICATION_ARM'):
    import comfy.sd
    import comfy.utils
    import folder_paths
    import torch

    from .contract import ARMS, AUDIO
    from .observer import emit, install

    install()

    class QualificationVideoVAELoader:
        @classmethod
        def INPUT_TYPES(cls):
            arm = ARMS[os.environ['H3_QUALIFICATION_ARM']]
            return {'required': {'vae_name': ([arm['checkpoint']],), 'precision': ([arm['dtype']],)}}

        RETURN_TYPES = ('VAE',)
        FUNCTION = 'load'
        CATEGORY = 'qualification_only'

        def load(self, vae_name, precision):
            arm = ARMS[os.environ['H3_QUALIFICATION_ARM']]
            if (vae_name, precision) != (arm['checkpoint'], arm['dtype']):
                raise ValueError('Arm precision/checkpoint differs')
            path = folder_paths.get_full_path_or_raise('vae', vae_name)
            import time
            started = time.monotonic()
            weights, metadata = comfy.utils.load_torch_file(path, return_metadata=True)
            if not {'decoder.transformer_blocks.0.scale1', 'encoder.down.5.block.0.conv1.weight'} <= weights.keys():
                raise ValueError('Not the reviewed H3 video VAE')
            dtype = getattr(torch, precision)
            vae = comfy.sd.VAE(sd=weights, metadata=metadata, dtype=dtype)
            vae.throw_exception_if_invalid()
            vae.patcher.cached_patcher_init = (comfy.sd.load_vae_patcher, (path, metadata, dtype))
            emit({'kind': 'loader', 'vaeKind': 'video', 'effectiveDtype': str(vae.vae_dtype),
                  'wallMs': (time.monotonic() - started) * 1000})
            return (vae,)

    class QualificationVAESmoke:
        @classmethod
        def INPUT_TYPES(cls):
            return {'required': {'video': ('VAE',), 'audio': ('VAE',)}}

        RETURN_TYPES = ()
        OUTPUT_NODE = True
        FUNCTION = 'run'
        CATEGORY = 'qualification_only'

        def run(self, video, audio):
            if str(audio.vae_dtype) != 'torch.bfloat16':
                raise ValueError('Baseline audio precision changed')
            if audio.first_stage_model.__class__.__name__ != 'MiniMaxH3AudioVAE':
                raise ValueError('Unexpected audio model')
            with torch.inference_mode():
                # One static 128px frame and 0.1s stereo silence; no denoising/MP4.
                latent = video.encode(torch.full((1, 128, 128, 3), 0.5))
                decoded = video.decode(latent)
                audio_latent = audio.encode(torch.zeros((1, 3200, 2)))
                audio_decoded = audio.decode(audio_latent)
                if not torch.isfinite(decoded).all() or not torch.isfinite(audio_decoded).all():
                    raise ValueError('Nonfinite component output')
            emit({'kind': 'smoke', 'videoShape': list(decoded.shape),
                  'audioShape': list(audio_decoded.shape), 'audioCheckpoint': AUDIO})
            return {}

    NODE_CLASS_MAPPINGS = {'QualificationVideoVAELoader': QualificationVideoVAELoader,
                           'QualificationVAESmoke': QualificationVAESmoke}
else:
    NODE_CLASS_MAPPINGS = {}
