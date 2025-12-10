import warnings
from talk_to_pdf.frontend.streamlit_app.runner import run as ui_run
from talk_to_pdf.backend.app.runner import run as api_run
warnings.filterwarnings("ignore", message="resource_tracker: There appear to be")
import sys
import pathlib
import subprocess
def main():
    api_proc = api_run()
    ui_proc = ui_run()
    try:
        # Wait until UI exits (or Ctrl+C in this terminal)
        ui_proc.wait()
    except KeyboardInterrupt:
        print("\n Ctrl+C received, shutting down...")
    finally:
        # Ask both processes to terminate (SIGTERM)
        for proc in (ui_proc,api_proc ):
            if proc and proc.poll() is None:
                try:
                    proc.terminate()  # softer than SIGINT
                except Exception:
                    pass

        # Give them a few seconds to exit cleanly, then force kill if needed
        for proc in (ui_proc,api_proc ):
            if proc and proc.poll() is None:
                try:
                    proc.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    proc.kill()
