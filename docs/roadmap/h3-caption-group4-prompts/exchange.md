# Hand-drawn conservatory exchange

Source: [retained prompt](../../../.local/ref2va/multistyle-screen-group1-20261113/campaign-v01/fixtures/g1-03-2d/prompt.txt) · [fixture manifest](../../../.local/ref2va/multistyle-screen-group1-20261113/campaign-v01/fixtures/g1-03-2d/manifest.json). Current full SHA-256: `0015b61331eb2689df5d06ea7a6b16c2d6fe800f70f27b22ca791536985ca34e`.

Both short prompts drop the three rendering instructions about clean linework, softly shaded color and coherent illustrated lighting. They retain hand-drawn 2D animation, the conservatory, both sightlines, left/right positions, shot sizes, the 3.50-second cut, the two Mandarin lines and the fading rain. The one picture is an ordered reference at 0 ms. The cut is specified in the prompt and the requested duration is 7.00 seconds.

## Current full

```text
Hand-drawn 2D animation, clean linework, softly shaded color, and coherent illustrated lighting. <Picture 1> establishes both people's opening positions in the conservatory. [Shot 1, 00:00.000–00:03.500] A steady medium-wide view of both people. The woman on the left looks at the man and says in Mandarin: <d>[Chinese] 雨停了吗？</d> [Shot 2, from 00:03.500] Cut to a steady medium shot favoring the man on the right. He looks toward the woman and replies in Mandarin: <d>[Chinese] 停了，我们走吧。</d> Each person speaks their own line once. Keep the same room and their left-right positions across the cut. Soft rain ambience fades naturally. No other intelligible voice, no music, no subtitles, closed captions, speech bubbles, or burned-in text.
```

## Template full

```text
Generation mode: Ref2VA
Duration: 7.00 seconds

subject_definitions:
<Subject 1> is the woman on the left (S1). <Subject 2> is the man on the right (S2). <Picture 1> establishes their opening positions in the conservatory.

summary:
In a hand-drawn 2D exchange the woman asks the man a question. A cut favors him as he replies.

retention_analysis:
<Picture 1>, Shots 1 and 2: partially_preserved — carry the same conservatory and left-right positions across the cut. Keep the clean linework, softly shaded color and coherent illustrated lighting while the framing changes.

detailed_description:
[Shot 1] 0.00–3.50 s. A steady medium-wide view of both people. <Subject 1> looks toward <Subject 2>. The woman (S1) asks once in Mandarin: <d>[Chinese] 雨停了吗？</d>
[Shot 2] At 00:03.500, cut to a steady medium shot favoring <Subject 2> on the right. He looks toward the woman. The man (S2) replies once in Mandarin: <d>[Chinese] 停了，我们走吧。</d>
No other intelligible voice, no music, no subtitles, closed captions, speech bubbles, or burned-in text.

overall_soundscape: Soft rain ambience fades naturally.

non_diegetic_music: N/A.
```

## Current short

```text
Hand-drawn 2D animation. <Picture 1> sets both people's opening positions in the conservatory. [Shot 1, 0.00–3.50 s] Steady medium-wide two-shot. The woman on the left looks at the man and asks once in Mandarin: <d>[Chinese] 雨停了吗？</d> [Shot 2, from 3.50 s] Cut to a steady medium shot favoring the man on the right. Looking toward her, he replies once in Mandarin: <d>[Chinese] 停了，我们走吧。</d> Keep the room and positions across the cut. Soft rain fades naturally. No other intelligible voice, no music, no subtitles, closed captions, speech bubbles, or burned-in text.
```

## Template short

```text
Generation mode: Ref2VA
Duration: 7.00 seconds

subject_definitions:
<Subject 1> is the woman on the left (S1), <Subject 2> the man on the right (S2). <Picture 1> sets their opening positions in the conservatory.

summary:
Hand-drawn 2D animation. The woman asks and the man replies.

retention_analysis:
<Picture 1>, Shots 1 and 2: partially_preserved — keep the room and left-right positions across the cut.

detailed_description:
[Shot 1] 0.00–3.50 s. Steady medium-wide two-shot. <Subject 1> looks at the man and asks once in Mandarin: <d>[Chinese] 雨停了吗？</d>
[Shot 2] At 00:03.500, cut to a steady medium shot favoring <Subject 2> on the right. Looking toward her, he replies once in Mandarin: <d>[Chinese] 停了，我们走吧。</d>
No other intelligible voice, no music, no subtitles, closed captions, speech bubbles, or burned-in text.

overall_soundscape: Soft rain fades naturally.

non_diegetic_music: N/A.
```
