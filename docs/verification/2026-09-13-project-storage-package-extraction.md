# Project-storage package extraction receipt

## Scope and baseline

Checkpoint `cf68c2f0950c98abe1ff86eb2b8a8bdce8395f7e` contained an 822-line
`src/plotloom/project_storage.py`.  The preserved public surface is
`ProjectFolderStorage`, `ProjectStore`, `ProjectDirectoryRegistry`,
`ProjectHome`, `ProjectManifest`, `OwnedArtifact`, `ProjectArtifactStore`,
`ApplicationStore`, `ApplicationProfile`, `GlobalAccountingEntry`, format-5
constants, and all four project-storage error types.

## Result

The module was replaced by an intentional `project_storage` package:

| Module | Responsibility |
| --- | --- |
| `format.py` | format-5 values, errors, JSON/hash/path/confinement primitives |
| `artifacts.py` | project-owned content-addressed bytes and artifact adapter |
| `application_store.py` | installation-local profile selection and accounting |
| `project_handle.py` | bound `ProjectSQLiteRepository`, CAS-facing methods, image handoff |
| `registry.py` | manifest-derived directory creation, discovery, and opening |
| `composition.py` | public project/application composition and direct text pipeline entry |
| `__init__.py` | explicit documented public exports only |

No database schema, format version, persistence capability, public signature,
direct `project_generation_storage` pipeline, or generated frontend asset moved.
`PROJECT_TEXT_PIPELINE_TABLE_NAMES` and `ProjectSQLiteRepository` remain in
`persistence.py`: their base/subclass extraction is deferred to avoid an
intermediate cyclic or forwarding import layer.

## Evidence

Focused storage, image workflow, and API modularization contracts passed after
the extraction: `12 passed`.  The repository does not install Ruff, so the
package was formatted with ephemeral `uvx ruff format` rather than altering
the locked project environment.

A wheel was built with `uv build --wheel`, installed into a fresh temporary
virtual environment, and imported there.  That installed-package smoke also
constructed two separate temporary `ProjectFolderStorage` homes.  An in-source
smoke created, closed, rediscovered, and reopened two distinct temporary
project homes through the retained public registry API.
