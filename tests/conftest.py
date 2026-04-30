import pytest
from unittest.mock import MagicMock

from ds_agent.config import Settings
from ds_agent.llm import LLMClient

@pytest.fixture
def fake_settings() -> Settings:
    """A Settings object with a fake API key and no .env loading."""
    return Settings(anthropic_api_key="sk-ant-test-fake", _env_file=None)

@pytest.fixture
def mock_llm_client(fake_settings) -> MagicMock:
    """A MagicMock pretending to be LLMClient. Set .complete.return_value as needed."""
    mock = MagicMock(spec=LLMClient)
    mock.complete.return_value = "default mocked response"
    return mock

