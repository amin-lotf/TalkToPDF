from __future__ import annotations

import streamlit as st

from talk_to_pdf.frontend.streamlit_app.main import get_api
from talk_to_pdf.frontend.streamlit_app.ui.auth import require_login
from talk_to_pdf.frontend.streamlit_app.ui.layout import hide_sidebar_nav, page_frame
from talk_to_pdf.frontend.streamlit_app.services.api import ApiError

st.set_page_config(page_title="Home", layout="wide")
hide_sidebar_nav()

api = get_api()
require_login(api)
page_frame("Home", key_prefix="home")


def _load_projects() -> list[dict]:
    token = st.session_state.get("access_token")
    try:
        return api.list_projects(token)
    except ApiError as e:
        st.sidebar.error(str(e))
        return []


def _sidebar_projects() -> None:
    st.sidebar.markdown("### Projects")

    # used only to force-reset uploader widget
    st.session_state.setdefault("new_project_uploader_key", 0)
    token = st.session_state.get("access_token")

    with st.sidebar.popover("＋ New project", use_container_width=True):
        upload_key = f"new_project_file_{st.session_state['new_project_uploader_key']}"

        with st.form("new_project_form", clear_on_submit=True):
            name = st.text_input("Name")  # no key needed; form clears it
            pdf = st.file_uploader("PDF", type=["pdf"], key=upload_key)
            submitted = st.form_submit_button("Create", use_container_width=True)

        if submitted:
            if not name.strip():
                st.error("Name is required.")
                return
            if pdf is None:
                st.error("PDF is required.")
                return

            try:
                api.create_project(
                    token,
                    name=name.strip(),
                    file_name=pdf.name,
                    file_bytes=pdf.getvalue(),
                    content_type=pdf.type or "application/pdf",
                )

                # reset uploader (forms don't clear uploader reliably)
                st.session_state["new_project_uploader_key"] += 1

                st.success("Project created")
                st.session_state["new_project_uploader_key"] += 1

            except ApiError as e:
                st.error(str(e))

    st.sidebar.divider()

    projects = _load_projects()
    if not projects:
        st.sidebar.caption("No projects.")
        return

    for p in projects:
        pid = p.get("id")
        if not pid:
            continue

        label = f"📄 {p.get('name', 'Untitled')}"
        if st.sidebar.button(label, use_container_width=True, key=f"open_{pid}"):
            st.session_state["selected_project_id"] = pid
            st.switch_page("pages/3_project.py")


_sidebar_projects()
st.write("Select a project from the sidebar.")
