import pytest

from ds_agent.llm import LLMClient

def test_complete_returns_text_when_mocked(fake_settings, monkeypatch):
    """Tests that complete() correctly calls the SDK and extracts the text."""
    from unittest.mock import MagicMock

    # Step 1: Build a fake response object
    fake_response = MagicMock()
    fake_response.content = [MagicMock(text="ahoy matey")]

    # Step 2: Build a fake Anthropic client
    fake_anthropic_client = MagicMock()
    fake_anthropic_client.messages.create.return_value = fake_response

    # Step 4: Construct an LLMClient and swap its real Anthropic client for the fake
    client = LLMClient(fake_settings)
    monkeypatch.setattr(client, "_client", fake_anthropic_client)

    # Step 5: Call complete() and assert
    result = client.complete("say hello in pirate")

    # Assertion A — return value
    assert result == "ahoy matey"

    # Assertion B — what we sent to the SDK
    fake_anthropic_client.messages.create.assert_called_once()
    call_kwargs = fake_anthropic_client.messages.create.call_args.kwargs
    assert call_kwargs["model"] == "claude-sonnet-4-6"
    assert call_kwargs["messages"] == [{"role": "user", "content": "say hello in pirate"}]

def test_complete_rejects_empty_user_message(fake_settings):
    """Tests that complete() raises a ValueError if user_message is empty or just whitespace."""
    client = LLMClient(fake_settings)

    with pytest.raises(ValueError):
        client.complete("   ")
    with pytest.raises(ValueError):
        client.complete("")

def test_complete_passes_system_prompt_when_provided(fake_settings, monkeypatch):
    """verifies that calling client.complete("hello", system="be terse") results in the SDK call having system="be terse" in its kwargs."""
    from unittest.mock import MagicMock

    fake_response = MagicMock()
    fake_response.content = [MagicMock(text="hi")]
    fake_anthropic_client = MagicMock()
    fake_anthropic_client.messages.create.return_value = fake_response

    client = LLMClient(fake_settings)
    monkeypatch.setattr(client, "_client", fake_anthropic_client)

    result = client.complete("hello", system="be terse")

    assert result == "hi"
    fake_anthropic_client.messages.create.assert_called_once()
    call_kwargs = fake_anthropic_client.messages.create.call_args.kwargs
    assert call_kwargs["system"] == "be terse"


def test_chat_returns_sdk_message_object_with_tool_use(fake_settings, monkeypatch):
    """chat() must return the SDK Message unchanged so the agent loop can read
    stop_reason and iterate over content blocks (incl. tool_use blocks)."""
    from unittest.mock import MagicMock

    # Fake a tool_use response: stop_reason="tool_use", content has a tool_use block.
    fake_tool_use_block = MagicMock(
        type="tool_use",
        id="toolu_test_123",
        name="run_sql",
        input={"sql": "SELECT 1"},
    )
    fake_response = MagicMock(stop_reason="tool_use", content=[fake_tool_use_block])

    fake_anthropic_client = MagicMock()
    fake_anthropic_client.messages.create.return_value = fake_response

    client = LLMClient(fake_settings)
    monkeypatch.setattr(client, "_client", fake_anthropic_client)

    tools = [
        {
            "name": "run_sql",
            "description": "Run a SQL query.",
            "input_schema": {
                "type": "object",
                "properties": {"sql": {"type": "string"}},
                "required": ["sql"],
            },
        }
    ]
    messages = [{"role": "user", "content": "How many orders?"}]

    result = client.chat(messages=messages, tools=tools, system="be terse")

    # Returned the SDK object as-is (no transformation).
    assert result is fake_response
    assert result.stop_reason == "tool_use"

    # SDK was called with the right kwargs.
    fake_anthropic_client.messages.create.assert_called_once()
    call_kwargs = fake_anthropic_client.messages.create.call_args.kwargs
    assert call_kwargs["model"] == "claude-sonnet-4-6"
    assert call_kwargs["messages"] == messages
    assert call_kwargs["tools"] == tools
    assert call_kwargs["system"] == "be terse"
