"""Index native Linux normalizer and observed text-to-emotion dispatch."""

import time
from .catalog import EMOTIONS
from .protocol import ExecutionEvidence


def generate(request, emit):
    from indextts.infer_v2 import IndexTTS2
    text_mode = request.delivery.mode == "text"
    settings = request.snapshot['settings']
    model = IndexTTS2(cfg_path=request.runtime["modelDir"] + "/config.yaml", model_dir=request.runtime["modelDir"],
                     use_fp16=settings['dtype'] == 'float16', use_cuda_kernel=settings['useCudaKernel'],
                     use_deepspeed=settings['useDeepspeed'], use_qwen_emo=text_mode,
                     aux_paths=request.runtime["auxPaths"])
    if text_mode:
        classify = model.qwen_emo.inference

        def observed_classification(description):
            started = time.monotonic()
            emit("phase", phase="interpreting")
            scores = classify(description)
            if tuple(scores) != EMOTIONS:
                raise ValueError("audio.invalid")
            vector = [float(scores[key]) for key in EMOTIONS]
            evidence = ExecutionEvidence(mode="text", rawVector=vector, effectiveVector=vector,
                                         classifierSeconds=time.monotonic() - started)
            emit("delivery", evidence=evidence)
            emit("phase", phase="synthesizing")
            return scores

        # Observe the actual helper without changing its scores or RNG behavior.
        model.qwen_emo.inference = observed_classification
    else:
        evidence = ExecutionEvidence(mode=request.delivery.mode, effectiveVector=request.delivery.vector)
        emit("delivery", evidence=evidence)
    emit("phase", phase="interpreting" if text_mode else "synthesizing")
    model.infer(spk_audio_prompt=request.reference, text=request.text, output_path=request.output,
                emo_vector=request.delivery.vector, use_emo_text=text_mode, emo_text=request.delivery.description,
                emo_alpha=settings['emoAlpha'], use_random=settings['useRandom'], verbose=False)
