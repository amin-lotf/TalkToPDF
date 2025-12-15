from __future__ import annotations

import streamlit as st

from talk_to_pdf.frontend.streamlit_app.main import get_api
from talk_to_pdf.frontend.streamlit_app.ui.auth import require_login
from talk_to_pdf.frontend.streamlit_app.ui.layout import hide_sidebar_nav, page_frame
from talk_to_pdf.frontend.streamlit_app.services.api import ApiError

st.set_page_config(page_title="Project", layout="wide")
hide_sidebar_nav()

api = get_api()
require_login(api)

project_id = st.session_state.get("selected_project_id")
if not project_id:
    st.switch_page("pages/0_home.py")

token = st.session_state.get("access_token")

# ✅ fetch FIRST
try:
    project = api.get_project(token, project_id)
except ApiError as e:
    st.error(str(e))
    st.page_link("pages/0_home.py", label="Back to home")
    st.stop()

# ✅ then render header
page_frame(project.get("name", "Project"), key_prefix="project")


# page content
st.caption(f"ID: {project.get('id')}")

st.json(project)  # later you’ll replace this with your real UI
