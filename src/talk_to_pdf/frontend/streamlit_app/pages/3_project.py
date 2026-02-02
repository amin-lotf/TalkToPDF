from __future__ import annotations

import time
from typing import Any, Dict, Optional

import streamlit as st

from talk_to_pdf.frontend.streamlit_app.main import get_api
from talk_to_pdf.frontend.streamlit_app.ui.auth import require_login, logout
from talk_to_pdf.frontend.streamlit_app.ui.layout import hide_sidebar_nav
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

# -----------------------------
# Sidebar: Navigation & Project Info
# -----------------------------
def _sidebar_navigation() -> None:
    """Display navigation buttons at the top of sidebar"""
    col1, col2 = st.sidebar.columns(2)
    with col1:
        if st.button("🏠 Home", use_container_width=True, key="nav_home"):
            st.switch_page("pages/0_home.py")
    with col2:
        if st.button("🚪 Logout", use_container_width=True, key="nav_logout"):
            logout()

    st.sidebar.divider()
    st.sidebar.markdown(f"### 📄 {project.get('name', 'Project')}")
    st.sidebar.caption(f"ID: {project.get('id')}")
    st.sidebar.divider()

# -----------------------------
# Sidebar: Indexing Status
# -----------------------------
def _sidebar_indexing(latest_status, latest_err, pending_doc_id) -> None:
    """Display indexing status and controls in sidebar"""
    st.sidebar.markdown("### 🔍 Indexing")

    if latest_err:
        st.sidebar.error(latest_err)

    if latest_status:
        status = str(latest_status.get("status") or "unknown")
        progress = int(latest_status.get("progress") or 0)
        message = latest_status.get("message")
        error = latest_status.get("error")
        cancel_requested = bool(latest_status.get("cancel_requested") or False)

        st.sidebar.markdown(f"**Status:** {_status_badge(status)} {status}")
        st.sidebar.progress(max(0, min(100, progress)) / 100.0)

        if cancel_requested:
            st.sidebar.caption("Cancel requested…")

        if message:
            st.sidebar.info(message)
        if error:
            st.sidebar.error(error)

        c1, c2 = st.sidebar.columns([1, 1], gap="small")
        with c1:
            if st.button("🔄 Refresh", use_container_width=True, key="idx_refresh"):
                st.rerun()

        with c2:
            if st.button("❌ Cancel", use_container_width=True, key="idx_cancel"):
                try:
                    api.cancel_indexing(token, index_id=str(latest_status["index_id"]))
                    st.sidebar.warning("Cancel requested.")
                    st.rerun()
                except ApiError as e:
                    st.sidebar.error(str(e))
    else:
        st.sidebar.caption("No indexing status yet.")
        if pending_doc_id:
            if st.sidebar.button("▶️ Start indexing", use_container_width=True, key="idx_start"):
                try:
                    started = api.start_indexing(
                        token,
                        project_id=str(project_id),
                        document_id=str(pending_doc_id),
                    )
                    st.session_state["current_index_id"] = started["index_id"]
                    st.sidebar.success("Indexing started.")
                    st.rerun()
                except ApiError as e:
                    st.sidebar.error(str(e))

    st.sidebar.divider()

# -----------------------------
# Sidebar: Chat Management
# -----------------------------
def _sidebar_chats(index_ready: bool) -> None:
    """Display chat creation and list in sidebar (only when index is ready)"""
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
# Indexing (auto-start + polling) - moved to sidebar
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

# Guard: check if index is ready
index_ready = False
if latest_status:
    s = str(latest_status.get("status") or "").lower()
    index_ready = s in {"ready", "completed"}

# Display sidebar components in order
_sidebar_navigation()
_sidebar_indexing(latest_status, latest_err, pending_doc_id)
_sidebar_chats(index_ready)

# -----------------------------
# Main Content: Chat Interface
# -----------------------------
selected_chat_id = st.session_state.get("selected_chat_id")

# Clear chat selection when switching projects
if "last_viewed_project" not in st.session_state or st.session_state["last_viewed_project"] != project_id:
    st.session_state["last_viewed_project"] = project_id
    st.session_state.pop("selected_chat_id", None)
    # Clear all cached chat messages
    keys_to_remove = [k for k in st.session_state.keys() if k.startswith("chat_messages_")]
    for k in keys_to_remove:
        st.session_state.pop(k, None)
    st.rerun()

selected_chat_id = st.session_state.get("selected_chat_id")

if not index_ready:
    st.info("💡 Finish indexing to create and use chats.")
