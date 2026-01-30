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
# Sidebar: Chat Management
# -----------------------------
def _sidebar_chats() -> None:
    """Display chat creation and list in sidebar (only when index is ready)"""
    # Check if index is ready
    index_ready = False
    if latest_status:
        s = str(latest_status.get("status") or "").lower()
        index_ready = s in {"ready", "completed"}

    if not index_ready:
        st.sidebar.info("🔄 Finish indexing to create chats")
        return

    st.sidebar.markdown("### 💬 Chats")

    # Create chat button with popover
    with st.sidebar.popover("➕ New Chat", use_container_width=True):
        with st.form("new_chat_form", clear_on_submit=True):
            chat_title = st.text_input("Chat title", placeholder="e.g., Questions about chapter 1")
            create_btn = st.form_submit_button("Create", use_container_width=True)

        if create_btn:
            if not chat_title.strip():
                st.error("Chat title is required.")
            else:
                try:
                    new_chat = api.create_chat(token, project_id=str(project_id), title=chat_title.strip())
                    st.session_state["selected_chat_id"] = new_chat.get("id")
                    st.success(f"Chat created!")
                    st.rerun()
                except ApiError as e:
                    st.error(str(e))

    st.sidebar.divider()

    # List chats
    try:
        chats_response = api.list_chats(token, project_id=str(project_id))
        chats = chats_response.get("items", [])
    except ApiError as e:
        st.sidebar.error(f"Failed to load chats: {e}")
        return

    if not chats:
        st.sidebar.caption("No chats yet.")
        return

    selected_chat_id = st.session_state.get("selected_chat_id")

    for chat in chats:
        chat_id = str(chat.get("id"))
        chat_title_text = chat.get("title", "Untitled")
        is_selected = (selected_chat_id == chat_id)

        row = st.sidebar.columns([8, 1], gap="small")

        with row[0]:
            btn_icon = "🔵" if is_selected else "💬"
            if st.button(f"{btn_icon} {chat_title_text}", use_container_width=True, key=f"open_chat_{chat_id}"):
                st.session_state["selected_chat_id"] = chat_id
                st.rerun()

        with row[1]:
            with st.popover("⋯", use_container_width=True):
                st.caption(chat_title_text)

                # Delete (confirm)
                st.warning("Delete is permanent.")
                confirm = st.checkbox("I understand", key=f"del_chat_confirm_{chat_id}")
                if st.button("Delete", use_container_width=True, key=f"delete_chat_{chat_id}", disabled=not confirm):
                    try:
                        api.delete_chat(token, chat_id=chat_id)

                        # Clear selection if this chat was selected
                        if st.session_state.get("selected_chat_id") == chat_id:
                            st.session_state.pop("selected_chat_id", None)

                        st.success("Chat deleted.")
                        st.rerun()
                    except ApiError as e:
                        st.error(str(e))

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

# Call sidebar function to display chats
_sidebar_chats()

# -----------------------------
# Main Content: Selected Chat
# -----------------------------
selected_chat_id = st.session_state.get("selected_chat_id")

# Guard: check if index is ready
index_ready = False
if latest_status:
    s = str(latest_status.get("status") or "").lower()
    index_ready = s in {"ready", "completed"}

if not index_ready:
    st.info("💡 Finish indexing to create and use chats.")
elif not selected_chat_id:
    st.info("💡 Select or create a chat from the sidebar to start asking questions.")
else:
    # Show the selected chat
    st.divider()
    st.subheader("💬 Ask a Question")

    # Input controls
    with st.form("query_form", clear_on_submit=False):
        q = st.text_input("Question", value=st.session_state.get("last_query", ""), placeholder="Ask about the PDF…")
        c1, c2, c3 = st.columns(3)
        with c1:
            top_k = st.number_input("top_k", min_value=1, max_value=50, value=10, step=1)
        with c2:
            top_n = st.number_input("top_n", min_value=1, max_value=20, value=5, step=1)
        with c3:
            rerank_timeout_s = st.number_input("rerank_timeout_s", min_value=0.0, max_value=20.0, value=0.6, step=0.1)

        submitted = st.form_submit_button("Run query")

    if submitted:
        if not q.strip():
            st.warning("Type a question first.")
        else:
            st.session_state["last_query"] = q
            try:
                t0 = time.perf_counter()
                reply = api.query_project(
                    token,
                    project_id=str(project_id),
                    query=q.strip(),
                    top_k=int(top_k),
                    top_n=int(top_n),
                    rerank_timeout_s=float(rerank_timeout_s),
                )
                dt_ms = (time.perf_counter() - t0) * 1000.0
                st.caption(f"Latency: {dt_ms:.0f} ms")

            except ApiError as e:
                st.error(str(e))
                reply = None

            if reply:
                # --- Answer ---
                st.markdown("### Answer")
                st.write(reply.get("answer", ""))

                # --- Context inspector ---
                st.markdown("### Context chunks (inspect quality)")

                ctx = reply.get("context") or {}
                chunks = ctx.get("chunks") or []

                # quick stats
                st.caption(
                    f"index_id: {ctx.get('index_id')} | "
                    f"embed_signature: {ctx.get('embed_signature')} | "
                    f"metric: {ctx.get('metric')} | "
                    f"chunks returned: {len(chunks)}"
                )

                # show chunks one-by-one (best for quality)
                for i, ch in enumerate(chunks, start=1):
                    score = ch.get("score")
                    chunk_id = ch.get("chunk_id")
                    chunk_index = ch.get("chunk_index")

                    title = f"#{i}  score={score:.4f}  chunk_index={chunk_index}  id={chunk_id}"
                    with st.expander(title, expanded=(i <= 2)):
                        # main text
                        st.write(ch.get("text", ""))

                        # meta & citation (debug)
                        meta = ch.get("meta")
                        citation = ch.get("citation")

                        m1, m2 = st.columns(2)
                        with m1:
                            st.caption("meta")
                            st.json(meta if meta is not None else {})
                        with m2:
                            st.caption("citation")
                            st.json(citation if citation is not None else {})

                # raw payload toggle (useful when debugging mapping)
                with st.expander("Raw reply payload (debug)", expanded=False):
                    st.json(reply)


st.divider()
st.subheader("Project payload (temporary debug)")
st.json(project)

