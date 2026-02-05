from __future__ import annotations

import sys

from talk_to_pdf.shared.proc import popen


def run(*, host: str = "0.0.0.0", port: int = 8000, reload: bool = True):
    api_cmd = [
        sys.executable, "-m", "uvicorn",
        "talk_to_pdf.backend.app.main:app",
        "--host", host,
        "--port", str(port),
        "--log-level", "info",
    ]
    if reload:
        api_cmd.append("--reload")

    print(f"[talk_to_pdf] API: http://{host}:{port}")
    return popen(api_cmd)
