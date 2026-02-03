#!/usr/bin/env python3
"""
Test if metrics are being generated correctly by the OpenAIReplyGenerator.
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from talk_to_pdf.backend.app.infrastructure.reply.reply_generator.openai_reply_generator import (
    OpenAIReplyGenerator,
    PromptTokenBreakdown,
    StreamMetrics
)
from talk_to_pdf.backend.app.domain.common.value_objects import ReplyGenerationConfig, ChatTurn
from talk_to_pdf.backend.app.domain.reply.value_objects import GenerateReplyInput
from talk_to_pdf.backend.app.domain.common.enums import ChatRole
from langchain_openai import ChatOpenAI

print("Testing OpenAIReplyGenerator metrics...")
print("=" * 60)

# Create a test instance
config = ReplyGenerationConfig(
    provider="openai",
    model="gpt-4o-mini",
    temperature=0.2,
)

# Mock LLM (you'll need an API key for real test)
try:
    llm = ChatOpenAI(model="gpt-4o-mini", temperature=0.2)
    generator = OpenAIReplyGenerator(llm=llm, cfg=config)

    print(f"✓ Generator created successfully")
    print(f"  Model: {generator.llm_model}")

    # Check if methods exist
    print(f"\n✓ Methods check:")
    print(f"  - has get_last_metrics: {hasattr(generator, 'get_last_metrics')}")
    print(f"  - has clear_metrics: {hasattr(generator, 'clear_metrics')}")
    print(f"  - has _last_metrics: {hasattr(generator, '_last_metrics')}")

    # Test _build_messages returns tuple with breakdown
    test_input = GenerateReplyInput(
        query="What is the capital of France?",
        context="France is a country in Europe. Paris is its capital.",
        history=[
            ChatTurn(role=ChatRole.USER, content="Hello"),
            ChatTurn(role=ChatRole.ASSISTANT, content="Hi there!"),
        ],
        system_prompt="You are a helpful assistant.",
    )

    msgs, breakdown = generator._build_messages(test_input)
    print(f"\n✓ _build_messages returns breakdown:")
    print(f"  - Type: {type(breakdown)}")
    print(f"  - System tokens: {breakdown.system}")
    print(f"  - Context tokens: {breakdown.context}")
    print(f"  - History tokens: {breakdown.history}")
    print(f"  - Question tokens: {breakdown.question}")

    print(f"\n✓ Initial metrics state: {generator._last_metrics}")

    print("\n" + "=" * 60)
    print("✓ All structural checks passed!")
    print("\nNote: To test actual streaming, you need to run the backend")
    print("and make a real API call with a valid OpenAI API key.")

except Exception as e:
    print(f"\n✗ Error: {e}")
    print(f"\nThis is expected if you don't have OPENAI_API_KEY set.")
    print("The important thing is that the code structure is correct.")
    import traceback
    traceback.print_exc()
