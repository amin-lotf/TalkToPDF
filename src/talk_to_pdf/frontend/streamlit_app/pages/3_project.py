from __future__ import annotations

import time
from typing import Any, Dict, Optional

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

# -----------------------------
# Helpers
# -----------------------------
def _extract_first_document_id(project_json: Dict[str, Any]) -> Optional[str]:
    """
    Try hard to find the 'first' document id from your project response,
    without assuming a fixed response shape.
    """
    # common: {"documents":[{"id":...}, ...]}
    docs = project_json.get("documents")
    if isinstance(docs, list) and docs:
        d0 = docs[0]
        if isinstance(d0, dict):
            return str(d0.get("id") or d0.get("document_id") or d0.get("doc_id") or "")
        if isinstance(d0, str):
            return d0

    # common: {"document":{"id":...}}
    doc = project_json.get("document")
    if isinstance(doc, dict):
        val = doc.get("id") or doc.get("document_id") or doc.get("doc_id")
        if val:
            return str(val)

    # fallback keys
    for k in ("document_id", "doc_id"):
        if project_json.get(k):
            return str(project_json[k])

    return None


def _is_terminal(status: str) -> bool:
    """
    You MUST adjust this once you confirm IndexStatus enum values.
    For now: treat common terminal states as done.
    """
    s = (status or "").lower()
    return s in {"ready", "completed", "failed", "error", "cancelled", "canceled"}


def _status_badge(status: str) -> str:
    s = (status or "").lower()
    if s in {"ready", "completed"}:
        return "✅"
    if s in {"failed", "error"}:
        return "❌"
    if s in {"cancelled", "canceled"}:
        return "🛑"
    if s in {"pending", "queued"}:
        return "⏳"
    return "🔄"


# -----------------------------
# Fetch project
# -----------------------------
try:
    project = api.get_project(token, project_id)
except ApiError as e:
    st.error(str(e))
    st.page_link("pages/0_home.py", label="Back to home")
    st.stop()

page_frame(project.get("name", "Project"), key_prefix="project")
# page content
st.caption(f"ID: {project.get('id')}")

# -----------------------------
# Indexing (auto-start + polling)
# -----------------------------
auto_start = bool(st.session_state.get("auto_start_indexing"))
pending_doc_id = st.session_state.get("pending_index_document_id")

st.session_state.setdefault("current_index_id", None)

latest_status = None
latest_err = None

# 1) Auto-start indexing ONCE (immediately after redirect)
if auto_start:
    if not pending_doc_id:
        st.error("auto_start_indexing is True but pending_index_document_id is missing.")
        st.info("This should be set on Home page from create_project() -> primary_document.id")
        st.stop()

    try:
        started = api.start_indexing(
            token,
            project_id=str(project_id),
            document_id=str(pending_doc_id),
        )
        st.session_state["current_index_id"] = started["index_id"]
        latest_status = started
        st.toast("Indexing started", icon="🔄")
    except ApiError as e:
        # If backend returns 409/400 because it already started, we can fall back to latest/poll.
        latest_err = str(e)

    # Never auto-start again
    st.session_state["auto_start_indexing"] = False

# 2) Poll status by index_id (best)
idx = st.session_state.get("current_index_id") or (latest_status or {}).get("index_id")
if idx:
    try:
        latest_status = api.get_index_status(token, index_id=str(idx))
    except ApiError as e:
        latest_err = str(e)
else:
    # 3) Optional fallback: try latest (your backend currently may 500 here if none exists)
    try:
        latest_status = api.get_latest_index_status(token, project_id=str(project_id))
        st.session_state["current_index_id"] = latest_status.get("index_id")
    except ApiError as e:
        msg = str(e)
        # treat "no index yet" as normal (even if backend incorrectly returns 500)
        if "No indexes found for project" in msg or "NoIndexesForProject" in msg or msg.startswith("500"):
            latest_status = None
            latest_err = None
        else:
            latest_err = msg

st.divider()
st.subheader("Indexing")

if latest_err:
    st.error(latest_err)

if latest_status:
    status = str(latest_status.get("status") or "unknown")
    progress = int(latest_status.get("progress") or 0)
    message = latest_status.get("message")
    error = latest_status.get("error")
    cancel_requested = bool(latest_status.get("cancel_requested") or False)

    st.markdown(f"### 🔄 {status}")
    st.progress(max(0, min(100, progress)))

    if cancel_requested:
        st.caption("Cancel requested…")

    if message:
        st.info(message)
    if error:
        st.error(error)

    c1, c2 = st.columns([1, 1], gap="small")
    with c1:
        if st.button("Refresh", use_container_width=True):
            st.rerun()

    with c2:
        if st.button("Cancel indexing", use_container_width=True):
            try:
                api.cancel_indexing(token, index_id=str(latest_status["index_id"]))
                st.warning("Cancel requested.")
                st.rerun()
            except ApiError as e:
                st.error(str(e))
else:
    st.caption("No indexing status yet.")
    st.caption(f"Document to index: {pending_doc_id or 'unknown'}")
    if pending_doc_id and st.button("Start indexing", use_container_width=False):
        try:
            started = api.start_indexing(
                token,
                project_id=str(project_id),
                document_id=str(pending_doc_id),
            )
            st.session_state["current_index_id"] = started["index_id"]
            st.success("Indexing started.")
            st.rerun()
        except ApiError as e:
            st.error(str(e))

st.divider()
st.subheader("Project payload (temporary debug)")
st.json(project)