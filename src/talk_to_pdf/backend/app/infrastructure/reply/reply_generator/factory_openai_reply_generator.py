from dataclasses import dataclass
from langchain_openai import ChatOpenAI

from talk_to_pdf.backend.app.domain.common.value_objects import ReplyGenerationConfig
from talk_to_pdf.backend.app.infrastructure.reply.reply_generator.openai_reply_generator import OpenAIReplyGenerator


@dataclass(frozen=True, slots=True)
class OpenAILlmReplyGeneratorFactory:
    api_key: str

    def create(self, cfg: ReplyGenerationConfig) -> OpenAIReplyGenerator:
        llm = ChatOpenAI(
            model=cfg.model,
            temperature=cfg.temperature,
            api_key=self.api_key,
        )
        return OpenAIReplyGenerator(llm=llm, cfg=cfg)
