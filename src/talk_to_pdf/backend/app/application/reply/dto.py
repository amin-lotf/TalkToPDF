from dataclasses import dataclass
from uuid import UUID

from talk_to_pdf.backend.app.application.common.dto import ContextPackDTO


@dataclass
class ReplyInputDTO:
    project_id: UUID
    owner_id: UUID
    query: str
    top_k: int
    top_n: int
    rerank_timeout_s: float


@dataclass
class ReplyOutputDTO:
    query: str
    context: ContextPackDTO
    answer: str