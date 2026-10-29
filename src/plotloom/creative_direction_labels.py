"""Built-in semantic selections project readable wording; custom prose stays exact."""
from __future__ import annotations

BUILTIN_ENGLISH = {
    "subject": {"都市": "Contemporary urban", "科幻": "Science fiction", "奇幻": "Fantasy", "历史": "Historical"},
    "narrative": {"剧情": "Drama", "悬疑": "Mystery", "爱情": "Romance", "喜剧": "Comedy", "冒险": "Adventure", "惊悚": "Thriller"},
    "representation": {"真人写实": "Live action", "2D 动画": "2D animation", "3D 动画": "3D animation"},
    "treatment": {"水墨": "Ink wash", "水彩": "Watercolor", "复古": "Retro", "赛博朋克": "Cyberpunk"},
    "lighting": {"暖色": "Warm colors", "冷色": "Cool colors", "低饱和": "Low saturation", "高反差": "High contrast"},
}


def composed_direction(selections, detail: str | None, language: str) -> str | None:
    words = [BUILTIN_ENGLISH.get(item.group, {}).get(item.value, item.value)
        if language == "en-US" else item.value for item in selections]
    return ("; " if language == "en-US" else "；").join(words + ([detail] if detail else [])) or None
