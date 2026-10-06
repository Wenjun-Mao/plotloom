"""Operator lifecycle safety with no Docker, SSH or generation calls."""
import importlib.util
import json
from pathlib import Path

import pytest

SERVICE = Path(__file__).resolve().parents[3] / "services/minimax_h3_gateway"


@pytest.fixture
def deploy(monkeypatch, tmp_path):
    spec = importlib.util.spec_from_file_location("vae_deploy_test", SERVICE / "tools/vae_adoption/deploy.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    monkeypatch.setattr(module, "ROOT", tmp_path)
    return module


def test_build_context_resolves_checkout_root(deploy):
    assert deploy.SERVICE == SERVICE
    assert (deploy.SERVICE.parents[1] / "services/minimax_h3_gateway/src/plotloom_h3_gateway").is_dir()


def test_build_binds_verified_local_image_tag_without_pulling(deploy):
    calls = []
    deploy.exists = lambda name: False
    deploy.command = lambda arguments: calls.append(arguments)
    deploy.inspect = lambda name: {"Id": "sha256:preserved"}
    deploy.build_gateway("sha256:preserved")
    assert calls[0] == ["docker", "tag", "sha256:preserved", deploy.GATEWAY_BASE_TAG]
    assert calls[1][:3] == ["docker", "build", "--pull=false"]
    assert f"BASE_IMAGE={deploy.GATEWAY_BASE_TAG}" in calls[1]
    assert "BASE_IMAGE=sha256:preserved" not in calls[1]


def test_build_rejects_existing_tag_bound_to_another_image(deploy):
    deploy.exists = lambda name: True
    deploy.inspect = lambda name: {"Id": "sha256:other"}
    deploy.command = lambda arguments: pytest.fail("Must not retag or build from an unverified image")
    with pytest.raises(RuntimeError, match="does not match preserved image"):
        deploy.build_gateway("sha256:preserved")


@pytest.mark.parametrize("original_cmd", [None, ["--disable-api-nodes"]])
def test_container_preserves_command_and_host_configuration_without_exposing_env(deploy, original_cmd):
    calls = []
    def capture(arguments):
        assert "private-test-key" not in arguments
        env = Path(arguments[arguments.index("--env-file") + 1])
        assert env.read_text() == "H3_API_KEY=private-test-key\n"
        calls.append(arguments)
    deploy.command = capture
    configuration = {
        "Config": {"User": "1000:1000", "Env": ["H3_API_KEY=private-test-key"], "Cmd": original_cmd},
        "HostConfig": {"NetworkMode": "bridge", "RestartPolicy": {"Name": "unless-stopped"},
                       "ShmSize": 17179869184,
                       "PortBindings": {"8188/tcp": [{"HostIp": "127.0.0.1", "HostPort": "8188"}]}},
        "Mounts": [],
    }
    deploy.clone_container("candidate", configuration, "exact-image", comfy=True)
    command = calls[0]
    assert command[-(len(original_cmd or []) + 2):] == (original_cmd or []) + ["--fast", "fp16_accumulation"]
    assert command[command.index("--shm-size") + 1] == "17179869184"
    assert command[command.index("-p") + 1] == "127.0.0.1:8188:8188/tcp"
    assert not list(deploy.ROOT.glob("h3-private-env-*"))


def test_restore_recovers_both_absent_current_containers(deploy):
    (deploy.ROOT / "before.json").write_text(json.dumps({"voices": {}}))
    calls = []
    deploy.exists = lambda name: name in {deploy.OLD_COMFY, deploy.OLD_GATEWAY}
    deploy.inspect = lambda name: {"State": {"Running": False}}
    deploy.gateway_proof = lambda **kw: {"busy": 0, "lane": 0}
    deploy.lab_proof = lambda: {"busy": {"generations": 0}, "unreleasedGrants": 0}
    deploy.command = lambda args: calls.append(args)
    deploy.wait_ready = dict
    deploy.same_identities = lambda before: {}
    deploy.restore()
    assert ["docker", "rename", deploy.OLD_COMFY, "spark-comfyui"] in calls
    assert ["docker", "rename", deploy.OLD_GATEWAY, "plotloom-h3-gateway"] in calls
    assert not any(call[:2] == ["docker", "stop"] and call[2] in {"spark-comfyui", "plotloom-h3-gateway"} for call in calls)


@pytest.mark.parametrize("busy", ["voice", "grant"])
def test_restore_refuses_voice_work_or_unreleased_grant_before_stopping(deploy, busy):
    (deploy.ROOT / "before.json").write_text(json.dumps({"voices": {}}))
    deploy.exists = lambda name: True
    deploy.inspect = lambda name: {"State": {"Running": False}}
    deploy.gateway_proof = lambda **kw: {"busy": 0, "lane": 0}
    deploy.lab_proof = lambda: {"busy": {"generations": int(busy == "voice")},
                                "unreleasedGrants": int(busy == "grant")}
    deploy.command = lambda args: pytest.fail("Must not stop active work")
    with pytest.raises(RuntimeError, match="Work unresolved"):
        deploy.restore()
