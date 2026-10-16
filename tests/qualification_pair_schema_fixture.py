"""Test-owned fake CLI/source allocation; never invokes production Codex or a provider."""
import argparse
import json
import sys
from pathlib import Path


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('action',choices=('prepare','inspect','shadow','registered','namespace'))
    parser.add_argument('--root',type=Path,required=True)
    parser.add_argument('--source',type=Path,required=True)
    args=parser.parse_args()
    root,source=args.root,args.source
    sys.dont_write_bytecode=True
    if args.action=='prepare':
        sys.path[:0]=[str(source/'src'),str(source/'services/creator_workbench'),
            str(source/'scripts/autopilot/handoff'),str(source/'scripts/autopilot')]
        from prepare_pair import prepare
        from handoff_files import canonical,exclusive_bytes
        author=json.loads((source/'scripts/autopilot/handoff/pair-author-inputs.example.json').read_bytes())
        allocation=prepare(source_root=source,work_root=root/'work',bundle_root=root/'bundle',phase_root=root/'phase',
            executable=root/'fake-codex',qa_bytes=(root/'qa.json').read_bytes(),author_inputs=author,
            preservation_bytes=canonical(dict(sourceRevision='synthetic-history',pinnedFiles={},
                baselinePath='unit-only-baseline.json',oldCampaignRoot='unit-only-history')),
            historical_context=dict(historicalSourceRevision='synthetic-history',qualifiedCurrentEvidence={},
                historicalHashManifest='unit-only-manifest.json',historicalHashManifestSha256='c'*64),
            functional_proof_root=root/'functional')
        raw=canonical(allocation.model_dump(mode='json',by_alias=True))
        exclusive_bytes(root,'allocation.json',raw)
        import handoff_bundle
        handoff_bundle.seal_bundle(root/'bundle',qa_bytes=(root/'qa.json').read_bytes(),pair_allocation_bytes=raw)
        from handoff_plan import prepare_transport
        packet=prepare_transport(root/'bundle',root/'phase',authority='qualification_pair_once',nonce=allocation.nonce)
        exclusive_bytes(root,'transport.json',canonical(packet))
        print(json.dumps(dict(syntheticEvidence=True,qualification=False,projectsCreated=0,generationDispatches=0)))
        return 0
    sys.path[:0]=[str(root/'bundle'),str(source/'src'),str(source/'services/creator_workbench')]
    if args.action=='registered':
        packet=json.loads((root/'transport.json').read_bytes())
        sys.argv=['pair_launch.py','--phase-root',str(root/'phase'),'--phase-sha',packet['phaseSha256']]
        import pair_launch
        return pair_launch.main()
    if args.action=='shadow':
        from types import ModuleType
        shadow=root/'shadow.py'
        shadow.write_text('# deliberately foreign unit control')
        module=ModuleType('campaign_guard')
        module.__file__=str(shadow)
        sys.modules['campaign_guard']=module
    from pair_context import install
    context=install()
    if args.action=='namespace':
        from codex_exec_supervisor import CodexExecSupervisor
        arm=context.allocation.serial
        ns=arm.namespace
        CodexExecSupervisor(Path(ns.executable.path),source_root=Path(ns.source_root.path),
            outputs_root=Path(ns.outputs_root.path),private_root=Path(ns.private_root.path),
            namespace_binding_sha256=arm.namespace_binding_sha256)
    print(json.dumps(dict(syntheticEvidence=True,qualification=False,source=str(context.source),work=str(context.campaign))))
    return 0


if __name__=='__main__':
    raise SystemExit(main())
