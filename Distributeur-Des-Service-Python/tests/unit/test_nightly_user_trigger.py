"""Tests du déclencheur nocturne (webhook n8n par utilisateur)."""

from unittest.mock import MagicMock, patch

import pytest

from src.application.app_service_impl import ApiServiceImpl


@pytest.fixture
def service_with_users():
    svc = ApiServiceImpl.__new__(ApiServiceImpl)
    mock_client = MagicMock()
    mock_client.table.return_value.select.return_value.execute.return_value.data = [
        {"iduser": 1, "nom": "oussema"},
        {"iduser": 2, "nom": "salah"},
        {"iduser": 3, "nom": ""},
    ]
    svc.client = mock_client
    return svc


@patch("src.application.app_service_impl.httpx.post")
@patch("src.application.app_service_impl.settings")
def test_run_nightly_user_webhook_trigger_calls_each_user(mock_settings, mock_post, service_with_users):
    mock_settings.NIGHTLY_USER_WEBHOOK_URL = (
        "http://localhost:5678/webhook/60fca303-14f2-4922-ab8e-764566b57e85"
    )
    mock_settings.NIGHTLY_USER_WEBHOOK_TIMEOUT_S = 30

    mock_response = MagicMock()
    mock_response.is_success = True
    mock_response.status_code = 200
    mock_response.text = "ok"
    mock_post.return_value = mock_response

    result = service_with_users.run_nightly_user_webhook_trigger()

    assert result["status"] == "completed"
    assert result["users_total"] == 3
    assert result["users_processed"] == 2
    assert result["success_count"] == 2
    assert result["skipped_count"] == 1
    assert mock_post.call_count == 2

    calls = mock_post.call_args_list
    assert calls[0].kwargs["params"] == {"user": "oussema"}
    assert calls[0].kwargs["json"] == {"user": "oussema"}
    assert calls[1].kwargs["params"] == {"user": "salah"}
    assert calls[1].kwargs["json"] == {"user": "salah"}


@patch("src.application.app_service_impl.settings")
def test_run_nightly_user_webhook_trigger_missing_url(mock_settings, service_with_users):
    mock_settings.NIGHTLY_USER_WEBHOOK_URL = ""
    with pytest.raises(RuntimeError, match="NIGHTLY_USER_WEBHOOK_URL"):
        service_with_users.run_nightly_user_webhook_trigger()
