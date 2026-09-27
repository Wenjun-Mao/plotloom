"""Run one private Voice Lab worker; never use multiple Uvicorn workers."""

import os

import uvicorn


if __name__ == "__main__":
    uvicorn.run(
        "plotloom_voice_lab.app:app",
        host=os.environ.get("VOICE_LAB_HOST", "127.0.0.1"),
        port=int(os.environ.get("VOICE_LAB_PORT", "8897")),
        workers=1,
    )
