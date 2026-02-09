from __future__ import annotations

import time
from typing import Any, Dict, Optional

import streamlit as st

from talk_to_pdf.frontend.streamlit_app.main import get_api
from talk_to_pdf.frontend.streamlit_app.ui.auth import require_login, logout
from talk_to_pdf.frontend.streamlit_app.ui.layout import hide_sidebar_nav
from talk_to_pdf.frontend.streamlit_app.services.api import ApiError

# -----------------------------
# Page config + global styling
# -----------------------------
st.set_page_config(page_title="TalkToPDF", layout="wide")
hide_sidebar_nav()

st.markdown(
    """
<style>
/* Tighten the whole app a bit */
.main .block-container { padding-top: 1.0rem; padding-bottom: 1.0rem; max-width: 1100px; }

/* Sidebar spacing */
section[data-testid="stSidebar"] .block-container { padding-top: 1.0rem; }

/* Make chat messages feel more like a modern chat */
[data-testid="stChatMessage"] {
  border-radius: 14px;
  padding: 0.15rem 0.25rem;
}

/* Slightly reduce big heading spacing */
h1, h2, h3 { margin-top: 0.6rem; margin-bottom: 0.6rem; }

/* Expander polish */
details summary { font-size: 0.92rem; }

/* Hide Streamlit default "Chat input" label spacing (keep input clean) */
[data-testid="stChatInput"] > div { gap: 0.25rem; }

/* Subtle divider line spacing */
hr { margin: 0.5rem 0 0.8rem 0; }
</style>
""",
    unsafe_allow_html=True,
)

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
    docs = project_json.get("documents")
    if isinstance(docs, list) and docs:
        d0 = docs[0]
        if isinstance(d0, dict):
            return str(d0.get("id") or d0.get("document_id") or d0.get("doc_id") or "")
        if isinstance(d0, str):
            return d0

    doc = project_json.get("document")
    if isinstance(doc, dict):
        val = doc.get("id") or doc.get("document_id") or doc.get("doc_id")
        if val:
            return str(val)

    for k in ("document_id", "doc_id"):
        if project_json.get(k):
            return str(project_json[k])

    return None


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
    return "⚙️"


def _safe_float(x, default: float = 0.0) -> float:
    try:
        return float(x)
    except Exception:
        return default


def _safe_int(x, default: int = 0) -> int:
    try:
        return int(x)
    except Exception:
        return default


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
    col1, col2 = st.sidebar.columns(2)
    with col1:
        if st.button("🏠 Home", use_container_width=True, key="nav_home"):
            st.switch_page("pages/0_home.py")
    with col2:
        if st.button("🚪 Logout", use_container_width=True, key="nav_logout"):
            logout()

    st.sidebar.divider()
    st.sidebar.markdown(f"### {project.get('name', 'Project')}")
    st.sidebar.caption(f"ID: {project.get('id')}")
    st.sidebar.divider()


