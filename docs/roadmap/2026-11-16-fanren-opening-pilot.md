# 《凡人修仙传》 opening pilot — source preparation

## Current status

Source preparation complete. The owner agreed to use the first three chapters
as the starting scope for one opening pilot, with final pacing/length to be
decided during outline authoring. The next manual workflow is `novel-outline`;
it has not been invoked by this source-preparation assignment.

| Claim | Required evidence | Fresh media | Status |
| --- | --- | --- | --- |
| Repo-local input covers only chapters1–3 | Chapter headings and exact source-boundary comparison | None | PASS:3 headings; chapter4 excluded |
| Source wording is preserved | Excerpt equals the original prefix after newline normalization only | None | PASS:wording and original typos unchanged |
| Original manuscript is unchanged | Original size/mtime retained; read-only extraction | None | PASS |

Working directory: this repository. Deliverable:
[凡人修仙传-前三章.txt](凡人修仙传-前三章.txt). Root owns preparation and scratch
cleanup. Stop after source preparation; no outline, screenplay, reference images,
TTS or video generation is authorized by this step. The previous story's
autonomous skill exception does not carry over.

## Source binding

- Original: `/Users/wjmao/Downloads/《凡人修仙传》.txt`.
- Original bytes:22,576,630; UTF-8.
- Original SHA-256:
  `c306ad6ad125e5b64362d13955c6646692fb0ea93f3eaff895a898a1b2172e9a`.
- Extracted source lines1–112, including the book title and all of chapters1–3;
  the final blank chapter-separator line is omitted.
- First excluded heading: `第四章 炼骨崖`.
- Repo excerpt:18,616 bytes, UTF-8 with LF line endings and one final newline.
- Excerpt SHA-256:
  `255f64920a0882526ba75cabd4fa6fdb144c8986a1c89b42542b46aec8f22761`.

| Chapter | Body characters, including punctuation |
| --- | ---: |
| 第一章 山边小村 | 2,599 |
| 第二章 青牛镇 | 2,132 |
| 第三章 七玄门 | 1,769 |

The story input ends as the children are brought to the bamboo slope for
selection. The test result and later cultivation events are outside this scope.
韩立 is ten years old in this excerpt. Preserve those source facts rather than
importing later-book knowledge or silently changing character ages.

The manuscript includes spelling/wording inconsistencies such as 仙霞山/彩霞山,
`zhan有`, and 韩理/韩立. Extraction preserves them. Any later editorial
normalization belongs in the authoring decisions, not a silent source rewrite.

Verification was deterministic extraction/encoding/boundary comparison and
documentation diff review. No application behavior changed; no application
suite, provider call, CI or push was requested or run.
