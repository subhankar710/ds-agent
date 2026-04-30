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
    