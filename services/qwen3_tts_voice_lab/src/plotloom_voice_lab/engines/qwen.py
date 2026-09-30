"""Pinned Qwen creation/reuse; imported only by the job subprocess."""

def generate(request, emit):
    import soundfile as sf
    import torch
    from qwen_tts import Qwen3TTSModel
    settings = request.snapshot['settings']
    model = Qwen3TTSModel.from_pretrained(request.runtime["modelDir"], device_map="cuda:0",
                                        dtype=getattr(torch, settings['dtype']), attn_implementation=settings['attention'])
    if request.snapshot["engineId"] == "qwen_design":
        emit("phase", phase="synthesizing")
        waves, rate = model.generate_voice_design(text=request.text, language=settings['language'],
            instruct=request.direction, do_sample=settings['doSample'])
    else:
        emit("delivery", evidence={"mode": "none"})
        prompt = model.create_voice_clone_prompt(ref_audio=request.reference, ref_text=request.referenceText,
                                                x_vector_only_mode=settings['xVectorOnly'])
        emit("phase", phase="synthesizing")
        waves, rate = model.generate_voice_clone(text=request.text, language=settings['language'], voice_clone_prompt=prompt, do_sample=settings['doSample'])
    if len(waves) != 1:
        raise ValueError("audio.invalid")
    sf.write(request.output, waves[0], rate, subtype="FLOAT")
