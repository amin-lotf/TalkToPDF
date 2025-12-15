from __future__ import annotations

import streamlit as st
from talk_to_pdf.frontend.streamlit_app.main import get_api
from talk_to_pdf.frontend.streamlit_app.ui.auth import init_auth_state, sync_user_state, is_logged_in
from talk_to_pdf.frontend.streamlit_app.services.api import ApiError
from talk_to_pdf.frontend.streamlit_app.ui.layout import  hide_sidebar_nav

st.set_page_config(page_title="Login", layout="wide")
hide_sidebar_nav()
# hide_sidebar_entirely()

st.set_page_config(page_title="Login", layout="centered")

init_auth_state()
api = get_api()
sync_user_state(api)

if is_logged_in():
    st.switch_page("pages/0_home.py")

st.title("Login")
st.divider()

with st.form("login_form"):
    email = st.text_input("Email")
    password = st.text_input("Password", type="password")
    submitted = st.form_submit_button("Login", use_container_width=True)

if submitted:
    if not email or not password:
        st.error("Email and password are required.")
    else:
        try:
            token = api.login(email=email, password=password)
            user = api.get_me(token)
            st.session_state["access_token"] = token
            st.session_state["current_user"] = user
            st.switch_page("pages/0_home.py")
        except ApiError as e:
            st.error(str(e))

st.page_link("pages/2_register.py", label="Create account")
