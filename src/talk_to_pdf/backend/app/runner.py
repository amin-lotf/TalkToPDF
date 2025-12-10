import subprocess
import sys
from pathlib import Path


def run():
    pkg_dir = Path(__file__).resolve().parent
    home_path = pkg_dir / "main.py"
    if not  home_path.exists():
        raise FileNotFoundError(f"No main.py found in {home_path}")

    api_cmd = [
        sys.executable,
        "-m", "uvicorn",
        "talk_to_pdf.backend.app.main:app",
        "--host", "0.0.0.0",
        "--port", "8000",
        # "--log-level", "warning",  # optional: less noisy logs
    ]

    print("Starting API on http://localhost:8000")
    ui_proc = subprocess.Popen(api_cmd)
    return ui_proc