# -----------------------------
# Mappers (domain <-> db model)
# -----------------------------
from talk_to_pdf.backend.app.domain.reply import ChatMessage, Chat
from talk_to_pdf.backend.app.infrastructure.db.models.reply import ChatMessageModel, ChatModel


def chat_domain_to_model(chat: Chat) -> ChatModel:
    """
    Minimal, explicit mapping. Adjust fields to match your real Chat entity.
    """
    return ChatModel(
        id=chat.id,
        project_id=chat.project_id,
        owner_id=chat.owner_id,
        title=chat.title,
        created_at=chat.created_at,
        updated_at=chat.updated_at,
        # If you store extra JSON/meta on chat:
        # meta=chat.meta,
    )


def chat_model_to_domain(m: ChatModel) -> Chat:
    """
    Adjust to match your Chat entity constructor/fields.
    """
    return Chat(
        id=m.id,
        project_id=m.project_id,
        owner_id=m.owner_id,
        title=m.title,
        created_at=m.created_at,
        updated_at=m.updated_at,
        # meta=m.meta,
    )


def message_domain_to_model(msg: ChatMessage) -> ChatMessageModel:
    """
    Adjust fields to match your real ChatMessage entity.
    Common fields: role, content, created_at, token counts, citations, etc.
    """
    return ChatMessageModel(
        id=msg.id,
        chat_id=msg.chat_id,

        role=msg.role,
        content=msg.content,
        created_at=msg.created_at,
        # Optional extras:
        # meta=msg.meta,
        # citations=msg.citations,
    )


def message_model_to_domain(m: ChatMessageModel) -> ChatMessage:
    return ChatMessage(
        id=m.id,
        chat_id=m.chat_id,
        role=m.role,
        content=m.content,
        created_at=m.created_at,
        # meta=m.meta,
        # citations=m.citations,
    )
