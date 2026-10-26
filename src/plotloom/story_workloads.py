"""Source-owned fixed story workloads shared by application probes and fixtures."""
from plotloom.brief_contracts import ProjectBrief

# Exercises three endings, two decisions per path and one explicit JOIN while
# retaining the exact frozen nine-node, one-to-four-shots-per-scene Brief.
FIXED_CHINESE_BRIEF = ProjectBrief(
    title="雾港回声",
    synopsis="失忆的摆渡人黎明前在雾港收到一封来自未来自己的信，必须决定交出船钟还是带它穿过封港线。",
    genre="悬疑",
    visual_style="克制的东方水墨电影感",
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
