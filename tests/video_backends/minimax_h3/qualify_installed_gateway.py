"""Real Plotloom HTTP consumer against an installed, provider-free gateway fixture."""
import argparse
import hashlib
import json
import os
import select
import sqlite3
import subprocess
import tempfile
import time
from pathlib import Path

from plotloom.video_backends.minimax_h3.transport import MiniMaxH3GatewayTransport
from plotloom.video_provider import WanDispatchError


def line(process):
    if not select.select([process.stdout], [], [], 30)[0]:
        raise RuntimeError("gateway fixture control did not respond")
    value = process.stdout.readline()
    if not value: raise RuntimeError("gateway fixture exited unexpectedly")
    return json.loads(value)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--gateway-python", type=Path, required=True)
    parser.add_argument("--fixture-script", type=Path, required=True)
    parser.add_argument("--image", type=Path, required=True)
    parser.add_argument("--video", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    image, video = args.image.read_bytes(), args.video.read_bytes()
    payload = {"prompt": "A pilot pauses at the airlock.", "quality": 1,
        "resolution": "832x480", "aspectPolicy": "cover_center_crop", "seed": 42, "durationSeconds": 5}
    with tempfile.TemporaryDirectory(prefix="media-consumer-proof-") as temporary:
        directory = Path(temporary); fixture_root = directory / "gateway"
        with (directory / "gateway.stderr").open("w+") as errors:
            process = subprocess.Popen([str(args.gateway_python.absolute()), "-I", str(args.fixture_script.resolve()),
                "--root", str(fixture_root), "--video", str(args.video.resolve())], cwd=directory,
                stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=errors, text=True,
                env={k:v for k,v in os.environ.items() if k not in {"PYTHONPATH", "PYTHONHOME"}})
            try:
                ready = line(process)
                assert "site-packages" in ready["installedModule"], ready
                assert Path(ready["installedModule"]).is_relative_to(args.gateway_python.absolute().parent.parent), ready
                transport = MiniMaxH3GatewayTransport("fixture-consumer-only", base_url=ready["baseUrl"])
                deadline = time.monotonic() + 15
                while True:
                    try: transport.preflight(); break
                    except WanDispatchError:
                        if time.monotonic() >= deadline: raise
                        time.sleep(.05)
                def dispatch():
                    process.stdin.write("dispatch\n"); process.stdin.flush(); return line(process)
                accepted = transport.submit_image(image, mime_type="image/png", payload=payload)
                assert accepted["status"] == "queued", accepted
                assert dispatch()["job"]["status"] == "submitted"
                completed = transport.poll(accepted["id"])
                assert completed["status"] == "succeeded" and completed["outputReady"], completed
                assert transport.download(accepted["id"]) == video
                rejected = MiniMaxH3GatewayTransport("wrong-fixture-key", base_url=ready["baseUrl"])
                try: rejected.submit_image(image, mime_type="image/png", payload=payload)
                except WanDispatchError as error:
                    assert error.diagnostic.code == "http_rejected" and error.diagnostic.status_code == 401
                else: raise AssertionError("real gateway accepted a wrong credential")
                uncertain = transport.submit_image(image, mime_type="image/png", payload={**payload, "prompt": "fixture-provider-unknown"})
                outcome = dispatch()
                assert outcome["job"]["status"] == "outcome_unknown", outcome
                assert transport.poll(uncertain["id"])["status"] == "outcome_unknown"
                assert dispatch()["providerCalls"] == 2, "uncertain provider submission retried"
                with sqlite3.connect(fixture_root / "data/gateway.sqlite3") as db:
                    statuses = dict(db.execute("SELECT status,count(*) FROM jobs GROUP BY status"))
                    assert statuses == {"succeeded": 1, "outcome_unknown": 1}, statuses
                receipt = {"status": "passed", "consumer": "actual Plotloom MiniMaxH3GatewayTransport",
                    "gatewayModule": ready["installedModule"], "inference": "fake only; no live provider calls",
                    "submitPollDownload": "passed", "downloadSha256": hashlib.sha256(video).hexdigest(),
                    "downloadBytes": len(video), "credentialRejection": 401,
                    "uncertainOutcome": "preserved without retry", "fakeProviderSubmissions": 2,
                    "temporaryJobStatuses": statuses, "productionStateChanged": False}
            except BaseException:
                errors.flush(); errors.seek(0); print(errors.read()); raise
            finally:
                process.stdin.close()
                try: process.wait(timeout=15)
                except subprocess.TimeoutExpired:
                    process.terminate(); process.wait(timeout=5)
                if process.returncode:
                    raise RuntimeError("gateway fixture did not exit cleanly")
            args.out.parent.mkdir(parents=True, exist_ok=True)
            args.out.write_text(json.dumps(receipt, indent=2) + "\n")
            print(json.dumps(receipt, indent=2))


if __name__ == "__main__": main()
