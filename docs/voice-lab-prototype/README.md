# Voice Lab interaction prototype

Open [index.html](index.html) locally in a browser. If the browser blocks local
files, run `python3 -m http.server 8897 --bind 127.0.0.1` from this directory
and visit `http://127.0.0.1:8897/`. It is a standalone, non-production UI study
for the synthetic-first character voice workflow.
The lab is not bound to a named Plotloom character or project. Its four bundled
samples are an example audition set, not a fixed product candidate count.

The four WAVs are the actual 2026-09-26 Qwen3-TTS VoiceDesign candidates from
Spark, all speaking the same Chinese audition line. Their 32-kHz mono PCM16
copies are included beside the page so playback works without a service.
The original 24-kHz float WAVs, model weights, full instructions, seed and
hash manifest remain under
`/home/wjmao/services/qwen3-tts-trial/experiments/2026-09-26/` on Spark.
Candidate A also has a bounded, user-accepted two-shot H3 trial recorded in
`/home/wjmao/services/spark-comfyui/data/output/experiments/h3-ref2va-qwen-voice-a-2026-09-26/`.

The page permits playback, blind shuffling, design-note reveal, and choosing
two samples for quick switching. Only one sample plays at a time. The editable
brief, audition line, and 2/4/6/8
candidate-count selector illustrate a future generation form; those counts are
prototype options, not an agreed backend limit. The Generate button is
intentionally disabled, and changing these controls never alters the four
saved samples. No backend request, project write, permanent selection, or local
storage is involved.
The blind shuffle reduces presentation-order bias but does not level-match the
samples or constitute a controlled listening study. The earlier H3 trial of
Candidate A is retained as evidence above, not presented as a current status or
decision in the audition interface. There is intentionally no "confirm
selection" action until a future workflow gives it a defined effect.

This is a design prototype, not delivery authority for Plotloom. The
[withheld handoff draft](../verification/2026-09-26-voice-candidate-handoff-draft.md)
holds the product boundary and open decisions. Do not send it to the director
until the owner releases the hold.
