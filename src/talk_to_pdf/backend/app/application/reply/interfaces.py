from typing import Protocol, AsyncIterator

from talk_to_pdf.backend.app.domain.reply.value_objects import GenerateReplyInput


class ReplyGenerator(Protocol):
    async def stream_answer(self, inp: GenerateReplyInput) -> AsyncIterator[str]:...