# -----------------------------
# Sidebar: Indexing Status
# -----------------------------
def _sidebar_indexing(latest_status, latest_err, pending_doc_id) -> None:
    st.sidebar.markdown("### Indexing")

    if latest_err:
        st.sidebar.error(latest_err)

    if latest_status:
        status = str(latest_status.get("status") or "unknown")
        progress = _safe_int(latest_status.get("progress"), 0)
        message = latest_status.get("message")
        error = latest_status.get("error")
        cancel_requested = bool(latest_status.get("cancel_requested") or False)

        st.sidebar.markdown(f"**{_status_badge(status)} {status}**")
        st.sidebar.progress(max(0, min(100, progress)) / 100.0)

        if cancel_requested:
            st.sidebar.caption("Cancel requested.")

        if message:
            st.sidebar.info(message)
        if error:
            st.sidebar.error(error)

        c1, c2 = st.sidebar.columns([1, 1], gap="small")
        with c1:
            if st.button("Refresh", use_container_width=True, key="idx_refresh"):
                st.rerun()

        with c2:
            if st.button("Cancel", use_container_width=True, key="idx_cancel"):
                try:
                    api.cancel_indexing(token, index_id=str(latest_status["index_id"]))
                    st.sidebar.warning("Cancel requested.")
                    st.rerun()
                except ApiError as e:
                    st.sidebar.error(str(e))
    else:
        st.sidebar.caption("No indexing status yet.")
        if pending_doc_id:
            if st.sidebar.button("Start indexing", use_container_width=True, key="idx_start"):
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
    if not index_ready:
        st.sidebar.info("Finish indexing to create chats.")
        return

    st.sidebar.markdown("### Chats")

    with st.sidebar.popover("New chat", use_container_width=True):
        with st.form("new_chat_form", clear_on_submit=True):
            chat_title = st.text_input("Title", placeholder="e.g., Chapter 1 questions")
            create_btn = st.form_submit_button("Create", use_container_width=True)

        if create_btn:
            if not chat_title.strip():
                st.error("Title is required.")
            else:
                try:
                    new_chat = api.create_chat(token, project_id=str(project_id), title=chat_title.strip())
                    st.session_state["selected_chat_id"] = new_chat.get("id")
                    st.success("Created.")
                    st.rerun()
                except ApiError as e:
                    st.error(str(e))

    st.sidebar.divider()

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
            icon = "●" if is_selected else "○"
            if st.button(f"{icon} {chat_title_text}", use_container_width=True, key=f"open_chat_{chat_id}"):
                st.session_state["selected_chat_id"] = chat_id
                st.rerun()

        with row[1]:
            with st.popover("⋯", use_container_width=True):
                st.caption(chat_title_text)
                st.warning("Delete is permanent.")
                confirm = st.checkbox("I understand", key=f"del_chat_confirm_{chat_id}")
                if st.button("Delete", use_container_width=True, key=f"delete_chat_{chat_id}", disabled=not confirm):
                    try:
                        api.delete_chat(token, chat_id=chat_id)
                        if st.session_state.get("selected_chat_id") == chat_id:
                            st.session_state.pop("selected_chat_id", None)
                        st.success("Deleted.")
                        st.rerun()
                    except ApiError as e:
                        st.error(str(e))


# -----------------------------
# Sidebar: Chat Settings (keeps main UI clean)
# -----------------------------
def _sidebar_chat_settings() -> None:
    st.sidebar.markdown("### Chat settings")
    st.session_state.setdefault("top_k", 40)
    st.session_state.setdefault("top_n", 10)
    st.session_state.setdefault("rerank_timeout_s", 2)

    st.session_state["top_k"] = st.sidebar.number_input(
        "top_k", min_value=1, max_value=50, value=int(st.session_state["top_k"]), step=1
    )
    st.session_state["top_n"] = st.sidebar.number_input(
        "top_n", min_value=1, max_value=20, value=int(st.session_state["top_n"]), step=1
    )
    st.session_state["rerank_timeout_s"] = st.sidebar.number_input(
        "rerank_timeout_s", min_value=0.0, max_value=20.0, value=float(st.session_state["rerank_timeout_s"]), step=0.1
    )
    st.sidebar.divider()


# -----------------------------
# Indexing (auto-start + polling) - in sidebar
# -----------------------------
auto_start = bool(st.session_state.get("auto_start_indexing"))
pending_doc_id = st.session_state.get("pending_index_document_id")

st.session_state.setdefault("current_index_id", None)

latest_status = None
latest_err = None

if auto_start:
    if not pending_doc_id:
        st.error("auto_start_indexing is True but pending_index_document_id is missing.")
        st.stop()

    try:
        started = api.start_indexing(
            token,
            project_id=str(project_id),
            document_id=str(pending_doc_id),
        )
        st.session_state["current_index_id"] = started["index_id"]
        latest_status = started
        st.toast("Indexing started", icon="⏳")
    except ApiError as e:
        latest_err = str(e)

    st.session_state["auto_start_indexing"] = False

idx = st.session_state.get("current_index_id") or (latest_status or {}).get("index_id")
if idx:
    try:
        latest_status = api.get_index_status(token, index_id=str(idx))
    except ApiError as e:
        latest_err = str(e)
