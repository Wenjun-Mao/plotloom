"""Private one-attempt worker that survives creator-workbench bridge restarts."""
from __future__ import annotations

import argparse
from pathlib import Path
from uuid import UUID


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("--attempt-id", required=True)
    parser.add_argument("--executable", type=Path, required=True)
    parser.add_argument("--source-root", type=Path, required=True)
    parser.add_argument("--outputs-root", type=Path, required=True)
    parser.add_argument("--private-root", type=Path, required=True)
    args = parser.parse_args(argv)

    from codex_exec_supervisor import CodexExecSupervisor

    supervisor = CodexExecSupervisor(
        args.executable,
        source_root=args.source_root,
        outputs_root=args.outputs_root,
        private_root=args.private_root,
    )
    supervisor.run_worker(UUID(args.attempt_id))


if __name__ == "__main__":
    main()
