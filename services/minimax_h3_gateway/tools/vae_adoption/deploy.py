"""One authorized Spark maintenance, with preserved-container rollback.

Stages immutable source, not models or data. Run prepare, component, activate
serially. A failed/unknown generation must be reconciled before restore.
"""
import argparse
import json
import subprocess
import sys
import tempfile
import time
from pathlib import Path

import requests

SERVICE = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(SERVICE / "tools/vae_qualification"))
from maintenance import (  # noqa: I001
    assert_idle,
    baseline_configuration,
    confirm_paused_idle,
    gateway_proof,
    lab_proof,
)
from contract import save

ROOT = Path("/home/wjmao/services/spark-comfyui/experiments/h3-vae-d-adoption-20261006")
OLD_COMFY = "spark-comfyui-bf16-rollback-20261006"
OLD_GATEWAY = "plotloom-h3-gateway-before-vae-d-20261006"
GATEWAY_IMAGE = "plotloom-h3-gateway:vae-d-20261006"
GATEWAY_BASE_TAG = "plotloom-h3-gateway:before-vae-d-20261006"


def command(arguments):
    result = subprocess.run(arguments, capture_output=True, text=True, check=False)
    if result.returncode:
        # Docker args/environment may contain keys; never format CalledProcessError.
        raise RuntimeError(f"Operator command failed: {arguments[0]} (exit {result.returncode})")
    return result.stdout.strip()


def inspect(name):
    return json.loads(command(["docker", "inspect", name]))[0]


def exists(name):
    return subprocess.run(["docker", "inspect", name], capture_output=True, check=False).returncode == 0


def same_identities(before):
    after = lab_proof()
    if before != after:
        raise RuntimeError("Published voice/take records or bytes changed")
    return after


def prepare():
    if ROOT.exists():
        raise RuntimeError("Maintenance already entered; inspect receipt, do not replay")
    identities = assert_idle()
    baseline = baseline_configuration()
    gateway = inspect("plotloom-h3-gateway")
    for name in (OLD_COMFY, OLD_GATEWAY):
        if exists(name):
            raise RuntimeError("Rollback name already exists")
    ROOT.mkdir(mode=0o700)
    save(ROOT / "before.json", {"voices": identities, "baseline": baseline,
                                "gatewayId": gateway["Id"], "gatewayImage": gateway["Image"]})
    command(["docker", "stop", "plotloom-h3-gateway"])
    command(["systemctl", "--user", "stop", "plotloom-voice-lab.service"])
    command(["docker", "stop", "spark-comfyui"])
    confirm_paused_idle()
    same_identities(identities)
    print("Paused idle baseline; published voices/takes unchanged", flush=True)


def component():
    before = json.loads((ROOT / "before.json").read_text())
    confirm_paused_idle()
    command([
        "docker", "run", "--name", "h3-vae-d-lifecycle-dynamic-20261006", "--gpus", "all",
        "--network", "none", "--shm-size", "16g", "--user", "1000:1000",
        "--workdir", "/opt/ComfyUI", "--entrypoint", "python",
        "--mount", "type=bind,src=/home/wjmao/models/comfyui-h3,dst=/opt/ComfyUI/models,readonly",
        "--mount", f"type=bind,src={SERVICE}/comfy_nodes/plotloom_h3_video_vae,dst=/opt/ComfyUI/custom_nodes/plotloom_h3_video_vae,readonly",
        "--mount", f"type=bind,src={SERVICE}/tools/vae_adoption,dst=/proof,readonly",
        "--mount", f"type=bind,src={ROOT},dst=/receipt",
        before["baseline"]["image"], "/proof/verify_lifecycle.py",
        "--receipt", "/receipt/lifecycle-dynamic.json", "--bf16-unet", "--bf16-text-enc",
        "--bf16-vae", "--use-sage-attention", "--fast", "fp16_accumulation",
    ])
    result = json.loads((ROOT / "lifecycle-dynamic.json").read_text())
    if result["status"] != "passed": raise RuntimeError("Lifecycle proof failed")
    same_identities(before["voices"])
    print("Pinned GPU lifecycle proof passed", flush=True)


def clone_container(name, configuration, image, *, comfy):
    host = configuration["HostConfig"]
    arguments = ["docker", "create", "--name", name, "--restart", host["RestartPolicy"]["Name"],
                 "--network", configuration["HostConfig"]["NetworkMode"]]
    if configuration["Config"]["User"]:
        arguments += ["--user", configuration["Config"]["User"]]
    if comfy:
        arguments += ["--gpus", "all", "--shm-size", str(host["ShmSize"])]
        for port, bindings in (host["PortBindings"] or {}).items():
            for binding in bindings:
                arguments += ["-p", f"{binding['HostIp']}:{binding['HostPort']}:{port}"]
    for mount in configuration["Mounts"]:
        source = mount["Name"] if mount["Type"] == "volume" else mount["Source"]
        readonly = not mount["RW"] or (comfy and mount["Destination"] == "/opt/ComfyUI/models")
        arguments += ["--mount", f"type={mount['Type']},src={source},dst={mount['Destination']}" + (",readonly" if readonly else "")]
    if comfy:
        arguments += ["--mount", f"type=bind,src={SERVICE}/comfy_nodes/plotloom_h3_video_vae,dst=/opt/ComfyUI/custom_nodes/plotloom_h3_video_vae,readonly"]
    # Copy existing environment privately; no key in arguments, receipt or output.
    with tempfile.NamedTemporaryFile(mode="w", prefix="h3-private-env-", dir=ROOT) as env:
        env.write("\n".join(configuration["Config"]["Env"]) + "\n"); env.flush()
        arguments += ["--env-file", env.name, image]
        arguments += configuration["Config"]["Cmd"] or []
        if comfy:
            arguments += ["--fast", "fp16_accumulation"]
        command(arguments)


