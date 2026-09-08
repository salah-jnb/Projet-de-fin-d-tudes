import pytest
import requests_mock
from src.infrastructure.n8n_client import N8NClient


def test_send_to_workflow_success():
    client = N8NClient()
    url = "https://your-n8n-instance.com/webhook/your-id"  # Doit correspondre à ton .env

    with requests_mock.Mocker() as m:
        # On simule une réponse positive de n8n
        m.post(url, json={"output": "Bonjour Oussema !"}, status_code=200)

        response = client.send_to_workflow("Salut", "user_123")

        assert response["output"] == "Bonjour Oussema !"
        assert m.called_once


def test_send_to_workflow_error():
    client = N8NClient()
    with requests_mock.Mocker() as m:
        # On simule une erreur serveur
        m.post(requests_mock.ANY, status_code=500)

        response = client.send_to_workflow("Salut", "user_123")
        assert response is None