elif not selected_chat_id:
    st.info("💡 Select or create a chat from the sidebar to start asking questions.")
else:
    # Load messages from backend when chat is selected
    # Use a key that changes when chat_id changes to trigger reload
    chat_key = f"chat_messages_{selected_chat_id}"

    # Load messages if not already loaded for this chat OR if we need to reload
    if chat_key not in st.session_state or st.session_state.get("reload_messages", False):
        try:
            messages_response = api.get_chat_messages(token, chat_id=selected_chat_id, limit=100)
            st.session_state[chat_key] = messages_response.get("items", [])
            st.session_state["reload_messages"] = False
        except ApiError as e:
            st.error(f"Failed to load messages: {e}")
            st.session_state[chat_key] = []

    messages = st.session_state[chat_key]

    # Show the selected chat with chat-style interface
    # Upper part: Conversation history
    st.markdown("### 💬 Conversation")

    # Container for chat messages with scrollable area
    chat_container = st.container(height=500)

    # Helper function to render a single message
    def render_message(msg, is_streaming=False):
        if msg["role"] == "user":
            st.markdown(f"""
            <div style='background-color: #e3f2fd; padding: 10px; border-radius: 10px; margin: 5px 0;'>
                <strong>🙋 You:</strong><br>{msg['content']}
            </div>
            """, unsafe_allow_html=True)
        else:
            # Assistant message with expandable citations
            content = msg.get('content', '')
            if is_streaming:
                content += "▌"  # Add cursor for streaming effect

            st.markdown(f"""
            <div style='background-color: #f5f5f5; padding: 10px; border-radius: 10px; margin: 5px 0;'>
                <strong>🤖 Assistant:</strong><br>{content}
            </div>
            """, unsafe_allow_html=True)

            # Show citations and metrics in compact expanders (collapsed by default) only if not streaming
            if not is_streaming:
                # Display metrics if available
                metrics_data = msg.get("metrics")
                if metrics_data:
                    tokens = metrics_data.get("tokens", {})
                    prompt = tokens.get("prompt", {})
                    latency = metrics_data.get("latency", {})

                    # Create compact summary for the button label
                    total_tokens = tokens.get("total", 0)
                    total_latency = latency.get("total", 0)

                    with st.expander(f"📊 Metrics ({total_tokens:,} tokens, {total_latency:.2f}s)", expanded=False):
                        # Token metrics
                        st.markdown("**🔢 Token Usage**")

                        col1, col2 = st.columns(2)

                        with col1:
                            st.markdown("**Prompt Breakdown:**")
                            st.caption(f"• System: {prompt.get('system', 0):,}")
                            st.caption(f"• History: {prompt.get('history', 0):,}")
                            st.caption(f"• Rewritten Question: {prompt.get('rewritten_question', 0):,}")
                            st.caption(f"• Context: {prompt.get('context', 0):,}")
                            st.caption(f"• Question: {prompt.get('question', 0):,}")
                            st.caption(f"**Total Prompt: {prompt.get('total', 0):,}**")

                        with col2:
                            st.markdown("**Summary:**")
                            st.caption(f"• Completion: {tokens.get('completion', 0):,}")
                            st.caption(f"**Total: {total_tokens:,}**")

                        st.divider()

                        # Latency metrics
                        st.markdown("**⏱️ Latency (seconds)**")

                        col1, col2, col3, col4 = st.columns(4)

                        with col1:
                            qr_latency = latency.get('query_rewriting')
                            st.metric("Query Rewriting", f"{qr_latency:.2f}s" if qr_latency else "N/A")

                        with col2:
                            ret_latency = latency.get('retrieval')
                            st.metric("Retrieval", f"{ret_latency:.2f}s" if ret_latency else "N/A")

                        with col3:
                            gen_latency = latency.get('reply_generation')
                            st.metric("Reply Generation", f"{gen_latency:.2f}s" if gen_latency else "N/A")

                        with col4:
                            st.metric("Total", f"{total_latency:.2f}s")

                citations_data = msg.get("citations")
                if citations_data:
                    chunks = citations_data.get("chunks", [])
                    num_sources = len(chunks)

                    with st.expander(f"📎 {num_sources} Source{'s' if num_sources != 1 else ''}", expanded=False):
                        # Display rewritten query if available
                        rewritten_query = citations_data.get('rewritten_query')
                        if rewritten_query:
                            st.markdown(f"**🔄 Rewritten Query:** _{rewritten_query}_")
                            st.divider()

                        # Display metadata header
                        col1, col2, col3 = st.columns(3)
                        with col1:
                            st.caption(f"**Model:** {citations_data.get('model', 'N/A')}")
                        with col2:
                            st.caption(f"**Top-k:** {citations_data.get('top_k', 'N/A')}")
                        with col3:
                            st.caption(f"**Metric:** {citations_data.get('metric', 'N/A')}")

                        st.divider()

                        # Display cited chunks
                        if chunks:
                            for idx, chunk in enumerate(chunks, 1):
                                citation = chunk.get("citation", {})
                                score = chunk.get("score")
                                content = chunk.get("content")

                                # Header with score
                                score_text = f" (score: {score:.3f})" if score is not None else ""
                                st.markdown(f"**Source {idx}**{score_text}")

                                # Display chunk content if available
                                if content:
                                    st.markdown(f"""
                                    <div style='background-color: #ffffff; padding: 10px; border-left: 3px solid #4CAF50; margin: 5px 0;'>
                                        {content}
                                    </div>
                                    """, unsafe_allow_html=True)

                                # Display all citation metadata dynamically
                                if citation:
                                    # Build metadata display from all keys in citation dict
                                    metadata_items = []
                                    for key, value in citation.items():
                                        # Format the key nicely (e.g., char_start -> Char Start)
                                        formatted_key = key.replace('_', ' ').title()
                                        metadata_items.append(f"**{formatted_key}:** {value}")

                                    if metadata_items:
                                        # Display metadata in a clean format
                                        st.caption(" • ".join(metadata_items))

                                if idx < len(chunks):
                                    st.divider()
                        else:
                            st.caption("No citations available.")

    with chat_container:
        if not messages:
            st.caption("No messages yet. Start by asking a question below.")
        else:
            # Render existing messages
            for msg in messages:
                render_message(msg, is_streaming=False)

    # Lower part: Input area (fixed at bottom)
    st.divider()
    st.markdown("### 📝 Ask a Question")

    # Input controls
    with st.form("query_form", clear_on_submit=True):
        q = st.text_area("Your question", placeholder="Ask about the PDF…", height=100)

        with st.expander("⚙️ Advanced Settings"):
            c1, c2, c3 = st.columns(3)
            with c1:
                top_k = st.number_input("top_k", min_value=1, max_value=50, value=10, step=1)
            with c2:
                top_n = st.number_input("top_n", min_value=1, max_value=20, value=5, step=1)
            with c3:
                rerank_timeout_s = st.number_input("rerank_timeout_s", min_value=0.0, max_value=20.0, value=0.6, step=0.1)

        submitted = st.form_submit_button("📤 Send", use_container_width=True)

    if submitted:
        if not q.strip():
            st.warning("Type a question first.")
        else:
            with st.spinner("Getting response..."):
                try:
                    # Create placeholders for streaming display
                    with chat_container:
                        # Show user message immediately
                        st.markdown(f"""
                        <div style='background-color: #e3f2fd; padding: 10px; border-radius: 10px; margin: 5px 0;'>
                            <strong>🙋 You:</strong><br>{q.strip()}
                        </div>
                        """, unsafe_allow_html=True)

                        # Create assistant message placeholder
                        assistant_placeholder = st.empty()
                        accumulated_text = []

                        # Stream the response
                        for chunk in api.query_project_stream(
                            token,
                            project_id=str(project_id),
                            chat_id=str(selected_chat_id),
                            query=q.strip(),
                            top_k=int(top_k),
                            top_n=int(top_n),
                            rerank_timeout_s=float(rerank_timeout_s),
                        ):
                            accumulated_text.append(chunk)
                            # Update the assistant message display
                            assistant_placeholder.markdown(f"""
                            <div style='background-color: #f5f5f5; padding: 10px; border-radius: 10px; margin: 5px 0;'>
                                <strong>🤖 Assistant:</strong><br>{"".join(accumulated_text)}▌
                            </div>
                            """, unsafe_allow_html=True)

                        # Final update without cursor
                        assistant_placeholder.markdown(f"""
                        <div style='background-color: #f5f5f5; padding: 10px; border-radius: 10px; margin: 5px 0;'>
                            <strong>🤖 Assistant:</strong><br>{"".join(accumulated_text)}
                        </div>
                        """, unsafe_allow_html=True)

                    # Reload messages from backend
                    st.session_state["reload_messages"] = True
                    st.success("✅ Response received")
                    time.sleep(0.5)
                    st.rerun()

                except ApiError as e:
                    st.error(str(e))

