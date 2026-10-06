"""Frozen, video-only VAE runtime policy shared by FL2VA and Ref2VA."""
from dataclasses import asdict, dataclass
from typing import Any


@dataclass(frozen=True)
class H3VAEPolicy:
    policy_id: str = "h3-int8-video-fp16-audio-bf16.v1"
    loader: str = "PlotloomH3VideoVAELoader"
    loader_version: int = 1
    video_checkpoint: str = "minimax_h3_video_vae_int8_convrot.safetensors"
    video_sha256: str = "52a2c8c73583c86e4f41cdcce3a6ad0ea562987bc0bf3d60a0cef5f5c8e60c0e"
    video_compute_dtype: str = "float16"
    audio_checkpoint: str = "minimax_h3_audio_vae_fp32.safetensors"
    audio_compute_dtype: str = "bfloat16"
    fp16_accumulation: bool = True

    def snapshot(self) -> dict[str, Any]:
        return asdict(self)


ADOPTED_VAE_POLICY = H3VAEPolicy()


def bind_vae_policy(graph: dict[str, Any], policy: H3VAEPolicy) -> None:
    if policy != ADOPTED_VAE_POLICY:
        raise ValueError("unsupported frozen H3 VAE policy")
    graph["105:11"] = {"class_type": policy.loader, "inputs": {
        "vae_name": policy.video_checkpoint, "policy": policy.policy_id,
    }}
    graph["105:24"] = {"class_type": "VAELoader", "inputs": {
        "vae_name": policy.audio_checkpoint,
    }}


def require_vae_runtime(object_info: object) -> None:
    """The maintained node advertises its policy only on the correct runtime."""
    policy = ADOPTED_VAE_POLICY
    try:
        required = object_info[policy.loader]["input"]["required"]
        if (policy.video_checkpoint not in required["vae_name"][0]
                or required["policy"][0] != [policy.policy_id]):
            raise ValueError
    except (KeyError, IndexError, TypeError, ValueError):
        raise ValueError("H3 video VAE runtime policy unavailable") from None
