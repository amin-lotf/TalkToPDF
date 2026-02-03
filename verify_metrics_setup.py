#!/usr/bin/env python3
"""
Script to verify metrics setup is complete.
Run this to check if all components are properly configured.
"""
import sys
import asyncio
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))


async def main():
    print("=" * 60)
    print("METRICS SETUP VERIFICATION")
    print("=" * 60)

    # 1. Check imports
    print("\n1. Checking imports...")
    try:
        from talk_to_pdf.backend.app.domain.reply.metrics import ReplyMetrics, TokenMetrics, LatencyMetrics
        print("   ✓ Domain metrics classes imported successfully")
    except ImportError as e:
        print(f"   ✗ Failed to import domain metrics: {e}")
        return False

    try:
        from talk_to_pdf.backend.app.infrastructure.common.token_counter import count_tokens, count_message_tokens
        print("   ✓ Token counter imported successfully")
    except ImportError as e:
        print(f"   ✗ Failed to import token counter: {e}")
        return False

    # 2. Check tiktoken
    print("\n2. Checking tiktoken...")
    try:
        import tiktoken
        enc = tiktoken.encoding_for_model("gpt-4")
        test_count = len(enc.encode("Hello, world!"))
        print(f"   ✓ tiktoken working (test: 'Hello, world!' = {test_count} tokens)")
    except Exception as e:
        print(f"   ✗ tiktoken error: {e}")
        print("   → Run: uv pip install tiktoken")
        return False

    # 3. Check database model
    print("\n3. Checking database model...")
    try:
        from talk_to_pdf.backend.app.infrastructure.db.models.reply import ChatMessageModel
        columns = [col.key for col in ChatMessageModel.__table__.columns]
        if 'metrics' in columns:
            print("   ✓ ChatMessageModel has 'metrics' column")
        else:
            print("   ✗ ChatMessageModel missing 'metrics' column")
            print(f"   Available columns: {columns}")
            print("   → Run: uv run alembic upgrade head")
            return False
    except Exception as e:
        print(f"   ✗ Failed to check model: {e}")
        return False

    # 4. Test token counting
    print("\n4. Testing token counting...")
    try:
        from talk_to_pdf.backend.app.infrastructure.common.token_counter import count_tokens
        test_text = "This is a test message for token counting."
        tokens = count_tokens(test_text, model="gpt-4")
        print(f"   ✓ Token counting works: '{test_text}' = {tokens} tokens")
    except Exception as e:
        print(f"   ✗ Token counting failed: {e}")
        return False

    # 5. Test metrics serialization
    print("\n5. Testing metrics serialization...")
    try:
        metrics = ReplyMetrics(
            prompt_tokens=TokenMetrics(
                system=120,
                history=640,
                rewritten_question=100,
                context=1800,
                question=90,
            ),
            completion_tokens=340,
            latency=LatencyMetrics(
                retrieval=1.25,
                reply_generation=2.34,
            ),
        )
        metrics_dict = metrics.to_dict()
        print(f"   ✓ Metrics serialization works")
        print(f"     - Total tokens: {metrics.total_tokens}")
        print(f"     - Total latency: {metrics.latency.total:.2f}s")

        # Test deserialization
        restored = ReplyMetrics.from_dict(metrics_dict)
        assert restored.total_tokens == metrics.total_tokens
        print(f"   ✓ Metrics deserialization works")
    except Exception as e:
        print(f"   ✗ Metrics serialization failed: {e}")
        return False

    # 6. Check API schema
    print("\n6. Checking API schema...")
    try:
        from talk_to_pdf.backend.app.api.v1.reply.schemas import MessageResponse
        fields = list(MessageResponse.model_fields.keys())
        if 'metrics' in fields:
            print("   ✓ MessageResponse has 'metrics' field")
            print(f"     Fields: {fields}")
        else:
            print("   ✗ MessageResponse missing 'metrics' field")
            print(f"     Available fields: {fields}")
            return False
    except Exception as e:
        print(f"   ✗ Failed to check API schema: {e}")
        return False

    print("\n" + "=" * 60)
    print("✓ ALL CHECKS PASSED!")
    print("=" * 60)
    print("\nMetrics tracking is properly configured.")
    print("\nNext steps:")
    print("1. If you haven't run the migration: uv run alembic upgrade head")
    print("2. Start/restart your backend server")
    print("3. Ask a new question in a chat")
    print("4. Check the assistant response for the metrics expander")
    print("\nNote: Only NEW messages will have metrics.")
    print("Old messages created before this update won't have metrics.")
    return True


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
