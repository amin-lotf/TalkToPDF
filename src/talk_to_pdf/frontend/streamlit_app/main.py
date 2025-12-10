import streamlit as st
from talk_to_pdf.frontend.streamlit_app.settings import BASE_URL

st.set_page_config(page_title="Talk to  PDF", page_icon="🎛️", layout="wide")

st.title("🎛Talk to your PDF")
st.caption(f"API: {BASE_URL}/docs")