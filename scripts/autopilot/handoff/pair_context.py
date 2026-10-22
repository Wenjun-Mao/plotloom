"""Explicit single-use locations for the migrated fixed controls; no module selector."""
import json
import os
import stat
from dataclasses import dataclass
from hashlib import sha256
from pathlib import Path

from handoff_files import read_owned, require
from pair_contracts import QualificationPairAllocation

CONTROLS = Path(__file__).resolve().parent
_context = None


@dataclass(frozen=True)
class PairContext:
    allocation: QualificationPairAllocation
    arm: str | None

    @property
    def source(self):
        return Path(self.allocation.serial.namespace.source_root.path)

    @property
    def campaign(self):
        return Path(self.allocation.work_root.path)

    @property
    def work(self):
        return self.campaign / self.arm if self.arm else self.campaign


def physical(expected):
    path = Path(expected.path)
    metadata = path.lstat()
    require(path.is_absolute() and path.resolve(strict=True) == path and not path.is_symlink()
        and metadata.st_uid == os.getuid() and
        (metadata.st_dev, metadata.st_ino, metadata.st_uid, stat.S_IMODE(metadata.st_mode)) ==
        (expected.device, expected.inode, expected.uid, expected.mode), "pair physical input/root differs")
    return path


def install(*, arm=None):
    global _context
    require(_context is None and arm in {None, "serial", "parallel"}, "pair context is single-use and finite")
    allocation = QualificationPairAllocation.model_validate_json(read_owned(CONTROLS / "pair-allocation.json"))
    require(physical(allocation.bundle_root) == CONTROLS, "pair controls origin differs")
    for root in (allocation.work_root, allocation.phase_root, allocation.serial.work_root, allocation.parallel.work_root):
        physical(root)
    for item in allocation.inputs:
        require(sha256(read_owned(physical(item))).hexdigest() == item.sha256, "pair frozen input bytes differ")
    marker = json.loads(read_owned(physical(allocation.owner_marker)))
    require(sha256(read_owned(Path(allocation.owner_marker.path))).hexdigest() == allocation.owner_marker.sha256
        and marker == dict(allocationId=str(allocation.allocation_id),nonce=allocation.nonce), "pair owner marker differs")
    qa = json.loads(read_owned(CONTROLS / "qa-interpreter.json"))
    require(allocation.serial.namespace.source_root == allocation.parallel.namespace.source_root
        and physical(allocation.serial.namespace.source_root) == Path(qa["projectRoot"]), "pair source origin differs")
    require(sha256(read_owned(CONTROLS / "qa-interpreter.json")).hexdigest() ==
        allocation.validator_runtime.qa_pin_sha256, "pair QA identity differs")
    _context = PairContext(allocation, arm)
    assert_control_bytes()
    assert_origins()
    return _context


def current():
    require(_context is not None, "pair locations must be verified before importing controls")
    return _context


def assert_origins():
    from handoff_source import PAIR_WORKFLOW_FILES
    import sys
    for filename in PAIR_WORKFLOW_FILES:
        name = filename.removesuffix(".py")
        module = sys.modules.get(name)
        if module is not None:
            require(Path(module.__file__).resolve(strict=True) == CONTROLS / filename,
                "pair control module shadowed: " + name)
    for name in ("plotloom", "isolated", "host_bridge"):
        module = sys.modules.get(name)
        if module is not None:
            origin = Path(module.__file__).resolve(strict=True)
            expected = current().source / ("src/plotloom/__init__.py" if name == "plotloom" else
                "services/creator_workbench/" + name + ".py")
            require(origin == expected, "pair production import origin differs: " + name)


def data_plan():
    assert_origins()
    context = current()
    return json.loads(read_owned(context.work / "plan.json"))


def assert_control_bytes():
    from handoff_source import WORKFLOW_FILES
    context = current()
    raw = read_owned(CONTROLS / 'pair-controls.json')
    require(all(sha256(raw).hexdigest() == getattr(context.allocation,arm).namespace.controls_sha256
        for arm in ('serial','parallel')), 'pair code-only controls pin differs')
    files = json.loads(raw)['files']
    require(set(files) == {*WORKFLOW_FILES, 'qa-interpreter.json', 'source-identity.json'}, 'pair code closure differs')
    for name,digest in files.items():
        require(sha256(read_owned(CONTROLS/name)).hexdigest() == digest, 'pair control bytes changed: '+name)
