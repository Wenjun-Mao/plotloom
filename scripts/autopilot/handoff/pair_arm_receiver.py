"""Fixed child entry for one arm, using only the sealed allocation's paths."""
from handoff_qa import admit


def main():
    qa=admit('inner')
    import argparse
    import json
    import sys
    import time
    from pathlib import Path
    parser=argparse.ArgumentParser()
    parser.add_argument('--arm',choices=('serial','parallel'),required=True)
    parser.add_argument('--execute',action='store_true')
    args=parser.parse_args()
    source=Path(qa['projectRoot'])
    sys.path[:0]=[str(source/'src'),str(source/'services/creator_workbench')]
    from pair_context import install
    context=install(arm=args.arm)
    if args.execute:
        from handoff_files import canonical, exclusive_bytes, require
        require(not any((context.work/name).exists() for name in ('arm-start.json','launch_intent.json','result.json')),
            'original arm already started; restart cannot advance or resend')
        ns=getattr(context.allocation,args.arm).namespace
        exclusive_bytes(context.work,'arm-start.json',canonical(dict(namespaceId=str(ns.namespace_id),
            wallNs=time.time_ns(),monotonicNs=time.monotonic_ns())))
    import run_arm
    import signal
    signal.signal(signal.SIGTERM,run_arm.stop)
    signal.signal(signal.SIGINT,run_arm.stop)
    return run_arm.main(['--execute'] if args.execute else [])


if __name__=='__main__':
    raise SystemExit(main())
