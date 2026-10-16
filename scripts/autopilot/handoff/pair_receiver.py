"""Original-handle attendance followed by the fixed finite serial-first pair."""
from handoff_qa import admit


def main():
    qa=admit('inner')
    import argparse
    import json
    import signal
    import sys
    import time
    from pathlib import Path
    from handoff_files import digest,publish_record,read_owned,read_record,require
    from handoff_phase import B,R,load_phase
    from handoff_process import child_tree
    from handoff_receiver import accept_attendance
    parser=argparse.ArgumentParser()
    parser.add_argument('--phase-root',required=True)
    parser.add_argument('--phase-sha',required=True)
    args=parser.parse_args()
    sys.path[:0]=[str(R/'src'),str(R/'services/creator_workbench')]
    phase=load_phase(args.phase_root,args.phase_sha,expected_kind='qualification_pair')
    root=Path(args.phase_root)
    launch=read_record(root,'launch.json')
    require(launch is not None,'missing original pair launch')
    tree=child_tree(launch[0],launch[1],json.loads(read_owned(B/'qa-interpreter.json')))
    publish_record(root,'driver-process.json',tree)
    from pair_context import install
    context=install()
    require(not (context.campaign/'campaign_intent.json').exists(),'original pair cannot restart')
    _attendance,witness=accept_attendance(phase,args.phase_sha,launch[0],tree)
    require(time.monotonic_ns()<int(witness['deadlineMonotonicNs'])
        and witness['allocationSha256']==phase['allocationSha256'],'pair attachment authority expired or changed')
    publish_record(root,'pair-authority-accepted.json',dict(allocationSha256=phase['allocationSha256'],
        witnessSha256=digest(read_owned(root/'receiver-accepted.json')),attachmentComplete=True,
        generationAuthorityFromAllocationOnly=True))
    import run_pair
    signal.signal(signal.SIGTERM,run_pair.stop)
    signal.signal(signal.SIGINT,run_pair.stop)
    sealed=run_pair.preflight()
    require(not run_pair.STOPPED,'operator stopped before pair intent')
    code=run_pair.execute(sealed)
    if code==0:
        import analyze_pair
        analysis=analyze_pair.main()
        from campaign_guard import require_pair_overlap
        overlap=require_pair_overlap(context.campaign,analysis)
        publish_record(root,'pair-overlap-qualified.json',overlap)
    return code


if __name__=='__main__':
    raise SystemExit(main())
