# talk_to_pdf/frontend/streamlit_app/components/auth_forms.py
from __future__ import annotations

from typing import Optional

import streamlit as st

from talk_to_pdf.frontend.streamlit_app.services.api import Api, ApiError


def _ensure_auth_state():
    if "access_token" not in st.session_state:
        st.session_state["access_token"] = None
    if "current_user" not in st.session_state:
        st.session_state["current_user"] = None


def render_login_form(api: Api) -> None:
    _ensure_auth_state()

    st.subheader("Login")

    with st.form("login_form"):
        email = st.text_input("Email", key="login_email")
        password = st.text_input("Password", type="password", key="login_password")
        submitted = st.form_submit_button("Login")

    if submitted:
        if not email or not password:
            st.error("Please enter both email and password.")
            return

        try:
            token = api.login(email=email, password=password)
            user = api.get_me(token)
        except ApiError as e:
            st.error(str(e))
            return

        st.session_state["access_token"] = token
        st.session_state["current_user"] = user
        st.success("Logged in successfully ✅")
        st.session_state["view"] = "landing"
        st.rerun()


def render_register_form(api: Api) -> None:
    _ensure_auth_state()

    st.subheader("Create a new account")

    with st.form("register_form"):
        name = st.text_input("Name (optional)", key="register_name")
        email = st.text_input("Email", key="register_email")
        password = st.text_input("Password", type="password", key="register_password")
        password_confirm = st.text_input(
            "Confirm Password",
            type="password",
            key="register_password_confirm",
        )
        submitted = st.form_submit_button("Register")

    if submitted:
        if not email or not password:
            st.error("Please enter at least email and password.")
            return

        if password != password_confirm:
            st.error("Passwords do not match.")
            return

        try:
            user = api.register_user(email=email, password=password, name=name or None)
        except ApiError as e:
            st.error(str(e))
            return

        st.success("Account created successfully 🎉 You can now log in.")
        # Optionally log them in immediately:
        try:
            token = api.login(email=email, password=password)
            me = api.get_me(token)
            st.session_state["access_token"] = token
            st.session_state["current_user"] = me
            st.session_state["view"] = "landing"
            st.rerun()
        except ApiError:
            # If auto-login fails, just leave them on this page
            pass
