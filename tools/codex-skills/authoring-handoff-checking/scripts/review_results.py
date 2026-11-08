"""Validate source-bound semantic review reports; not semantic correctness."""
import argparse
import hashlib
import json
from common import digest, pointer, read, verify_case

ASPECTS = {"hook", "dialogue", "visibility_state", "action_ownership", "sound"}
DECISIONS = {"pass", "fail", "needs_review"}


def validate(case_file, report):
    case = read(case_file)
    ids = verify_case(case)
    if report.get("schemaVersion") != 1 or report.get("skillVersion") != case["skillVersion"] or report.get("caseId") != case["caseId"] or report.get("caseSha256") != digest(case_file):
        raise ValueError("report does not bind the case")
    if report.get("decision") not in DECISIONS or not report.get("summary"):
        raise ValueError("invalid decision or summary")
    reviewer = report.get("reviewer", {})
    if not reviewer.get("model") or not reviewer.get("reasoning"):
        raise ValueError("reviewer identity missing")
    checks = report.get("checks", [])
    if len(checks) != len(ASPECTS) or {x.get("aspect") for x in checks} != ASPECTS:
        raise ValueError("all five aspects must be assessed exactly once")
    ev = {x["id"]: x for x in case["evidence"]}
    docs = {k: read(v["file"]) for k, v in case["sources"].items()}
    def refs_ok(refs):
        if not refs:
            raise ValueError("evidence references required")
        for ref in refs:
            if ref.get("id") not in ids:
                raise ValueError("unknown evidence id")
            row = ev[ref["id"]]
            sub = ref.get("pointer")
            if not isinstance(sub, str) or (sub and not sub.startswith("/")):
                raise ValueError("invalid relative pointer")
            pointer(docs[row["source"]], row["pointer"] + sub)
    for check in checks:
        if check.get("status") not in DECISIONS or not check.get("notes"):
            raise ValueError("invalid check")
        refs_ok(check.get("evidence", []))
    findings = report.get("findings", [])
    for f in findings:
        if f.get("aspect") not in ASPECTS or f.get("severity") not in {"material", "minor", "uncertain"} or not f.get("claim") or f.get("origin") not in {"source", "transport", "generation", "unknown"}:
            raise ValueError("invalid finding")
        refs_ok(f.get("evidence", []))
        if f["severity"] == "material" and len({r["id"] for r in f["evidence"]}) < 2:
            raise ValueError("material finding needs two evidence IDs")
    material = any(f["severity"] == "material" for f in findings)
    uncertain = any(f["severity"] == "uncertain" for f in findings)
    statuses = {x["status"] for x in checks}
    if report["decision"] == "pass" and (material or uncertain or statuses != {"pass"}):
        raise ValueError("pass contains unresolved checks or findings")
    if report["decision"] == "fail" and (not material or "fail" not in statuses):
        raise ValueError("fail requires material finding and failed check")
    if report["decision"] == "needs_review":
        if material or "fail" in statuses:
            raise ValueError("needs_review cannot hide a material failure")
        if not (uncertain or "needs_review" in statuses):
            raise ValueError("needs_review requires uncertainty")
    failed_aspects = {x["aspect"] for x in checks if x["status"] == "fail"}
    material_aspects = {f["aspect"] for f in findings if f["severity"] == "material"}
    if failed_aspects != material_aspects:
        raise ValueError("failed checks and material findings must match by aspect")
    if not isinstance(report.get("limitations"), list):
        raise ValueError("limitations required")
    return True


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("case")
    p.add_argument("report")
    args = p.parse_args()
    validate(args.case, read(args.report))
    print("PASS: structure, evidence pointers, case binding and current source hashes; semantic claims not verified")


if __name__ == "__main__":
    main()
