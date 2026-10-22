"""Direct guard for the existing exclusive one-step/pause sidecar method."""


def requires_pause(snapshot):
    run, attempts = snapshot['run'], snapshot['attempts']
    checkpoints = run['checkpoints']
    if (run['state'] == 'awaiting_review' or run.get('bundle') is not None
            or any(item['operationKey'] not in {'source','outline'} for item in checkpoints)
            or any(item['operationKey']=='outline' and item['state']=='adopted' for item in checkpoints)
            or len(attempts)>1 or any(item['domain']!='text' or item['operationKey']!='outline' for item in attempts)):
        raise RuntimeError('sidecar exceeded its original Outline/no-adoption boundary')
    delivered = any(item['operationKey']=='outline' and item['state']=='delivered' for item in checkpoints)
    if delivered and not attempts:
        raise RuntimeError('sidecar delivered checkpoint has no original attempt')
    # Recording a successful delivery and adopting it are different controller
    # steps. Pause before the next step even if completion preceded PID sampling.
    return delivered or any(item['processId'] is not None or item['terminalResult']=='success' for item in attempts)
