"""Resolve checking findings to actual frozen sources or derived prompt fields."""
from .production_brief_display import source_owner


def known_paths(value, prefix=""):
    paths = {prefix} if prefix else set()
    if isinstance(value, dict):
        for key, child in value.items():
            paths.update(known_paths(child, f"{prefix}.{key}" if prefix else key))
    elif isinstance(value, list):
        for index, child in enumerate(value):
            paths.update(known_paths(child, f"{prefix}.{index}"))
    return paths


def bind_finding_paths(snapshot, directions, findings):
    paths = known_paths(snapshot) | known_paths(directions, "directions")
    paths |= {"compiledPrompt", "compiledPrompt.integrated_multimodal_description",
        "compiledPrompt.overall_soundscape", "compiledPrompt.non_diegetic_music"}
    translations = {item["path"]: item["path"] for item in directions["fields"]}
    for index, item in enumerate(directions["fields"]):
        translations[f"directions.fields.{index}.english"] = item["path"]
        translations[f"directions.fields.{index}"] = item["path"]
    paths |= set(translations)
    english = snapshot["languageContract"]["contentLocale"] == "en-US"
    bound = []
    for finding in findings:
        if finding.path not in paths:
            raise ValueError(f"fidelity finding path is not a frozen source or direction field: {finding.path}")
        source_path = translations.get(finding.path, finding.path)
        owner = source_owner(source_path, english)
        if source_path.startswith(("compiledPrompt", "directions")):
            owner = "Provider adapter" if english else "提供方适配器"
        bound.append(finding.model_dump(mode="json", by_alias=True) | {"sourcePath": source_path, "sourceOwner": owner})
    return bound
