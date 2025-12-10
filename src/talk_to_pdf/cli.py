import warnings
from talk_to_pdf.frontend.streamlit_app.runner import run
warnings.filterwarnings("ignore", message="resource_tracker: There appear to be")
import sys
import pathlib
import subprocess
def main():
    ui_proc = run()

    try:
        # Wait until UI exits (or Ctrl+C in this terminal)
        ui_proc.wait()
    except KeyboardInterrupt:
        print("\n Ctrl+C received, shutting down...")
    finally:
        # Ask both processes to terminate (SIGTERM)
        for proc in (ui_proc, ):
            if proc and proc.poll() is None:
                try:
                    proc.terminate()  # softer than SIGINT
                except Exception:
                    pass

        # Give them a few seconds to exit cleanly, then force kill if needed
        for proc in (ui_proc, ):
            if proc and proc.poll() is None:
                try:
                    proc.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    proc.kill()
