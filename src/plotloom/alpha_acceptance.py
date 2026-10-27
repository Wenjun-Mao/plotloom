"""Current native Alpha CLI; optional protocol conformance remains independent."""
import argparse
import json
import subprocess
import sys
from pathlib import Path

from .alpha_campaign import load_campaign, prepare_campaign, write_private_json
from .alpha_provenance import source_checkout_root
from .alpha_publication import load_private_review_manifest, publish_native_review_pack
from .alpha_receipts import native_qualification_issue_codes
from .alpha_reviews import codex_external_review_receipt


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    prepare = commands.add_parser("prepare", help="Freeze all nine disposable sample identities before admission")
    prepare.add_argument("--campaign", type=Path, required=True)
    prepare.add_argument("--codex", type=Path, required=True)
    prepare.add_argument("--preflight-proof", type=Path, required=True)
    for name in ("run", "cancel", "resume"):
        command = commands.add_parser(name, help="Use the source-owned isolated workbench for one exact sample")
        command.add_argument("--campaign", type=Path, required=True)
        command.add_argument("--sample", required=True)
        if name == "resume":
            command.add_argument("--project", required=True)
            command.add_argument("--run", required=True)
            command.add_argument("--revision", type=int, required=True)
            command.add_argument("--pause-hash", required=True)
    publish = commands.add_parser("publish-review", help="Atomically publish the three preselected blind samples")
    publish.add_argument("--campaign", type=Path, required=True)
    publish.add_argument("--review-directory", type=Path, required=True)
    review = commands.add_parser("review-gate", help="Check independent blinded scores against exact published hashes")
    review.add_argument("--private-mapping", type=Path, required=True)
    review.add_argument("--scores", type=Path, nargs="+", required=True)
    review.add_argument("--receipt", type=Path, required=True)
    gate = commands.add_parser("qualify", help="Require nine installations, 60/72 first passes and independent content review")
    gate.add_argument("--campaign", type=Path, required=True)
    gate.add_argument("--review-receipt", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        if args.command == "prepare":
            campaign = prepare_campaign(args.campaign, args.codex, args.preflight_proof)
            print(json.dumps({"version": campaign.version, "samples": len(campaign.samples),
                "commit": campaign.source["commit"], "contractHash": campaign.contract_hash}))
        elif args.command in {"run", "cancel", "resume"}:
            root = source_checkout_root()
            load_campaign(args.campaign, check_source=True)
            runtime = root / "services/creator_workbench/alpha_native_runtime.py"
            if not runtime.is_file():
                raise ValueError("native qualification requires its source-owned workbench service")
            command = [sys.executable, str(runtime), "--campaign", str(args.campaign), "--sample", args.sample]
            if args.command == "cancel":
                command.append("--cancel")
            if args.command == "resume":
                from .alpha_pause import QualificationResume
                request = QualificationResume(project_id=args.project, run_id=args.run,
                    revision=args.revision, snapshot_hash=args.pause_hash)
                command.extend(["--resume-project", str(request.project_id), "--resume-run", str(request.run_id),
                    "--resume-revision", str(request.revision), "--pause-hash", request.snapshot_hash])
            return subprocess.run(command, cwd=root, check=False).returncode
        elif args.command == "publish-review":
            paths, _mapping = publish_native_review_pack(args.campaign, args.review_directory)
            print(json.dumps({"reviewDirectory": str(args.review_directory), "samples": len(paths)}))
        elif args.command == "review-gate":
            pack = load_private_review_manifest(args.private_mapping)
            reviews = [json.loads(path.read_bytes()) for path in args.scores]
            receipt = codex_external_review_receipt(reviews, review_pack=pack)
            write_private_json(args.receipt, receipt.model_dump(mode="json", by_alias=True))
            print(receipt.gate.model_dump_json(by_alias=True))
            return 0 if receipt.gate.passed else 1
        else:
            return _qualify(args.campaign, args.review_receipt)
    except (ValueError, OSError, subprocess.SubprocessError):
        # Arbitrary file/CLI/reviewer data must not cross the public receipt/log boundary.
        print("native Alpha refused: invalid or unavailable frozen qualification input", file=sys.stderr)
        return 2
    return 0


def _qualify(root, review_receipt_path):
    from .alpha_review_contracts import CodexExternalReviewReceipt
    from .alpha_reviews import codex_external_review_gate
    campaign = load_campaign(root)
    receipts = [json.loads((root / "evidence" / sample.sample_id / "outcome/receipt.json").read_bytes())
        for sample in campaign.samples]
    issues = set(native_qualification_issue_codes(receipts))
    pack = load_private_review_manifest(root / "private/review-mapping.private.json", campaign_root=root)
    review = CodexExternalReviewReceipt.model_validate_json(review_receipt_path.read_bytes())
    gate = codex_external_review_gate((sheet.model_dump(mode="json", by_alias=True) for sheet in review.reviews), review_pack=pack)
    if (not gate.passed or gate != review.gate or pack.commit != campaign.source["commit"]
            or pack.contract_hash != campaign.contract_hash
            or any(row["commit"] != campaign.source["commit"] or row["contractHash"] != campaign.contract_hash
                or row["profileHash"] != campaign.source["profileHash"] for row in receipts)):
        issues.add("alpha.external_review")
    print(json.dumps({"version": campaign.version, "commit": campaign.source["commit"],
        "contractHash": campaign.contract_hash, "issueCodes": sorted(issues), "passed": not issues}))
    return 1 if issues else 0


if __name__ == "__main__":
    raise SystemExit(main())
