"""Pinned-image GPU component proof; no diffusion or Comfy server required.

Run from /opt/ComfyUI in an isolated container with global --bf16-vae and
--fast fp16_accumulation. Mount maintained nodes read-only and models/evidence.
"""
import argparse
import copy
import json
import sys
from importlib import import_module
from pathlib import Path

parser = argparse.ArgumentParser()
parser.add_argument("--receipt", required=True, type=Path)
options, comfy_args = parser.parse_known_args()
sys.argv = [sys.argv[0], *comfy_args]
sys.path.insert(0, "/opt/ComfyUI")
sys.path.insert(0, "/opt/ComfyUI/custom_nodes")
import comfy.options

comfy.options.enable_args_parsing()
# Import the pinned runtime's actual device/DynamicVRAM bootstrap, without
# calling start_comfyui() or starting a server. Importing model_management alone
# leaves CoreModelPatcher static and cannot exercise dynamic delegate reloads.
import_module("main")
import comfy.model_management as management
import comfy.model_patcher
import torch
from nodes import VAELoader
from plotloom_h3_video_vae.loader import (
    CHECKPOINT,
    POLICY,
    PlotloomH3VideoVAELoader,
)


def compute(vae, label, *, video):
    activations = []
    expected = torch.float16 if video else torch.bfloat16
    assert vae.vae_dtype == expected
    def observe(_module, values):
        value = values[0]
        activations.append({"dtype": str(value.dtype), "device": str(value.device)})
    hooks = [getattr(vae.first_stage_model, part).register_forward_pre_hook(observe)
             for part in ("encoder", "decoder")]
    try:
        with torch.inference_mode():
            pixels = torch.full((1, 128, 128, 3), 0.5) if video else torch.zeros((1, 3200, 2))
            output = vae.decode(vae.encode(pixels))
            assert torch.isfinite(output).all()
        assert len(activations) >= 2
        assert all(item == {"dtype": str(expected), "device": "cuda:0"} for item in activations)
        return {"label": label, "effectiveDtype": str(vae.vae_dtype),
                "activations": activations, "finite": True, "shape": list(output.shape)}
    finally:
        for hook in hooks: hook.remove()


def wrapper(original, patcher):
    value = copy.copy(original)
    value.patcher, value.first_stage_model = patcher, patcher.model
    value.device = patcher.load_device
    return value


receipt = {"status": "running", "checks": []}
assert not options.receipt.exists(), "Refuse overwriting lifecycle proof"
try:
    assert comfy.model_patcher.CoreModelPatcher is comfy.model_patcher.ModelPatcherDynamic
    receipt["dynamicRuntimeInitialized"] = True
    video, = PlotloomH3VideoVAELoader().load(CHECKPOINT, POLICY)
    audio, = VAELoader().load_vae("minimax_h3_audio_vae_fp32.safetensors")
    factory = video.patcher.cached_patcher_init
    receipt["checks"].append(compute(video, "initial", video=True))
    ordinary = video.patcher.clone(disable_dynamic=True)
    assert not ordinary.is_dynamic() and ordinary.model is not video.patcher.model
    assert ordinary.cached_patcher_init == factory
    receipt["checks"].append(compute(wrapper(video, ordinary), "nondynamic-clone", video=True))
    deep = video.patcher.deepclone_multigpu(new_load_device=torch.device("cuda:0"))
    assert deep.model is not video.patcher.model and deep.cached_patcher_init == factory
    receipt["checks"].append(compute(wrapper(video, deep), "same-device-deepclone", video=True))
    management.unload_all_models()
    receipt["checks"].append(compute(video, "after-offload-reload", video=True))
    reloaded = factory[0](*factory[1])
    assert reloaded.model is not video.patcher.model
    receipt["checks"].append(compute(wrapper(video, reloaded), "disk-factory", video=True))
    receipt["checks"].append(compute(audio, "stock-audio-after-video-lifecycle", video=False))
    receipt.update(status="passed", policy=POLICY,
                   fp16Accumulation=torch.backends.cuda.matmul.allow_fp16_accumulation)
except Exception as error:
    receipt.update(status="failed", errorType=type(error).__name__, error=str(error))
    raise
finally:
    options.receipt.write_text(json.dumps(receipt, indent=2) + "\n")
