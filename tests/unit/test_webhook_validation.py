import pytest

from atlasqueue.infrastructure.http.webhook_client import (
    WebhookValidationError,
    validate_webhook_url,
)
from atlasqueue.shared.config import Settings


def test_block_private_webhook_urls() -> None:
    settings = Settings(BLOCK_PRIVATE_WEBHOOK_URLS=True)
    with pytest.raises(WebhookValidationError):
        validate_webhook_url("http://localhost/hook", settings)
    with pytest.raises(WebhookValidationError):
        validate_webhook_url("http://192.168.1.1/hook", settings)


def test_allow_public_webhook_urls() -> None:
    settings = Settings(BLOCK_PRIVATE_WEBHOOK_URLS=True)
    validate_webhook_url("https://example.com/hook", settings)


def test_allow_private_when_disabled() -> None:
    settings = Settings(BLOCK_PRIVATE_WEBHOOK_URLS=False)
    validate_webhook_url("http://localhost/hook", settings)
