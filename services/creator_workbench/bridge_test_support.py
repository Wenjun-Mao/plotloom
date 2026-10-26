"""Exercise the deployment boundary without sending any native assignment."""

import json
import subprocess
from http.server import ThreadingHTTPServer
from io import BytesIO
from threading import Thread
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen
from uuid import uuid4

import codex_client
import pytest
from host_bridge import QueueBridge, handler_for

from plotloom.codex_exec_contracts import (
    CodexExecAttempt,
    CodexExecHostStatus,
    CodexExecProfile,
    transition_exec_attempt,
)

TEXT_TASK = "01a0dfa6-40ae-7cf2-82eb-edcde7a8fcc0"
IMAGE_TASK = "01a0c506-84d5-7161-8ae0-2ae914e5d81a"


@pytest.fixture
def bridge(tmp_path):
    executable = tmp_path / "codex"
    executable.touch()
    settings = tmp_path / "settings.json"
    settings.write_text(
        json.dumps(
            {
                "settings": {
                    "text": {"taskId": TEXT_TASK},
                    "image": {"taskId": IMAGE_TASK},
                }
            }
        )
    )
    return QueueBridge(executable, settings, "test-token" * 8)



def _spawn_intent_attempt():
    return CodexExecAttempt(
        attemptId=uuid4(),
        runId=uuid4(),
        projectId=uuid4(),
        jobId="ch_" + "a" * 24,
        operationKey="outline",
        domain="text",
        requestHash="a" * 64,
        packageHash="b" * 64,
        profileHash="c" * 64,
        reservedImageOutputs=0,
        state="spawn_intent",
    )
