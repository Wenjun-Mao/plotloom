"""Explicit FP16 video policy, including pristine disk-backed patcher reloads."""
from functools import lru_cache
from hashlib import sha256
from pathlib import Path

import comfy.sd
import comfy.utils
import folder_paths
import torch
from comfy.cli_args import args

CHECKPOINT = "minimax_h3_video_vae_int8_convrot.safetensors"
CHECKPOINT_SHA256 = "52a2c8c73583c86e4f41cdcce3a6ad0ea562987bc0bf3d60a0cef5f5c8e60c0e"
POLICY = "h3-int8-video-fp16-audio-bf16.v1"


def require_runtime() -> None:
    if (not args.bf16_vae or args.fp16_vae or args.fp32_vae
            or not torch.backends.cuda.matmul.allow_fp16_accumulation):
        raise ValueError("H3 policy requires global BF16 VAE and FP16 accumulation")


@lru_cache(maxsize=4)
def _verified_file(path: str, size: int, modified: int, changed: int) -> None:
    # Production mounts this release and models read-only. Stat-keyed caching
    # avoids hashing 2.8 GB for every clone, but invalidates a replaced file.
    digest = sha256()
    with Path(path).open("rb") as stream:
        for block in iter(lambda: stream.read(4 * 1024 * 1024), b""):
            digest.update(block)
    if digest.hexdigest() != CHECKPOINT_SHA256:
        raise ValueError("H3 video checkpoint hash differs from reviewed asset")


def load_video_vae(path: str, device=None, disable_dynamic: bool = False):
    require_runtime()
    stat = Path(path).stat()
    _verified_file(path, stat.st_size, stat.st_mtime_ns, stat.st_ctime_ns)
    weights, metadata = comfy.utils.load_torch_file(path, safe_load=True, return_metadata=True)
    vae = comfy.sd.VAE(sd=weights, metadata=metadata, dtype=torch.float16, device=device)
    vae.throw_exception_if_invalid()
    if vae.first_stage_model.__class__.__name__ != "MiniMaxH3VideoVAE":
        raise ValueError("Reviewed H3 video VAE required")
    if disable_dynamic and vae.patcher.is_dynamic():
        # Pinned VAE has no disable_dynamic argument. A freshly loaded model
        # has no patches/backups to inherit; materialize it like core's ordinary
        # VAE path. The calling clone constructs the ordinary patcher itself.
        vae.first_stage_model.to(vae.vae_dtype)
    return vae


def reload_video_patcher(path: str, device=None, disable_dynamic: bool = False):
    return load_video_vae(path, device=device, disable_dynamic=disable_dynamic).patcher


class PlotloomH3VideoVAELoader:
    @classmethod
    def INPUT_TYPES(cls):
        try:
            require_runtime()
            policies = [POLICY]
        except ValueError:
            policies = []  # Readiness/admission fail before generation.
        files = [CHECKPOINT] if CHECKPOINT in folder_paths.get_filename_list("vae") else []
        return {"required": {"vae_name": (files,), "policy": (policies,)}}

    RETURN_TYPES = ("VAE",)
    FUNCTION = "load"
    CATEGORY = "model/loaders/plotloom"

    def load(self, vae_name: str, policy: str):
        if (vae_name, policy) != (CHECKPOINT, POLICY):
            raise ValueError("Unsupported H3 video VAE policy")
        path = folder_paths.get_full_path_or_raise("vae", vae_name)
        vae = load_video_vae(path)
        vae.patcher.cached_patcher_init = (reload_video_patcher, (path, None))
        return (vae,)
