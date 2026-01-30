# -----------------------------
# Mappers (domain <-> db model)
# -----------------------------
from talk_to_pdf.backend.app.domain.reply import ChatMessage, Chat
from talk_to_pdf.backend.app.domain.reply.value_objects import ChatMessageCitations, CitedChunk
from talk_to_pdf.backend.app.domain.common.enums import VectorMetric
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
    citations_dict = None
    if msg.citations:
        citations_dict = {
            "index_id": str(msg.citations.index_id),
            "embed_signature": msg.citations.embed_signature,
            "metric": msg.citations.metric if isinstance(msg.citations.metric, str) else msg.citations.metric.value,
            "chunks": [
                {
                    "chunk_id": str(chunk.chunk_id),
                    "score": chunk.score,
                    "citation": chunk.citation,
                }
                for chunk in msg.citations.chunks
            ],
            "top_k": msg.citations.top_k,
            "rerank_signature": msg.citations.rerank_signature,
            "prompt_version": msg.citations.prompt_version,
            "model": msg.citations.model,
        }

    return ChatMessageModel(
        id=msg.id,
        chat_id=msg.chat_id,
        role=msg.role,
        content=msg.content,
        created_at=msg.created_at,
        citations=citations_dict,
    )


def message_model_to_domain(m: ChatMessageModel) -> ChatMessage:
    citations = None
    if m.citations:
        from uuid import UUID
        citations = ChatMessageCitations(
            index_id=UUID(m.citations["index_id"]),
            embed_signature=m.citations["embed_signature"],
            metric=VectorMetric(m.citations["metric"]) if m.citations["metric"] in [e.value for e in VectorMetric] else m.citations["metric"],
            chunks=[
                CitedChunk(
                    chunk_id=UUID(chunk["chunk_id"]),
                    score=chunk["score"],
                    citation=chunk["citation"],
                )
                for chunk in m.citations.get("chunks", [])
            ],
            top_k=m.citations["top_k"],
            rerank_signature=m.citations.get("rerank_signature"),
            prompt_version=m.citations.get("prompt_version"),
            model=m.citations.get("model"),
        )

    return ChatMessage(
        id=m.id,
        chat_id=m.chat_id,
        role=m.role,
        content=m.content,
        created_at=m.created_at,
        citations=citations,
    )
