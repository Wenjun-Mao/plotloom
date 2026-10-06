"""At most two sole managed submissions from retained qualification inputs.

Operator-only Spark script. Unknown results are durable and never replayed.
Outputs are private proof copies, not new approved creative assets.
"""
import argparse
import hashlib
import json
import subprocess
import sys
import time
from pathlib import Path

import requests

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "vae_qualification"))
from contract import fingerprint, save
from maintenance import assert_idle, lab_proof

ROOT = Path("/home/wjmao/services/spark-comfyui/experiments/h3-vae-d-adoption-20261006")
FROZEN = Path("/home/wjmao/services/spark-comfyui/experiments/h3-vae-qualification-2026-10-06-resumed/cases.json")
CASES_HASH = "b5971616b3a8edd89e4360000e617c10938ef9675fd5e0923c8e888f3430257b"
URL = "http://100.64.35.71:8090"


def stored_snapshot(job_id):
    script = """import sqlite3,sys
db=sqlite3.connect('file:/var/lib/plotloom-h3-gateway/gateway.sqlite3?mode=ro',uri=True)
print(db.execute('SELECT execution_snapshot_json FROM jobs WHERE id=?',(sys.argv[1],)).fetchone()[0])
"""
    result = subprocess.run(["docker", "exec", "plotloom-h3-gateway", "python", "-c", script, job_id],
                            check=True, capture_output=True, text=True)
    return json.loads(result.stdout)


def inspect_media(path, width, height):
    value = subprocess.run(["ffprobe", "-v", "error", "-show_entries",
        "format=duration:stream=codec_type,codec_name,width,height,nb_frames,r_frame_rate,sample_rate",
        "-of", "json", str(path)], check=True, capture_output=True, text=True)
    subprocess.run(["ffmpeg", "-v", "error", "-i", str(path), "-map", "0:v:0",
                    "-map", "0:a:0", "-f", "null", "-"], check=True, capture_output=True)
    probe = json.loads(value.stdout)
    video = next(item for item in probe["streams"] if item["codec_type"] == "video")
    audio = next(item for item in probe["streams"] if item["codec_type"] == "audio")
    assert (video["width"], video["height"], int(video["nb_frames"])) == (width, height, 124)
    assert video["r_frame_rate"] == "24/1" and audio["sample_rate"] == "32000"
    assert abs(float(probe["format"]["duration"]) - 124 / 24) < 0.15
    return probe


def existing_receipt(path, reconcile):
    if not path.exists():
        if reconcile: raise RuntimeError("No accepted canary to reconcile")
        return {"status": "running", "cap": 2, "casesHash": CASES_HASH, "calls": []}
    if not reconcile: raise RuntimeError("Canary lane already entered; no replay")
    value = json.loads(path.read_text())
    calls = value["calls"]
    read_only_stop = (value["status"] == "stopped" and len(calls) == 2
                      and calls[0]["state"] == "passed" and calls[-1]["state"] == "accepted")
    if ((value["status"] != "running" and not read_only_stop)
            or value["cap"] != 2 or value["casesHash"] != CASES_HASH
            or not 1 <= len(calls) <= 2
            or [item["case"] for item in calls] != ["portrait", "voice"][:len(calls)]
            or any(item["state"] not in {"accepted", "passed"} or not item.get("jobId") for item in calls)
            or sum(item["state"] == "accepted" for item in calls) != 1
            or calls[-1]["state"] != "accepted"):
        raise RuntimeError("Only one acknowledged accepted canary may be reconciled")
    return value


def succeeded(status):
    return status["status"] == "succeeded"


