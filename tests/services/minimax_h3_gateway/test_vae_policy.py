"""Frozen binding and maintained loader contracts, without Torch on the Mac."""
import importlib.util
import json
import sys
from hashlib import sha256
from pathlib import Path
from types import ModuleType, SimpleNamespace

import pytest
from plotloom_h3_gateway.profile_catalog import (
    admitted_execution,
    execution_from_snapshot,
)
from plotloom_h3_gateway.vae_policy import ADOPTED_VAE_POLICY, require_vae_runtime
from plotloom_h3_gateway.workflow import load_h3_template, render_workflow

NODE = Path(__file__).resolve().parents[3] / "services/minimax_h3_gateway/comfy_nodes/plotloom_h3_video_vae/loader.py"


@pytest.mark.parametrize("quality", [1, 2, 3, 8])
def test_each_quality_freezes_and_renders_video_only_precision(quality):
    execution = admitted_execution(quality=quality, resolution="704x1280")
    frozen = execution.snapshot_json()
    assert json.loads(frozen)["vaePolicy"] == ADOPTED_VAE_POLICY.snapshot()
    graph = render_workflow(load_h3_template()["prompt"], execution=execution_from_snapshot(frozen),
                            prompt="test", start_input_name="start.png", end_input_name="end.png",
                            seed=4, frame_count=124)
    assert graph["105:11"] == {"class_type": ADOPTED_VAE_POLICY.loader, "inputs": {
        "vae_name": ADOPTED_VAE_POLICY.video_checkpoint, "policy": ADOPTED_VAE_POLICY.policy_id}}
    assert graph["105:24"] == {"class_type": "VAELoader", "inputs": {
        "vae_name": ADOPTED_VAE_POLICY.audio_checkpoint}}


@pytest.mark.parametrize("change", ["missing", "old", "dtype", "hash"])
def test_unsupported_frozen_policy_is_not_reinterpreted(change):
    payload = admitted_execution(quality=1, resolution="576x1024").snapshot()
    if change == "missing": del payload["vaePolicy"]
    elif change == "old": payload["workflowRendererVersion"] = 3
    elif change == "dtype": payload["vaePolicy"]["video_compute_dtype"] = "bfloat16"
    else: payload["vaePolicy"]["video_sha256"] = "0" * 64
    with pytest.raises(ValueError): execution_from_snapshot(json.dumps(payload))


@pytest.mark.parametrize("missing", ["node", "checkpoint", "runtime"])
def test_preflight_requires_video_policy_not_just_stock_vae(missing):
    required = {"vae_name": [[ADOPTED_VAE_POLICY.video_checkpoint]],
                "policy": [[ADOPTED_VAE_POLICY.policy_id]]}
    info = {ADOPTED_VAE_POLICY.loader: {"input": {"required": required}}}
    if missing == "node": info.clear()
    elif missing == "checkpoint": required["vae_name"] = [[]]
    else: required["policy"] = [[]]
    with pytest.raises(ValueError): require_vae_runtime(info)


@pytest.fixture
def loader(monkeypatch, tmp_path):
    calls = []
    class MiniMaxH3VideoVAE:
        def to(self, dtype): calls.append(("to", dtype)); return self
    class Patcher:
        def __init__(self, model, load_device="cuda:0", offload_device="cpu", fast_disk=True):
            self.model, self.load_device = model, load_device
            self.offload_device, self.fast_disk = offload_device, fast_disk
            self.cached_patcher_init = None
        def is_dynamic(self): return type(self) is Patcher
    class Ordinary(Patcher): pass
    class VAE:
        def __init__(self, **kwargs):
            calls.append(kwargs)
            self.vae_dtype, self.device = kwargs["dtype"], kwargs["device"] or "cuda:0"
            self.first_stage_model = MiniMaxH3VideoVAE()
            self.patcher = Patcher(self.first_stage_model)
        def throw_exception_if_invalid(self): pass
    parent = ModuleType("comfy")
    for name, values in {
        "sd": {"VAE": VAE}, "model_patcher": {"ModelPatcher": Ordinary},
        "utils": {"load_torch_file": lambda path, **kw: ({"weights": path}, {"metadata": True})},
        "cli_args": {"args": SimpleNamespace(bf16_vae=True, fp16_vae=False, fp32_vae=False)},
    }.items():
        module = ModuleType("comfy." + name); module.__dict__.update(values)
        setattr(parent, name, module); monkeypatch.setitem(sys.modules, module.__name__, module)
    monkeypatch.setitem(sys.modules, "comfy", parent)
    torch = ModuleType("torch"); torch.float16 = "torch.float16"
    torch.backends = SimpleNamespace(cuda=SimpleNamespace(matmul=SimpleNamespace(allow_fp16_accumulation=True)))
    monkeypatch.setitem(sys.modules, "torch", torch)
    checkpoint = tmp_path / ADOPTED_VAE_POLICY.video_checkpoint; checkpoint.write_bytes(b"test")
    folder = ModuleType("folder_paths")
    folder.get_filename_list = lambda kind: [checkpoint.name]
    folder.get_full_path_or_raise = lambda kind, name: str(checkpoint)
    monkeypatch.setitem(sys.modules, "folder_paths", folder)
    spec = importlib.util.spec_from_file_location("h3_loader_test", NODE)
    module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
    module.CHECKPOINT_SHA256 = sha256(b"test").hexdigest()
    return module, calls, checkpoint


def test_factory_preserves_precision_device_and_delegate_contract(loader):
    node, calls, _path = loader
    assert node.POLICY == ADOPTED_VAE_POLICY.policy_id
    vae, = node.PlotloomH3VideoVAELoader().load(node.CHECKPOINT, node.POLICY)
    factory, arguments = vae.patcher.cached_patcher_init
    reloaded = factory(*arguments, disable_dynamic=True)
    # The factory returns fresh weights; core's outer clone constructs the
    # nondynamic delegate, so no temporary replacement patcher is created here.
    assert reloaded.is_dynamic()
    assert calls[0]["dtype"] == calls[1]["dtype"] == "torch.float16"
    assert calls[0]["device"] is None and calls[1]["device"] is None
    assert calls[1]["metadata"] == {"metadata": True}
    assert reloaded.cached_patcher_init is None
    assert ("to", "torch.float16") in calls


def test_loader_runtime_and_checkpoint_replacement_fail_closed(loader):
    node, _calls, path = loader
    node.PlotloomH3VideoVAELoader().load(node.CHECKPOINT, node.POLICY)
    path.write_bytes(b"modified")
    with pytest.raises(ValueError, match="hash"):
        node.load_video_vae(str(path))
    node.args.bf16_vae = False
    assert node.PlotloomH3VideoVAELoader.INPUT_TYPES()["required"]["policy"] == ([],)
    with pytest.raises(ValueError, match="global BF16"):
        node.load_video_vae(str(path))
