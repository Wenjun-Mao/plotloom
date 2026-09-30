"""Pinned MOSS VoiceGenerator with the reviewed local codec and decoding."""

def generate(request, emit):
    import soundfile as sf
    import torch
    from transformers import AutoModel, AutoProcessor
    settings = request.snapshot["settings"]
    torch.backends.cuda.enable_cudnn_sdp(False)
    # This pinned custom processor forwards unknown kwargs into ProcessorMixin.
    # Offline loading is enforced by the runner environment, not this kwarg.
    processor = AutoProcessor.from_pretrained(request.runtime["modelDir"], codec_path=request.runtime["codecDir"],
                                             trust_remote_code=True, normalize_inputs=True)
    processor.audio_tokenizer = processor.audio_tokenizer.to("cuda")
    model = AutoModel.from_pretrained(request.runtime["modelDir"], trust_remote_code=True, local_files_only=True,
                                     attn_implementation=settings['attention'], dtype=getattr(torch, settings['dtype'])).to("cuda")
    model.eval()
    batch = processor([[processor.build_user_message(text=request.text, instruction=request.direction)]], mode="generation")
    emit("phase", phase="synthesizing")
    with torch.inference_mode():
        result = model.generate(input_ids=batch["input_ids"].to("cuda"), attention_mask=batch["attention_mask"].to("cuda"),
                                **{key: value for key, value in settings.items() if key not in {"dtype", "attention"}})
    messages = processor.decode(result)
    if len(messages) != 1 or not messages[0].audio_codes_list:
        raise ValueError("audio.invalid")
    audio = messages[0].audio_codes_list[0].detach().float().cpu().numpy().reshape(-1)
    sf.write(request.output, audio, int(processor.model_config.sampling_rate), subtype="FLOAT")
