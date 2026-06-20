import pytest
from unittest.mock import patch, MagicMock
from backend.ai_service import AIService


def test_ai_service_init():
    """Test that AIService initializes with environment variables."""
    service = AIService(api_key="test-key", base_url="https://test.com")
    assert service.api_key == "test-key"
    assert service.base_url == "https://test.com"
    assert service.is_configured()


def test_ai_service_not_configured():
    """Test that AIService detects missing API key."""
    service = AIService(api_key=None)
    # Clear env var if it exists
    import os
    old_key = os.environ.get("OPENROUTER_API_KEY")
    if "OPENROUTER_API_KEY" in os.environ:
        del os.environ["OPENROUTER_API_KEY"]
    
    service = AIService()
    assert not service.is_configured()
    
    # Restore env var
    if old_key:
        os.environ["OPENROUTER_API_KEY"] = old_key


def test_ai_service_call_ai_not_configured():
    """Test that call_ai raises error when not configured."""
    service = AIService(api_key=None)
    with pytest.raises(ValueError, match="OPENROUTER_API_KEY is not set"):
        service.call_ai("test prompt")


@patch("backend.ai_service.httpx.post")
def test_ai_service_call_ai_success(mock_post):
    """Test successful AI API call."""
    mock_response = MagicMock()
    mock_response.json.return_value = {
        "choices": [{"message": {"content": "Hello, I'm an AI!"}}]
    }
    mock_post.return_value = mock_response

    service = AIService(api_key="test-key")
    result = service.call_ai("Hello")

    assert result == "Hello, I'm an AI!"
    mock_post.assert_called_once()


@patch("backend.ai_service.httpx.post")
def test_ai_service_test_connectivity_success(mock_post):
    """Test AI connectivity test."""
    mock_response = MagicMock()
    mock_response.json.return_value = {
        "choices": [{"message": {"content": "4"}}]
    }
    mock_post.return_value = mock_response

    service = AIService(api_key="test-key")
    result = service.test_connectivity()

    assert result["status"] == "success"
    assert result["result"] == "4"
    assert "model" in result


@patch("backend.ai_service.httpx.post")
def test_ai_service_test_connectivity_error(mock_post):
    """Test AI connectivity test with error."""
    mock_post.side_effect = Exception("Network error")

    service = AIService(api_key="test-key")
    result = service.test_connectivity()

    assert result["status"] == "error"
    assert "error" in result
    assert "model" in result
