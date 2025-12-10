import subprocess
import sys
from pathlib import Path


def run():
    pkg_dir = Path(__file__).resolve().parent
    home_path = pkg_dir / "home.py"
    if not  home_path.exists():
        home_path.write_text("""
        import streamlit as st
        st.set_page_config(page_title="Talk to  PDF", page_icon="🎛️", layout="wide")
        st.title("🎛Talk to your PDF")
        """)
    ui_cmd = [
        sys.executable,
        "-m", "streamlit",
        "run",
        str(home_path),
    ]

    print("Starting UI on http://localhost:8501")
    api_proc = subprocess.Popen(ui_cmd)
    return api_proc