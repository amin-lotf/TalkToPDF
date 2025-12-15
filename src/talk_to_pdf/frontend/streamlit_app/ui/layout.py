from __future__ import annotations
import streamlit as st

from talk_to_pdf.frontend.streamlit_app.ui.auth import logout

def hide_sidebar_nav() -> None:
    st.markdown(
        "<style>[data-testid='stSidebarNav']{display:none;}</style>",
        unsafe_allow_html=True,
    )

def top_bar(key_prefix: str) -> None:
    cols = st.columns([1, 6, 1])

    with cols[0]:
        if st.button(
            "Home",
            use_container_width=True,
            key=f"{key_prefix}_nav_home",
        ):
            st.switch_page("pages/0_home.py")

    with cols[1]:
        user = st.session_state.get("current_user") or {}
        st.caption(user.get("email", ""))

    with cols[2]:
        if st.button(
            "Log out",
            use_container_width=True,
            key=f"{key_prefix}_nav_logout",
        ):
            logout()


def page_frame(title: str, *, key_prefix: str) -> None:
    top_bar(key_prefix)
    st.divider()
    st.title(title)
