from __future__ import annotations

import time

from talk_to_pdf.backend.app.runner import run as api_run
from talk_to_pdf.frontend.streamlit_app.runner import run as ui_run
from talk_to_pdf.shared.proc import terminate_tree


def main() -> None:
    api_proc = api_run(host="0.0.0.0", port=8000, reload=True)
    ui_proc = ui_run(port=8501, address="0.0.0.0")

    try:
        while True:
            api_rc = api_proc.poll()
            ui_rc = ui_proc.poll()

            # If either dies, kill the other and exit with a helpful error
            if api_rc is not None:
                raise SystemExit(f"[talk_to_pdf] API exited with code {api_rc}")
            if ui_rc is not None:
                raise SystemExit(f"[talk_to_pdf] UI exited with code {ui_rc}")

            time.sleep(0.3)

    except KeyboardInterrupt:
        print("\n[talk_to_pdf] Ctrl+C received, shutting down...")
    finally:
        terminate_tree(ui_proc)
        terminate_tree(api_proc)


if __name__ == "__main__":
    main()
