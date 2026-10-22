import os
from hashlib import sha256

import pytest

from plotloom.codex_exec_contracts import output_manifest_hash, package_manifest_hash
from plotloom.codex_exec_files import (
    CodexExecFileError,
    _assert_no_case_or_unicode_collisions,
    assert_empty_directory,
    output_evidence_for_tree,
    read_confined_regular_file,
    scan_regular_tree,
)


def test_scanner_hashes_a_complete_sorted_tree_and_output_manifest(tmp_path):
    package = tmp_path / "package"
    (package / "inputs").mkdir(parents=True)
    (package / "request.json").write_bytes(b'{"jobId":"job_1"}')
    (package / "inputs" / "reference.png").write_bytes(b"reference-bytes")

    files = scan_regular_tree(tmp_path.resolve(), "package")
    assert [item.relative_path for item in files] == [
        "inputs/reference.png",
        "request.json",
    ]
    assert files[0].sha256 == sha256(b"reference-bytes").hexdigest()
    package_hash = package_manifest_hash(files)
    (package / "request.json").write_bytes(b'{"jobId":"job_2"}')
    assert package_manifest_hash(scan_regular_tree(tmp_path.resolve(), "package")) != package_hash

    outputs = package / "delivery" / "outputs"
    outputs.mkdir(parents=True)
    (outputs / "frame.png").write_bytes(b"image-bytes")
    output_evidence = output_evidence_for_tree(
        tmp_path.resolve(),
        "package/delivery/outputs",
        output_prefix="delivery/outputs",
    )
    assert output_evidence[0].output_relative_path == "delivery/outputs/frame.png"
    assert output_evidence[0].output_hash == sha256(b"image-bytes").hexdigest()
    assert output_manifest_hash(output_evidence)


def test_empty_directory_gate_accepts_empty_delivery_and_rejects_retained_entries(tmp_path):
    delivery = tmp_path / "delivery"
    delivery.mkdir()
    assert_empty_directory(tmp_path.resolve(), "delivery")

    (delivery / "partial-evidence").write_bytes(b"retained")
    with pytest.raises(CodexExecFileError, match="must be empty"):
        assert_empty_directory(tmp_path.resolve(), "delivery")


def test_confined_file_reader_reads_only_stable_regular_files_within_root(tmp_path):
    package = tmp_path / "package"
    package.mkdir()
    request = package / "request.json"
    request.write_bytes(b'{"stage":"outline"}')
    assert read_confined_regular_file(
        tmp_path.resolve(), "package/request.json", max_bytes=1024
    ) == b'{"stage":"outline"}'

    outside = tmp_path / "outside.json"
    outside.write_bytes(b"secret")
    (package / "link.json").symlink_to(outside)
    with pytest.raises(CodexExecFileError, match="regular file|safely"):
        read_confined_regular_file(tmp_path.resolve(), "package/link.json", max_bytes=1024)
    with pytest.raises(CodexExecFileError, match="traverse"):
        read_confined_regular_file(tmp_path.resolve(), "../outside.json", max_bytes=1024)
    with pytest.raises(CodexExecFileError, match="byte limit"):
        read_confined_regular_file(tmp_path.resolve(), "outside.json", max_bytes=2)


@pytest.mark.parametrize("relative", ["../outside", "package\\inputs", "/absolute"])
def test_scanner_rejects_nonrelative_or_nonposix_directory_paths(tmp_path, relative):
    with pytest.raises(CodexExecFileError):
        scan_regular_tree(tmp_path.resolve(), relative)


@pytest.mark.parametrize(
    "names",
    [
        ["Request.json", "request.json"],
        ["é.txt", "e\u0301.txt"],
    ],
)
def test_scanner_rejects_case_or_unicode_collisions(names):
    # The Mac test filesystem cannot create these aliases as separate entries,
    # so exercise the directory-listing guard with both names explicitly.
    with pytest.raises(CodexExecFileError, match="collisions"):
        _assert_no_case_or_unicode_collisions(names)


def test_scanner_rejects_symlinks_and_duplicate_file_identities(tmp_path):
    package = tmp_path / "package"
    package.mkdir()
    source = package / "request.json"
    source.write_bytes(b"request")
    (package / "linked.json").symlink_to(source)
    with pytest.raises(CodexExecFileError, match="symlinks"):
        scan_regular_tree(tmp_path.resolve(), "package")

    (package / "linked.json").unlink()
    os.link(source, package / "hardlink.json")
    with pytest.raises(CodexExecFileError, match="filesystem identities"):
        scan_regular_tree(tmp_path.resolve(), "package")


def test_scanner_rejects_nonregular_files_and_tree_limit_overflow(tmp_path):
    package = tmp_path / "package"
    package.mkdir()
    (package / "request.json").write_bytes(b"0123456789")
    if hasattr(os, "mkfifo"):
        os.mkfifo(package / "not-a-file")
        with pytest.raises(CodexExecFileError, match="non-regular"):
            scan_regular_tree(tmp_path.resolve(), "package")
        (package / "not-a-file").unlink()
    with pytest.raises(CodexExecFileError, match="byte limit"):
        scan_regular_tree(tmp_path.resolve(), "package", max_total_bytes=5)
