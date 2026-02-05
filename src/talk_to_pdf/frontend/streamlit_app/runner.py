from __future__ import annotations

import sys
from pathlib import Path

from talk_to_pdf.shared.proc import popen


def run(*, port: int = 8501, address: str = "0.0.0.0"):
    ui_path = Path("src/talk_to_pdf/frontend/streamlit_app/main.py").resolve()
    if not ui_path.exists():
        raise FileNotFoundError(f"Streamlit entrypoint not found: {ui_path}")

    ui_cmd = [
        sys.executable, "-m", "streamlit", "run",
        str(ui_path),
        "--server.port", str(port),
        "--server.address", address,

        # huge CPU saver in dev:
        "--server.fileWatcherType", "none",
        "--server.runOnSave", "false",
    ]

    print(f"[talk_to_pdf] UI : http://localhost:{port}")
    return popen(ui_cmd)
