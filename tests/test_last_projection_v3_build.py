from pathlib import Path

import pytest

from scripts.prototypes.last_projection_v3.build import build


def test_v3_zip_cannot_overwrite_any_file_inside_retained_v2_directory(tmp_path: Path) -> None:
    v2 = tmp_path / "v2"
    v2.mkdir()
    source = v2 / "source.zip"
    source.write_bytes(b"retained source")
    protected = v2 / "游玩说明.txt"
    protected.write_text("keep this file", encoding="utf-8")

    with pytest.raises(ValueError, match="V3 ZIP must be separate"):
        build(source, tmp_path / "v3", tmp_path / "static", protected)

    assert protected.read_text(encoding="utf-8") == "keep this file"
