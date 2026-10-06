#
# * This test file focuses on the /webhook endpoint, which is the entry point for GitHub webhook events. The tests cover various scenarios related to signature verification, event type handling, and action handling.
import hmac
import json
from hashlib import sha256

from app.config import settings
from unittest.mock import AsyncMock

WEBHOOK_SECRET = settings.webhook_secret.encode()

# uv run pytest
# uv run ruff check .


def make_signature(body_bytes: bytes) -> str:
    """Compute the HMAC-SHA256 signature for a given body, the same way GitHub does."""
    return (
        "sha256="
        + hmac.new(
            key=WEBHOOK_SECRET,
            msg=body_bytes,
            digestmod=sha256,
        ).hexdigest()
    )


# ---------------------------------------------------------------------------- #
# 1. No signature header - 401
def test_missing_signature(client_empty_db):
    # Arrange: no setup needed
    # Act: POST with no headers
    response = client_empty_db.post("/webhook")
    # Assert: 401 Unauthorized
    assert response.status_code == 401


# 2. Invalid signature format - 403
# Doesn't start with "sha256="
def test_invalid_signature_format(client_empty_db):
    # Arrange: create a signature that doesn't start with "sha256="
    headers = {"X-Hub-Signature-256": "invalidsignature"}
    # Act: POST with invalid signature format
    response = client_empty_db.post("/webhook", headers=headers)
    # Assert: 403 Forbidden
    assert response.status_code == 403


# 3. Invalid signature - 403
def test_invalid_signature(client_empty_db):
    # Arrange: create a signature with correct format but wrong value
    headers = {"X-Hub-Signature-256": "sha256=invalidsignature"}
    # Act: POST with invalid signature
    response = client_empty_db.post("/webhook", headers=headers)
    # Assert: 403 Forbidden
    assert response.status_code == 403


# 4. Unsupported event type - 200 with ignored status
def test_unsupported_event_type(client_empty_db):
    # Arrange: sign an empty body (no json payload sent)
    body_bytes = b""
    headers = {
        "X-Hub-Signature-256": make_signature(body_bytes),
        "X-GitHub-Event": "issues",  # Not pull_request
    }
    # Act: POST with unsupported event type
    response = client_empty_db.post("/webhook", headers=headers, content=body_bytes)
    # Assert: 200 OK with ignored status
    assert response.status_code == 200
    assert response.json()["status"] == "ignored"


# 5. Unsupported action - 200 with ignored status
def test_unsupported_action(client_empty_db):
    # Arrange: sign the exact bytes we'll send
    body = {"action": "closed"}
    body_bytes = json.dumps(body).encode()
    headers = {
        "X-Hub-Signature-256": make_signature(body_bytes),
        "X-GitHub-Event": "pull_request",
    }
    # Act: POST with unsupported action (e.g., "closed")
    response = client_empty_db.post("/webhook", headers=headers, content=body_bytes)
    # Assert: 200 OK with ignored status
    assert response.status_code == 200
    assert response.json()["status"] == "ignored"


# 6. Valid request - 200 with received status
def test_valid_request(client_empty_db, monkeypatch):
    run_mock = AsyncMock()
    monkeypatch.setattr("app.routers.webhook.run_analysis", run_mock)

    # Arrange: build a full PR body matching what GitHub sends, then sign it
    body = {
        "action": "opened",
        "repository": {"full_name": "test-org/test-repo"},
        "pull_request": {"number": 1},
    }
    body_bytes = json.dumps(body).encode()
    headers = {
        "X-Hub-Signature-256": make_signature(body_bytes),
        "X-GitHub-Event": "pull_request",
        "X-GitHub-Delivery": "test-delivery-id",
    }
    # Act: POST with valid request
    response = client_empty_db.post("/webhook", headers=headers, content=body_bytes)
    # Assert: 200 OK with received status
    assert response.status_code == 200
    assert response.json()["status"] == "received"
    run_mock.assert_awaited_once_with(1, "test-org/test-repo", 1)


# 7. Duplicate request - 200 and unique
def test_duplicate_delivery(client_duplicate_delivery, monkeypatch):
    run_mock = AsyncMock()
    monkeypatch.setattr("app.routers.webhook.run_analysis", run_mock)

    # Arrange: build a full PR body matching what GitHub sends, then sign it
    body = {
        "action": "opened",
        "repository": {"full_name": "test-org/test-repo"},
        "pull_request": {"number": 1},
    }
    body_bytes = json.dumps(body).encode()
    headers = {
        "X-Hub-Signature-256": make_signature(body_bytes),
        "X-GitHub-Event": "pull_request",
        "X-GitHub-Delivery": "test-delivery-id",
    }
    # Act: POST with valid request
    response = client_duplicate_delivery.post(
        "/webhook", headers=headers, content=body_bytes
    )
    # Assert: 200 OK with received status
    assert response.json() == {"status": "ignored", "reason": "Duplicate delivery"}
    run_mock.assert_not_awaited()
