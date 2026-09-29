"""Compare IndexTTS2's pinned text front end with either upstream backend.

Run on Spark in the isolated IndexTTS2 trial environment. This script never
loads a model or touches the live Voice Lab.
"""

from __future__ import annotations

import argparse
import json
import subprocess
from pathlib import Path


SOURCE_REVISION = "ee40fa7d6c6b8a2c7f06105f9f1e65775b74868c"
CASES = (
    ("neutral", "灯塔的备用电源已经接通。我们还有十分钟检查航道。"),
    ("urgent", "等等，别打开那扇门！控制台还在报警，先把电源切断！"),
    ("gentle", "我知道你害怕。先跟着我的声音，慢慢呼吸，我们一起出去。"),
    ("quantity", "把三号阀门调到百分之七十五，再等二十秒。"),
    ("digits", "把3号阀门调到75%，再等20秒。"),
    ("time", "现在是凌晨两点零五分。我们在06:30之前离开。"),
    ("date", "2026年9月29日，第二艘船抵达。"),
    ("temperature", "舱内温度降到零下12度，氧气只剩15%。"),
    ("distance", "再走1.5公里，就到B区的4号门。"),
    ("code", "输入验证码2048，然后按确认。"),
    ("currency", "这件设备要价￥1,280.50。"),
    ("name", "林默，别让王·阿宁一个人进去。"),
    ("english_name", "Alex，去检查A-17区的备用电源。"),
    ("acronym", "AI系统刚把GPS坐标传给了控制台。"),
    ("mixed_language", "请打开backup channel，马上回应我。"),
    ("pinyin", "这里的‘行’读作 <行|xing2>，别念错。"),
    ("ellipsis", "我本以为……算了，现在不是解释的时候。"),
    ("interrupt", "不，等等——你刚才说她还活着？"),
    ("quoted", "她说：‘别回头。’然后无线电就断了。"),
    ("numbered_choice", "第一条路通向甲板；第二条路通向货舱。"),
    ("interjection_a", "啊，我想起来了！那个人还在船上。"),
    ("interjection_en", "嗯……先别说话，听门外的脚步声。"),
    ("interjection_ai", "唉，这不是我们约定的路线。"),
    ("interjection_o", "哦，原来你一直都知道。"),
    ("erhua", "门口那盏灯一会儿亮，一会儿灭。"),
    ("erhua_dialect", "待会儿咱们从这儿绕过去。"),
    ("repeated_fillers", "呃，我，我不是那个意思……你先听我说。"),
    ("breathless", "快！往右边跑，别回头，别停！"),
    ("english", "Stay behind me. We have ten minutes."),
    ("english_digits", "The door code is 2048. Meet me at 6:30."),
)


def select_wetext_backend() -> None:
    """Select the exact trial adapter; upstream chooses this on Mac/Windows."""
    from indextts.utils.front import TextNormalizer
    from wetext import Normalizer

    def load(self: TextNormalizer) -> None:
        if self.zh_normalizer is None or self.en_normalizer is None:
            self.zh_normalizer = Normalizer(remove_erhua=False, lang="zh", operator="tn")
            self.en_normalizer = Normalizer(lang="en", operator="tn")

    TextNormalizer.load = load


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-dir", type=Path, required=True)
    parser.add_argument("--backend", choices=("linux", "wetext"), required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    revision = subprocess.check_output(
        ["git", "-C", str(args.source_dir), "rev-parse", "HEAD"], text=True
    ).strip()
    if revision != SOURCE_REVISION:
        raise ValueError("IndexTTS2 source revision changed")
    if args.backend == "wetext":
        select_wetext_backend()
    from indextts.utils.front import TextNormalizer

    normalizer = TextNormalizer()
    normalizer.load()
    cases = []
    for case_id, original in CASES:
        normalized = normalizer.normalize(original)
        if not normalized:
            raise ValueError(f"Empty normalization result for {case_id}")
        cases.append({"id": case_id, "original": original, "normalized": normalized})
    result = {
        "sourceRevision": revision,
        "backend": args.backend,
        "cases": cases,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"{args.backend}: {len(cases)} cases -> {args.output}")


if __name__ == "__main__":
    main()
