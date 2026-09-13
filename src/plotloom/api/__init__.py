"""Public API composition façade.

Route ownership lives in focused modules; this compatibility surface preserves
the historical factory imports used by runtimes, tests, and installed wheels.
"""

from .application import create_app
from .project_folder import create_project_folder_authoring_app

__all__ = ["create_app", "create_project_folder_authoring_app"]