else:
    try:
        latest_status = api.get_latest_index_status(token, project_id=str(project_id))
        st.session_state["current_index_id"] = latest_status.get("index_id")
    except ApiError as e:
        msg = str(e)
        if "No indexes found for project" in msg or "NoIndexesForProject" in msg or msg.startswith("500"):
            latest_status = None
            latest_err = None
        else:
            latest_err = msg

index_ready = False
if latest_status:
    s = str(latest_status.get("status") or "").lower()
    index_ready = s in {"ready", "completed"}

# Sidebar render order
_sidebar_navigation()
_sidebar_indexing(latest_status, latest_err, pending_doc_id)
_sidebar_chats(index_ready)

selected_chat_id = st.session_state.get("selected_chat_id")
if index_ready and selected_chat_id:
    _sidebar_chat_settings()

# -----------------------------
# Main Content: Chat Interface (clean + sticky input)
# -----------------------------
# Clear chat selection when switching projects
if "last_viewed_project" not in st.session_state or st.session_state["last_viewed_project"] != project_id:
    st.session_state["last_viewed_project"] = project_id
    st.session_state.pop("selected_chat_id", None)
    keys_to_remove = [k for k in st.session_state.keys() if k.startswith("chat_messages_")]
    for k in keys_to_remove:
        st.session_state.pop(k, None)
    st.rerun()

selected_chat_id = st.session_state.get("selected_chat_id")

if not index_ready:
    st.info("Indexing is required before chatting.")
    st.stop()

if not selected_chat_id:
    st.info("Select or create a chat from the sidebar.")
    st.stop()

# Load messages for this chat
chat_key = f"chat_messages_{selected_chat_id}"
if chat_key not in st.session_state or st.session_state.get("reload_messages", False):
    try:
        messages_response = api.get_chat_messages(token, chat_id=selected_chat_id, limit=100)
        st.session_state[chat_key] = messages_response.get("items", [])
        st.session_state["reload_messages"] = False
    except ApiError as e:
        st.error(f"Failed to load messages: {e}")
        st.session_state[chat_key] = []

messages = st.session_state[chat_key]

