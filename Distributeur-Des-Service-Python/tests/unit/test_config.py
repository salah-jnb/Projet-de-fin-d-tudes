import pytest
from src.config.config import Settings

def test_env_variables_load():
    settings = Settings()
    # Vérifie que les variables ne sont pas vides
    assert settings.SUPABASE_URL is not None
    assert "supabase.co" in settings.SUPABASE_URL
    assert settings.N8N_URL is not None