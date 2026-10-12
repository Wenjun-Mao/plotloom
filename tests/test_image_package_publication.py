"""Original immutable image package publication after interruption/concurrency."""
from concurrent.futures import ThreadPoolExecutor
from hashlib import sha256
from pathlib import Path
import pytest
from plotloom.image_job_contracts import ImageJobError
from plotloom.image_job_exchange import ImageJobExchange
from plotloom.image_job_package import canonical_json, project_image_package
from plotloom.managed_media import ManagedMediaLimits


def package(tmp_path):
    root = tmp_path / "exchange"
    exchange = ImageJobExchange(root, limits=ManagedMediaLimits())
    request = {"schemaVersion": 3, "jobId": "ij_" + "a" * 32, "kind": "original",
        "specialistPreflight": {"version": "p1.5-pin.v1", "skillVersion": "plotloom-image-specialist.v3"}}
    digest = sha256(canonical_json(request)).hexdigest()
    arguments = {"job_id": request["jobId"], "request": request, "request_hash": digest, "references": []}
    return root, exchange, arguments


def test_interrupted_write_never_publishes_partial_package_and_original_retry_succeeds(tmp_path, monkeypatch):
    from plotloom import image_package_publication
    root, exchange, arguments = package(tmp_path)
    rename = image_package_publication.os.rename
    monkeypatch.setattr(image_package_publication.os, "rename", lambda *_args, **_kwargs: (_ for _ in ()).throw(OSError("interrupted publication")))
    with pytest.raises(OSError, match="interrupted publication"):
        exchange.write_package(**arguments)
    job = root / "jobs" / arguments["job_id"]
    assert {item.name for item in job.iterdir()} == {".package-publication.lock"}
    monkeypatch.setattr(image_package_publication.os, "rename", rename)
    result = exchange.write_package(**arguments)
    assert (Path(result["packagePath"]) / "request.json").is_file()
    exchange.verify_package(**arguments)


@pytest.mark.parametrize("foreign", [False, True])
def test_original_static_orphan_prefix_is_reclaimed_but_foreign_bytes_untouched(tmp_path, foreign):
    root, exchange, arguments = package(tmp_path)
    request, _instructions, _template, _entries = project_image_package(root=root, job_id=arguments["job_id"],
        request=arguments["request"], request_hash=arguments["request_hash"], reference_entries=[])
    orphan = root / "jobs" / arguments["job_id"] / f".package-{arguments['request_hash']}-{'b' * 32}"
    orphan.mkdir(parents=True)
    content = b"foreign" if foreign else canonical_json(request)[:17]
    (orphan / "request.json").write_bytes(content)
    if foreign:
        with pytest.raises(ImageJobError, match="changed bytes"):
            exchange.write_package(**arguments)
        assert (orphan / "request.json").read_bytes() == content
    else:
        exchange.write_package(**arguments)
        assert not orphan.exists()
        exchange.verify_package(**arguments)


def test_concurrent_publishers_observe_one_verified_original_package(tmp_path):
    root, exchange, arguments = package(tmp_path)
    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(lambda _: exchange.write_package(**arguments), range(2)))
    assert results[0] == results[1]
    exchange.verify_package(**arguments)
    assert {item.name for item in (root / "jobs" / arguments["job_id"]).iterdir()} == {"package", ".package-publication.lock"}
