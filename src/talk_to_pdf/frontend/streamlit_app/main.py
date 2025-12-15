from __future__ import annotations

import streamlit as st
from talk_to_pdf.frontend.streamlit_app.settings import BASE_URL
from talk_to_pdf.frontend.streamlit_app.services.api import Api
from talk_to_pdf.frontend.streamlit_app.ui.auth import init_auth_state, sync_user_state, is_logged_in

st.set_page_config(page_title="Talk to PDF", layout="wide")
# and call hide_* before switching if you want, but it barely matters since you switch immediately

@st.cache_resource
def get_api() -> Api:
    return Api(base_url=BASE_URL)

def main() -> None:
    st.set_page_config(page_title="Talk to PDF", layout="centered")
    init_auth_state()
    api = get_api()
    sync_user_state(api)

    # Entry behavior:
    if is_logged_in():
        st.switch_page("pages/0_home.py")
    else:
        st.switch_page("pages/1_login.py")

if __name__ == "__main__":
    main()