# Render conversation
for msg in messages:
    role = msg.get("role", "assistant")
    content = msg.get("content", "")

    if role == "user":
        with st.chat_message("user", avatar="🧑‍💻"):
            st.markdown(content)
    else:
        with st.chat_message("assistant", avatar="🤖"):
            st.markdown(content)

            # Metrics + citations live under each assistant message, collapsed by default
            metrics_data = msg.get("metrics") or {}
            citations_data = msg.get("citations") or {}

            has_metrics = bool(metrics_data)
            has_citations = bool(citations_data.get("chunks"))

            if has_metrics or has_citations:
                label_bits = []
                if has_metrics:
                    tokens = metrics_data.get("tokens", {})
                    latency = metrics_data.get("latency", {})
                    total_tokens = _safe_int(tokens.get("total"), 0)
                    total_latency = _safe_float(latency.get("total"), 0.0)
                    label_bits.append(f"{total_tokens:,} tok")
                    label_bits.append(f"{total_latency:.2f}s")

                if has_citations:
                    label_bits.append(f"{len(citations_data.get('chunks', []))} sources")

                exp_label = " · ".join(label_bits) if label_bits else "Details"

                with st.expander(exp_label, expanded=False):
                    if has_metrics:
                        tokens = metrics_data.get("tokens", {})
                        prompt = (tokens.get("prompt") or {})
                        latency = (metrics_data.get("latency") or {})

                        st.markdown("**Token usage**")
                        c1, c2 = st.columns(2)
                        with c1:
                            st.caption(f"System: {prompt.get('system', 0):,}")
                            st.caption(f"History: {prompt.get('history', 0):,}")
                            st.caption(f"Rewritten Q: {prompt.get('rewritten_question', 0):,}")
                            st.caption(f"Context: {prompt.get('context', 0):,}")
                            st.caption(f"Question: {prompt.get('question', 0):,}")
                            st.caption(f"Prompt total: {prompt.get('total', 0):,}")
                        with c2:
                            st.caption(f"Completion: {tokens.get('completion', 0):,}")
                            st.caption(f"Total: {tokens.get('total', 0):,}")

                        st.divider()
                        st.markdown("**Latency (s)**")
                        c1, c2, c3, c4 = st.columns(4)
                        with c1:
                            v = latency.get("query_rewriting")
                            st.metric("Rewrite", f"{v:.2f}" if v is not None else "N/A")
                        with c2:
                            v = latency.get("retrieval")
                            st.metric("Retrieval", f"{v:.2f}" if v is not None else "N/A")
                        with c3:
                            v = latency.get("reply_generation")
                            st.metric("Generate", f"{v:.2f}" if v is not None else "N/A")
                        with c4:
                            v = latency.get("total")
                            st.metric("Total", f"{v:.2f}" if v is not None else "N/A")

                    if has_citations:
                        st.divider()
                        rewritten_queries = citations_data.get("rewritten_queries") or []
                        if isinstance(rewritten_queries, str):
                            rewritten_queries = [rewritten_queries]
                        single_rewrite = citations_data.get("rewritten_query")
                        original_query = citations_data.get("original_query")

                        queries_to_show = rewritten_queries or ([single_rewrite] if single_rewrite else [])
                        if not queries_to_show and original_query:
                            queries_to_show = [original_query]

                        if queries_to_show:
                            st.markdown("**Retrieval queries**")
                            for i, rq in enumerate(queries_to_show, 1):
                                st.caption(f"{i}. {rq}")
                            strategy = citations_data.get("rewrite_strategy")
                            if strategy:
                                st.caption(f"Strategy: {strategy}")

                        st.divider()
                        meta1, meta2, meta3 = st.columns(3)
                        with meta1:
                            st.caption(f"Model: {citations_data.get('model', 'N/A')}")
                        with meta2:
                            st.caption(f"Top-k: {citations_data.get('top_k', 'N/A')}")
                        with meta3:
                            st.caption(f"Metric: {citations_data.get('metric', 'N/A')}")

                        st.divider()
                        for idx_src, chunk in enumerate(citations_data.get("chunks", []), 1):
                            citation = chunk.get("citation", {}) or {}
                            score = chunk.get("score")
                            chunk_text = chunk.get("content") or ""

                            score_text = f" · {score:.3f}" if score is not None else ""
                            st.markdown(f"**Source {idx_src}{score_text}**")
                            if chunk_text:
                                st.markdown(chunk_text)

                            if citation:
                                items = []
                                for k, v in citation.items():
                                    items.append(f"{k}: {v}")
                                st.caption(" | ".join(items))

                            if idx_src < len(citations_data.get("chunks", [])):
                                st.divider()

# -----------------------------
# Sticky bottom input (Streamlit-native)
# -----------------------------
q = st.chat_input("Ask a question…")
if q:
    q = q.strip()
    if not q:
        st.warning("Type a question first.")
        st.stop()

    # Show the user message immediately
    with st.chat_message("user", avatar="🧑‍💻"):
        st.markdown(q)

    # Stream assistant response
    with st.chat_message("assistant", avatar="🤖"):
        placeholder = st.empty()
        acc: list[str] = []

        try:
            top_k = int(st.session_state.get("top_k", 10))
            top_n = int(st.session_state.get("top_n", 5))
            rerank_timeout_s = float(st.session_state.get("rerank_timeout_s", 0.6))

            for chunk in api.query_project_stream(
                token,
                project_id=str(project_id),
                chat_id=str(selected_chat_id),
                query=q,
                top_k=top_k,
                top_n=top_n,
                rerank_timeout_s=rerank_timeout_s,
            ):
                acc.append(chunk)
                placeholder.markdown("".join(acc) + "▌")

            placeholder.markdown("".join(acc))

            st.session_state["reload_messages"] = True
            st.rerun()

        except ApiError as e:
            st.error(str(e))
