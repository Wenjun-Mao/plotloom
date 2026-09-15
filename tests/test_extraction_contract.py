"""Distribution and source-boundary checks for the standalone Plotloom product."""

from __future__ import annotations

import ast
import json
import os
import re
import subprocess
import sys
import textwrap
import zipfile
from pathlib import Path

import pytest


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
PACKAGE_ROOT = REPOSITORY_ROOT / "src" / "plotloom"
FRONTEND_ROOT = REPOSITORY_ROOT / "frontend"
ENV_EXAMPLE = REPOSITORY_ROOT / ".env.example"

PROMPT_FILENAMES = {
    "media_image.yaml",
    "media_video.yaml",
    "repair_json.yaml",
    "scene_beats.yaml",
    "scene_beats_fragment.yaml",
    "story_bible.yaml",
    "story_graph.yaml",
    "story_graph_content_fill.yaml",
    "storyboard.yaml",
    "storyboard_fragment.yaml",
    "work_unit_correction.yaml",
}
FORBIDDEN_IMPORT_ROOTS = {"app", "backend", "narrative_forge"}
FORBIDDEN_RUNTIME_PATH_MARKERS = {
    "app.py",
    "backend/",
    "projects/_provider_config.json",
    "src/narrative_forge/",
    "static/src/",
}
FORBIDDEN_REPOSITORY_PATHS = {
    "app.py",
    "backend",
    "static",
    "src/narrative_forge",
    "projects",
}
ALLOWED_REPOSITORY_ROOTS = {
    ".agents",
    ".env.example",
    ".github",
    ".gitignore",
    ".python-version",
    "AGENTS.md",
    "LICENSE",
    "NOTICE",
    "README.md",
    "docs",
    "frontend",
    "pyproject.toml",
    "scripts",
    "services",
    "src",
    "tests",
    "uv.lock",
}
ALLOWED_SERVICE_DIRECTORY = "minimax_h3_gateway"
IGNORED_WORKTREE_ROOTS = {
    ".env",
    ".git",
    ".local",
    ".mypy_cache",
    ".pytest_cache",
    ".ruff_cache",
    ".venv",
    "build",
    "data",
    "dist",
    "htmlcov",
    "node_modules",
}
FORBIDDEN_PRODUCT_IDENTITY_MARKERS = {
    "Narrative Forge",
    "NARRATIVE_FORGE",
    "NF_V2_API_ORIGIN",
    "X-NF-Session-API-Key",
    "narrative-forge-v2",
    "narrative_forge_v2",
}
IGNORED_SEARCH_DIRECTORIES = {
    ".git",
    ".mypy_cache",
    ".pytest_cache",
    ".ruff_cache",
    ".venv",
    "__pycache__",
    "node_modules",
}


