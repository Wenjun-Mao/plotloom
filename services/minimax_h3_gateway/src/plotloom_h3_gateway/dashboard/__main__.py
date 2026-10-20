"""Independent loopback-only viewer process; never starts inference workers."""
import os
from pathlib import Path

import uvicorn

from .api import create_dashboard


def main():
    app = create_dashboard(Path(os.environ.get("H3_DASHBOARD_DATA_DIR", "/data")))
    uvicorn.run(app, host="127.0.0.1", port=8091, workers=1, access_log=False,
                proxy_headers=False)


if __name__ == "__main__":
    main()
