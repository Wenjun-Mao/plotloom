"""Install the built Plotloom wheel and probe it outside the source checkout."""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
import tempfile
import textwrap
import zipfile
from pathlib import Path


def _wheel_from(directory: Path) -> Path:
    wheels = sorted(directory.resolve().glob("plotloom-*.whl"))
    if len(wheels) != 1:
        raise SystemExit(f"expected one Plotloom wheel in {directory}, found {len(wheels)}")
    return wheels[0]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("wheel_directory", type=Path, nargs="?", default=Path("dist"))
    args = parser.parse_args()
    wheel = _wheel_from(args.wheel_directory)
    with zipfile.ZipFile(wheel) as archive:
        names = set(archive.namelist())
        license_roots = {
            name.rsplit("/", 1)[0]
            for name in names
            if name.endswith(".dist-info/licenses/LICENSE")
        }
        if len(license_roots) != 1:
            raise SystemExit("wheel must contain one dist-info license directory")
        license_root = next(iter(license_roots))
        for filename in ("LICENSE", "NOTICE"):
            member = f"{license_root}/{filename}"
            if member not in names or not archive.read(member).strip():
                raise SystemExit(f"wheel is missing non-empty {filename}")

    with tempfile.TemporaryDirectory(prefix="plotloom-installed-wheel-") as temporary:
        temporary_root = Path(temporary)
        environment_root = temporary_root / "environment"
        subprocess.run(
            ["uv", "venv", "--python", "3.12", str(environment_root)],
            check=True,
        )
        python = (
            environment_root / "Scripts" / "python.exe"
            if os.name == "nt"
            else environment_root / "bin" / "python"
        )
        subprocess.run(
            ["uv", "pip", "install", "--python", str(python), str(wheel)],
            check=True,
        )

        unrelated = temporary_root / "unrelated-working-directory"
        unrelated.mkdir()
        (unrelated / "pyproject.toml").write_text(
            "[project]\nname='unrelated-launch-directory'\n",
            encoding="utf-8",
        )
        (unrelated / ".env").write_text(
            "PLOTLOOM_DATA_DIR=cwd-poison-data\nTEXT_MODEL=cwd-poison-model\n",
            encoding="utf-8",
        )
        probe_home = temporary_root / "probe-home"
        database = temporary_root / "installed.sqlite3"
        probe = textwrap.dedent(
            """
            import importlib.metadata
            import os
            import sqlite3
            import sys
            from pathlib import Path

            from alembic.script import ScriptDirectory
            import plotloom
            from plotloom.config import PlotloomSettings
            from plotloom.domain import ProjectBrief
            from plotloom.generation.prompts import PromptRepository
            from plotloom.project_storage import ProjectFolderStorage
            from plotloom.schema import SchemaMigrator

            database = Path(sys.argv[1]).resolve()
            package_root = Path(plotloom.__file__).resolve().parent
            assert "site-packages" in package_root.parts, package_root
            assert importlib.metadata.version("plotloom") == "0.1.0"
            scripts = {
                entry.name: entry.value
                for entry in importlib.metadata.entry_points(group="console_scripts")
            }
            assert scripts["plotloom"] == "plotloom.runtime:main"
            assert set(PromptRepository().list_ids()) == {
                "media_image", "media_video", "repair_json", "scene_beats",
                "scene_beats_fragment", "story_bible", "story_graph",
                "story_graph_content_fill", "storyboard", "storyboard_fragment",
                "work_unit_correction",
            }
            assert (package_root / "static" / "index.html").is_file()
            assert (package_root / "static" / "workbench.js").is_file()
            assert (package_root / "alembic" / "versions" / "0001_initial.py").is_file()
            assert (
                package_root
                / "alembic"
                / "versions"
                / "0006_model_profiles_and_graph_topologies.py"
            ).is_file()
            assert (
                package_root
                / "alembic"
                / "versions"
                / "0007_generation_run_failure_codes.py"
            ).is_file()

            settings = PlotloomSettings.from_env()
            home = Path.home()
            if sys.platform == "darwin":
                expected = home / "Library" / "Application Support" / "Plotloom"
            elif os.name == "nt":
                expected = home / "AppData" / "Local" / "Plotloom"
            else:
                expected = Path(os.environ["XDG_DATA_HOME"]) / "plotloom"
            assert settings.data_dir == expected.resolve(), settings.data_dir
            assert settings.text_model != "cwd-poison-model"
            assert not settings.data_dir.is_relative_to(Path.cwd())

            project_root = database.parent / "project-folder"
            outputs_root = project_root / "outputs"
            application_root = project_root / "application"
            outputs_root.mkdir(parents=True)
            application_root.mkdir()
            storage = ProjectFolderStorage(
                outputs_root=outputs_root, application_data_root=application_root
            )
            project_store = storage.projects.create(
                ProjectBrief(title="wheel project", synopsis="independent project folder")
            )
            project_store.close()
            assert "plotloom.persistence.legacy_repository" not in sys.modules

            migrator = SchemaMigrator(f"sqlite:///{database}")
            migrator.upgrade()
            expected_head = ScriptDirectory(str(migrator.script_location)).get_current_head()
            with sqlite3.connect(database) as connection:
                actual_head = connection.execute(
                    "SELECT version_num FROM alembic_version"
                ).fetchone()
            assert actual_head == (expected_head,), actual_head
            """
        )
        environment = os.environ.copy()
        provider_environment_names = {
            "ATLASCLOUD_API_KEY",
            "HOST",
            "IMAGE_BASE_URL",
            "IMAGE_MODEL",
            "IMAGE_MODEL_API_KEY",
            "IMAGE_PROVIDER",
            "PORT",
            "TEXT_BASE_URL",
            "TEXT_MODEL",
            "TEXT_MODEL_API_KEY",
            "TEXT_PROVIDER",
            "VIDEO_BASE_URL",
            "VIDEO_MODEL",
            "VIDEO_MODEL_API_KEY",
            "VIDEO_PROVIDER",
        }
        for name in tuple(environment):
            if name.startswith("PLOTLOOM_") or name in provider_environment_names:
                environment.pop(name, None)
        environment["HOME"] = str(probe_home)
        environment["XDG_DATA_HOME"] = str(probe_home / "xdg-data")
        subprocess.run(
            [str(python), "-I", "-c", probe, str(database)],
            cwd=unrelated,
            env=environment,
            check=True,
        )

    print(f"installed-wheel smoke passed: {wheel.name}")


if __name__ == "__main__":
    main()
