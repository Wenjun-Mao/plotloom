"""Executable synthetic boundary: real registered source, fake external native IO.

The fixture substitutes only uv exec/process observations and the external Codex
CLI. Project preparation, claims, CAS, namespace, validation/receipts and HOLD
run through the actual production source in the disposable committed checkout.
"""
import argparse
import json
import os
import subprocess
import sys
import time
from pathlib import Path


def arguments():
    parser = argparse.ArgumentParser()
    parser.add_argument("action", choices=["prepare", "outer", "inner"])
    parser.add_argument("--case-root", type=Path, required=True)
    parser.add_argument("--source-root", type=Path, required=True)
    parser.add_argument("--mode", default="success")
    return parser.parse_args()


def main():
    args = arguments()
    case, source = args.case_root, args.source_root
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    from tests.paid_outline_processes import install_spawn_journal, journal_spawn
    journal_spawn(case, os.getpid(), parent_pid=os.getppid())
    install_spawn_journal(case)
    sys.path.insert(0, str(source / "src"))
    sys.path.insert(0, str(source / "scripts/autopilot/handoff" if args.action == "prepare" else case / "bundle"))
    if args.action == "prepare":
        return prepare(case, source)
    return receive(case, source, args.action, args.mode)


def prepare(case, source):
    import hashlib

    from handoff_files import canonical, exclusive_bytes
    from paid_outline_prepare import prepare_outline_allocation

    from plotloom.autopilot_contracts import LaunchRequest
    from plotloom.conformance import FIXED_CHINESE_BRIEF

    qa_raw = (case / "qa.json").read_bytes()
    allocation = prepare_outline_allocation(data_root=case / "data", bundle_root=case / "bundle",
        phase_root=case / "phase", source_root=source, executable=case / "fake-codex",
        qa=json.loads(qa_raw), qa_pin_sha256=hashlib.sha256(qa_raw).hexdigest(),
        brief=FIXED_CHINESE_BRIEF.model_copy(update={"decision_points_per_path": 1, "ending_count": 2, "desired_join_count": 0}),
        launch_request=LaunchRequest(expected_brief_revision=1, render_style="realistic", art_render_style="realistic"))
    sys.path.insert(0, str(source / "scripts/autopilot"))
    from handoff_bundle import seal_bundle
    seal_bundle(case / "bundle", source=source / "scripts/autopilot/handoff", qa_bytes=qa_raw,
        allocation_bytes=canonical(allocation.model_dump(mode="json", by_alias=True)))
    from handoff_plan import prepare_transport
    packet = prepare_transport(case / "bundle", case / "phase", authority="paid_outline_once", nonce=allocation.nonce)
    exclusive_bytes(case, "transport.json", canonical(packet))
    return 0


def receive(case, source, action, mode):
    packet = json.loads((case / "transport.json").read_bytes())
    bundle, root, phase_sha = case / "bundle", case / "phase", packet["phaseSha256"]
    real_check_output = subprocess.check_output
    birth = "Thu Oct 15 06:09:00 2026"
    qa = json.loads((case / "qa.json").read_bytes())
    from handoff_source import ENTRY_REGISTRY, RECEIVER_REGISTRY
    kind='qualification_pair' if mode=='pair-transport' else 'paid_outline'
    argv = ["/opt/homebrew/bin/uv", "run", "--locked", "--no-sync", "python", "-B",
        str(bundle / RECEIVER_REGISTRY[kind]), "--phase-root", str(root), "--phase-sha", phase_sha]
    parent_command = " ".join(argv)
    child_command = " ".join([qa["allowedInnerExecutables"][0], *argv[5:]])
    def fake_ps(command, **kwargs):
        if command[0] == "ps" and "-p" in command:
            requested = command[command.index("-p") + 1]
            if action == "outer" and requested == str(os.getpid()) and not (root / "launch.json").exists():
                return f"{os.getpid()} {os.getppid()} {os.getpid()} {birth} {parent_command}\n"
            if action == "inner" and requested == f"{os.getppid()},{os.getpid()}":
                return f"{os.getppid()} 1 {os.getppid()} {birth} {parent_command}\n{os.getpid()} {os.getppid()} {os.getppid()} {birth} {child_command}\n"
        return real_check_output(command, **kwargs)
    subprocess.check_output = fake_ps
    if action == "outer":
        def fake_exec(executable, command, environment):
            assert executable == "/opt/homebrew/bin/uv" and command == argv
            child = [sys.executable, "-B", str(Path(__file__).resolve()), "inner", "--case-root", str(case),
                "--source-root", str(source), "--mode", mode]
            process = subprocess.Popen(child, cwd=source, env=environment)
            # Parent fixture owns every recorded descendant on timeout/error;
            # preserve natural completion and do not kill only the direct child.
            raise SystemExit(process.wait(timeout=45))
        os.execvpe = fake_exec
        sys.argv = [str(bundle / ENTRY_REGISTRY[kind]), "--phase-root", str(root), "--phase-sha", phase_sha]
        if kind=='qualification_pair':
            import pair_launch
            return pair_launch.main()
        import paid_launch
        return paid_launch.main()
    if mode == "deadline":
        started = int(json.loads((root / "launch.json").read_bytes())["startedMonotonicNs"])
        now = {"value": started + 1}
        time.monotonic_ns = lambda: now["value"]
        real_run = subprocess.run
        def readiness_clock(command, **kwargs):
            result = real_run(command, **kwargs)
            if command[-2:] == ["login", "status"]:
                now["value"] = started + 60_000_000_001
            return result
        subprocess.run = readiness_clock
    if mode == "lost-ack":
        real_popen = subprocess.Popen
        def lost_worker(command, **kwargs):
            if len(command) > 1 and str(command[1]).endswith("codex_exec_supervisor_worker.py"):
                raise OSError("synthetic worker launch acknowledgment lost")
            return real_popen(command, **kwargs)
        subprocess.Popen = lost_worker
    if kind=='qualification_pair':
        import pair_context
        original_install=pair_context.install
        def install_transport_callback():
            context=original_install()
            import run_pair
            run_pair.preflight=lambda:dict(syntheticEvidence=True,qualification=False)
            def held_execute(_sealed):
                from handoff_files import publish_record,read_record
                witness=read_record(root,'receiver-accepted.json')[0]
                assert witness['nativeExecHandle']==42
                assert witness['allocationSha256']==json.loads((root/'phase.json').read_bytes())['allocationSha256']
                publish_record(root,'synthetic-pair-callback.json',dict(syntheticEvidence=True,qualification=False,
                    nativeExecHandle=witness['nativeExecHandle'],generationDispatches=0,heldBeforeProjects=True))
                return 1
            run_pair.execute=held_execute
            return context
        pair_context.install=install_transport_callback
        import pair_receiver
        sys.argv=['pair_receiver.py','--phase-root',str(root),'--phase-sha',phase_sha]
        return pair_receiver.main()
    import paid_receiver
    return paid_receiver.main(["--phase-root", str(root), "--phase-sha", phase_sha])


if __name__ == "__main__":
    raise SystemExit(main())
