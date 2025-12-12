from __future__ import annotations
import streamlit as st
from talk_to_pdf.frontend.streamlit_app.settings import BASE_URL
import os
from services.api import Api, ApiError
from components.auth_forms import render_login_form, render_register_form

def sync_user_state(api: Api) -> None:
    """
    Try to sync the logged-in user from backend into session_state.

    - In prod: uses access_token if present.
    - In dev (SKIP_AUTH=True): backend returns DEV_USER even without token.
    """
    # If we already have a user, don't redo this
    if st.session_state.get("current_user") is not None:
        return

    token = st.session_state.get("access_token")

    try:
        user = api.get_me(token)
    except ApiError:
        # Not logged in / dev disabled / etc.
        return

    st.session_state["current_user"] = user



# ---------- API factory ----------

@st.cache_resource
def get_api() -> Api:
    # Example: "http://localhost:8000/api/v1"
    return Api(base_url=BASE_URL)


# ---------- State helpers ----------

def init_state() -> None:
    if "view" not in st.session_state:
        st.session_state["view"] = "landing"
    if "access_token" not in st.session_state:
        st.session_state["access_token"] = None
    if "current_user" not in st.session_state:
        st.session_state["current_user"] = None


def set_view(view: str) -> None:
    st.session_state["view"] = view


# ---------- Layout components ----------

def render_header() -> None:
    st.title("Talk to PDF – Auth")

    user = st.session_state.get("current_user")
    cols = st.columns([3, 1])

    with cols[0]:
        if user:
            st.markdown(
                f"**Logged in as:** {user.get('email', 'Unknown')} "
                f"({user.get('name') or 'No name'})"
            )
        else:
            st.markdown("_Not logged in_")

    with cols[1]:
        if user:
            if st.button("Log out"):
                st.session_state["access_token"] = None
                st.session_state["current_user"] = None
                st.session_state["view"] = "landing"
                st.rerun()


def render_landing_page() -> None:
    user = st.session_state.get("current_user")

    st.subheader("Welcome 👋")

    # Show buttons ONLY when not logged in
    if not user:
        st.write("Please choose how you want to continue:")

        col1, col2 = st.columns(2)

        with col1:
            if st.button("🔐 Login", use_container_width=True):
                set_view("login")
                st.rerun()

        with col2:
            if st.button("📝 Register", use_container_width=True):
                set_view("register")
                st.rerun()
    else:
        # If logged in, show a clean success message instead
        st.success(
            f"You're logged in as **{user.get('email')}**.\n"
            "Use the menu above or log out when you're done."
        )



# ---------- Main router ----------

def main() -> None:
    st.set_page_config(
        page_title="Talk to PDF – Auth",
        page_icon="📄",
        layout="centered",
    )
    init_state()
    api = get_api()

    sync_user_state(api)
    render_header()

    view = st.session_state["view"]

    if view == "landing":
        render_landing_page()
    elif view == "login":
        if st.button("← Back", key="back_from_login"):
            set_view("landing")
            st.rerun()
        render_login_form(api)
    elif view == "register":
        if st.button("← Back", key="back_from_register"):
            set_view("landing")
            st.rerun()
        render_register_form(api)
    else:
        # Fallback
        st.error(f"Unknown view: {view}")
        set_view("landing")


if __name__ == "__main__":
    main()