def _absolute_imports(path: Path) -> list[tuple[int, str]]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    imports: list[tuple[int, str]] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imports.extend((node.lineno, alias.name) for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
            imports.append((node.lineno, node.module))
    return imports


def _find_named_files(root: Path, filenames: set[str]) -> set[Path]:
    matches: set[Path] = set()
    for directory, child_directories, child_filenames in os.walk(root):
        child_directories[:] = [
            name for name in child_directories if name not in IGNORED_SEARCH_DIRECTORIES
        ]
        directory_path = Path(directory)
        matches.update(directory_path / name for name in child_filenames if name in filenames)
    return matches


def _assert_services_root_is_gateway_only(root: Path, tracked_paths: list[Path]) -> None:
    """Keep the private gateway a narrow exception to source-root isolation."""

    services_root = root / "services"
    assert services_root.is_dir() and not services_root.is_symlink(), (
        "services must be a real directory"
    )
    children = {path.name for path in services_root.iterdir()}
    assert children == {ALLOWED_SERVICE_DIRECTORY}, (
        "services permits only the tracked MiniMax H3 gateway subtree: "
        + ", ".join(sorted(children))
    )
    gateway_root = services_root / ALLOWED_SERVICE_DIRECTORY
    assert gateway_root.is_dir() and not gateway_root.is_symlink(), (
        "the admitted MiniMax H3 gateway must be a real directory"
    )

    tracked_service_paths = {
        path.as_posix() for path in tracked_paths if path.parts and path.parts[0] == "services"
    }
    invalid_tracked_paths = sorted(
        path for path in tracked_service_paths
        if not path.startswith(f"services/{ALLOWED_SERVICE_DIRECTORY}/")
    )
    assert not invalid_tracked_paths, (
        "tracked files outside the admitted gateway subtree: "
        + ", ".join(invalid_tracked_paths)
    )
    actual_service_paths = {
        path.relative_to(root).as_posix()
        for path in services_root.rglob("*")
        if path.is_file() or path.is_symlink()
    }
    assert actual_service_paths == tracked_service_paths, (
        "services must contain only tracked gateway files; unexpected: "
        + ", ".join(sorted(actual_service_paths - tracked_service_paths))
        + "; missing: "
        + ", ".join(sorted(tracked_service_paths - actual_service_paths))
    )


def _build_distribution_wheel(wheel_directory: Path) -> Path:
    result = subprocess.run(
        ["uv", "build", "--wheel", "--out-dir", str(wheel_directory)],
        cwd=REPOSITORY_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, (
        "the Plotloom wheel failed to build\n"
        f"stdout:\n{result.stdout}\n"
        f"stderr:\n{result.stderr}"
    )
    wheels = list(wheel_directory.glob("*.whl"))
    assert len(wheels) == 1
    return wheels[0]


def _toml_string_array(path: Path, key: str) -> set[str]:
    source = path.read_text(encoding="utf-8")
    match = re.search(rf"(?ms)^{re.escape(key)}\s*=\s*\[(.*?)^\]", source)
    assert match is not None, f"{path} does not declare {key}"
    return set(re.findall(r'"([^"\\]*(?:\\.[^"\\]*)*)"', match.group(1)))


def test_python_sources_have_no_legacy_runtime_dependency() -> None:
    violations: list[str] = []
    for path in sorted(PACKAGE_ROOT.rglob("*.py")):
        for line, module in _absolute_imports(path):
            if module.split(".", 1)[0] in FORBIDDEN_IMPORT_ROOTS:
                violations.append(f"{path.relative_to(PACKAGE_ROOT)}:{line}: {module}")
    assert not violations, "Plotloom imports legacy runtime modules:\n" + "\n".join(violations)

    named_paths: list[str] = []
    for path in sorted(PACKAGE_ROOT.rglob("*.py")):
        source = path.read_text(encoding="utf-8")
        for marker in FORBIDDEN_RUNTIME_PATH_MARKERS:
            if marker in source:
                named_paths.append(f"{path.relative_to(PACKAGE_ROOT)}: {marker}")
    assert not named_paths, "Plotloom names legacy runtime paths:\n" + "\n".join(named_paths)


def test_clean_repository_has_no_legacy_runtime_roots() -> None:
    present = sorted(
        path for path in FORBIDDEN_REPOSITORY_PATHS if (REPOSITORY_ROOT / path).exists()
    )
    assert not present, "legacy runtime roots entered Plotloom: " + ", ".join(present)


def test_clean_repository_has_only_declared_product_roots() -> None:
    visible_roots = {
        path.name
        for path in REPOSITORY_ROOT.iterdir()
        if path.name not in IGNORED_WORKTREE_ROOTS
        and path.name != ".DS_Store"
        and not path.name.startswith(".coverage")
    }
    unexpected = sorted(visible_roots - ALLOWED_REPOSITORY_ROOTS)
    assert not unexpected, "undeclared repository roots could hide predecessor code: " + ", ".join(
        unexpected
    )

    tracked_result = subprocess.run(
        ["git", "ls-files", "-z"],
        cwd=REPOSITORY_ROOT,
        capture_output=True,
        check=False,
    )
    assert tracked_result.returncode == 0, tracked_result.stderr.decode(errors="replace")
    tracked_paths = [
        Path(value.decode())
        for value in tracked_result.stdout.split(b"\0")
        if value
    ]
    unexpected_tracked_roots = sorted(
        {path.parts[0] for path in tracked_paths} - ALLOWED_REPOSITORY_ROOTS
    )
    assert not unexpected_tracked_roots, (
        "tracked roots fall outside the Plotloom repository contract: "
        + ", ".join(unexpected_tracked_roots)
    )
    foreign_source_paths = sorted(
        path.as_posix()
        for path in tracked_paths
        if path.parts[0] == "src"
        and (len(path.parts) < 2 or path.parts[1] != "plotloom")
    )
    assert not foreign_source_paths, "non-Plotloom source packages are tracked:\n" + "\n".join(
        foreign_source_paths
    )
    _assert_services_root_is_gateway_only(REPOSITORY_ROOT, tracked_paths)


def test_services_root_admission_rejects_other_children_and_untracked_files(tmp_path: Path) -> None:
    tracked = [Path("services/minimax_h3_gateway/README.md")]
    gateway = tmp_path / "services" / "minimax_h3_gateway"
    gateway.mkdir(parents=True)
    (gateway / "README.md").write_text("gateway", encoding="utf-8")

    _assert_services_root_is_gateway_only(tmp_path, tracked)

    (tmp_path / "services" / "unrelated.py").write_text("blocked", encoding="utf-8")
    with pytest.raises(AssertionError, match="permits only"):
        _assert_services_root_is_gateway_only(tmp_path, tracked)
    (tmp_path / "services" / "unrelated.py").unlink()

    (gateway / "local.env").write_text("blocked", encoding="utf-8")
    with pytest.raises(AssertionError, match="only tracked gateway files"):
        _assert_services_root_is_gateway_only(tmp_path, tracked)


def test_product_code_contains_no_predecessor_identity() -> None:
    roots = (
        PACKAGE_ROOT,
        FRONTEND_ROOT / "src",
        FRONTEND_ROOT / "e2e",
        FRONTEND_ROOT / "tests",
        REPOSITORY_ROOT / "scripts",
    )
    violations: list[str] = []
    for root in roots:
        for path in sorted(item for item in root.rglob("*") if item.is_file()):
            if "__pycache__" in path.parts or path.suffix in {".pyc", ".png", ".jpg"}:
                continue
            source = path.read_text(encoding="utf-8", errors="ignore")
            for marker in FORBIDDEN_PRODUCT_IDENTITY_MARKERS:
                if marker in source:
                    violations.append(f"{path.relative_to(REPOSITORY_ROOT)}: {marker}")
    assert not violations, "predecessor identity entered product code:\n" + "\n".join(violations)


def test_root_metadata_exposes_only_plotloom_distribution() -> None:
    pyproject = REPOSITORY_ROOT / "pyproject.toml"
    source = pyproject.read_text(encoding="utf-8")
    assert 'name = "plotloom"' in source
    assert 'plotloom = "plotloom.runtime:main"' in source
    assert 'module-name = "plotloom"' in source
    assert "narrative_forge_v2" not in source
    assert _toml_string_array(pyproject, "dependencies")
    assert _toml_string_array(pyproject, "dev")


def test_environment_template_is_plotloom_only() -> None:
    source = ENV_EXAMPLE.read_text(encoding="utf-8")
    declared_names = set(re.findall(r"(?m)^#?\s*([A-Z][A-Z0-9_]*)=", source))
    assert {
        "ATLASCLOUD_API_KEY",
        "TEXT_MODEL_API_KEY",
        "IMAGE_MODEL_API_KEY",
        "VIDEO_MODEL_API_KEY",
        "TEXT_PROVIDER",
        "TEXT_BASE_URL",
        "TEXT_MODEL",
        "IMAGE_PROVIDER",
        "IMAGE_BASE_URL",
        "IMAGE_MODEL",
        "VIDEO_PROVIDER",
        "VIDEO_BASE_URL",
            "VIDEO_MODEL",
            "PLOTLOOM_HOST",
            "PLOTLOOM_PORT",
            "PLOTLOOM_OUTPUTS_DIR",
            "PLOTLOOM_APPLICATION_DATA_DIR",
        "PLOTLOOM_MANAGED_MEDIA_MAX_IMPORT_BYTES",
        "PLOTLOOM_MANAGED_MEDIA_MAX_IMPORT_PIXELS",
    }.issubset(declared_names)
    assert not any(name.startswith(("DIRECTOR_", "NARRATIVE_FORGE_")) for name in declared_names)
    assert "IMAGE_EDIT_MODEL" not in declared_names


def test_prompt_templates_have_one_package_owned_source_of_truth() -> None:
    prompt_root = PACKAGE_ROOT / "prompt_templates"
    assert {path.name for path in prompt_root.glob("*.yaml")} == PROMPT_FILENAMES

    copies = _find_named_files(REPOSITORY_ROOT, PROMPT_FILENAMES)
    assert copies == {prompt_root / name for name in PROMPT_FILENAMES}
    assert not (REPOSITORY_ROOT / "prompts").exists()


def test_frontend_source_does_not_escape_its_product_root() -> None:
    import_pattern = re.compile(r"(?:from\s+|import\s*)[\"']([^\"']+)[\"']")
    violations: list[str] = []
    for path in sorted((FRONTEND_ROOT / "src").rglob("*")):
        if path.suffix not in {".ts", ".tsx", ".css"}:
            continue
        for specifier in import_pattern.findall(path.read_text(encoding="utf-8")):
            if not specifier.startswith("."):
                continue
            resolved = (path.parent / specifier).resolve()
            if not resolved.is_relative_to(FRONTEND_ROOT.resolve()):
                violations.append(f"{path.relative_to(FRONTEND_ROOT)}: {specifier}")
    assert not violations, "frontend imports outside its product root:\n" + "\n".join(violations)

    vite_config = (FRONTEND_ROOT / "vite.config.ts").read_text(encoding="utf-8")
    assert 'base: "/v2/"' in vite_config
    assert 'new URL("../src/plotloom/static"' in vite_config


def test_frontend_package_and_lockfile_are_standalone() -> None:
    package = json.loads((FRONTEND_ROOT / "package.json").read_text(encoding="utf-8"))
    lock = json.loads((FRONTEND_ROOT / "package-lock.json").read_text(encoding="utf-8"))
    root_lock = lock["packages"][""]

    assert root_lock["name"] == package["name"]
    assert root_lock["version"] == package["version"]
    assert root_lock["dependencies"] == package["dependencies"]
    assert root_lock["devDependencies"] == package["devDependencies"]

    serialized = json.dumps(lock, sort_keys=True)
    assert "file:" not in serialized
    assert "link:" not in serialized
    assert "narrative-forge" not in serialized


def test_test_package_marker_describes_plotloom() -> None:
    marker = REPOSITORY_ROOT / "tests" / "__init__.py"
    assert marker.is_file()
    assert "Plotloom" in marker.read_text(encoding="utf-8")


def test_distribution_wheel_is_complete_and_isolated(tmp_path: Path) -> None:
    wheel = _build_distribution_wheel(tmp_path / "wheelhouse")
    with zipfile.ZipFile(wheel) as archive:
        members = set(archive.namelist())
        expected_package_members = {
            path.relative_to(PACKAGE_ROOT.parent).as_posix()
            for path in PACKAGE_ROOT.rglob("*")
            if path.is_file() and "__pycache__" not in path.parts and path.suffix != ".pyc"
        }
        missing_members = expected_package_members - members
        assert not missing_members, "wheel omitted package files:\n" + "\n".join(
            sorted(missing_members)
        )
        assert not any(
            name.startswith(("narrative_forge/", "backend/", "static/src/", "projects/"))
            for name in members
        )
        assert any(name.endswith(".dist-info/licenses/LICENSE") for name in members)
        assert any(name.endswith(".dist-info/licenses/NOTICE") for name in members)
        assert {f"plotloom/prompt_templates/{name}" for name in PROMPT_FILENAMES}.issubset(members)
        assert {
            "plotloom/static/index.html",
            "plotloom/static/workbench.css",
            "plotloom/static/workbench.js",
            "plotloom/alembic/env.py",
            "plotloom/alembic/script.py.mako",
            "plotloom/alembic/versions/0001_initial.py",
        }.issubset(members)

        unpacked = tmp_path / "unpacked-wheel"
        archive.extractall(unpacked)

    database_path = tmp_path / "standalone.sqlite3"
    probe_cwd = tmp_path / "unrelated-cwd"
    probe_cwd.mkdir()
    (probe_cwd / "pyproject.toml").write_text(
        "[project]\nname='unrelated-launch-directory'\n", encoding="utf-8"
    )
    (probe_cwd / ".env").write_text(
        "PLOTLOOM_DATA_DIR=cwd-poison-data\nTEXT_MODEL=cwd-poison-model\n",
        encoding="utf-8",
    )
    probe_home = tmp_path / "probe-home"
    probe = textwrap.dedent(
        """
        import os
        import sqlite3
        import sys
        from pathlib import Path

        unpacked = Path(sys.argv[1]).resolve()
        database_path = Path(sys.argv[2]).resolve()
        sys.path.insert(0, str(unpacked))

        import plotloom
        from alembic.script import ScriptDirectory
        from plotloom.config import PlotloomSettings
        from plotloom.generation.prompts import PromptRepository
        from plotloom.schema import SchemaMigrator

        package_root = Path(plotloom.__file__).resolve().parent
        assert package_root.is_relative_to(unpacked)
        assert set(PromptRepository().list_ids()) == {
            "media_image", "media_video", "repair_json", "scene_beats",
            "scene_beats_fragment", "story_bible", "story_graph", "story_graph_content_fill", "storyboard",
                "storyboard_fragment", "work_unit_correction",
        }
        static_root = package_root / "static"
        index = (static_root / "index.html").read_text(encoding="utf-8")
        assert "/v2/workbench.js" in index
        assert "/v2/workbench.css" in index

        settings = PlotloomSettings.from_env()
        home = Path.home()
        if sys.platform == "darwin":
            expected_data_root = home / "Library" / "Application Support" / "Plotloom"
        elif os.name == "nt":
            expected_data_root = home / "AppData" / "Local" / "Plotloom"
        else:
            expected_data_root = Path(os.environ["XDG_DATA_HOME"]) / "plotloom"
        assert settings.repo_root == expected_data_root.resolve(), settings.repo_root
        assert settings.outputs_dir == (expected_data_root / "outputs").resolve(), settings.outputs_dir
        assert settings.application_data_dir == (expected_data_root / "data").resolve()
        assert settings.text_model != "cwd-poison-model"
        assert not settings.outputs_dir.is_relative_to(Path.cwd())
        assert not settings.application_data_dir.is_relative_to(package_root)
        settings.application_data_dir.mkdir(parents=True, exist_ok=True)
        (settings.application_data_dir / "write-probe").write_text("ok", encoding="utf-8")

        license_roots = list(unpacked.glob("*.dist-info/licenses"))
        assert len(license_roots) == 1, license_roots
        assert (license_roots[0] / "LICENSE").read_text(encoding="utf-8").strip()
        assert (license_roots[0] / "NOTICE").read_text(encoding="utf-8").strip()

        migrator = SchemaMigrator(f"sqlite:///{database_path}")
        assert migrator.script_location.is_relative_to(package_root)
        assert migrator.upgrade() is None
        expected_head = ScriptDirectory(str(migrator.script_location)).get_current_head()
        with sqlite3.connect(database_path) as connection:
            revision = connection.execute("SELECT version_num FROM alembic_version").fetchone()
        assert revision == (expected_head,), revision
        """
    )
    probe_environment = os.environ.copy()
    for name in (
            "PLOTLOOM_DATA_DIR",
            "PLOTLOOM_DATABASE_URL",
            "PLOTLOOM_ARTIFACT_ROOT",
            "PLOTLOOM_LEGACY_ARTIFACT_ROOTS",
            "PLOTLOOM_IMAGE_EXCHANGE_ROOT",
            "PLOTLOOM_ENABLE_WAN_P2",
            "PLOTLOOM_OUTPUTS_DIR",
            "PLOTLOOM_APPLICATION_DATA_DIR",
        "PLOTLOOM_STATIC_DIR",
        "TEXT_MODEL",
    ):
        probe_environment.pop(name, None)
    probe_environment["HOME"] = str(probe_home)
    probe_environment["XDG_DATA_HOME"] = str(probe_home / "xdg-data")
    result = subprocess.run(
        [sys.executable, "-I", "-c", probe, str(unpacked), str(database_path)],
        cwd=probe_cwd,
        env=probe_environment,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, (
        "the built wheel failed its isolated package probe\n"
        f"stdout:\n{result.stdout}\n"
        f"stderr:\n{result.stderr}"
    )