def run(reconcile=False):
    path = ROOT / "canaries.json"
    receipt = existing_receipt(path, reconcile)
    assert_idle()
    before = json.loads((ROOT / "before.json").read_text())["voices"]
    assert before == lab_proof()
    frozen = json.loads(FROZEN.read_text())
    assert fingerprint(frozen) == CASES_HASH
    assets = {Path(item["path"]).name: item for item in frozen["assets"]}
    for name in ("portrait.png", "voice.png", "performance.wav"):
        asset = assets[name]
        assert hashlib.sha256(Path(asset["path"]).read_bytes()).hexdigest() == asset["sha256"]
    result = subprocess.run(["docker", "inspect", "plotloom-h3-gateway"], check=True,
                            capture_output=True, text=True)
    environment = json.loads(result.stdout)[0]["Config"]["Env"]
    key = next(value.split("=", 1)[1] for value in environment if value.startswith("H3_API_KEY="))
    session = requests.Session(); session.headers["Authorization"] = "Bearer " + key
    if reconcile:
        accepted = receipt["calls"][-1]
        response = session.get(URL + "/v1/video-jobs/" + accepted["jobId"], timeout=15)
        response.raise_for_status()
        if not succeeded(response.json()):
            raise RuntimeError("Accepted canary must already be succeeded; no further submission")
        receipt.setdefault("reconciledAcceptedJobIds", []).append(accepted["jobId"])
        if receipt["status"] == "stopped":
            receipt["reconciledObserverErrorType"] = receipt.pop("errorType", None)
        receipt["status"] = "running"
    save(path, receipt)
    try:
        for case_id in ("portrait", "voice"):
            item = next((item for item in receipt["calls"] if item["case"] == case_id), None)
            if item and item["state"] == "passed": continue
            case = next(item for item in frozen["cases"] if item["id"] == case_id)
            graph = case["graph"]
            fields = {"prompt": graph["105:104"]["inputs"]["prompt"],
                      "resolution": f"{case['width']}x{case['height']}",
                      "aspectPolicy": "reject_mismatch", "durationSeconds": "5",
                      "seed": str(graph["105:15"]["inputs"]["noise_seed"])}
            files = {"image": (case_id + ".png", Path(assets[case_id + ".png"]["path"]).read_bytes(), "image/png")}
            route = "/v1/video-jobs/from-image"
            if case_id == "voice":
                route += "-with-voice"
                files["voiceAudio"] = ("performance.wav", Path(assets["performance.wav"]["path"]).read_bytes(), "audio/wav")
            else: fields["quality"] = "1"
            if item is None:
                item = {"case": case_id, "state": "outcome_unknown"}
                receipt["calls"].append(item); save(path, receipt)
                response = session.post(URL + route, data=fields, files=files, timeout=45)
                if response.status_code != 202:
                    item.update(state="request_rejected", httpStatus=response.status_code)
                    save(path, receipt); raise RuntimeError("Canary rejected; no replacement")
                item.update(state="accepted", jobId=response.json()["id"]); save(path, receipt)
                print(json.dumps({"case": case_id, "state": "accepted", "jobId": item["jobId"]}), flush=True)
            job_id = item["jobId"]
            deadline = time.monotonic() + 1800
            while time.monotonic() < deadline:
                status = session.get(URL + "/v1/video-jobs/" + job_id, timeout=15)
                status.raise_for_status(); status = status.json()
                if succeeded(status): break
                if status["status"] in {"failed", "cancelled", "outcome_unknown", "expired"}:
                    item.update(state=status["status"], error=status.get("error")); save(path, receipt)
                    raise RuntimeError("Canary did not complete; no replay")
                time.sleep(5)
            else: raise RuntimeError("Canary deadline; reconcile before further action")
            output = session.get(URL + f"/v1/video-jobs/{job_id}/output", timeout=60)
            output.raise_for_status()
            media = ROOT / (case_id + ".mp4"); media.write_bytes(output.content)
            snapshot = stored_snapshot(job_id)
            assert snapshot["vaePolicy"]["policy_id"] == "h3-int8-video-fp16-audio-bf16.v1"
            item.update(state="passed", status=status, execution=snapshot,
                        mediaSha256=hashlib.sha256(output.content).hexdigest(),
                        media=inspect_media(media, case["width"], case["height"]))
            save(path, receipt)
            print(json.dumps({"case": case_id, "state": "passed"}), flush=True)
        assert_idle(); assert before == lab_proof()
        receipt["status"] = "passed"; save(path, receipt)
    except Exception as error:
        receipt.update(status="stopped", errorType=type(error).__name__)
        save(path, receipt); raise


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--reconcile-succeeded", action="store_true")
    run(parser.parse_args().reconcile_succeeded)
