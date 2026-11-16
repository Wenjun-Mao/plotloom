"""Image-only Ref2VA readiness against the actual installed native node schema."""
from .contracts import GatewayError
from .vae_policy import require_vae_runtime
from .voice_reference import VOICE_MODEL


def preflight_references(client, count: int, audio_count: int = 0) -> None:
    client._get_json("/system_stats", code="comfy_unavailable")
    info = client._get_json("/object_info", code="comfy_reference_profile_unavailable")
    try:
        require_vae_runtime(info)
        unets = info["UNETLoader"]["input"]["required"]["unet_name"][0]
        clips = info["CLIPLoader"]["input"]["required"]["clip_name"][0]
        vaes = info["VAELoader"]["input"]["required"]["vae_name"][0]
        reference = info["MiniMaxH3ReferenceToVideo"]
        images = reference["input"]["optional"]["ref_images"]
        template = images[1]["template"]
        guide = info["MiniMaxH3AddGuide"]
        if (not isinstance(unets, list) or VOICE_MODEL not in unets
                or not isinstance(clips, list) or "qwen3vl_32b_minimax_h3_nvfp4_awq.safetensors" not in clips
                or not isinstance(vaes, list) or "minimax_h3_audio_vae_fp32.safetensors" not in vaes
                or images[0] != "COMFY_AUTOGROW_V3" or template["prefix"] != "ref_image_"
                or template["min"] != 0 or type(template["max"]) is not int
                or not 1 <= count <= min(9, template["max"])
                or template["input"]["required"]["ref_image"][0] != "IMAGE"
                or reference["output"] != ["CONDITIONING", "LATENT"]
                or guide["output"] != ["CONDITIONING"]
                or guide["input"]["required"]["positive"][0] != "CONDITIONING"
                or guide["input"]["required"]["latent"][0] != "LATENT"
                or guide["input"]["required"]["frame_idx"][0] != "INT"
                or guide["input"]["optional"]["image"][0] != "IMAGE"
                or guide["input"]["optional"]["vae"][0] != "VAE"
                or not {"LoadImage", "PrimitiveInt", "KSamplerSelect", "BasicScheduler",
                        "BasicGuider", "SamplerCustomAdvanced"}.issubset(info)):
            raise ValueError
        if audio_count:
            audios = reference["input"]["optional"]["ref_audios"]
            audio_template = audios[1]["template"]
            if (audios[0] != "COMFY_AUTOGROW_V3"
                    or audio_template["prefix"] != "ref_audio_"
                    or audio_template["min"] != 0 or type(audio_template["max"]) is not int
                    or not 1 <= audio_count <= min(3, audio_template["max"])
                    or audio_template["input"]["required"]["ref_audio"][0] != "AUDIO"
                    or reference["input"]["optional"]["audio_vae"][0] != "VAE"
                    or "LoadAudio" not in info):
                raise ValueError
    except (KeyError, IndexError, TypeError, ValueError) as error:
        raise GatewayError("comfy_reference_profile_unavailable", 503) from error
