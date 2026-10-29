"""Validate or render advisory prose against one frozen Source topology."""
import argparse
import html
import json
from pathlib import Path
from plotloom.branch_suggestions import BranchSuggestion, bind_branches
from plotloom.language_policy import assert_candidate_report_language, report_locale


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("validate", "render"))
    parser.add_argument("candidate", type=Path)
    parser.add_argument("--request", required=True, type=Path)
    args = parser.parse_args()
    request = json.loads(args.request.read_text(encoding="utf-8"))
    if request.get("stage") != "branches":
        parser.error("request must be a frozen branches package")
    candidate = json.loads(args.candidate.read_text(encoding="utf-8"))
    assert_candidate_report_language(candidate, request["inputArtifacts"])
    proposal = BranchSuggestion.model_validate(candidate)
    bind_branches(proposal, request["source"]["topology"])
    if args.command == "validate":
        print("valid advisory branch suggestion")
        return
    en = report_locale(request["inputArtifacts"]) == "en"
    title = "Story branches and endings · pending creator review" if en else "剧情分支与结局 · 待作者审阅"
    chunks = [f'<!doctype html><html lang="{"en-US" if en else "zh-CN"}"><meta charset="utf-8"><title>{title}</title><style>body{{max-width:900px;margin:40px auto;padding:24px;font:18px/1.7 system-ui;background:#10121a;color:#eee}}h1,h2{{line-height:1.3}}p{{white-space:pre-wrap}}</style><h1>{title}</h1>']
    def section(title, text):
        chunks.append(f'<h2>{html.escape(title)}</h2><p>{html.escape(text)}</p>')
    for node in proposal.nodes:
        section(node.title, node.summary)
    for choice in proposal.choices:
        section("Playback question" if en else "播放时显示的问题", choice.question)
        for option in choice.options:
            section(option.label, option.consequence)
    for join in proposal.joins:
        section("Story reconciliation" if en else "剧情汇合说明", join.reconciliation)
    for note in proposal.clarifications:
        section("Clarification for review" if en else "待确认说明", note)
    print("".join(chunks) + "</html>")


if __name__ == "__main__":
    main()
