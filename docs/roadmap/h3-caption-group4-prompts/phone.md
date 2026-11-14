# Realistic phone listener

Source: [retained prompt](../../../.local/ref2va/caption-recurrence-group2-20261113/campaign-v01/fixtures/g1-02-realistic/prompt.txt) · [fixture manifest](../../../.local/ref2va/caption-recurrence-group2-20261113/campaign-v01/fixtures/g1-02-realistic/manifest.json). Current full SHA-256: `ec47a06c6cd1e6f01bc1aed28f13e0d357eb323b2eefabf3944bc716cbaaeca6`.

Both short prompts drop the two rendering instructions about skin texture and physically plausible lighting. They retain photorealistic live action, the hallway and opening position, the continuous steady medium shot, the closed-mouth listener’s one small nod and the single female caller’s Mandarin line. The one picture is an ordered reference at 0 ms. The requested duration is 5.00 seconds.

## Current full

```text
Photorealistic live-action cinematography, natural skin texture and physically plausible lighting. <Picture 1> establishes the opening position and hallway. One continuous, steady medium shot. The man listens with the phone held near his ear, keeps his mouth closed, and gives one small nod. A single adult female voice comes from the phone in natural Mandarin and says once: <d>[Chinese] 这边已经收拾好了，你可以过来了。</d> The man does not speak. Quiet indoor room tone. No music, no other intelligible voices, no subtitles, closed captions, speech bubbles, or burned-in text.
```

## Template full

```text
Generation mode: Ref2VA
Duration: 5.00 seconds

subject_definitions:
<Subject 1> is the man listening in the hallway. The only speaker (S1) is the offscreen adult woman on the phone. <Picture 1> gives the man's opening position and the hallway.

summary:
A photorealistic live-action shot holds on the man as he listens to the woman speaking over the phone.

retention_analysis:
<Picture 1>, Shot 1: partially_preserved — keep the hallway and the man's opening position, with natural skin texture and physically plausible lighting. Allow his head to move for the nod.

detailed_description:
[Shot 1] 0.00–5.00 s. One continuous, steady medium shot. <Subject 1> holds the phone near his ear, keeps his mouth closed and gives one small nod. He does not speak. The adult woman (S1) speaks once through the phone in natural Mandarin: <d>[Chinese] 这边已经收拾好了，你可以过来了。</d>
No music, no other intelligible voices, no subtitles, closed captions, speech bubbles, or burned-in text.

overall_soundscape: Quiet indoor room tone.

non_diegetic_music: N/A.
```

## Current short

```text
Photorealistic live action. <Picture 1> gives the opening position and hallway. One continuous, steady medium shot. The silent man holds his phone near his ear, mouth closed, and gives one small nod. An adult woman speaks once through the phone in natural Mandarin: <d>[Chinese] 这边已经收拾好了，你可以过来了。</d> Quiet indoor room tone. No music, no other intelligible voices, no subtitles, closed captions, speech bubbles, or burned-in text.
```

## Template short

```text
Generation mode: Ref2VA
Duration: 5.00 seconds

subject_definitions:
<Subject 1> is the male listener. The adult female caller (S1) is offscreen. <Picture 1> gives the opening position and hallway.

summary:
Photorealistic live action. A man listens to a phone call.

retention_analysis:
<Picture 1>, Shot 1: partially_preserved — keep the hallway and opening position, allowing his nod.

detailed_description:
[Shot 1] 0.00–5.00 s. One continuous, steady medium shot. <Subject 1> holds the phone near his ear, mouth closed, and nods once slightly. The woman (S1) speaks once through the phone in natural Mandarin: <d>[Chinese] 这边已经收拾好了，你可以过来了。</d>
No music, no other intelligible voices, no subtitles, closed captions, speech bubbles, or burned-in text.

overall_soundscape: Quiet indoor room tone.

non_diegetic_music: N/A.
```