def wait_ready():
    deadline = time.monotonic() + 240
    while time.monotonic() < deadline:
        try:
            response = requests.get("http://100.64.35.71:8090/health", timeout=5)
            if response.status_code == 200:
                return response.json()
        except requests.RequestException:
            pass
        time.sleep(5)
    raise RuntimeError("Gateway readiness deadline; retain diagnostic container")


def build_gateway(image_id):
    # FROM resolves an image reference, not a raw local sha256 image ID.
    # Bind a unique local tag to the captured image; never fetch dependencies.
    if not exists(GATEWAY_BASE_TAG):
        command(["docker", "tag", image_id, GATEWAY_BASE_TAG])
    if inspect(GATEWAY_BASE_TAG)["Id"] != image_id:
        raise RuntimeError("Gateway base tag does not match preserved image")
    context = SERVICE.parents[1]
    if not (context / "services/minimax_h3_gateway/src/plotloom_h3_gateway").is_dir():
        raise RuntimeError("Gateway build context missing source")
    command(["docker", "build", "--pull=false", "--build-arg", f"BASE_IMAGE={GATEWAY_BASE_TAG}",
             "-f", str(SERVICE / "tools/vae_adoption/gateway-source.Dockerfile"),
             "-t", GATEWAY_IMAGE, str(context)])


def activate():
    before = json.loads((ROOT / "before.json").read_text())
    if json.loads((ROOT / "lifecycle-dynamic.json").read_text())["status"] != "passed":
        raise RuntimeError("Lifecycle proof not passed")
    confirm_paused_idle()
    same_identities(before["voices"])
    comfy, gateway = inspect("spark-comfyui"), inspect("plotloom-h3-gateway")
    if comfy["Id"] != before["baseline"]["containerId"] or gateway["Id"] != before["gatewayId"]:
        raise RuntimeError("Baseline container identity changed")
    build_gateway(gateway["Image"])
    command(["docker", "rename", "spark-comfyui", OLD_COMFY])
    command(["docker", "rename", "plotloom-h3-gateway", OLD_GATEWAY])
    clone_container("spark-comfyui", comfy, comfy["Image"], comfy=True)
    clone_container("plotloom-h3-gateway", gateway, GATEWAY_IMAGE, comfy=False)
    command(["docker", "start", "spark-comfyui", "plotloom-h3-gateway"])
    command(["systemctl", "--user", "start", "plotloom-voice-lab.service"])
    health = wait_ready()
    same_identities(before["voices"])
    save(ROOT / "activated.json", {"status": "serving", "health": health,
         "comfyId": inspect("spark-comfyui")["Id"], "gatewayId": inspect("plotloom-h3-gateway")["Id"],
         "gatewayImage": inspect("plotloom-h3-gateway")["Image"], "rollback": [OLD_COMFY, OLD_GATEWAY]})
    print("D serving; original containers retained stopped", flush=True)


def restore():
    before = json.loads((ROOT / "before.json").read_text())
    # Includes unknown dispatches: never stop uncertain work as a rollback trick.
    gateway_name = "plotloom-h3-gateway" if exists("plotloom-h3-gateway") else OLD_GATEWAY
    proof, voice = gateway_proof(container=gateway_name), lab_proof()
    queue = {"queue_running": [], "queue_pending": []}
    comfy_name = "spark-comfyui" if exists("spark-comfyui") else OLD_COMFY
    if inspect(comfy_name)["State"]["Running"]:
        response = requests.get("http://127.0.0.1:8188/queue", timeout=10)
        response.raise_for_status()
        queue = response.json()
    if (proof["busy"] or proof["lane"] or queue["queue_running"] or queue["queue_pending"]
            or any(voice["busy"].values()) or voice["unreleasedGrants"]):
        raise RuntimeError("Work unresolved; reconcile before rollback")
    command(["systemctl", "--user", "stop", "plotloom-voice-lab.service"])
    for current in (gateway_name, comfy_name):
        command(["docker", "stop", current])
    proof, voice = gateway_proof(container=gateway_name), lab_proof()
    if proof["busy"] or proof["lane"] or any(voice["busy"].values()) or voice["unreleasedGrants"]:
        raise RuntimeError("Work raced pause; do not replace runtime")
    for current, old in (("plotloom-h3-gateway", OLD_GATEWAY), ("spark-comfyui", OLD_COMFY)):
        if exists(old):
            if exists(current):
                command(["docker", "rename", current, current + "-d-diagnostic-20261006"])
            command(["docker", "rename", old, current])
        command(["docker", "start", current])
    command(["systemctl", "--user", "start", "plotloom-voice-lab.service"])
    wait_ready(); same_identities(before["voices"])
    save(ROOT / "restored.json", {"status": "baseline_restored"})


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("phase", choices=("prepare", "component", "activate", "restore"))
    globals()[parser.parse_args().phase]()
