"""The three fixed Chinese Alpha workloads and exact native sample matrix."""
from dataclasses import dataclass
from plotloom.brief_contracts import ProjectBrief
ALPHA_ACCEPTANCE_VERSION = "alpha_native_codex_three_story.v3"
ALPHA_EXPECTED_REVIEW_COUNT = 3
NATIVE_OPERATIONS = ("outline", "branches", "characters", "art", "script", "storyboard", "bridge-intent", "bridge-presentation")

@dataclass(frozen=True)
class AlphaStory:
    """A versioned Chinese brief whose stable alias never names a provider."""

    alias: str
    version: str
    brief: ProjectBrief

def _brief(*, title: str, synopsis: str, genre: str, visual_style: str) -> ProjectBrief:
    return ProjectBrief(
        title=title,
        synopsis=synopsis,
        genre=genre,
        visual_style=visual_style,
        language="zh-CN",
        target_playthrough_seconds=60,
        decision_points_per_path=2,
        ending_count=3,
        node_budget=9,
        max_out_degree=3,
        desired_join_count=1,
        shots_per_scene_min=1,
        shots_per_scene_max=4,
    )

ALPHA_STORIES: tuple[AlphaStory, ...] = (
    AlphaStory(
        alias="story-01",
        version="v1",
        brief=_brief(
            title="雾港回声",
            synopsis="失忆的摆渡人黎明前在雾港收到一封来自未来自己的信，必须决定交出船钟还是带它穿过封港线。",
            genre="悬疑",
            visual_style="克制的东方水墨电影感",
        ),
    ),
    AlphaStory(
        alias="story-02",
        version="v1",
        brief=_brief(
            title="最后一盏灯",
            synopsis="山城停电前，值班电工发现每一次恢复街区照明都会抹去一户人家的记忆，必须决定把最后电量交给医院还是旧剧院。",
            genre="科幻伦理",
            visual_style="潮湿夜色中的钠灯橙光与深蓝阴影",
        ),
    ),
    AlphaStory(
        alias="story-03",
        version="v1",
        brief=_brief(
            title="雪线来信",
            synopsis="高原邮差在暴雪封路前收到三封互相矛盾的遗书，必须决定先送出哪一封，并承担另外两条命运被改写的后果。",
            genre="人性剧情",
            visual_style="高反差雪原、红色邮包与低饱和人物特写",
        ),
    ),
)

SAMPLE_KEYS = tuple(f"{story.alias}-repeat-{repeat:02}" for story in ALPHA_STORIES for repeat in range(1, 4))
REVIEW_SAMPLE_KEYS = tuple(f"{story.alias}-repeat-01" for story in ALPHA_STORIES)
