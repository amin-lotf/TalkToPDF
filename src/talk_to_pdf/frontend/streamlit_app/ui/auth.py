from __future__ import annotations

import streamlit as st
from talk_to_pdf.frontend.streamlit_app.services.api import Api, ApiError

def init_auth_state() -> None:
    st.session_state.setdefault("access_token", None)
    st.session_state.setdefault("current_user", None)

def sync_user_state(api: Api) -> None:
    """Populate current_user if possible (prod via token, dev via SKIP_AUTH)."""
    if st.session_state.get("current_user") is not None:
        return

    token = st.session_state.get("access_token")
    try:
        st.session_state["current_user"] = api.get_me(token)
    except ApiError:
        # Not logged in / dev disabled / etc.
        return

def is_logged_in() -> bool:
    return st.session_state.get("current_user") is not None

def require_login(api: Api) -> None:
    init_auth_state()
    sync_user_state(api)
    if not is_logged_in():
        st.switch_page("pages/1_login.py")

def logout() -> None:
    st.session_state["access_token"] = None
    st.session_state["current_user"] = None
    st.switch_page("pages/1_login.py")
